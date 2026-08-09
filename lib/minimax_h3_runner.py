"""MiniMax H3 open-weights video (T2V / I2V / R2V) — native ComfyUI nodes.

SSOT models (Comfy-Org/MiniMax-H3, pruned int8 low-VRAM pack):
  F:\\model\\diffusion_models\\MinimaxH3\\minimax_h3_fl2va_pruned_int8_convrot.safetensors  # T2V/I2V
  F:\\model\\diffusion_models\\MinimaxH3\\minimax_h3_ref2va_pruned_int8_convrot.safetensors # R2V
  F:\\model\\text_encoders\\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
  F:\\model\\vae\\minimax_h3_video_vae_fp16.safetensors
  F:\\model\\vae\\minimax_h3_audio_vae_fp32.safetensors

Native nodes: MiniMaxH3ImageToVideo (T2V/I2V/FL) · MiniMaxH3ReferenceToVideo (R2V).
Native stereo audio is decoded with the audio VAE and muxed into MP4.

Bench (RTX 4090, 5s, 20 steps, same prompt, 2026-08-07):
  0.4 MP 864x480  ~113s end-to-end
  0.98 MP 1344x768 ~378s end-to-end (native short-edge 768)
"""

from __future__ import annotations

import os
import random
import shutil
import time
from pathlib import Path
from typing import Any, Sequence

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    get_comfy_input_dir,
    get_comfy_output_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import FAMILY_MINIMAX_H3, ensure_engine
from lib.workflow_video_runner import extract_first_video

UNET_FL2VA = r"MinimaxH3\minimax_h3_fl2va_pruned_int8_convrot.safetensors"
UNET_REF2VA = r"MinimaxH3\minimax_h3_ref2va_pruned_int8_convrot.safetensors"
CLIP_NAME = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VAE_VIDEO = "minimax_h3_video_vae_fp16.safetensors"
VAE_AUDIO = "minimax_h3_audio_vae_fp32.safetensors"

# Duration (sec) → frame length on 17k+5 grid @24fps (official template expression)
LENGTH_EXPR = "max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17"

# Agent quality tiers (ResolutionSelector megapixels + defaults)
PROFILES: dict[str, dict[str, Any]] = {
    "draft": {
        "megapixels": 0.3,
        "duration": 3.0,
        "steps": 16,
        "notes": "scout ~736x416 @16:9; fast prompt iterate",
    },
    "work": {
        "megapixels": 0.4,
        "duration": 5.0,
        "steps": 20,
        "notes": "DEFAULT agent work ~864x480; ~2min on 4090 / 5s",
    },
    "native": {
        "megapixels": 0.98,
        "duration": 5.0,
        "steps": 20,
        "notes": "H3 native canvas ~1344x768; ~6min on 4090 / 5s",
    },
    "hero": {
        "megapixels": 0.98,
        "duration": 5.0,
        "steps": 24,
        "notes": "native res + extra steps for hero stills-as-video",
    },
}

ASPECT_MAP = {
    "16:9": "16:9 (Widescreen)",
    "9:16": "9:16 (Portrait Widescreen)",
    "1:1": "1:1 (Square)",
    "cinematic_16x9": "16:9 (Widescreen)",
    "shorts_9x16": "9:16 (Portrait Widescreen)",
    "square_1x1": "1:1 (Square)",
}


def list_profiles() -> dict[str, dict[str, Any]]:
    return dict(PROFILES)


def _stage_image(path: str, server: str) -> str:
    """Copy local image into Comfy input; return basename for LoadImage."""
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"image not found: {src}")
    dest_dir = Path(get_comfy_input_dir(server))
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Stable unique-ish name to avoid collisions
    stem = src.stem[:40]
    name = f"mmh3_{stem}_{int(time.time() * 1000) % 10_000_000}{src.suffix.lower()}"
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return name


def _resolve_local_video(filename: str, subfolder: str, ftype: str, server: str) -> str:
    if ftype == "temp":
        # Prefer live temp if present
        base = os.path.join(get_comfy_output_dir(server), os.pardir, "temp")
        base = os.path.normpath(base)
    elif ftype == "input":
        base = get_comfy_input_dir(server)
    else:
        base = get_comfy_output_dir(server)
    parts = [base]
    if subfolder:
        parts.append(subfolder)
    parts.append(filename)
    return os.path.join(*parts)


