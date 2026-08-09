"""LTX 2.3 full-quality spatial upscale for decoded videos (MiniMax H3 work → HD).

Community / CRT path (requires ComfyUI-LTXVideo + crt-nodes):
  VHS_LoadVideo → CRT_LTX23USConfig (V2V images + audio)
  UnetLoaderGGUF (local distilled Q4) + upscale IC-LoRA as model_upscale
  LatentUpscaleModelLoader (spatial x2 1.1)
  CRT_LTX23UnifiedSampler(workflow_mode=V2V, v2v_mode=Upscale)
  → VHS_VideoCombine

Fallback core-only (no refine) is available via path=\"core\" if CRT/LTXVideo broken:
  VAEEncode → LTXVLatentUpsampler → VAEDecode (audio passthrough)

Models (F:\\model via extra_model_paths):
  - diffusion LTX2.3\\\\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf
  - loras LTX2.3\\\\ltx2.3_upscale_ic-lora_06250.safetensors
  - latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors
  - vae/LTX23_video_vae_bf16 + LTX23_audio_vae_bf16
  - text encoders via CRTAutoDLLTX23CLIP (local gemma + projection)
"""

from __future__ import annotations

import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

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
from lib.comfy_engine_session import FAMILY_LTX, ensure_engine
from lib.workflow_video_runner import extract_first_video

SPATIAL_UPSCALER = "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
AUDIO_VAE = "LTX23_audio_vae_bf16.safetensors"
UNET_GGUF = r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf"
UPSCALE_IC_LORA = r"LTX2.3\ltx2.3_upscale_ic-lora_06250.safetensors"

DEFAULT_PROMPT = (
    "high quality, sharp details, clean motion, natural textures, "
    "preserve original composition and identity, crisp anime lines"
)
DEFAULT_NEGATIVE = (
    "blurry, low quality, soft, plastic skin, oversmoothed, watermark, "
    "text, subtitle, jitter, flicker, morphing face"
)


def _stage_video(path: str, server: str) -> str:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"video not found: {src}")
    dest_dir = Path(get_comfy_input_dir(server))
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"ltx_spup_{src.stem[:40]}_{int(time.time() * 1000) % 10_000_000}{src.suffix.lower()}"
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return name


def _resolve_local_video(filename: str, subfolder: str, ftype: str, server: str) -> str:
    if ftype == "temp":
        base = os.path.normpath(os.path.join(get_comfy_output_dir(server), os.pardir, "temp"))
    elif ftype == "input":
        base = get_comfy_input_dir(server)
    else:
        base = get_comfy_output_dir(server)
    parts = [base]
    if subfolder:
        parts.append(subfolder)
    parts.append(filename)
    return os.path.join(*parts)


def build_ltx_spatial_upscale_api(
    *,
    video_basename: str,
    prompt: str = "",
    negative: str = "",
    seed: int = 0,
    steps: int = 4,
    guide_strength: float = 0.45,
    megapixels_target: float = 1.5,
    fps: float = 24.0,
    low_vram: bool = False,
    use_upscale_ic_lora: bool = True,
    upscale_ic_strength: float = 0.75,
    sage_attention: str = "auto",
    filename_prefix: str = "video/ltx_spatial_up",
    path: str = "full",
) -> dict[str, Any]:
    """Build API graph. path=full (CRT IC-LoRA refine) or core (spatial only)."""
    path = (path or "full").strip().lower()
    if path == "core":
        return _build_core_api(
            video_basename=video_basename,
            fps=fps,
            filename_prefix=filename_prefix,
        )
    return _build_full_api(
        video_basename=video_basename,
        prompt=prompt or DEFAULT_PROMPT,
        seed=seed,
        steps=steps,
        guide_strength=guide_strength,
        megapixels_target=megapixels_target,
        fps=fps,
        low_vram=low_vram,
        use_upscale_ic_lora=use_upscale_ic_lora,
        upscale_ic_strength=upscale_ic_strength,
        filename_prefix=filename_prefix,
    )


