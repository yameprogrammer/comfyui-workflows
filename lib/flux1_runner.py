"""Flux.1 Dev T2I + Flux.1 Fill inpaint — native API graphs.

Not a Krea replacement (cinematic default stays generate_krea).
Not a Qwen InstantX replacement (instruction / Qwen look stays generate_qwen_inpaint).
"""

from __future__ import annotations

import os
from typing import Any

from lib.still_api import new_seed, run_still_api, stage_input_image
from lib.still_model_profiles import (
    COMFY_MODELS,
    FLUX1_CLIP_L,
    FLUX1_DEV_UNET,
    FLUX1_FILL_UNET,
    FLUX1_T5,
    FLUX1_VAE,
    FLUX1_VAE_ALT,
)

FAMILY_FLUX1 = "flux1"

_FLUX1_FILES = {
    "unet_dev": ("diffusion_models", "Flux1", "flux1-dev-Q4_K_S.gguf"),
    "unet_fill": ("diffusion_models", "Flux1", "flux1-fill-dev-Q4_K_S.gguf"),
    "clip_l": ("text_encoders", FLUX1_CLIP_L),
    "t5": ("text_encoders", FLUX1_T5),
    "vae": ("vae", FLUX1_VAE),
}


def check_flux1_models(*, need_fill: bool = False) -> dict[str, Any]:
    keys = ["unet_dev", "clip_l", "t5"]
    if need_fill:
        keys = ["unet_fill", "clip_l", "t5"]
    vae_path = os.path.join(COMFY_MODELS, "vae", FLUX1_VAE)
    vae_alt = os.path.join(COMFY_MODELS, "vae", FLUX1_VAE_ALT)
    vae_ok = os.path.isfile(vae_path) or os.path.isfile(vae_alt)
    missing: list[str] = []
    paths: dict[str, str] = {}
    for k in keys:
        parts = _FLUX1_FILES[k]
        p = os.path.join(COMFY_MODELS, *parts)
        paths[k] = p
        if not os.path.isfile(p):
            missing.append(k)
    paths["vae"] = vae_path if os.path.isfile(vae_path) else vae_alt
    if not vae_ok:
        missing.append("vae")
    return {"ok": not missing, "missing": missing, "paths": paths}


def _vae_name() -> str:
    if os.path.isfile(os.path.join(COMFY_MODELS, "vae", FLUX1_VAE)):
        return FLUX1_VAE
    return FLUX1_VAE_ALT


def _loaders(
    *,
    unet_name: str,
    clip_l: str = FLUX1_CLIP_L,
    t5: str = FLUX1_T5,
    vae_name: str | None = None,
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": unet_name},
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": clip_l,
                "clip_name2": t5,
                "type": "flux",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name or _vae_name()},
        },
    }


def build_flux1_t2i_api(
    *,
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int = 1,
    steps: int = 20,
    guidance: float = 3.5,
    unet_name: str = FLUX1_DEV_UNET,
    filename_prefix: str = "flux1_t2i",
) -> dict[str, Any]:
    api = _loaders(unet_name=unet_name)
    api.update(
        {
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["2", 0]},
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["2", 0]},
            },
            "6": {
                "class_type": "FluxGuidance",
                "inputs": {"conditioning": ["4", 0], "guidance": float(guidance)},
            },
            "7": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": int(width),
                    "height": int(height),
                    "batch_size": 1,
                },
            },
            "8": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["6", 0],
                    "negative": ["5", 0],
                    "latent_image": ["7", 0],
                    "seed": int(seed),
                    "steps": int(steps),
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                },
            },
            "9": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["8", 0], "vae": ["3", 0]},
            },
            "10": {
                "class_type": "SaveImage",
                "inputs": {"images": ["9", 0], "filename_prefix": filename_prefix},
            },
        }
    )
    return api


