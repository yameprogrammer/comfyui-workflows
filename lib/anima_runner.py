"""Anima & Anima-LLLite Execution Runner for AI Agent.

Provides direct, programmatic execution of Anima DiT 2B and Anima-LLLite ControlNet
pipelines via ComfyUI API.

Supported modes:
  - t2i: Base Text to Image anime generation
  - lineart: Sketch / manga lineart auto-coloring
  - depth: Spatial / perspective depth-guided generation
  - pose: OpenPose / skeleton body pose lock
  - inpaint: 4-channel anime inpainting & localized retouching
  - all_control: Chained multi-control (Lineart + Depth + Pose)
  - hires: 2-pass latent upscale & anime detailer (2K/4K)
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
    download_image,
    extract_first_image,
    fail_result,
    get_comfy_input_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)

DEFAULT_UNET = "anima-base-v1.0.safetensors"
DEFAULT_CLIP = "qwen_3_06b_base.safetensors"
DEFAULT_VAE = "qwen_image_vae.safetensors"
DEFAULT_TURBO_LORA = "anima-turbo-lora-v0.2.safetensors"

DEFAULT_LINEART_PATCH = "anima-lllite-lineart-1.safetensors"
DEFAULT_DEPTH_PATCH = "anima-lllite-depth-1.safetensors"
DEFAULT_POSE_PATCH = "anima-lllite-pose-1.safetensors"
DEFAULT_INPAINT_PATCH = "anima-lllite-inpainting-v2.safetensors"

DEFAULT_POSITIVE = "1girl, anime masterpiece, exquisite face, detailed lighting, rich colors, studio quality, 8k render"
DEFAULT_NEGATIVE = "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, extra limbs, bad anatomy, deformed"


def _upload_file_to_comfy_input(local_path: str | Path, server_url: str = DEFAULT_SERVER) -> str:
    """Ensure image exists in ComfyUI input directory."""
    if not local_path or not os.path.isfile(local_path):
        raise FileNotFoundError(f"Input file not found: {local_path}")
    
    input_dir = get_comfy_input_dir(server_url)
    filename = os.path.basename(local_path)
    dst = os.path.join(input_dir, filename)
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(local_path):
        shutil.copy2(local_path, dst)
    return filename


def build_anima_api_prompt(
    mode: str = "t2i",
    prompt: str = DEFAULT_POSITIVE,
    negative: str = DEFAULT_NEGATIVE,
    width: int = 832,
    height: int = 1216,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 4.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    denoise: float = 1.0,
    turbo: bool = False,
    control_strength: float = 1.0,
    image_filename: str | None = None,
    mask_filename: str | None = None,
    lineart_filename: str | None = None,
    depth_filename: str | None = None,
    pose_filename: str | None = None,
) -> dict[str, Any]:
    """Assemble a standalone, pristine ComfyUI API graph for Anima."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)
        
    if turbo:
        steps = 8
        cfg = 1.0

    nodes: dict[str, Any] = {}
    
    # 1. Base Model Loaders
    nodes["1"] = {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": DEFAULT_UNET, "weight_dtype": "default"}
    }
    nodes["2"] = {
        "class_type": "CLIPLoader",
        "inputs": {"clip_name": DEFAULT_CLIP, "type": "stable_diffusion"}
    }
    nodes["3"] = {
        "class_type": "VAELoader",
        "inputs": {"vae_name": DEFAULT_VAE}
    }
    
    # Current active model reference
    active_model = ["1", 0]
    
    # Optional Turbo LoRA
    if turbo:
        nodes["4"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": active_model,
                "lora_name": DEFAULT_TURBO_LORA,
                "strength_model": 1.0
            }
        }
        active_model = ["4", 0]
        
    # Text Conditioning
    nodes["5"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt, "clip": ["2", 0]}
    }
    nodes["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": ["2", 0]}
    }

    # =========================================================================
    # Mode-specific graph routing
    # =========================================================================
    if mode == "t2i":
        nodes["7"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        }
        nodes["8"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": active_model,
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": denoise
            }
        }
        nodes["9"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["8", 0], "vae": ["3", 0]}
        }
        nodes["10"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": "Anima_T2I"}
        }

    elif mode in ("lineart", "depth", "pose"):
        patch_file = DEFAULT_LINEART_PATCH if mode == "lineart" else (DEFAULT_DEPTH_PATCH if mode == "depth" else DEFAULT_POSE_PATCH)
        prefix = f"Anima_{mode.capitalize()}"
        
        nodes["7"] = {
            "class_type": "ModelPatchLoader",
            "inputs": {"name": patch_file}
        }
        nodes["8"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename or "example.png"}
        }
        nodes["9"] = {
            "class_type": "AnimaLLLiteApply",
            "inputs": {
                "model": active_model,
                "model_patch": ["7", 0],
                "image": ["8", 0],
                "strength": control_strength,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        }
        nodes["10"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        }
        nodes["11"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["9", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["10", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": denoise
            }
        }
        nodes["12"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["11", 0], "vae": ["3", 0]}
        }
        nodes["13"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["12", 0], "filename_prefix": prefix}
        }

    elif mode == "inpaint":
        nodes["7"] = {
            "class_type": "ModelPatchLoader",
            "inputs": {"name": DEFAULT_INPAINT_PATCH}
        }
        nodes["8"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename or "example.png"}
        }
        # If separate mask image provided, load it; else use LoadImage mask
        mask_ref = ["8", 1]
        if mask_filename:
            nodes["14"] = {
                "class_type": "LoadImage",
                "inputs": {"image": mask_filename}
            }
            nodes["15"] = {
                "class_type": "ImageToMask",
                "inputs": {"image": ["14", 0], "channel": "red"}
            }
            mask_ref = ["15", 0]

        nodes["9"] = {
            "class_type": "AnimaLLLiteApply",
            "inputs": {
                "model": active_model,
                "model_patch": ["7", 0],
                "image": ["8", 0],
                "mask": mask_ref,
                "strength": control_strength,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        }
        nodes["10"] = {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {
                "pixels": ["8", 0],
                "vae": ["3", 0],
                "mask": mask_ref,
                "grow_mask_by": 6
            }
        }
        nodes["11"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["9", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["10", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": denoise if denoise < 1.0 else 0.75
            }
        }
        nodes["12"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["11", 0], "vae": ["3", 0]}
        }
        nodes["13"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["12", 0], "filename_prefix": "Anima_Inpainted"}
        }

    elif mode in ("all_control", "multicontrol"):
        # Chain 3 controls: Lineart -> Depth -> Pose
        nodes["7"] = {"class_type": "ModelPatchLoader", "inputs": {"name": DEFAULT_LINEART_PATCH}}
        nodes["8"] = {"class_type": "ModelPatchLoader", "inputs": {"name": DEFAULT_DEPTH_PATCH}}
        nodes["9"] = {"class_type": "ModelPatchLoader", "inputs": {"name": DEFAULT_POSE_PATCH}}
        
        nodes["10"] = {"class_type": "LoadImage", "inputs": {"image": lineart_filename or image_filename or "lineart.png"}}
        nodes["11"] = {"class_type": "LoadImage", "inputs": {"image": depth_filename or image_filename or "depth.png"}}
        nodes["12"] = {"class_type": "LoadImage", "inputs": {"image": pose_filename or image_filename or "pose.png"}}
        
        nodes["13"] = {
            "class_type": "AnimaLLLiteApply",
            "inputs": {
                "model": active_model,
                "model_patch": ["7", 0],
                "image": ["10", 0],
                "strength": 0.8,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        }
        nodes["14"] = {
            "class_type": "AnimaLLLiteApply",
            "inputs": {
                "model": ["13", 0],
                "model_patch": ["8", 0],
                "image": ["11", 0],
                "strength": 0.6,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        }
        nodes["15"] = {
            "class_type": "AnimaLLLiteApply",
            "inputs": {
                "model": ["14", 0],
                "model_patch": ["9", 0],
                "image": ["12", 0],
                "strength": 0.8,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        }
        nodes["16"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        }
        nodes["17"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["15", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["16", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": denoise
            }
        }
        nodes["18"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["17", 0], "vae": ["3", 0]}
        }
        nodes["19"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["18", 0], "filename_prefix": "Anima_AllControl"}
        }

    elif mode in ("hires", "upscale"):
        nodes["7"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        }
        nodes["8"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": active_model,
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0
            }
        }
        nodes["9"] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": ["8", 0],
                "upscale_method": "nearest-exact",
                "scale_by": 1.5
            }
        }
        nodes["10"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": active_model,
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["9", 0],
                "seed": seed,
                "steps": 20,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 0.38
            }
        }
        nodes["11"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["10", 0], "vae": ["3", 0]}
        }
        nodes["12"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["11", 0], "filename_prefix": "Anima_HiRes"}
        }

    return nodes


