"""Idle still-model aliases — one name per distinct look, no quant duplicates.

Krea / Z-Image / SDXL checkpoints already on F:\\model. Agents pick --profile / --model
instead of raw Comfy paths. GGUF twins of an already-wired fp8/int8 unet are omitted.
"""

from __future__ import annotations

import os
from typing import Any

COMFY_MODELS = os.environ.get("COMFYUI_MODELS", r"F:\model")

# ---------------------------------------------------------------------------
# Krea2 UNET variants (same krea2_t2i_v10 graph — UNETLoader, not GGUF)
# turbo = current factory default (omit --profile / leave unet unset)
# ---------------------------------------------------------------------------

KREA_UNET_PROFILES: dict[str, dict[str, str]] = {
    "turbo": {
        "unet": r"Krea2Turbo\krea2_turbo_fp8_scaled.safetensors",
        "disk": r"diffusion_models\Krea2Turbo\krea2_turbo_fp8_scaled.safetensors",
        "when": "factory default cinematic still",
    },
    "int8": {
        "unet": r"Krea2Turbo\krea2_turbo_int8_convrot.safetensors",
        "disk": r"diffusion_models\Krea2Turbo\krea2_turbo_int8_convrot.safetensors",
        "when": "same turbo, int8 convrot quant",
    },
    "animosity": {
        "unet": r"Krea 2\Your models\Animosity_Krea_v1.1.safetensors",
        "disk": r"diffusion_models\Krea 2\Your models\Animosity_Krea_v1.1.safetensors",
        "when": "Animosity Krea mix — punchier contrast / stylized photoreal",
    },
    "raw": {
        "unet": r"Krea2Raw\krea2_raw_fp8_scaled.safetensors",
        "disk": r"diffusion_models\Krea2Raw\krea2_raw_fp8_scaled.safetensors",
        "when": "Krea2 raw (less turbo-baked look)",
    },
    "redcraft": {
        "unet": r"Krea 2\Your models\redcraft22INT8INT4_2Krea2Edition.safetensors",
        "disk": r"diffusion_models\Krea 2\Your models\redcraft22INT8INT4_2Krea2Edition.safetensors",
        "when": "RedCraft Krea2 edition mix",
    },
    "gpt": {
        "unet": r"Krea 2\Your models\krea2GPTGrandPUSSYTruth_krea2GPT.safetensors",
        "disk": r"diffusion_models\Krea 2\Your models\krea2GPTGrandPUSSYTruth_krea2GPT.safetensors",
        "when": "NSFW-leaning Krea mix — prefer generate_krea_nsfw --profile gpt",
    },
    "mix": {
        "unet": r"Krea2Turbo\moodyKrea2Mix_v40NonComfyFP8.safetensors",
        "disk": r"diffusion_models\Krea2Turbo\moodyKrea2Mix_v40NonComfyFP8.safetensors",
        "when": "Moody Krea2 mix v40",
    },
}

KREA_PROFILE_CHOICES: tuple[str, ...] = tuple(KREA_UNET_PROFILES.keys())

# ---------------------------------------------------------------------------
# Z-Image / Lonecat unets — generate_moody -m …
# gguf selects lonecat_t2i_gguf via select_lonecat_preset (filename ends .gguf)
# ---------------------------------------------------------------------------

ZIMAGE_UNET_ALIASES: dict[str, str] = {
    "real": r"ZImageTurbo\moodyRealMix_zitV6DPO.safetensors",
    "pro": r"ZImageTurbo\moodyProMix_zitV12DPO.safetensors",
    "wild": r"ZImageTurbo\moodyWildMixZIBZID_v01.safetensors",
    "v13": r"ZImageTurbo\moodyProMix_zitV13FP8.safetensors",
    "turbo": r"ZImageTurbo\z_image_turbo_int8_convrot.safetensors",
    "gguf": r"ZImageTurbo\z-image-turbo-Q4_K_M.gguf",
}

ZIMAGE_ALIAS_WHEN: dict[str, str] = {
    "real": "Moody Real Mix — photoreal Z-Image",
    "pro": "Moody Pro Mix v12 DPO — factory I2I/experiment default",
    "wild": "Moody Wild Mix — looser / stylized",
    "v13": "Moody Pro Mix v13 FP8 — newer pro mix",
    "turbo": "official Z-Image Turbo int8 (not a Moody mix)",
    "gguf": "official Z-Image Turbo Q4 GGUF (low VRAM)",
}

ZIMAGE_MODEL_CHOICES: tuple[str, ...] = tuple(ZIMAGE_UNET_ALIASES.keys())

# ---------------------------------------------------------------------------
# SDXL photoreal / pony / lightning — NOT Illustrious (different dialect)
# ---------------------------------------------------------------------------