def build_api_prompt(
    *,
    task: str,
    prompt: str,
    seed: int,
    duration: float,
    megapixels: float,
    steps: int,
    aspect_ratio: str = "16:9 (Widescreen)",
    first_frame_name: str | None = None,
    last_frame_name: str | None = None,
    ref_image_names: Sequence[str] | None = None,
    ref_image_size: str = "match",
    filename_prefix: str = "video/MiniMax_H3_agent",
    sampler_name: str = "res_multistep",
    scheduler: str = "simple",
    fps: float = 24.0,
) -> dict[str, Any]:
    """Build a flat API graph for MiniMax H3."""
    task = (task or "t2v").strip().lower()
    if task not in ("t2v", "i2v", "r2v", "flf"):
        raise ValueError(f"unknown task {task!r}; use t2v|i2v|r2v|flf")

    use_r2v = task == "r2v"
    unet = UNET_REF2VA if use_r2v else UNET_FL2VA

    # Node id layout (stable for meta / debugging)
    api: dict[str, Any] = {
        "92": {
            "class_type": "SaveVideo",
            "inputs": {
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
                "video": ["130", 0],
            },
        },
        "115": {
            "class_type": "ResolutionSelector",
            "inputs": {
                "aspect_ratio": aspect_ratio,
                "megapixels": float(megapixels),
                "multiple": 32,
            },
        },
        "119": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE_VIDEO},
        },
        "120": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE_AUDIO},
        },
        "121": {
            "class_type": "VAEDecodeAudio",
            "inputs": {"samples": ["125", 0], "vae": ["120", 0]},
        },
        "122": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["125", 0], "vae": ["119", 0]},
        },
        "123": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": sampler_name},
        },
        "124": {
            "class_type": "BasicScheduler",
            "inputs": {
                "scheduler": scheduler,
                "steps": int(steps),
                "denoise": 1.0,
                "model": ["127", 0],
            },
        },
        "125": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["129", 0],
                "guider": ["126", 0],
                "sampler": ["123", 0],
                "sigmas": ["124", 0],
                "latent_image": ["131", 1],
            },
        },
        "126": {
            "class_type": "BasicGuider",
            "inputs": {"model": ["127", 0], "conditioning": ["131", 0]},
        },
        "127": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet, "weight_dtype": "default"},
        },
        "128": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": CLIP_NAME,
                "type": "minimax",
                "device": "default",
            },
        },
        "129": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": int(seed)},
        },
        "130": {
            "class_type": "CreateVideo",
            "inputs": {
                "fps": float(fps),
                "bit_depth": 8,
                "images": ["122", 0],
                "audio": ["121", 0],
            },
        },
        "132": {
            "class_type": "ComfyMathExpression",
            "inputs": {
                "expression": LENGTH_EXPR,
                "values.a": ["133", 0],
            },
        },
        "133": {
            "class_type": "PrimitiveFloat",
            "inputs": {"value": float(duration)},
            "_meta": {"title": "Float (duration)"},
        },
    }

    if use_r2v:
        refs = list(ref_image_names or [])
        if not refs:
            raise ValueError("r2v requires at least one --ref-image")
        ref_inputs: dict[str, Any] = {
            "clip": ["128", 0],
            "vae": ["119", 0],
            "audio_vae": ["120", 0],
            "prompt": prompt,
            "width": ["115", 0],
            "height": ["115", 1],
            "length": ["132", 1],
            "ref_image_size": ref_image_size or "match",
        }
        for i, name in enumerate(refs[:9]):
            load_id = str(200 + i)
            api[load_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": name},
            }
            ref_inputs[f"ref_images.ref_image_{i}"] = [load_id, 0]
        api["131"] = {
            "class_type": "MiniMaxH3ReferenceToVideo",
            "inputs": ref_inputs,
        }
    else:
        cond: dict[str, Any] = {
            "clip": ["128", 0],
            "vae": ["119", 0],
            "prompt": prompt,
            "width": ["115", 0],
            "height": ["115", 1],
            "length": ["132", 1],
        }
        if first_frame_name:
            api["140"] = {
                "class_type": "LoadImage",
                "inputs": {"image": first_frame_name},
            }
            cond["first_frame"] = ["140", 0]
        if last_frame_name:
            api["141"] = {
                "class_type": "LoadImage",
                "inputs": {"image": last_frame_name},
            }
            cond["last_frame"] = ["141", 0]
        if task in ("i2v", "flf") and not first_frame_name:
            raise ValueError(f"{task} requires --image / first frame")
        if task == "flf" and not last_frame_name:
            raise ValueError("flf requires --last / last frame")
        api["131"] = {
            "class_type": "MiniMaxH3ImageToVideo",
            "inputs": cond,
        }

    return api