def _build_core_api(
    *,
    video_basename: str,
    fps: float,
    filename_prefix: str,
) -> dict[str, Any]:
    """Fast spatial-only (no IC-LoRA refine)."""
    return {
        "20": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": video_basename,
                "force_rate": float(fps),
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "LTXV",
            },
        },
        "11": {
            "class_type": "VAELoaderKJ",
            "inputs": {
                "vae_name": VIDEO_VAE,
                "device": "main_device",
                "weight_dtype": "bf16",
            },
        },
        "14": {
            "class_type": "LatentUpscaleModelLoader",
            "inputs": {"model_name": SPATIAL_UPSCALER},
        },
        "30": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["20", 0], "vae": ["11", 0]},
        },
        "40": {
            "class_type": "LTXVLatentUpsampler",
            "inputs": {
                "samples": ["30", 0],
                "upscale_model": ["14", 0],
                "vae": ["11", 0],
            },
        },
        "50": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["40", 0], "vae": ["11", 0]},
        },
        "60": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["50", 0],
                "audio": ["20", 2],
                "frame_rate": float(fps),
                "loop_count": 0,
                "filename_prefix": filename_prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def _build_full_api(
    *,
    video_basename: str,
    prompt: str,
    seed: int,
    steps: int,
    guide_strength: float,
    megapixels_target: float,
    fps: float,
    low_vram: bool,
    use_upscale_ic_lora: bool,
    upscale_ic_strength: float,
    filename_prefix: str,
) -> dict[str, Any]:
    """Community full path: spatial x2 + IC-LoRA guided refine via CRT US."""
    api: dict[str, Any] = {
        "10": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": UNET_GGUF},
        },
        "11": {
            "class_type": "VAELoaderKJ",
            "inputs": {
                "vae_name": VIDEO_VAE,
                "device": "main_device",
                "weight_dtype": "bf16",
            },
        },
        "12": {
            "class_type": "VAELoaderKJ",
            "inputs": {
                "vae_name": AUDIO_VAE,
                "device": "main_device",
                "weight_dtype": "bf16",
            },
        },
        "13": {
            "class_type": "CRTAutoDLLTX23CLIP",
            "inputs": {},
        },
        "14": {
            "class_type": "LatentUpscaleModelLoader",
            "inputs": {"model_name": SPATIAL_UPSCALER},
        },
        "15": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["10", 0],
                "lora_name": UPSCALE_IC_LORA,
                "strength_model": float(upscale_ic_strength if use_upscale_ic_lora else 0.0),
            },
        },
        "20": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": video_basename,
                "force_rate": float(fps),
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "LTXV",
            },
        },
        "30": {
            "class_type": "CRT_LTX23USConfig",
            "inputs": {
                "prompt": (prompt or DEFAULT_PROMPT).strip(),
                "seed": int(seed),
                "Video (V2V image batch)": ["20", 0],
                "source_audio": ["20", 2],
            },
        },
        "40": {
            "class_type": "CRT_LTX23USModelsPipe",
            "inputs": {
                "model": ["10", 0],
                "vae": ["11", 0],
                "audio_vae": ["12", 0],
                "clip": ["13", 0],
                "model_upscale": ["15", 0],
                "spatial_upscale_model": ["14", 0],
                "latent_downscale_factor": 1.0,
            },
        },
        "50": {
            "class_type": "CRT_LTX23UnifiedSampler",
            "inputs": {
                "models_pipe": ["40", 0],
                "config_pipe": ["30", 0],
                "workflow_mode": "V2V",
                "hq": False,
                "live_preview": False,
                "frame_count_from_audio": False,
                "vae_decode_tiled": bool(low_vram),
                "unload_model_before_vae_decode": bool(low_vram),
                "low_vram": bool(low_vram),
                "megapixels_target": float(megapixels_target),
                "aspect_ratio": "16:9 (Landscape)",
                "frame_count": 121,
                "v2v_mode": "Upscale",
                "v2v_guide_strength": float(guide_strength),
                "depth_megapixels": 0.5,
                "v2v_aspect_ratio": "16:9 (Landscape)",
                "sampler_main": "euler_cfg_pp",
                "sampler_refine": "euler_cfg_pp",
                "steps": int(steps),
                "generated_audio_gain_db": 0.0,
                "firstframe_strength": 1.0,
                "depth_mouth_mask": False,
                "mouth_detect_megapixels": 0.3,
                "mouth_single_item": True,
                "mouth_detect_chunk_size": 8,
                "mouth_mask_expand": 0,
                "mouth_mask_blur": 0.0,
            },
        },
        "60": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["50", 0],
                "audio": ["50", 1],
                "frame_rate": float(fps),
                "loop_count": 0,
                "filename_prefix": filename_prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }
    return api