def build_flux1_fill_api(
    *,
    prompt: str,
    image_name: str,
    mask_name: str,
    negative: str = "",
    seed: int = 1,
    steps: int = 20,
    guidance: float = 3.5,
    grow_mask: int = 6,
    unet_name: str = FLUX1_FILL_UNET,
    filename_prefix: str = "flux1_fill",
) -> dict[str, Any]:
    api = _loaders(unet_name=unet_name)
    api.update(
        {
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["2", 0]},
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["2", 0]},
            },
            "6": {
                "class_type": "FluxGuidance",
                "inputs": {"conditioning": ["4", 0], "guidance": float(guidance)},
            },
            "7": {
                "class_type": "LoadImage",
                "inputs": {"image": image_name},
            },
            "8": {
                "class_type": "LoadImage",
                "inputs": {"image": mask_name},
            },
            "9": {
                "class_type": "ImageToMask",
                "inputs": {"image": ["8", 0], "channel": "red"},
            },
            "10": {
                "class_type": "GrowMask",
                "inputs": {"mask": ["9", 0], "expand": int(grow_mask), "tapered_corners": True},
            },
            "11": {
                "class_type": "InpaintModelConditioning",
                "inputs": {
                    "positive": ["6", 0],
                    "negative": ["5", 0],
                    "vae": ["3", 0],
                    "pixels": ["7", 0],
                    "mask": ["10", 0],
                    "noise_mask": True,
                },
            },
            "12": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["11", 0],
                    "negative": ["11", 1],
                    "latent_image": ["11", 2],
                    "seed": int(seed),
                    "steps": int(steps),
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                },
            },
            "13": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["12", 0], "vae": ["3", 0]},
            },
            "14": {
                "class_type": "SaveImage",
                "inputs": {"images": ["13", 0], "filename_prefix": filename_prefix},
            },
        }
    )
    return api


def generate_flux1_t2i(
    *,
    prompt: str,
    output_path: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    steps: int = 20,
    guidance: float = 3.5,
    unet_name: str | None = None,
    timeout_sec: float = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    chk = check_flux1_models(need_fill=False)
    if not chk["ok"]:
        return {
            "ok": False,
            "error": "MISSING_MODELS",
            "message": f"Flux.1 Dev incomplete: missing={chk['missing']}",
            "model_check": chk,
        }
    seed_i = new_seed(seed)
    unet = unet_name or FLUX1_DEV_UNET
    api = build_flux1_t2i_api(
        prompt=prompt,
        negative=negative,
        width=width,
        height=height,
        seed=seed_i,
        steps=steps,
        guidance=guidance,
        unet_name=unet,
    )
    print(
        f"Flux.1 Dev T2I {width}x{height} steps={steps} guidance={guidance} "
        f"seed={seed_i} unet={unet}"
    )
    return run_still_api(
        api,
        output_path=output_path,
        family=FAMILY_FLUX1,
        caller="generate_flux",
        seed=seed_i,
        timeout_sec=timeout_sec,
        dry_run=dry_run,
        meta={
            "mode": "flux1_dev_t2i",
            "prompt": prompt[:2000],
            "negative": negative or None,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance": guidance,
            "unet": unet,
            "not_default_t2i": True,
        },
    )


def generate_flux1_fill(
    *,
    prompt: str,
    image_path: str,
    mask_path: str,
    output_path: str,
    negative: str = "",
    seed: int | None = None,
    steps: int = 20,
    guidance: float = 3.5,
    grow_mask: int = 6,
    unet_name: str | None = None,
    timeout_sec: float = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    chk = check_flux1_models(need_fill=True)
    if not chk["ok"]:
        return {
            "ok": False,
            "error": "MISSING_MODELS",
            "message": f"Flux.1 Fill incomplete: missing={chk['missing']}",
            "model_check": chk,
        }
    if not os.path.isfile(image_path):
        return {"ok": False, "error": "IMAGE_MISSING", "message": image_path}
    if not os.path.isfile(mask_path):
        return {"ok": False, "error": "MASK_MISSING", "message": mask_path}
    seed_i = new_seed(seed)
    unet = unet_name or FLUX1_FILL_UNET
    img = stage_input_image(image_path, prefix="flux_fill_img")
    msk = stage_input_image(mask_path, prefix="flux_fill_msk")
    api = build_flux1_fill_api(
        prompt=prompt,
        image_name=img,
        mask_name=msk,
        negative=negative,
        seed=seed_i,
        steps=steps,
        guidance=guidance,
        grow_mask=grow_mask,
        unet_name=unet,
    )
    print(
        f"Flux.1 Fill inpaint steps={steps} guidance={guidance} "
        f"grow={grow_mask} seed={seed_i} unet={unet}"
    )
    return run_still_api(
        api,
        output_path=output_path,
        family=FAMILY_FLUX1,
        caller="generate_flux_fill",
        seed=seed_i,
        timeout_sec=timeout_sec,
        dry_run=dry_run,
        meta={
            "mode": "flux1_fill_inpaint",
            "prompt": prompt[:2000],
            "image": os.path.abspath(image_path),
            "mask": os.path.abspath(mask_path),
            "steps": steps,
            "guidance": guidance,
            "grow_mask": grow_mask,
            "unet": unet,
        },
    )
