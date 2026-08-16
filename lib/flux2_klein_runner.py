"""Flux.2 Klein 9B GGUF — T2I and I2I.

Official Klein edit weights are not on disk. I2I is denoise-on-encode, not Qwen-style
instruction edit. Default cinematic still stays generate_krea.
"""

from __future__ import annotations

import os
from typing import Any

from lib.still_api import new_seed, run_still_api, stage_input_image
from lib.still_model_profiles import (
    COMFY_MODELS,
    FLUX2_KLEIN_CLIP,
    FLUX2_KLEIN_UNET,
    FLUX2_VAE,
)

FAMILY_FLUX2 = "flux2_klein"


def check_klein_models() -> dict[str, Any]:
    paths = {
        "unet": os.path.join(
            COMFY_MODELS, "diffusion_models", "Flux2", "flux-2-klein-9b-Q4_K_M.gguf"
        ),
        "clip": os.path.join(COMFY_MODELS, "text_encoders", FLUX2_KLEIN_CLIP),
        "vae": os.path.join(COMFY_MODELS, "vae", FLUX2_VAE),
    }
    missing = [k for k, p in paths.items() if not os.path.isfile(p)]
    return {"ok": not missing, "missing": missing, "paths": paths}


def _base_loaders(
    *,
    unet_name: str,
    clip_name: str,
    vae_name: str,
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": unet_name},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": clip_name,
                "type": "flux2",
                "device": "default",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        },
    }


def _sample_tail(
    *,
    prompt: str,
    negative: str,
    seed: int,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    latent_src: list[Any],
    denoise: float,
    filename_prefix: str,
) -> dict[str, Any]:
    return {
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2", 0]},
        },
        "6": {
            "class_type": "CFGGuider",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "cfg": float(cfg),
            },
        },
        "7": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": int(seed)},
        },
        "8": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler"},
        },
        "9": {
            "class_type": "Flux2Scheduler",
            "inputs": {
                "steps": int(steps),
                "width": int(width),
                "height": int(height),
            },
        },
        "10": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["7", 0],
                "guider": ["6", 0],
                "sampler": ["8", 0],
                "sigmas": ["9", 0],
                "latent_image": latent_src,
            },
        },
        "11": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["10", 0], "vae": ["3", 0]},
        },
        "12": {
            "class_type": "SaveImage",
            "inputs": {"images": ["11", 0], "filename_prefix": filename_prefix},
        },
    }


def build_klein_t2i_api(
    *,
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int = 1,
    steps: int = 20,
    cfg: float = 5.0,
    unet_name: str = FLUX2_KLEIN_UNET,
    clip_name: str = FLUX2_KLEIN_CLIP,
    vae_name: str = FLUX2_VAE,
    filename_prefix: str = "flux2_klein_t2i",
) -> dict[str, Any]:
    api = _base_loaders(unet_name=unet_name, clip_name=clip_name, vae_name=vae_name)
    api["20"] = {
        "class_type": "EmptyFlux2LatentImage",
        "inputs": {"width": int(width), "height": int(height), "batch_size": 1},
    }
    api.update(
        _sample_tail(
            prompt=prompt,
            negative=negative,
            seed=seed,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            latent_src=["20", 0],
            denoise=1.0,
            filename_prefix=filename_prefix,
        )
    )
    return api


def build_klein_i2i_api(
    *,
    prompt: str,
    image_name: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int = 1,
    steps: int = 20,
    cfg: float = 5.0,
    denoise: float = 0.65,
    unet_name: str = FLUX2_KLEIN_UNET,
    clip_name: str = FLUX2_KLEIN_CLIP,
    vae_name: str = FLUX2_VAE,
    filename_prefix: str = "flux2_klein_i2i",
) -> dict[str, Any]:
    api = _base_loaders(unet_name=unet_name, clip_name=clip_name, vae_name=vae_name)
    api["20"] = {
        "class_type": "LoadImage",
        "inputs": {"image": image_name},
    }
    api["21"] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": ["20", 0], "vae": ["3", 0]},
    }
    # SamplerCustomAdvanced has no denoise; approximate via fewer scheduler steps
    # is wrong. Use KSampler on encoded latent so --denoise is real.
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
            "8": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["21", 0],
                    "seed": int(seed),
                    "steps": int(steps),
                    "cfg": float(cfg),
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": float(denoise),
                },
            },
            "11": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["8", 0], "vae": ["3", 0]},
            },
            "12": {
                "class_type": "SaveImage",
                "inputs": {"images": ["11", 0], "filename_prefix": filename_prefix},
            },
        }
    )
    return api


def generate_flux2_klein(
    *,
    prompt: str,
    output_path: str,
    mode: str = "t2i",
    image_path: str | None = None,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    steps: int = 20,
    cfg: float = 5.0,
    denoise: float = 0.65,
    unet_name: str | None = None,
    timeout_sec: float = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    chk = check_klein_models()
    if not chk["ok"]:
        return {
            "ok": False,
            "error": "MISSING_MODELS",
            "message": f"Flux.2 Klein incomplete: missing={chk['missing']}",
            "model_check": chk,
        }
    mode_l = (mode or "t2i").strip().lower()
    if mode_l not in ("t2i", "i2i"):
        return {
            "ok": False,
            "error": "BAD_MODE",
            "message": "generate_flux2_klein --mode t2i|i2i (no native edit weights on disk)",
        }
    seed_i = new_seed(seed)
    unet = unet_name or FLUX2_KLEIN_UNET
    if mode_l == "t2i":
        api = build_klein_t2i_api(
            prompt=prompt,
            negative=negative,
            width=width,
            height=height,
            seed=seed_i,
            steps=steps,
            cfg=cfg,
            unet_name=unet,
        )
    else:
        if not image_path or not os.path.isfile(image_path):
            return {
                "ok": False,
                "error": "IMAGE_MISSING",
                "message": "--mode i2i requires -i existing image",
            }
        img = stage_input_image(image_path, prefix="klein_i2i")
        api = build_klein_i2i_api(
            prompt=prompt,
            image_name=img,
            negative=negative,
            width=width,
            height=height,
            seed=seed_i,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            unet_name=unet,
        )
    print(
        f"Flux.2 Klein {mode_l} {width}x{height} steps={steps} cfg={cfg} "
        f"seed={seed_i} unet={unet}"
        + (f" denoise={denoise}" if mode_l == "i2i" else "")
    )
    return run_still_api(
        api,
        output_path=output_path,
        family=FAMILY_FLUX2,
        caller="generate_flux2_klein",
        seed=seed_i,
        timeout_sec=timeout_sec,
        dry_run=dry_run,
        meta={
            "mode": f"flux2_klein_{mode_l}",
            "prompt": prompt[:2000],
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "denoise": denoise if mode_l == "i2i" else 1.0,
            "unet": unet,
            "image": os.path.abspath(image_path) if image_path else None,
            "not_default_t2i": True,
        },
    )