def ltx_spatial_upscale_video(
    *,
    input_path: str,
    output_path: str,
    prompt: str | None = None,
    negative: str | None = None,
    seed: int | None = None,
    steps: int = 4,
    guide_strength: float = 0.45,
    megapixels_target: float = 1.5,
    fps: float = 24.0,
    low_vram: bool = False,
    use_upscale_ic_lora: bool = True,
    upscale_ic_strength: float = 0.75,
    path: str = "full",
    timeout_sec: float = 1800.0,
    server_address: str = DEFAULT_SERVER,
    free_policy: str | None = None,
) -> dict[str, Any]:
    """Upscale video. path=full (default, community quality) or core (fast spatial)."""
    if not os.path.isfile(input_path):
        return fail_result(error="SOURCE_MISSING", message=input_path)

    seed_v = int(seed if seed is not None else random.randint(0, 2**63 - 1))
    prompt_v = (prompt or DEFAULT_PROMPT).strip()
    path_v = (path or "full").strip().lower()

    try:
        ensure_engine(
            FAMILY_LTX,
            server_address=server_address,
            policy=free_policy,
            caller="ltx_spatial_upscale",
            enforce_threshold=False,
        )
    except Exception as e:
        return fail_result(error="engine_session", message=str(e))

    try:
        vid_name = _stage_video(input_path, server_address)
    except Exception as e:
        return fail_result(error="stage_video", message=str(e))

    api = build_ltx_spatial_upscale_api(
        video_basename=vid_name,
        prompt=prompt_v,
        negative=negative or DEFAULT_NEGATIVE,
        seed=seed_v,
        steps=steps,
        guide_strength=guide_strength,
        megapixels_target=megapixels_target,
        fps=fps,
        low_vram=low_vram,
        use_upscale_ic_lora=use_upscale_ic_lora,
        upscale_ic_strength=upscale_ic_strength,
        path=path_v,
    )

    t0 = time.time()
    try:
        prompt_id = queue_prompt(server_address, api)
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
        fn, sub, ftype = extract_first_video(history)
        src = _resolve_local_video(fn, sub, ftype, server_address)
        ensure_parent_dir(output_path)
        if os.path.isfile(src):
            shutil.copy2(src, output_path)
        else:
            from lib.comfy_client import download_image

            download_image(server_address, fn, sub, ftype, output_path)
    except Exception as e:
        return fail_result(error="comfy_run", message=str(e), seed=seed_v, path=path_v)

    elapsed = round(time.time() - t0, 2)
    meta = {
        "tool": "ltx_spatial_upscale",
        "backend": f"ltx23_spatial_x2_{path_v}",
        "path": path_v,
        "input_path": os.path.abspath(input_path),
        "output_path": os.path.abspath(output_path),
        "seed": seed_v,
        "steps": steps if path_v == "full" else None,
        "guide_strength": guide_strength if path_v == "full" else None,
        "megapixels_target": megapixels_target if path_v == "full" else None,
        "fps": fps,
        "prompt": prompt_v if path_v == "full" else None,
        "prompt_id": prompt_id,
        "elapsed_sec": elapsed,
        "spatial_upscaler": SPATIAL_UPSCALER,
        "created_at": utc_now_iso(),
        "notes": (
            "full = CRT V2V Upscale + IC-LoRA refine (community quality). "
            "core = latent spatial x2 only (fast, less detail)."
        ),
    }
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    try:
        write_meta(meta_path, meta)
    except Exception:
        meta_path = None

    return ok_result(
        output=output_path,
        output_path=output_path,
        seed=seed_v,
        prompt_id=prompt_id,
        elapsed_sec=elapsed,
        meta_path=meta_path,
        backend=meta["backend"],
        path=path_v,
    )
