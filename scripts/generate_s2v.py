#!/usr/bin/env python3
"""
Speech/Sound-to-Video (SI2V) multi-backend.

Backends:
  - ltx23_aio* / ltx23_ia2v: real LTX 2.3 All-in-One UI workflow + [[P:]] mode switches
  - infinitetalk: Wan Multi/InfiniteTalk (WanVideoWrapper)

LTX path (default):
  workflows/human/ltx23AllInOneWorkflowForRTX_v44(_IA2V).json
  → apply_aio_mode_to_ui_workflow (Orchestrator mute table)
  → expand_ui_workflow_to_api → inject Trim/clip/edge/aspect/seed

Emergency only:
  AGENT_LTX_FORCE_MINI_GRAPH=1 → legacy homemade mini graphs (not preferred)
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    ok_result,
    resolve_meta_out,
    utc_now_iso,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine, family_for_s2v_backend
from lib.ffmpeg_util import normalize_clip_audio, replace_clip_audio
from lib.ltx_aio_live_template import (
    build_ia2v_live_api,
    is_live_template_available,
)
from lib.ltx_aio_workflow_runner import build_aio_switched_api
from lib.ltx_s2v import (
    AIO_DISTILL_LORA,
    AIO_DISTILL_LORA_STRENGTH,
    AIO_MODES,
    BACKEND_TO_AIO_MODE,
    DEFAULT_DISTILL_LORA,
    DEFAULT_GEMMA,
    DEFAULT_UNET_GGUF,
    aio_profile_defaults,
    build_ltx_aio_mode_api,
    build_ltx_custom_audio_api,
    is_ltx_backend,
    resolve_aio_mode,
    snap_ltx_dim,
    snap_ltx_frames,
)
from lib.s2v_length_contract import (
    apply_frame_cap,
    default_tail_sec,
    frames_from_duration,
)


def _api_for_comfy(api: dict) -> dict:
    """Strip non-Comfy keys (_meta, mode) before /prompt."""
    clean: dict = {}
    for nid, node in api.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type")
        if not ct:
            continue
        clean[str(nid)] = {
            "class_type": ct,
            "inputs": dict(node.get("inputs") or {}),
        }
    return clean

S2V_BACKENDS = (
    "infinitetalk",
    "ltx23_ia2v",
    "ltx23_aio",
    "ltx23_aio_i2v",
    "ltx23_aio_flf",
    "ltx23_aio_flf_audio",
    "ltx23_aio_fml",
    "ltx23_aio_fml_audio",
    "ltx23_aio_v2v",
    "ltx23_aio_v2v_audio",
    "ltx23_aio_t2v",
    "ltx23_aio_t2v_audio",
)

COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"

DEFAULT_NEG = (
    "bright tones, overexposed, static, blurred details, subtitles, watermark, "
    "ugly, deformed, extra fingers, still picture, morphing face, identity shift"
)

# Model paths relative to Comfy models folders
DEFAULT_I2V = r"Wan2.1\wan2.1-i2v-14b-720p-Q4_K_M.gguf"
DEFAULT_MULTITALK = r"Wan2.1\Wan2_1-InfiniTetalk-Single_fp16.safetensors"
DEFAULT_WAV2VEC = "TencentGameMate/chinese-wav2vec2-base"
DEFAULT_VAE = "wan_2.1_vae.safetensors"
DEFAULT_CLIP_VISION = "clip_vision_h.safetensors"
DEFAULT_T5 = "umt5-xxl-enc-bf16.safetensors"
# Distill LoRA: 4–8 step InfiniteTalk (Comfy models/loras/...)
DEFAULT_IT_SPEED_LORA = (
    r"Wan2.1\Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors"
)
# With lightx2v: 8 is fastest; hero lip default 12 (user QA 2026-07-13 C winner).
DEFAULT_IT_SPEED_STEPS = 12


def _snap_dim(n: int, multiple: int = 16) -> int:
    if n < multiple:
        return multiple
    return max(multiple, int(round(n / multiple) * multiple))


def _ensure_playable_h264(path: str) -> None:
    """Re-encode to yuv420p High if needed (Windows player compatibility)."""
    if not path or not os.path.isfile(path):
        return
    try:
        import json
        from lib.ffmpeg_util import find_ffmpeg, run_ffmpeg

        out = subprocess.check_output(
            [
                shutil.which("ffprobe") or "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=pix_fmt,profile",
                "-of",
                "json",
                path,
            ],
            text=True,
            timeout=30,
        )
        st = (json.loads(out).get("streams") or [{}])[0]
        pix = (st.get("pix_fmt") or "").lower()
        prof = (st.get("profile") or "").lower()
        if pix in ("yuv420p", "yuvj420p") and "4:4:4" not in prof:
            return
        tmp = path + ".playable.mp4"
        r = run_ffmpeg(
            [
                "-i",
                path,
                "-c:v",
                "libx264",
                "-profile:v",
                "high",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                tmp,
            ],
            timeout_sec=600,
        )
        if r.get("ok") and os.path.isfile(tmp):
            os.replace(tmp, path)
            print(f"  re-encoded playable yuv420p: {path}")
        elif os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    except Exception as e:
        print(f"[WARN] playable re-encode skipped: {e}")


def _snap_frames(n: int) -> int:
    n = max(9, int(n))
    base = ((n - 1) // 4) * 4 + 1
    alt = base + 4
    return alt if abs(alt - n) < abs(base - n) else base


def _probe_audio_duration(path: str) -> float | None:
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                path,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None


def _queue(server: str, api_prompt: dict) -> dict:
    payload = json.dumps({"prompt": _api_for_comfy(api_prompt)}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_history(server: str, prompt_id: str, timeout_sec: float) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server}/history/{prompt_id}", timeout=30
            ) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
                if prompt_id in hist:
                    return hist[prompt_id]
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(prompt_id)


def build_infinitetalk_api(
    *,
    image_name: str,
    audio_abs_path: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    num_frames: int,
    fps: float,
    steps: int,
    cfg: float,
    seed: int,
    i2v_model: str,
    multitalk_model: str,
    wav2vec: str,
    vae: str,
    clip_vision: str,
    t5: str,
    filename_prefix: str = "agent_s2v",
    api_opts: dict | None = None,
) -> dict:
    """InfiniteTalk I2V graph with optional lightx2v distill LoRA + TeaCache."""
    api_opts = api_opts or {}
    speed_lora = api_opts.get("speed_lora")  # path str or None / ""
    speed_lora_strength = float(api_opts.get("speed_lora_strength", 1.0))
    use_teacache = bool(api_opts.get("teacache", False))
    teacache_thresh = float(api_opts.get("teacache_thresh", 0.2))
    # Default sageattn (package installed in Comfy portable). Fallback: AGENT_IT_ATTENTION=sdpa
    attention_mode = str(api_opts.get("attention_mode") or "sageattn").strip() or "sageattn"

    api: dict = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "ImageResizeKJv2",
            "inputs": {
                "image": ["1", 0],
                "width": width,
                "height": height,
                "upscale_method": "lanczos",
                "keep_proportion": "crop",
                "pad_color": "0, 0, 0",
                "crop_position": "center",
                "divisible_by": 16,
                "device": "cpu",
            },
        },
        "3": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": clip_vision},
        },
        "4": {
            "class_type": "WanVideoClipVisionEncode",
            "inputs": {
                "clip_vision": ["3", 0],
                "image_1": ["2", 0],
                "strength_1": 1.0,
                "strength_2": 1.0,
                "crop": "center",
                "combine_embeds": "average",
                "force_offload": True,
                "tiles": 0,
                "ratio": 0.5,
            },
        },
        "5": {
            "class_type": "JWLoadAudio",
            "inputs": {
                "path": audio_abs_path,
                "gain_db": 0.0,
                "offset_seconds": 0.0,
                "duration_seconds": 0.0,
                "resample_to_hz": 0.0,
                "make_stereo": True,
            },
        },
        "6": {
            "class_type": "DownloadAndLoadWav2VecModel",
            "inputs": {
                "model": wav2vec if "/" in wav2vec else "TencentGameMate/chinese-wav2vec2-base",
                "base_precision": "fp16",
                "load_device": "main_device",
            },
        },
        "7": {
            "class_type": "MultiTalkWav2VecEmbeds",
            "inputs": {
                "wav2vec_model": ["6", 0],
                "audio_1": ["5", 0],
                "normalize_loudness": True,
                "num_frames": num_frames,
                "fps": float(fps),
                "audio_scale": float(api_opts.get("audio_scale", 1.5)),
                "audio_cfg_scale": float(api_opts.get("audio_cfg_scale", 1.0)),
                "multi_audio_type": "para",
                "add_noise_floor": False,
                "smooth_transients": False,
            },
        },
        "8": {
            "class_type": "MultiTalkModelLoader",
            "inputs": {"model": multitalk_model},
        },
        "9": {
            "class_type": "WanVideoBlockSwap",
            "inputs": {
                "blocks_to_swap": 30,
                "offload_img_emb": False,
                "offload_txt_emb": False,
                "use_non_blocking": False,
                "vace_blocks_to_swap": 0,
                "prefetch_blocks": 1,
                "block_swap_debug": False,
            },
        },
        "10": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": i2v_model,
                "base_precision": "fp16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": attention_mode,
                "block_swap_args": ["9", 0],
                "multitalk_model": ["8", 0],
                "rms_norm_function": "default",
            },
        },
        "11": {
            "class_type": "WanVideoVAELoader",
            "inputs": {"model_name": vae, "precision": "bf16"},
        },
        "12": {
            "class_type": "WanVideoTextEncodeCached",
            "inputs": {
                "model_name": t5,
                "precision": "bf16",
                "positive_prompt": prompt,
                "negative_prompt": negative,
                "quantization": "disabled",
                "use_disk_cache": True,
                "device": "gpu",
            },
        },
        "13": {
            "class_type": "WanVideoImageToVideoMultiTalk",
            "inputs": {
                "vae": ["11", 0],
                "width": width,
                "height": height,
                "frame_window_size": num_frames,
                "motion_frame": min(9, max(1, num_frames // 4)),
                "force_offload": True,
                "colormatch": "disabled",
                "start_image": ["2", 0],
                "tiled_vae": False,
                "clip_embeds": ["4", 0],
                "mode": "infinitetalk",
                "output_path": "",
            },
        },
    }

    model_ref: list = ["10", 0]
    # lightx2v distill: enables 4–8 step sampling (GGUF → merge_loras must stay False)
    if speed_lora:
        api["26"] = {
            "class_type": "WanVideoLoraSelect",
            "inputs": {
                "lora": str(speed_lora),
                "strength": speed_lora_strength,
                "low_mem_load": False,
                "merge_loras": False,
            },
        }
        api["27"] = {
            "class_type": "WanVideoSetLoRAs",
            "inputs": {
                "model": ["10", 0],
                "lora": ["26", 0],
            },
        }
        model_ref = ["27", 0]

    sampler_inputs: dict = {
        "model": model_ref,
        "image_embeds": ["13", 0],
        "steps": steps,
        "cfg": cfg,
        "shift": float(api_opts.get("shift", 11.0)),
        "seed": seed,
        "force_offload": True,
        "scheduler": str(api_opts.get("scheduler", "dpm++_sde")),
        "riflex_freq_index": 0,
        "text_embeds": ["12", 0],
        "denoise_strength": 1.0,
        "batched_cfg": False,
        "rope_function": "comfy",
        "start_step": 0,
        "end_step": -1,
        "add_noise_to_samples": False,
        "multitalk_embeds": ["7", 0],
    }
    if use_teacache:
        api["28"] = {
            "class_type": "WanVideoTeaCache",
            "inputs": {
                "rel_l1_thresh": teacache_thresh,
                "start_step": 1,
                "end_step": -1,
                "cache_device": "offload_device",
                "use_coefficients": True,
                "mode": "e",
            },
        }
        sampler_inputs["cache_args"] = ["28", 0]

    api["14"] = {"class_type": "WanVideoSampler", "inputs": sampler_inputs}
    api["15"] = {
        "class_type": "WanVideoDecode",
        "inputs": {
            "vae": ["11", 0],
            "samples": ["14", 0],
            "enable_vae_tiling": False,
            "tile_x": 272,
            "tile_y": 272,
            "tile_stride_x": 144,
            "tile_stride_y": 128,
            "normalization": "default",
        },
    }
    api["16"] = {
        "class_type": "VHS_VideoCombine",
        "inputs": {
            "images": ["15", 0],
            "audio": ["7", 1],
            "frame_rate": float(fps),
            "loop_count": 0,
            "filename_prefix": filename_prefix,
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
        },
    }
    return api


def generate_s2v(
    input_image_path: str,
    audio_path: str | None = None,
    output_filename: str | None = None,
    *,
    backend: str = "ltx23_aio",
    prompt: str = (
        "person speaking clearly with natural lip sync, mouth opens and closes "
        "with the dialogue, jaw movement, subtle head motion, keep identity fixed, cinematic"
    ),
    negative: str = DEFAULT_NEG,
    width: int = 640,
    height: int = 640,
    num_frames: int | None = None,
    fps: float = 16.0,
    steps: int = 20,
    cfg: float = 1.0,
    seed: int | None = None,
    i2v_model: str = DEFAULT_I2V,
    multitalk_model: str = DEFAULT_MULTITALK,
    wav2vec: str = DEFAULT_WAV2VEC,
    ltx_unet: str = DEFAULT_UNET_GGUF,
    ltx_lora: str = DEFAULT_DISTILL_LORA,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
    dry_run: bool = False,
    audio_scale: float = 1.5,  # hero lip default (QA 2026-07-13 C); was 1.35 mild
    audio_cfg_scale: float = 1.0,
    scheduler: str = "dpm++_sde",
    shift: float = 11.0,
    speed_lora: str | bool | None = True,
    speed_lora_strength: float = 1.0,
    teacache: bool = False,  # default off — better lip timing
    teacache_thresh: float = 0.2,
    ltx_mode: str | None = None,
    last_image_path: str | None = None,
    mid_image_path: str | None = None,
    guide_strength: float = 0.9,
    allow_clamp: bool | None = None,
    tail_sec: float | None = None,
) -> dict:
    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    backend = (backend or "ltx23_ia2v").strip().lower()
    if backend not in S2V_BACKENDS:
        return fail_result(
            error="BAD_BACKEND",
            message=f"{backend!r}; choose from {S2V_BACKENDS}",
        )

    eng = ensure_engine(
        family_for_s2v_backend(backend),
        server_address,
        caller=f"generate_s2v:{backend}",
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    use_aio_switched = False
    use_live_aio_template = False
    live_meta: dict | None = None
    ltx_runner = "none"

    # Resolve AIO mode early to know if audio is required
    _early_mode = None
    if is_ltx_backend(backend):
        try:
            _early_mode = resolve_aio_mode(backend, ltx_mode)
        except ValueError as e:
            return fail_result(error="BAD_MODE", message=str(e))
        if backend == "ltx23_ia2v" and not ltx_mode:
            _early_mode = "i2v_audio"
    audio_required = backend == "infinitetalk" or (
        _early_mode in ("i2v_audio", "flf_audio", "fml_audio", "v2v_audio", "t2v_audio")
        or (_early_mode == "v2v" and audio_path)
    )
    # pure i2v / flf / fml / t2v without audio: allow missing audio
    if _early_mode in ("i2v", "flf", "fml", "t2v", "v2v") and not audio_path:
        audio_required = False
    if audio_required and (not audio_path or not os.path.isfile(audio_path)):
        return fail_result(error="AUDIO_MISSING", message=audio_path or "(none)")

    if is_ltx_backend(backend):
        width = snap_ltx_dim(width, 32)
        height = snap_ltx_dim(height, 32)
        if fps is None or fps <= 0:
            fps = 24.0
        # AIO distilled stack is 24fps; IT default 16 must not leak in.
        # Also avoid 25fps accidental defaults (frame/audio length mismatch).
        if backend.startswith("ltx23_aio") or abs(float(fps) - 16.0) < 0.01:
            fps = 24.0
    else:
        width = _snap_dim(width, 16)
        height = _snap_dim(height, 16)

    # P0-1: frames from audio length; hard-fail if over max (no silent cut).
    snap = snap_ltx_frames if is_ltx_backend(backend) else _snap_frames
    adur = _probe_audio_duration(audio_path) if audio_path else None
    if num_frames is None:
        dur = adur
        if not dur or dur > 120:
            if audio_path:
                print(f"[WARN] audio duration probe={dur}; using 5.0s for frame count")
            dur = 5.0
        tail = default_tail_sec() if tail_sec is None else float(tail_sec)
        num_frames = frames_from_duration(dur, fps, tail_sec=tail, snap_fn=snap)
    else:
        num_frames = snap(int(num_frames))

    cap = apply_frame_cap(
        int(num_frames),
        backend=backend,
        fps=float(fps),
        audio_duration_sec=adur,
        allow_clamp_override=allow_clamp,
    )
    if not cap.get("ok"):
        return fail_result(
            error=cap.get("error") or "FRAMES_EXCEED_MAX",
            message=cap.get("message") or "frame cap",
            max_frames=cap.get("max_frames"),
            needed_frames=cap.get("num_frames"),
            suggest_split=cap.get("suggest_split"),
            suggest_max_dialogue_sec=cap.get("suggest_max_dialogue_sec"),
        )
    num_frames = int(cap["num_frames"])
    if cap.get("clamped"):
        print(f"[WARN] {cap.get('warning')}")
    elif adur:
        print(
            f"[length] audio={float(adur):.2f}s frames={num_frames} "
            f"clip~{cap.get('clip_sec'):.2f}s max={cap.get('max_frames')}"
        )

    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    if steps is None:
        if backend == "infinitetalk":
            # With speed LoRA default 8; without, 20
            use_sl = not (speed_lora is False or speed_lora == "")
            steps = DEFAULT_IT_SPEED_STEPS if use_sl else 20
        else:
            steps = 20
    if output_filename is None:
        output_filename = os.path.join(
            os.path.dirname(os.path.abspath(input_image_path)), "s2v_out.mp4"
        )
    ensure_parent_dir(output_filename)

    # copy image + optional audio into Comfy input
    img_name = "temp_s2v_input.png"
    audio_name = "temp_s2v_drive.wav"
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, img_name))
    audio_abs = os.path.abspath(audio_path) if audio_path else ""
    if audio_path and os.path.isfile(audio_path):
        # preserve extension (AIO LoadAudio handles mp3/wav)
        ext = os.path.splitext(audio_path)[1].lower() or ".wav"
        if ext not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
            ext = ".wav"
        audio_name = f"temp_s2v_drive{ext}"
        shutil.copy2(audio_abs, os.path.join(COMFYUI_INPUT_DIR, audio_name))
    else:
        audio_name = None

    if is_ltx_backend(backend):
        try:
            mode = resolve_aio_mode(backend, ltx_mode)
        except ValueError as e:
            return fail_result(error="BAD_MODE", message=str(e))
        if backend == "ltx23_ia2v" and not ltx_mode:
            mode = "i2v_audio"

        aio_d = aio_profile_defaults()
        lora_use = aio_d["distill_lora"]
        lora_str = float(aio_d["lora_strength"])
        if ltx_lora and ltx_lora not in (DEFAULT_DISTILL_LORA, AIO_DISTILL_LORA, ""):
            lora_use = ltx_lora

        # stage guide images into Comfy input
        last_name = None
        mid_name = None
        if last_image_path:
            if not os.path.isfile(last_image_path):
                return fail_result(error="LAST_MISSING", message=last_image_path)
            last_name = "temp_s2v_last.png"
            shutil.copy2(last_image_path, os.path.join(COMFYUI_INPUT_DIR, last_name))
        if mid_image_path:
            if not os.path.isfile(mid_image_path):
                return fail_result(error="MID_MISSING", message=mid_image_path)
            mid_name = "temp_s2v_mid.png"
            shutil.copy2(mid_image_path, os.path.join(COMFYUI_INPUT_DIR, mid_name))

        audio_for_graph = (
            audio_name
            if mode
            in (
                "i2v_audio",
                "flf_audio",
                "fml_audio",
                "v2v_audio",
                "t2v_audio",
            )
            or (mode == "v2v" and audio_path)
            else None
        )
        if mode in ("i2v_audio", "flf_audio", "fml_audio", "v2v_audio", "t2v_audio") and not audio_path:
            return fail_result(error="AUDIO_REQUIRED", message=f"mode {mode} needs -a")
        if mode in ("flf", "flf_audio") and not last_name:
            return fail_result(error="LAST_REQUIRED", message=f"mode {mode} needs --last")
        if mode in ("fml", "fml_audio") and (not last_name or not mid_name):
            return fail_result(
                error="MID_LAST_REQUIRED", message=f"mode {mode} needs --mid and --last"
            )

        force_mini = os.environ.get("AGENT_LTX_FORCE_MINI_GRAPH", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        force_live_template = os.environ.get(
            "AGENT_LTX_FORCE_LIVE_TEMPLATE", ""
        ).strip().lower() in ("1", "true", "yes")
        # Prefer real AIO UI workflow + [[P:]] switch/select for ALL modes.
        # Optional: frozen IA2V history template; emergency mini graphs only if forced.
        use_aio_switched = not force_mini and not force_live_template
        use_live_aio_template = False
        ltx_runner = "none"

        adur = _probe_audio_duration(audio_path) if audio_path else None
        edge = max(int(width), int(height))
        if edge < 512:
            edge = 1024
        aspect = "9:16" if int(height) >= int(width) else "16:9"
        # Match runner default: audio+1.5 then ceil (S02 bench preferred for lip/prop).
        # Tight: AGENT_LTX_CLIP_TIGHT=1 or AGENT_LTX_CLIP_PAD_SEC=0
        clip_sec = None
        if adur:
            tight = os.environ.get("AGENT_LTX_CLIP_TIGHT", "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            default_pad = "0" if tight else "1.5"
            try:
                pad = float(
                    os.environ.get("AGENT_LTX_CLIP_PAD_SEC", default_pad) or default_pad
                )
            except ValueError:
                pad = 0.0 if tight else 1.5
            try:
                extra = int(float(os.environ.get("AGENT_LTX_CLIP_EXTRA_SEC", "0") or 0))
            except ValueError:
                extra = 0
            import math as _math

            clip_sec = float(int(_math.ceil(float(adur) + pad - 1e-9)) + max(0, extra))
        elif num_frames and fps:
            clip_sec = float(num_frames) / float(fps)
        if seed is None:
            seed = random.randint(0, 2**63 - 1)

        if use_aio_switched:
            try:
                api, live_meta = build_aio_switched_api(
                    mode=mode,
                    image_name=img_name if mode not in ("t2v", "t2v_audio") else None,
                    audio_name=audio_for_graph,
                    last_image_name=last_name,
                    mid_image_name=mid_name,
                    prompt=prompt,
                    negative=negative or "animation, cartoon, text",
                    seed=int(seed),
                    audio_duration_sec=float(adur) if adur else None,
                    clip_length_sec=clip_sec,
                    trim_start_sec=0.0,
                    longer_edge=edge,
                    aspect=aspect,
                    fps=int(round(float(fps))),
                    filename_prefix="agent_ltx_aio",
                )
                ltx_runner = "ltx_aio_workflow_runner"
                lora_use = "PowerLora(from_AIO_workflow)"
                lora_str = 0.9
                print(
                    f"generate_s2v backend={backend} mode={mode} "
                    f"AIO_SWITCH edge={edge} aspect={aspect} "
                    f"trim={live_meta.get('trim_duration_sec')}s "
                    f"clip={live_meta.get('clip_length_sec')}s "
                    f"fps={live_meta.get('fps')} seed={seed} "
                    f"api_nodes={live_meta.get('api_nodes')} "
                    f"mode_changes={live_meta.get('mode_changes')}"
                )
            except Exception as e:
                print(f"[WARN] AIO switch runner failed ({e}); trying fallbacks")
                use_aio_switched = False
                api = None  # type: ignore
                live_meta = None

        if not use_aio_switched and (
            force_live_template
            or (
                mode == "i2v_audio"
                and not force_mini
                and is_live_template_available()
                and bool(audio_name)
            )
        ):
            # Frozen manual-success IA2V API graph (still real AIO, not mini)
            api, live_meta = build_ia2v_live_api(
                image_name=img_name,
                audio_name=audio_name,
                prompt=prompt,
                negative=negative or "animation, cartoon, text",
                seed=int(seed),
                audio_duration_sec=float(adur) if adur else None,
                clip_length_sec=clip_sec,
                trim_start_sec=0.0,
                longer_edge=edge,
                aspect=aspect,
                fps=int(round(float(fps))),
                filename_prefix="agent_ltx_ia2v",
            )
            use_live_aio_template = True
            ltx_runner = "ltx_aio_live_template"
            lora_use = "PowerLora(from_template)"
            lora_str = 0.9
            print(
                f"generate_s2v backend={backend} mode={mode} "
                f"LIVE_AIO_TEMPLATE edge={edge} aspect={aspect} "
                f"trim={live_meta.get('trim_duration_sec')}s "
                f"clip={live_meta.get('clip_length_sec')}s "
                f"fps={live_meta.get('fps')} seed={seed}"
            )
        elif not use_aio_switched:
            # LEGACY mini-graph only when AGENT_LTX_FORCE_MINI_GRAPH=1 or all real paths fail
            if not force_mini:
                print(
                    "[WARN] falling back to LEGACY mini graph — "
                    "set AGENT_LTX_FORCE_MINI_GRAPH=1 only intentionally"
                )
            ltx_cfg = 1.0 if cfg is None else float(cfg)
            ltx_runner = "legacy_mini_graph"
            if mode == "i2v_audio" and audio_name:
                api = build_ltx_custom_audio_api(
                    image_name=img_name,
                    audio_name=audio_name,
                    prompt=prompt,
                    negative=negative or DEFAULT_NEG,
                    width=width,
                    height=height,
                    num_frames=num_frames,
                    fps=fps,
                    seed=seed,
                    cfg=ltx_cfg,
                    unet_gguf=ltx_unet,
                    distill_lora=lora_use,
                    lora_strength=lora_str,
                    profile="aio",
                )
            else:
                api = build_ltx_aio_mode_api(
                    mode=mode,
                    first_image=img_name,
                    last_image=last_name,
                    mid_image=mid_name,
                    audio_name=audio_for_graph,
                    prompt=prompt,
                    negative=negative or DEFAULT_NEG,
                    width=width,
                    height=height,
                    num_frames=num_frames,
                    fps=fps,
                    seed=seed,
                    cfg=ltx_cfg,
                    unet_gguf=ltx_unet,
                    distill_lora=lora_use,
                    lora_strength=lora_str,
                    guide_strength=guide_strength,
                )
            print(
                f"generate_s2v backend={backend} mode={mode} "
                f"LEGACY_MINI {width}x{height} frames={num_frames} fps={fps} seed={seed}"
            )

        print(f"  image={input_image_path}")
        if last_image_path:
            print(f"  last={last_image_path}")
        if mid_image_path:
            print(f"  mid={mid_image_path}")
        print(f"  audio={audio_path}")
        print(f"  runner={ltx_runner}")
        print(f"  unet={'from_AIO_workflow' if use_aio_switched or use_live_aio_template else ltx_unet}")
        print(f"  lora={lora_use} @ {lora_str}")
    else:
        # Resolve speed LoRA path
        lora_path: str | None = None
        if speed_lora is True or speed_lora is None:
            lora_path = DEFAULT_IT_SPEED_LORA
        elif speed_lora is False or speed_lora == "":
            lora_path = None
        else:
            lora_path = str(speed_lora)

        # With distill LoRA, default steps drop unless caller set them high intentionally
        if lora_path and steps >= 16:
            print(
                f"[speed] lightx2v LoRA on — clamping steps {steps} → {DEFAULT_IT_SPEED_STEPS} "
                f"(pass --steps explicitly after --no-speed-lora for full quality)"
            )
            # Only auto-clamp when it looks like a legacy "full quality" default
            # Callers that want 20 steps WITH lora can pass steps=20 and we still use lora;
            # actually clamping always when lora and steps>12 is safer for agent speed.
        # Allow up to 16 steps with lightx2v; clamp only obvious full-quality defaults (20+)
        if lora_path and steps > 16:
            print(f"[speed] steps {steps} → {DEFAULT_IT_SPEED_STEPS} with distill LoRA")
            steps = DEFAULT_IT_SPEED_STEPS
        if lora_path:
            cfg = 1.0  # cfg-distill LoRA expects cfg≈1

        it_attention = (
            os.environ.get("AGENT_IT_ATTENTION", "sageattn").strip() or "sageattn"
        )

        api = build_infinitetalk_api(
            image_name=img_name,
            audio_abs_path=os.path.join(COMFYUI_INPUT_DIR, audio_name),
            prompt=prompt,
            negative=negative or DEFAULT_NEG,
            width=width,
            height=height,
            num_frames=num_frames,
            fps=fps,
            steps=steps,
            cfg=cfg,
            seed=seed,
            i2v_model=i2v_model,
            multitalk_model=multitalk_model,
            wav2vec=wav2vec,
            vae=DEFAULT_VAE,
            clip_vision=DEFAULT_CLIP_VISION,
            t5=DEFAULT_T5,
            api_opts={
                "audio_scale": audio_scale,
                "audio_cfg_scale": audio_cfg_scale,
                "scheduler": scheduler,
                "shift": shift,
                "speed_lora": lora_path,
                "speed_lora_strength": speed_lora_strength,
                "teacache": teacache,
                "teacache_thresh": teacache_thresh,
                "attention_mode": it_attention,
            },
        )
        print(
            f"generate_s2v backend=infinitetalk {width}x{height} frames={num_frames} "
            f"fps={fps} steps={steps} seed={seed}"
        )
        print(f"  image={input_image_path}")
        print(f"  audio={audio_path}")
        print(f"  i2v={i2v_model}")
        print(f"  multitalk={multitalk_model}")
        print(f"  attention={it_attention} speed_lora={lora_path or 'off'} teacache={teacache}")

    if dry_run:
        meta = {
            "mode": "s2v",
            "backend": backend,
            "status": "dry_run",
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "fps": fps,
            "steps": steps,
            "seed": seed,
            "source_image": os.path.abspath(input_image_path),
            "driving_audio": audio_abs,
            "output_path": os.path.abspath(output_filename),
            "created_at": utc_now_iso(),
        }
        mp = resolve_meta_out(output_filename, meta_out)
        if mp:
            write_meta(mp, meta)
            print(f"  plan meta={mp}")
        return ok_result(dry_run=True, meta=meta, meta_path=mp)

    try:
        res = _queue(server_address, api)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] queue HTTP {e.code}: {body[:2000]}")
        return fail_result(error="QUEUE_FAILED", message=body[:800])
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e))

    if res.get("node_errors"):
        print(f"[ERROR] node_errors: {res['node_errors']}")
        return fail_result(error="NODE_ERRORS", message=str(res["node_errors"])[:800])

    prompt_id = res["prompt_id"]
    print(f"Prompt queued: {prompt_id}")

    try:
        history = _wait_history(server_address, prompt_id, timeout_sec)
    except TimeoutError:
        return fail_result(error="COMFY_TIMEOUT", message="S2V timeout", prompt_id=prompt_id)

    status = history.get("status") or {}
    if status.get("status_str") == "error" or status.get("completed") is False:
        err_msg = "execution error"
        for msg in status.get("messages") or []:
            if msg and msg[0] == "execution_error":
                err_msg = msg[1].get("exception_message") or err_msg
                print(
                    f"[ERROR] node={msg[1].get('node_id')} {msg[1].get('node_type')}: "
                    f"{str(err_msg)[:800]}"
                )
        return fail_result(
            error="EXECUTION_ERROR", message=str(err_msg)[:800], prompt_id=prompt_id, seed=seed
        )

    # find video (InfiniteTalk: gifs/videos; LTX SaveVideo: images[].mp4)
    video_info = None
    for _nid, out in (history.get("outputs") or {}).items():
        for key in ("gifs", "videos", "images"):
            if key not in out or not out[key]:
                continue
            cand = out[key][0]
            fn = str(cand.get("filename") or "")
            if key == "images" and not fn.lower().endswith((".mp4", ".webm", ".mkv")):
                continue
            video_info = cand
            break
        if video_info:
            break

    if video_info:
        filename = video_info.get("filename")
        subfolder = video_info.get("subfolder", "")
        ftype = video_info.get("type", "output")
        base = COMFY_OUTPUT_DIR if ftype == "output" else COMFY_TEMP_DIR
        src = os.path.join(base, subfolder, filename) if subfolder else os.path.join(base, filename)
        if os.path.isfile(src):
            shutil.copy2(src, output_filename)
            print(f"Copied: {src} -> {output_filename}")
        else:
            view = (
                f"http://{server_address}/view?filename={urllib.parse.quote(filename)}"
                f"&subfolder={urllib.parse.quote(subfolder)}&type={ftype}"
            )
            urllib.request.urlretrieve(view, output_filename)
            print(f"Downloaded: {filename}")
        _ensure_playable_h264(output_filename)
    else:
        prefixes = (
            "agent_ltx_ia2v",
            "agent_ltx_s2v",
            "agent_ltx_aio",
            "agent_s2v",
            "ltx2_",
        )
        candidates = []
        for folder in (COMFY_OUTPUT_DIR, COMFY_TEMP_DIR):
            if not os.path.isdir(folder):
                continue
            for root, _d, files in os.walk(folder):
                for fn in files:
                    if not fn.lower().endswith(".mp4"):
                        continue
                    fl = fn.lower()
                    if any(p in fl for p in prefixes):
                        fp = os.path.join(root, fn)
                        candidates.append((os.path.getmtime(fp), fp))
        if not candidates:
            return fail_result(error="COMFY_NO_OUTPUT", message="no video", prompt_id=prompt_id)
        candidates.sort(reverse=True)
        shutil.copy2(candidates[0][1], output_filename)
        print(f"Copied newest: {candidates[0][1]}")
        _ensure_playable_h264(output_filename)

    # Mini-graph LTX sometimes hallucinates speech — remux TTS.
    # Real AIO switch / live template already use proper Audio input path; keep native
    # audio unless AGENT_LTX_FORCE_TTS_REMUX=1.
    audio_replaced = False
    force_tts = os.environ.get("AGENT_LTX_FORCE_TTS_REMUX", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    real_aio_audio = use_aio_switched or use_live_aio_template
    if (
        is_ltx_backend(backend)
        and audio_path
        and os.path.isfile(audio_path)
        and (force_tts or not real_aio_audio)
    ):
        try:
            rr = replace_clip_audio(output_filename, audio_path)
            if rr.get("ok"):
                audio_replaced = True
                print(f"Audio replaced with driving/TTS: {audio_path}")
            else:
                print(
                    f"[WARN] LTX audio replace failed: {rr.get('error')} {rr.get('message')}"
                )
        except Exception as e:
            print(f"[WARN] LTX audio replace failed: {e}")

    # Comfy often writes 16 kHz mono AAC (InfiniteTalk/VHS) — many Windows players
    # appear silent. Re-encode to 48 kHz stereo AAC for preview compatibility.
    try:
        nr = normalize_clip_audio(
            output_filename,
            loudnorm=is_ltx_backend(backend) and not audio_replaced,
        )
        if nr.get("ok"):
            print(
                f"Audio normalized: {nr.get('sample_rate')}Hz "
                f"ch={nr.get('channels')} loudnorm={nr.get('loudnorm')}"
            )
        else:
            print(f"[WARN] audio normalize skipped: {nr.get('error')} {nr.get('message')}")
    except Exception as e:
        print(f"[WARN] audio normalize failed: {e}")

    meta = {
        "mode": "s2v",
        "backend": backend,
        "status": "ok",
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "fps": fps,
        "steps": steps,
        "cfg": cfg,
        "seed": seed,
        "prompt": prompt,
        "negative": negative,
        "audio_replaced_with_driving": audio_replaced,
        "ltx_te": DEFAULT_GEMMA if is_ltx_backend(backend) else None,
        "ltx_runner": ltx_runner if is_ltx_backend(backend) else None,
        "aio_switched": use_aio_switched if is_ltx_backend(backend) else False,
        "live_aio_template": use_live_aio_template,
        "live_aio_meta": live_meta,
        "ltx_mode": live_meta.get("mode") if isinstance(live_meta, dict) else (
            _early_mode if is_ltx_backend(backend) else None
        ),
        "i2v_model": i2v_model if backend == "infinitetalk" else ltx_unet,
        "multitalk_model": multitalk_model if backend == "infinitetalk" else ltx_lora,
        "speed_lora": (
            (DEFAULT_IT_SPEED_LORA if speed_lora is True else speed_lora)
            if backend == "infinitetalk" and speed_lora not in (False, "")
            else None
        ),
        "teacache": teacache if backend == "infinitetalk" else False,
        "source_image": os.path.abspath(input_image_path),
        "driving_audio": audio_abs,
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
    }
    mp = resolve_meta_out(output_filename, meta_out)
    if mp:
        write_meta(mp, meta)
        print(f"Meta: {mp}")

    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=seed,
        prompt_id=prompt_id,
        meta_path=mp,
        meta=meta,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SI2V multi-backend (InfiniteTalk / LTX AIO modes)")
    p.add_argument("--input", "-i", required=True, help="First/keyframe image (v2v: last frame of prior clip)")
    p.add_argument("--audio", "-a", default=None, help="Driving audio (required for *_audio / IT)")
    p.add_argument("--last", default=None, dest="last_image", help="Last frame (flf/fml)")
    p.add_argument("--mid", default=None, dest="mid_image", help="Mid frame (fml)")
    p.add_argument(
        "--ltx-mode",
        default=None,
        choices=list(AIO_MODES),
        help="Override AIO mode (switch/select): i2v|i2v_audio|flf|flf_audio|fml|fml_audio|v2v|v2v_audio|t2v|t2v_audio",
    )
    p.add_argument("--guide-strength", type=float, default=0.9)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--backend",
        default="ltx23_aio",
        choices=list(S2V_BACKENDS),
        help="ltx23_aio* mode backends | ltx23_ia2v | infinitetalk",
    )
    p.add_argument(
        "--prompt",
        "-p",
        default=(
            "person speaking clearly with natural lip sync, mouth opens and closes "
            "with the dialogue, jaw movement, subtle head motion, keep identity fixed"
        ),
    )
    p.add_argument("--negative", default=DEFAULT_NEG)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=640)
    p.add_argument("--frames", type=int, default=None)
    p.add_argument(
        "--allow-clamp",
        action="store_true",
        help="Allow truncating frames to AGENT_*_MAX_FRAMES (cuts audio — not recommended)",
    )
    p.add_argument(
        "--tail-sec",
        type=float,
        default=None,
        help="Extra seconds after audio for frame count (default AGENT_S2V_TAIL_SEC=0.15)",
    )
    p.add_argument("--fps", type=float, default=25.0, help="Default 25 (IT examples / LTX often 24)")
    p.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Sampler steps (IT default 12 with speed LoRA, 20 without)",
    )
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument(
        "--audio-scale",
        type=float,
        default=1.5,
        help="IT lip intensity (hero default 1.5; lower ~1.35 milder, raise ~1.6 bigger mouths)",
    )
    p.add_argument("--audio-cfg-scale", type=float, default=1.0)
    p.add_argument("--scheduler", default="dpm++_sde")
    p.add_argument("--shift", type=float, default=11.0)
    p.add_argument(
        "--speed-lora",
        dest="speed_lora",
        action="store_true",
        default=True,
        help="Apply lightx2v distill LoRA (default on; hero uses 12 steps)",
    )
    p.add_argument(
        "--no-speed-lora",
        dest="speed_lora",
        action="store_false",
        help="Disable distill LoRA (full steps quality path)",
    )
    p.add_argument(
        "--speed-lora-path",
        default=None,
        help=f"Override LoRA path (default {DEFAULT_IT_SPEED_LORA})",
    )
    p.add_argument(
        "--teacache",
        dest="teacache",
        action="store_true",
        default=False,
        help="WanVideoTeaCache on InfiniteTalk (default off — better lip timing)",
    )
    p.add_argument(
        "--no-teacache",
        dest="teacache",
        action="store_false",
        help="Disable TeaCache (default)",
    )
    p.add_argument("--teacache-thresh", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--i2v-model", default=DEFAULT_I2V)
    p.add_argument("--multitalk-model", default=DEFAULT_MULTITALK)
    p.add_argument("--wav2vec", default=DEFAULT_WAV2VEC)
    p.add_argument("--ltx-unet", default=DEFAULT_UNET_GGUF)
    p.add_argument("--ltx-lora", default=DEFAULT_DISTILL_LORA)
    args = p.parse_args(argv)

    r = generate_s2v(
        args.input,
        args.audio,
        args.output,
        backend=args.backend,
        prompt=args.prompt,
        negative=args.negative,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        fps=args.fps,
        steps=args.steps,
        cfg=args.cfg,
        seed=args.seed,
        i2v_model=args.i2v_model,
        multitalk_model=args.multitalk_model,
        wav2vec=args.wav2vec,
        ltx_unet=args.ltx_unet,
        ltx_lora=args.ltx_lora,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=args.dry_run,
        audio_scale=args.audio_scale,
        audio_cfg_scale=args.audio_cfg_scale,
        scheduler=args.scheduler,
        shift=args.shift,
        speed_lora=(
            args.speed_lora_path
            if args.speed_lora and args.speed_lora_path
            else (True if args.speed_lora else False)
        ),
        speed_lora_strength=1.0,
        teacache=args.teacache,
        teacache_thresh=args.teacache_thresh,
        ltx_mode=args.ltx_mode,
        last_image_path=args.last_image,
        mid_image_path=args.mid_image,
        guide_strength=args.guide_strength,
        allow_clamp=True if args.allow_clamp else None,
        tail_sec=args.tail_sec,
    )
    if r.get("ok"):
        print(f"OK {r.get('output_path') or '(dry-run)'}")
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