def generate_minimax_h3(
    *,
    prompt: str,
    output_path: str,
    task: str = "t2v",
    image_path: str | None = None,
    last_image_path: str | None = None,
    ref_images: Sequence[str] | None = None,
    seed: int | None = None,
    duration: float | None = None,
    megapixels: float | None = None,
    steps: int | None = None,
    profile: str = "work",
    aspect: str = "16:9",
    ref_image_size: str = "match",
    filename_prefix: str = "video/MiniMax_H3_agent",
    timeout_sec: float = 1800.0,
    server_address: str = DEFAULT_SERVER,
    free_policy: str | None = None,
) -> dict[str, Any]:
    """Queue MiniMax H3 and copy the resulting MP4 to output_path."""
    prompt = (prompt or "").strip()
    if not prompt:
        return fail_result(error="missing_prompt", message="prompt is required")

    prof_name = (profile or "work").strip().lower()
    if prof_name not in PROFILES:
        return fail_result(
            error="bad_profile",
            message=f"unknown profile {profile!r}; choose {list(PROFILES)}",
        )
    prof = PROFILES[prof_name]
    duration_v = float(duration if duration is not None else prof["duration"])
    megapixels_v = float(megapixels if megapixels is not None else prof["megapixels"])
    steps_v = int(steps if steps is not None else prof["steps"])
    seed_v = int(seed if seed is not None else random.randint(0, 2**63 - 1))

    aspect_key = (aspect or "16:9").strip()
    aspect_ratio = ASPECT_MAP.get(aspect_key, aspect_key)
    if aspect_ratio not in ASPECT_MAP.values() and "(" not in aspect_ratio:
        # allow raw Comfy combo strings
        aspect_ratio = ASPECT_MAP.get("16:9", "16:9 (Widescreen)")

    task_v = (task or "t2v").strip().lower()
    if task_v == "i2v" and last_image_path and image_path:
        task_v = "flf"  # first+last convenience

    try:
        ensure_engine(
            FAMILY_MINIMAX_H3,
            server_address=server_address,
            policy=free_policy,
            caller="minimax_h3",
        )
    except Exception as e:
        return fail_result(error="engine_session", message=str(e))

    first_name = last_name = None
    ref_names: list[str] = []
    try:
        if image_path:
            first_name = _stage_image(image_path, server_address)
        if last_image_path:
            last_name = _stage_image(last_image_path, server_address)
        for p in ref_images or []:
            ref_names.append(_stage_image(p, server_address))
    except Exception as e:
        return fail_result(error="stage_image", message=str(e))

    try:
        api = build_api_prompt(
            task=task_v,
            prompt=prompt,
            seed=seed_v,
            duration=duration_v,
            megapixels=megapixels_v,
            steps=steps_v,
            aspect_ratio=aspect_ratio,
            first_frame_name=first_name,
            last_frame_name=last_name,
            ref_image_names=ref_names,
            ref_image_size=ref_image_size,
            filename_prefix=filename_prefix,
        )
    except Exception as e:
        return fail_result(error="build_graph", message=str(e))

    t0 = time.time()
    try:
        prompt_id = queue_prompt(server_address, api)
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
        fn, sub, ftype = extract_first_video(history)
        src = _resolve_local_video(fn, sub, ftype, server_address)
        if not os.path.isfile(src):
            # fallback: download via /view
            from lib.comfy_client import download_image

            ensure_parent_dir(output_path)
            download_image(server_address, fn, sub, ftype, output_path)
            dest = output_path
        else:
            ensure_parent_dir(output_path)
            shutil.copy2(src, output_path)
            dest = output_path
    except Exception as e:
        return fail_result(
            error="comfy_run",
            message=str(e),
            seed=seed_v,
            task=task_v,
            profile=prof_name,
        )

    elapsed = round(time.time() - t0, 2)
    meta = {
        "tool": "minimax_h3",
        "task": task_v,
        "profile": prof_name,
        "seed": seed_v,
        "duration_sec": duration_v,
        "megapixels": megapixels_v,
        "steps": steps_v,
        "aspect": aspect_ratio,
        "prompt": prompt,
        "unet": UNET_REF2VA if task_v == "r2v" else UNET_FL2VA,
        "prompt_id": prompt_id,
        "elapsed_sec": elapsed,
        "output_path": dest,
        "comfy_video": {"filename": fn, "subfolder": sub, "type": ftype},
        "created_at": utc_now_iso(),
        "models": {
            "diffusion": UNET_REF2VA if task_v == "r2v" else UNET_FL2VA,
            "text_encoder": CLIP_NAME,
            "vae_video": VAE_VIDEO,
            "vae_audio": VAE_AUDIO,
        },
        "bench_note": (
            "4090: work 0.4MP 5s ~113s; native 0.98MP 5s ~378s (2026-08-07)"
        ),
    }
    meta_path = resolve_meta_path(dest)
    try:
        write_meta(meta_path, meta)
    except Exception:
        meta_path = None

    return ok_result(
        output=dest,
        output_path=dest,
        seed=seed_v,
        prompt_id=prompt_id,
        task=task_v,
        profile=prof_name,
        elapsed_sec=elapsed,
        megapixels=megapixels_v,
        duration_sec=duration_v,
        steps=steps_v,
        meta_path=meta_path,
        unet=meta["unet"],
    )


def resolve_meta_path(output_path: str) -> str:
    base, _ = os.path.splitext(output_path)
    return base + ".meta.json"