SDXL_CKPT_PROFILES: dict[str, dict[str, Any]] = {
    "juggernaut": {
        "ckpt": r"SDXL\juggernautXL_ragnarokBy.safetensors",
        "steps": 28,
        "cfg": 5.0,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "when": "classic SDXL photoreal (Juggernaut XL Ragnarok)",
        "dialect": "nl_sdxl",
    },
    "lightning": {
        "ckpt": r"SDXL\dreamshaperXL_lightningDPMSDE.safetensors",
        "steps": 6,
        "cfg": 2.0,
        "sampler": "dpmpp_sde",
        "scheduler": "karras",
        "when": "4–8 step scout / draft (Dreamshaper XL Lightning)",
        "dialect": "nl_sdxl",
    },
    "pony": {
        "ckpt": r"SDXL\gonzalomoXLFluxPony_v60PhotoXLDMD.safetensors",
        "steps": 25,
        "cfg": 6.0,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "when": "Pony/photo hybrid — score tags, not Illustrious Danbooru",
        "dialect": "pony_score",
    },
    "nsfw": {
        "ckpt": r"SDXL\pornmaster_proSDXLV8.safetensors",
        "steps": 28,
        "cfg": 5.0,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "when": "SDXL NSFW look — default 18+ still is still generate_krea_nsfw",
        "dialect": "nl_sdxl",
    },
}

SDXL_MODEL_CHOICES: tuple[str, ...] = tuple(SDXL_CKPT_PROFILES.keys())

# Flux.1 / Flux.2 Klein — one file each, no alias table
FLUX1_DEV_UNET = r"Flux1\flux1-dev-Q4_K_S.gguf"
FLUX1_FILL_UNET = r"Flux1\flux1-fill-dev-Q4_K_S.gguf"
FLUX1_CLIP_L = "clip_l.safetensors"
FLUX1_T5 = "t5xxl_fp16.safetensors"
FLUX1_VAE = "ae.safetensors"
FLUX1_VAE_ALT = "vae-flux1-dev.safetensors"

FLUX2_KLEIN_UNET = r"Flux2\flux-2-klein-9b-Q4_K_M.gguf"
FLUX2_KLEIN_CLIP = "qwen_3_8b_fp8mixed.safetensors"
FLUX2_VAE = "flux2-vae.safetensors"


def _disk(*parts: str) -> str:
    return os.path.join(COMFY_MODELS, *parts)


def resolve_krea_unet(profile: str | None, unet_name: str | None = None) -> str | None:
    """Return Comfy unet_name, or None to keep the krea2_t2i_v10 preset default."""
    if unet_name and str(unet_name).strip():
        return str(unet_name).strip()
    key = (profile or "turbo").strip().lower()
    if key in ("", "turbo", "default"):
        return None
    if key not in KREA_UNET_PROFILES:
        raise KeyError(
            f"unknown Krea --profile {profile!r}; choose {', '.join(KREA_PROFILE_CHOICES)}"
        )
    return KREA_UNET_PROFILES[key]["unet"]


def resolve_zimage_unet(model_type: str | None, unet_name: str | None = None) -> str:
    if unet_name and str(unet_name).strip():
        return str(unet_name).strip()
    key = (model_type or "real").strip().lower()
    if key not in ZIMAGE_UNET_ALIASES:
        raise KeyError(
            f"unknown Z-Image --model {model_type!r}; choose {', '.join(ZIMAGE_MODEL_CHOICES)}"
        )
    return ZIMAGE_UNET_ALIASES[key]


def resolve_sdxl_profile(model: str | None) -> dict[str, Any]:
    key = (model or "juggernaut").strip().lower()
    if key not in SDXL_CKPT_PROFILES:
        raise KeyError(
            f"unknown SDXL --model {model!r}; choose {', '.join(SDXL_MODEL_CHOICES)}"
        )
    out = dict(SDXL_CKPT_PROFILES[key])
    out["name"] = key
    return out


def file_exists(rel_under_model: str) -> bool:
    return os.path.isfile(_disk(*rel_under_model.split("\\")))


def format_profile_table(family: str) -> str:
    lines = [f"{family} profiles (on-disk = {COMFY_MODELS})", ""]
    if family == "krea":
        for name, spec in KREA_UNET_PROFILES.items():
            ok = "ok" if file_exists(spec["disk"]) else "MISSING"
            lines.append(f"  {name:12} [{ok:7}] {spec['unet']}")
            lines.append(f"               {spec['when']}")
    elif family == "zimage":
        for name, unet in ZIMAGE_UNET_ALIASES.items():
            rel = rf"diffusion_models\{unet}"
            ok = "ok" if file_exists(rel) else "MISSING"
            lines.append(f"  {name:12} [{ok:7}] {unet}")
            lines.append(f"               {ZIMAGE_ALIAS_WHEN.get(name, '')}")
    elif family == "sdxl":
        for name, spec in SDXL_CKPT_PROFILES.items():
            rel = rf"checkpoints\{spec['ckpt']}"
            ok = "ok" if file_exists(rel) else "MISSING"
            lines.append(
                f"  {name:12} [{ok:7}] {spec['ckpt']}  "
                f"steps={spec['steps']} cfg={spec['cfg']}"
            )
            lines.append(f"               {spec['when']}")
    else:
        raise KeyError(family)
    return "\n".join(lines)
