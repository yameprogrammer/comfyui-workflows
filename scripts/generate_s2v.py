#!/usr/bin/env python3
"""
Speech/Sound-to-Video (SI2V) multi-backend.

Backends:
  - infinitetalk (default): Wan Multi/InfiniteTalk (WanVideoWrapper)
  - ltx23_ia2v: LTX 2.3 image + custom audio (community IA2V / AV latent)

Wan inventory:
  - diffusion_models/Wan2.1/wan2.1-i2v-14b-720p-Q4_K_M.gguf
  - InfiniTetalk-Single + wav2vec / umt5 / clip_vision / wan_2.1_vae

LTX inventory (portable):
  - diffusion_models/LTX2.3/*-Q4_K_M.gguf + distilled-lora-384
  - vae/LTX23_{video,audio}_vae_bf16 + gemma + text_projection
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
from lib.ffmpeg_util import normalize_clip_audio
from lib.ltx_s2v import (
    AIO_DISTILL_LORA,
    AIO_DISTILL_LORA_STRENGTH,
    AIO_MODES,
    BACKEND_TO_AIO_MODE,
    DEFAULT_DISTILL_LORA,
    DEFAULT_UNET_GGUF,
    aio_profile_defaults,
    build_ltx_aio_mode_api,
    build_ltx_custom_audio_api,
    is_ltx_backend,
    resolve_aio_mode,
    snap_ltx_dim,
    snap_ltx_frames,
)

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
# With lightx2v: 8 is fastest; production mild default is 10 (episode_s2v / hero profile).
DEFAULT_IT_SPEED_STEPS = 10


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
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
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
                "attention_mode": "sdpa",
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
    audio_scale: float = 1.35,  # mild IT default; LTX callers can pass 1.5
    audio_cfg_scale: float = 1.0,
    scheduler: str = "dpm++_sde",
    shift: float = 11.0,
    speed_lora: str | bool | None = True,
    speed_lora_strength: float = 1.0,
    teacache: bool = True,
    teacache_thresh: float = 0.2,
    ltx_mode: str | None = None,
    last_image_path: str | None = None,
    mid_image_path: str | None = None,
    guide_strength: float = 0.9,
) -> dict:
    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    backend = (backend or "ltx23_ia2v").strip().lower()
    if backend not in S2V_BACKENDS:
        return fail_result(
            error="BAD_BACKEND",
            message=f"{backend!r}; choose from {S2V_BACKENDS}",
        )

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
        _early_mode in ("i2v_audio", "flf_audio", "fml_audio")
        or (_early_mode == "v2v" and audio_path)
    )
    # pure i2v / flf / fml without audio: allow missing audio
    if _early_mode in ("i2v", "flf", "fml") and not audio_path:
        audio_required = False
    if audio_required and (not audio_path or not os.path.isfile(audio_path)):
        return fail_result(error="AUDIO_MISSING", message=audio_path or "(none)")

    if is_ltx_backend(backend):
        width = snap_ltx_dim(width, 32)
        height = snap_ltx_dim(height, 32)
        if fps is None or fps <= 0:
            fps = 24.0
        if backend == "ltx23_aio" and (fps is None or abs(float(fps) - 16.0) < 0.01):
            # episode_s2v often passes IT default 16; AIO table uses 24
            fps = 24.0
    else:
        width = _snap_dim(width, 16)
        height = _snap_dim(height, 16)

    if num_frames is None:
        import math

        dur = _probe_audio_duration(audio_path) if audio_path else None
        if not dur or dur > 30:
            if audio_path:
                print(f"[WARN] audio duration probe={dur}; using 5.0s for frame count")
            dur = 5.0
        # ceil so video never ends before audio (round() was chopping last syllables)
        raw_frames = int(math.ceil(float(dur) * float(fps) - 1e-9))
        # optional extra tail frames (silence already in wav is preferred; this is safety)
        try:
            tail = float(os.environ.get("AGENT_S2V_TAIL_SEC", "0") or 0)
        except ValueError:
            tail = 0.0
        if tail > 0:
            raw_frames += int(math.ceil(tail * float(fps)))
        if is_ltx_backend(backend):
            num_frames = snap_ltx_frames(raw_frames)
        else:
            num_frames = _snap_frames(raw_frames)
    else:
        if is_ltx_backend(backend):
            num_frames = snap_ltx_frames(num_frames)
        else:
            num_frames = _snap_frames(num_frames)

    # MultiTalk window often prefers values like 81; clamp smoke length
    # LTX: default was 121 (~4.8s@25fps) for smoke VRAM; production dialogue
    # often needs longer — override with AGENT_LTX_MAX_FRAMES / AGENT_IT_MAX_FRAMES.
    if backend == "infinitetalk":
        if num_frames < 17:
            num_frames = 17
        it_max = int(os.environ.get("AGENT_IT_MAX_FRAMES", "129"))
        if num_frames > it_max:
            print(f"[WARN] clamping frames {num_frames} -> {it_max} (AGENT_IT_MAX_FRAMES)")
            num_frames = it_max
    elif is_ltx_backend(backend):
        ltx_max = int(os.environ.get("AGENT_LTX_MAX_FRAMES", "361"))
        if num_frames > ltx_max:
            print(f"[WARN] clamping LTX frames {num_frames} -> {ltx_max} (AGENT_LTX_MAX_FRAMES)")
            num_frames = ltx_max

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
        # LTX LoadAudio needs file under input/; InfiniteTalk uses abs path but copy is fine
        shutil.copy2(audio_abs, os.path.join(COMFYUI_INPUT_DIR, audio_name))
    else:
        audio_name = None

    if is_ltx_backend(backend):
        try:
            mode = resolve_aio_mode(backend, ltx_mode)
        except ValueError as e:
            return fail_result(error="BAD_MODE", message=str(e))
        # AIO stack defaults for all ltx23_aio* ; ia2v keeps lighter lora
        use_aio_stack = backend.startswith("ltx23_aio") or mode != "i2v_audio"
        if backend == "ltx23_ia2v" and not ltx_mode:
            mode = "i2v_audio"
            use_aio_stack = False
        lora_use = ltx_lora
        lora_str = 0.6
        if use_aio_stack or backend.startswith("ltx23_aio"):
            aio_d = aio_profile_defaults()
            if ltx_lora in (DEFAULT_DISTILL_LORA, None, ""):
                lora_use = aio_d["distill_lora"]
            lora_str = float(aio_d["lora_strength"])
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
        # silent-audio modes still load image; audio optional for pure i2v
        audio_for_graph = audio_name if mode in (
            "i2v_audio",
            "flf_audio",
            "fml_audio",
        ) or (mode == "v2v" and audio_path) else None
        if mode in ("i2v_audio", "flf_audio", "fml_audio") and not audio_path:
            return fail_result(error="AUDIO_REQUIRED", message=f"mode {mode} needs -a")
        if mode in ("flf", "flf_audio") and not last_name:
            return fail_result(error="LAST_REQUIRED", message=f"mode {mode} needs --last")
        if mode in ("fml", "fml_audio") and (not last_name or not mid_name):
            return fail_result(error="MID_LAST_REQUIRED", message=f"mode {mode} needs --mid and --last")

        if backend == "ltx23_ia2v" and mode == "i2v_audio" and not ltx_mode:
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
                cfg=cfg,
                unet_gguf=ltx_unet,
                distill_lora=lora_use,
                lora_strength=lora_str,
                profile="ia2v",
            )
        else:
            # pure i2v: still need dummy audio file path only if use_audio — not for i2v
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
                cfg=cfg,
                unet_gguf=ltx_unet,
                distill_lora=lora_use,
                lora_strength=lora_str,
                guide_strength=guide_strength,
            )
        print(
            f"generate_s2v backend={backend} mode={mode} "
            f"{width}x{height} frames={num_frames} fps={fps} seed={seed}"
        )
        print(f"  image={input_image_path}")
        if last_image_path:
            print(f"  last={last_image_path}")
        if mid_image_path:
            print(f"  mid={mid_image_path}")
        print(f"  audio={audio_path}")
        print(f"  unet={ltx_unet}")
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
        if lora_path and steps > 12:
            print(f"[speed] steps {steps} → {DEFAULT_IT_SPEED_STEPS} with distill LoRA")
            steps = DEFAULT_IT_SPEED_STEPS
        if lora_path:
            cfg = 1.0  # cfg-distill LoRA expects cfg≈1

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
        print(f"  speed_lora={lora_path or 'off'} teacache={teacache}")

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
        prefixes = ("agent_ltx_s2v", "agent_ltx_aio", "agent_s2v")
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

    # Comfy often writes 16 kHz mono AAC (InfiniteTalk/VHS) — many Windows players
    # appear silent. Re-encode to 48 kHz stereo AAC for preview compatibility.
    try:
        nr = normalize_clip_audio(
            output_filename,
            loudnorm=is_ltx_backend(backend),
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
        help="Override AIO mode: i2v|i2v_audio|flf|flf_audio|fml|fml_audio|v2v",
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
    p.add_argument("--fps", type=float, default=25.0, help="Default 25 (IT examples / LTX often 24)")
    p.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Sampler steps (IT default 8 with speed LoRA, 20 without)",
    )
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument(
        "--audio-scale",
        type=float,
        default=1.35,
        help="IT lip intensity (mild default 1.35; raise to ~1.6 for bigger mouths)",
    )
    p.add_argument("--audio-cfg-scale", type=float, default=1.0)
    p.add_argument("--scheduler", default="dpm++_sde")
    p.add_argument("--shift", type=float, default=11.0)
    p.add_argument(
        "--speed-lora",
        dest="speed_lora",
        action="store_true",
        default=True,
        help="Apply lightx2v distill LoRA for 4–8 step IT (default on)",
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
        default=True,
        help="WanVideoTeaCache on InfiniteTalk sampler (default on)",
    )
    p.add_argument(
        "--no-teacache",
        dest="teacache",
        action="store_false",
        help="Disable TeaCache",
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
    )
    if r.get("ok"):
        print(f"OK {r.get('output_path') or '(dry-run)'}")
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
