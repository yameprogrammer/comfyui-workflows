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
    DEFAULT_DISTILL_LORA,
    DEFAULT_UNET_GGUF,
    build_ltx_custom_audio_api,
    snap_ltx_dim,
    snap_ltx_frames,
)

S2V_BACKENDS = ("infinitetalk", "ltx23_ia2v")

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


def _snap_dim(n: int, multiple: int = 16) -> int:
    if n < multiple:
        return multiple
    return max(multiple, int(round(n / multiple) * multiple))


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
    """Minimal InfiniteTalk I2V graph (no MelBand vocal split)."""
    api_opts = api_opts or {}
    return {
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
            # MultiTalk expects Tencent-style wav2vec weights; HF download node
            # is more reliable than local korean-base hardlink key layout.
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
                # Stronger audio conditioning; cfg>1 allows more motion but weaker lock —
                # keep 1.0 for lip lock smoke (example InfiniteTalk default).
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
        "14": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["10", 0],
                "image_embeds": ["13", 0],
                "steps": steps,
                "cfg": cfg,
                "shift": float(api_opts.get("shift", 11.0)),
                "seed": seed,
                "force_offload": True,
                # Match InfiniteTalk example scheduler more closely
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
            },
        },
        "15": {
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
        },
        "16": {
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
        },
    }


def generate_s2v(
    input_image_path: str,
    audio_path: str,
    output_filename: str | None = None,
    *,
    backend: str = "ltx23_ia2v",
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
    audio_scale: float = 1.5,
    audio_cfg_scale: float = 1.0,
    scheduler: str = "dpm++_sde",
    shift: float = 11.0,
) -> dict:
    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)
    if not os.path.isfile(audio_path):
        return fail_result(error="AUDIO_MISSING", message=audio_path)

    backend = (backend or "ltx23_ia2v").strip().lower()
    if backend not in S2V_BACKENDS:
        return fail_result(
            error="BAD_BACKEND",
            message=f"{backend!r}; choose from {S2V_BACKENDS}",
        )

    if backend == "ltx23_ia2v":
        width = snap_ltx_dim(width, 32)
        height = snap_ltx_dim(height, 32)
        if fps is None or fps <= 0:
            fps = 24.0
    else:
        width = _snap_dim(width, 16)
        height = _snap_dim(height, 16)

    if num_frames is None:
        dur = _probe_audio_duration(audio_path)
        if not dur or dur > 30:
            # bad container metadata (seen with wav copy-slice) — fallback short smoke
            print(f"[WARN] audio duration probe={dur}; using 5.0s for frame count")
            dur = 5.0
        raw_frames = int(round(float(dur) * float(fps)))
        if backend == "ltx23_ia2v":
            num_frames = snap_ltx_frames(raw_frames)
        else:
            num_frames = _snap_frames(raw_frames)
    else:
        if backend == "ltx23_ia2v":
            num_frames = snap_ltx_frames(num_frames)
        else:
            num_frames = _snap_frames(num_frames)

    # MultiTalk window often prefers values like 81; clamp smoke length
    if backend == "infinitetalk":
        if num_frames < 17:
            num_frames = 17
        if num_frames > 129:
            print(f"[WARN] clamping frames {num_frames} -> 81 for smoke stability")
            num_frames = 81
    else:
        if num_frames > 121:
            print(f"[WARN] clamping LTX frames {num_frames} -> 121 for smoke VRAM")
            num_frames = 121

    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    if output_filename is None:
        output_filename = os.path.join(
            os.path.dirname(os.path.abspath(input_image_path)), "s2v_out.mp4"
        )
    ensure_parent_dir(output_filename)

    # copy image + audio into Comfy input
    img_name = "temp_s2v_input.png"
    audio_name = "temp_s2v_drive.wav"
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, img_name))
    audio_abs = os.path.abspath(audio_path)
    # LTX LoadAudio needs file under input/; InfiniteTalk uses abs path but copy is fine
    shutil.copy2(audio_abs, os.path.join(COMFYUI_INPUT_DIR, audio_name))

    if backend == "ltx23_ia2v":
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
            distill_lora=ltx_lora,
        )
        print(
            f"generate_s2v backend=ltx23_ia2v {width}x{height} frames={num_frames} "
            f"fps={fps} seed={seed} (distilled sigma schedule)"
        )
        print(f"  image={input_image_path}")
        print(f"  audio={audio_path}")
        print(f"  unet={ltx_unet}")
        print(f"  lora={ltx_lora}")
    else:
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
    else:
        prefixes = ("agent_ltx_s2v", "agent_s2v")
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

    # Comfy often writes 16 kHz mono AAC (InfiniteTalk/VHS) — many Windows players
    # appear silent. Re-encode to 48 kHz stereo AAC for preview compatibility.
    try:
        nr = normalize_clip_audio(
            output_filename,
            loudnorm=(backend == "ltx23_ia2v"),
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
    p = argparse.ArgumentParser(description="SI2V multi-backend (InfiniteTalk / LTX custom-audio)")
    p.add_argument("--input", "-i", required=True, help="Keyframe image")
    p.add_argument("--audio", "-a", required=True, help="Driving audio")
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--backend",
        default="ltx23_ia2v",
        choices=list(S2V_BACKENDS),
        help="ltx23_ia2v (default, fast agent path) | infinitetalk (hero lips, slow)",
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
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--audio-scale", type=float, default=1.5)
    p.add_argument("--audio-cfg-scale", type=float, default=1.0)
    p.add_argument("--scheduler", default="dpm++_sde")
    p.add_argument("--shift", type=float, default=11.0)
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
    )
    if r.get("ok"):
        print(f"OK {r.get('output_path') or '(dry-run)'}")
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