def generate_anima(
    prompt: str = DEFAULT_POSITIVE,
    negative: str = DEFAULT_NEGATIVE,
    output_path: str | Path | None = None,
    mode: str = "t2i",
    image: str | Path | None = None,
    mask: str | Path | None = None,
    lineart_image: str | Path | None = None,
    depth_image: str | Path | None = None,
    pose_image: str | Path | None = None,
    width: int = 832,
    height: int = 1216,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 4.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    denoise: float = 1.0,
    control_strength: float = 1.0,
    turbo: bool = False,
    server_url: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    """Execute Anima generation pipeline and save output."""
    t_start = time.time()
    
    # Normalize mode
    norm_mode = mode.lower().replace("-", "_").strip()
    if norm_mode in ("text2image", "txt2img"):
        norm_mode = "t2i"
    elif norm_mode in ("inpainting", "inpaint_mask"):
        norm_mode = "inpaint"
    elif norm_mode in ("all_in_one", "allcontrol", "multi"):
        norm_mode = "all_control"

    # Prepare input images
    img_name = _upload_file_to_comfy_input(image, server_url) if image else None
    mask_name = _upload_file_to_comfy_input(mask, server_url) if mask else None
    lineart_name = _upload_file_to_comfy_input(lineart_image, server_url) if lineart_image else None
    depth_name = _upload_file_to_comfy_input(depth_image, server_url) if depth_image else None
    pose_name = _upload_file_to_comfy_input(pose_image, server_url) if pose_image else None

    # Build graph
    prompt_graph = build_anima_api_prompt(
        mode=norm_mode,
        prompt=prompt,
        negative=negative,
        width=width,
        height=height,
        seed=seed,
        steps=steps,
        cfg=cfg,
        sampler=sampler,
        scheduler=scheduler,
        denoise=denoise,
        turbo=turbo,
        control_strength=control_strength,
        image_filename=img_name,
        mask_filename=mask_name,
        lineart_filename=lineart_name,
        depth_filename=depth_name,
        pose_filename=pose_name,
    )

    # Queue execution (signature: queue_prompt(server_address, api_prompt))
    prompt_id = queue_prompt(server_url, prompt_graph)
    history = wait_for_history(server_url, prompt_id, timeout_sec=300.0)
    
    # extract_first_image returns tuple: (filename, subfolder, type)
    filename, subfolder, image_type = extract_first_image(history)
    
    if not filename:
        return fail_result(error="NO_IMAGE", message="Execution finished but no output image extracted from history")

    # Determine destination
    if output_path is None:
        out_dir = Path("workspace")
        out_dir.mkdir(parents=True, exist_ok=True)
        final_dest = out_dir / f"anima_{norm_mode}_{int(time.time())}.png"
    else:
        final_dest = Path(output_path).resolve()
        final_dest.parent.mkdir(parents=True, exist_ok=True)

    # download_image signature: download_image(server_address, filename, subfolder, image_type, dest_path)
    download_image(
        server_url,
        filename,
        subfolder,
        image_type,
        str(final_dest),
    )

    elapsed = round(time.time() - t_start, 2)
    meta = {
        "generator": "generate_anima",
        "mode": norm_mode,
        "backend": "anima_dit_2b",
        "prompt": prompt,
        "negative": negative,
        "width": width,
        "height": height,
        "steps": 8 if turbo else steps,
        "cfg": 1.0 if turbo else cfg,
        "sampler": sampler,
        "scheduler": scheduler,
        "turbo": turbo,
        "control_strength": control_strength,
        "prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "elapsed_seconds": elapsed,
    }
    write_meta(str(final_dest) + ".meta.json", meta)

    return ok_result(
        path=str(final_dest),
        output_path=str(final_dest),
        meta_path=str(final_dest) + ".meta.json",
        meta=meta,
        prompt_id=prompt_id,
        elapsed_seconds=elapsed,
        mode=norm_mode,
    )
