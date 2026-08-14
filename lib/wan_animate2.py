"""
Wan-Animate-2 (2026-08) — character still + driving video → motion transfer.

Native ComfyUI nodes (WanAnimate2ToVideo). No pose/skeleton extract.
Background and camera come from the text prompt, not the driving clip.

Validated 2026-08-14 on RTX 4090 24GB:
  wan_animate_2_int8_convrot + LightX2V 480p LoRA + LCM 6 step + cache CPU
  480x832 / 81 frames / street_dance_drive → identity + dance phrase transfer.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    ensure_comfy_running,
    fail_result,
    get_comfy_input_dir,
    get_comfy_output_dir,
    history_execution_error,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)

DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 832
DEFAULT_FRAMES = 81
DEFAULT_STEPS = 6
DEFAULT_CFG = 1.0
DEFAULT_SHIFT = 5.0
DEFAULT_POSE_STRENGTH = 1.0
DEFAULT_REF_STRENGTH = 1.0

DEFAULT_UNET = "wan_animate_2_int8_convrot.safetensors"
DEFAULT_LORA = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
DEFAULT_CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
DEFAULT_CLIP_VISION = "clip_vision_h.safetensors"
DEFAULT_VAE = "wan_2.1_vae.safetensors"

DEFAULT_NEGATIVE = (
    "static, blurry, low quality, extra fingers, extra limbs, "
    "deformed face, watermark, text, crowded background"
)
DEFAULT_POSE_PROMPT = "a person dancing, background stationary"
DEFAULT_BACKGROUND = "Plain light gray studio background, soft even lighting, no decorations."


def snap_wan_frames(n: int) -> int:
    n = max(5, int(n))
    return ((n - 1) // 4) * 4 + 1


def stage_to_comfy_input(src: str, name: str | None = None) -> str:
    import uuid

    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    inp = get_comfy_input_dir()
    os.makedirs(inp, exist_ok=True)
    base = name or f"wan_animate2_{uuid.uuid4().hex[:10]}{os.path.splitext(src)[1]}"
    shutil.copy2(src, os.path.join(inp, base))
    return base


def compose_positive(look: str, background: str, prompt: str) -> str:
    raw = (prompt or "").strip()
    if raw and (
        "Character appearance" in raw
        or "인물" in raw
        or "Background description" in raw
    ):
        return raw
    look_s = (look or raw or "the character from the reference image").strip()
    bg_s = (background or DEFAULT_BACKGROUND).strip()
    return (
        f"Character appearance description: {look_s}\n"
        f"Background description: {bg_s}"
    )


def build_animate2_api(
    *,
    image_name: str,
    video_name: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    shift: float = DEFAULT_SHIFT,
    seed: int = 42,
    pose_strength: float = DEFAULT_POSE_STRENGTH,
    reference_image_strength: float = DEFAULT_REF_STRENGTH,
    positive: str,
    negative: str,
    pose_prompt: str,
    filename_prefix: str = "wan_animate2/WanAnimate2",
    unet_name: str = DEFAULT_UNET,
    lora_name: str = DEFAULT_LORA,
    clip_name: str = DEFAULT_CLIP,
    clip_vision_name: str = DEFAULT_CLIP_VISION,
    vae_name: str = DEFAULT_VAE,
    cache_device: str = "cpu",
    cache_dtype: str = "int8",
) -> dict[str, Any]:
    frames = snap_wan_frames(num_frames)
    return {
        "10": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "11": {"class_type": "LoadVideo", "inputs": {"file": video_name}},
        "12": {
            "class_type": "GetVideoComponents",
            "inputs": {"video": ["11", 0]},
        },
        "20": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet_name, "weight_dtype": "default"},
        },
        "21": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["20", 0],
                "lora_name": lora_name,
                "strength_model": 1.0,
            },
        },
        "22": {
            "class_type": "WanAnimate2Cache",
            "inputs": {
                "model": ["21", 0],
                "device": cache_device,
                "dtype": cache_dtype,
            },
        },
        "23": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": clip_name,
                "type": "wan",
                "device": "default",
            },
        },
        "24": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": clip_vision_name},
        },
        "25": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        },
        "30": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["23", 0], "text": positive},
        },
        "31": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["23", 0], "text": negative or DEFAULT_NEGATIVE},
        },
        "32": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["23", 0],
                "text": pose_prompt or DEFAULT_POSE_PROMPT,
            },
        },
        "40": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["10", 0],
                "upscale_method": "area",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        },
        "41": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["12", 0],
                "upscale_method": "area",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        },
        "42": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["24", 0],
                "image": ["40", 0],
                "crop": "none",
            },
        },
        "43": {
            "class_type": "ImageFromBatch",
            "inputs": {"image": ["41", 0], "batch_index": 0, "length": 1},
        },
        "44": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["24", 0],
                "image": ["43", 0],
                "crop": "none",
            },
        },
        "50": {
            "class_type": "WanAnimate2ToVideo",
            "inputs": {
                "positive": ["30", 0],
                "negative": ["31", 0],
                "vae": ["25", 0],
                "reference_image": ["40", 0],
                "pose_video": ["41", 0],
                "clip_vision_output": ["42", 0],
                "positive_pose": ["32", 0],
                "clip_vision_output_pose": ["44", 0],
                "width": int(width),
                "height": int(height),
                "length": int(frames),
                "batch_size": 1,
                "video_frame_offset": 0,
                "pose_strength": float(pose_strength),
                "pose_start_percent": 0.0,
                "pose_end_percent": 1.0,
                "reference_image_strength": float(reference_image_strength),
            },
        },
        "60": {
            "class_type": "ModelSamplingSD3",
            "inputs": {"model": ["22", 0], "shift": float(shift)},
        },
        "61": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "lcm"},
        },
        "62": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["22", 0],
                "scheduler": "simple",
                "steps": int(steps),
                "denoise": 1.0,
            },
        },
        "63": {
            "class_type": "SamplerCustom",
            "inputs": {
                "model": ["60", 0],
                "add_noise": True,
                "noise_seed": int(seed),
                "cfg": float(cfg),
                "positive": ["50", 0],
                "negative": ["50", 1],
                "sampler": ["61", 0],
                "sigmas": ["62", 0],
                "latent_image": ["50", 2],
            },
        },
        "70": {
            "class_type": "TrimVideoLatent",
            "inputs": {"samples": ["63", 0], "trim_amount": ["50", 3]},
        },
        "71": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["70", 0], "vae": ["25", 0]},
        },
        "80": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["71", 0],
                "fps": ["12", 2],
                "audio": ["12", 1],
            },
        },
        "81": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["80", 0],
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
            },
        },
    }


def _extract_video(hist: dict) -> tuple[str, str, str]:
    for _nid, node_out in (hist.get("outputs") or {}).items():
        for key in ("gifs", "videos", "images"):
            items = node_out.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
    raise FileNotFoundError(f"No video outputs: {list((hist.get('outputs') or {}).keys())}")


def generate_wan_animate2(
    character_image: str,
    reference_video: str,
    output_path: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    shift: float = DEFAULT_SHIFT,
    seed: int | None = None,
    pose_strength: float = DEFAULT_POSE_STRENGTH,
    reference_image_strength: float = DEFAULT_REF_STRENGTH,
    prompt: str = "",
    look: str = "",
    background: str = "",
    pose_prompt: str = "",
    negative: str = "",
    cache_device: str = "cpu",
    cache_dtype: str = "int8",
    filename_prefix: str = "wan_animate2/WanAnimate2",
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not os.path.isfile(character_image):
        return fail_result(error="SOURCE_MISSING", message=character_image)
    if not os.path.isfile(reference_video):
        return fail_result(error="VIDEO_MISSING", message=reference_video)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    frames = snap_wan_frames(num_frames)
    seed_i = int(seed if seed is not None else 42)
    positive = compose_positive(look, background, prompt)

    api = build_animate2_api(
        image_name="__img__",
        video_name="__vid__",
        width=width,
        height=height,
        num_frames=frames,
        steps=steps,
        cfg=cfg,
        shift=shift,
        seed=seed_i,
        pose_strength=pose_strength,
        reference_image_strength=reference_image_strength,
        positive=positive,
        negative=negative,
        pose_prompt=pose_prompt or DEFAULT_POSE_PROMPT,
        filename_prefix=filename_prefix,
        cache_device=cache_device,
        cache_dtype=cache_dtype,
    )

    meta: dict[str, Any] = {
        "tool": "generate_wan_animate2",
        "created_at": utc_now_iso(),
        "character_image": os.path.abspath(character_image),
        "reference_video": os.path.abspath(reference_video),
        "width": width,
        "height": height,
        "num_frames": frames,
        "steps": steps,
        "cfg": cfg,
        "seed": seed_i,
        "pose_strength": pose_strength,
        "reference_image_strength": reference_image_strength,
        "cache_device": cache_device,
        "positive": positive,
        "pose_prompt": pose_prompt or DEFAULT_POSE_PROMPT,
    }

    if dry_run:
        meta["dry_run"] = True
        meta["api_node_count"] = len(api)
        if meta_out:
            write_meta(meta_out, meta)
        return ok_result(output_path=None, meta_path=meta_out, **meta)

    ensure_comfy_running(server_address)
    try:
        iname = stage_to_comfy_input(os.path.abspath(character_image))
        vname = stage_to_comfy_input(os.path.abspath(reference_video))
    except Exception as e:
        return fail_result(error="STAGE_FAILED", message=str(e), **meta)

    api["10"]["inputs"]["image"] = iname
    api["11"]["inputs"]["file"] = vname
    meta["comfy_image"] = iname
    meta["comfy_video"] = vname

    t0 = time.time()
    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), **meta)

    meta["prompt_id"] = prompt_id
    try:
        hist = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(
            error="WAIT_FAILED", message=str(e), prompt_id=prompt_id, **meta
        )

    err = history_execution_error(hist)
    if err:
        return fail_result(
            error="EXECUTION_ERROR", message=err, prompt_id=prompt_id, **meta
        )

    try:
        fn, sub, typ = _extract_video(hist)
    except Exception as e:
        return fail_result(
            error="EXTRACT_FAILED", message=str(e), prompt_id=prompt_id, **meta
        )

    comfy_out = get_comfy_output_dir(server_address)
    src = os.path.join(comfy_out, sub, fn) if sub else os.path.join(comfy_out, fn)
    try:
        if os.path.isfile(src):
            shutil.copy2(src, output_path)
        else:
            download_image(server_address, fn, sub, typ, output_path)
    except Exception as e:
        return fail_result(error="COPY_FAILED", message=str(e), **meta)

    elapsed = round(time.time() - t0, 1)
    meta.update(
        {
            "ok": True,
            "output_path": os.path.abspath(output_path),
            "elapsed_sec": elapsed,
            "comfy_filename": fn,
            "subfolder": sub,
        }
    )
    if meta_out:
        write_meta(meta_out, meta)
        meta["meta_path"] = meta_out
    return ok_result(**meta)
