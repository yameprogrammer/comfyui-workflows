"""Wan 2.2 NSFW / 빨간맛 I2V configuration.

Default stack (correct product design):
  **Remix NSFW High/Low UNets** (dedicated adult models)
  + lightx2v distill (speed)
  + optional style LoRA pair (general / dr34ml4y)

Fallback: base GGUF Q4 + NSFW LoRA only (--unet-profile base).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any  # noqa: F401 — used in annotations

from lib.video_backends import load_video_backends

# Relative to Comfy models/loras/
DEFAULT_NSFW_LORA_DIR = Path("Wan2.2") / "nsfw"

# Prefer explicit pair names; also scan common community filename tokens
_HIGH_TOKENS = ("high", "highnoise", "high_noise", "hn")
_LOW_TOKENS = ("low", "lownoise", "low_noise", "ln")
_NSFW_TOKENS = ("nsfw", "erotic", "sex", "adult", "dr34m", "clk_nsfw", "uncen")

# Comfy models roots (host)
_MODEL_ROOTS = [
    Path(r"F:\model\loras"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\loras"),
]
_DIFFUSION_ROOTS = [
    Path(r"F:\model\diffusion_models"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\diffusion_models"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\unet"),
]

REMIX_UNET = {
    "high": r"Wan2.2\nsfw_remix\Wan2.2_Remix_NSFW_i2v_14b_HIGH_fp8_v3.0.safetensors",
    "low": r"Wan2.2\nsfw_remix\Wan2.2_Remix_NSFW_i2v_14b_LOW_fp8_v3.0.safetensors",
}

DEFAULT_NEGATIVE_NSFW = (
    "static, still image, blurry, low quality, worst quality, deformed, "
    "bad anatomy, watermark, text, logo, jitter, flicker, "
    "child, underage, loli, shota, teen"
)


def _rel_lora_path(abs_path: Path) -> str:
    """Path relative to a models/loras root, with backslashes for Comfy."""
    s = str(abs_path.resolve())
    for root in _MODEL_ROOTS:
        try:
            rel = abs_path.resolve().relative_to(root.resolve())
            return str(rel).replace("/", "\\")
        except ValueError:
            continue
    # fallback: keep filename under Wan2.2\nsfw\
    return str(Path("Wan2.2") / "nsfw" / abs_path.name).replace("/", "\\")


def _is_high(name: str) -> bool:
    n = name.lower().replace("-", "_")
    if "low" in n and "high" not in n:
        return False
    return any(t in n for t in _HIGH_TOKENS)


def _is_low(name: str) -> bool:
    n = name.lower().replace("-", "_")
    if "high" in n and "low" not in n:
        return False
    return any(t in n for t in _LOW_TOKENS)


def _looks_nsfw(name: str) -> bool:
    n = name.lower()
    return any(t in n for t in _NSFW_TOKENS)


def discover_nsfw_lora_pair() -> dict[str, Any]:
    """Scan loras/Wan2.2/** for a HIGH+LOW NSFW pair."""
    found_high: Path | None = None
    found_low: Path | None = None
    scanned: list[str] = []

    for root in _MODEL_ROOTS:
        if not root.is_dir():
            continue
        for base in (root / "Wan2.2" / "nsfw", root / "Wan2.2", root):
            if not base.is_dir():
                continue
            for p in base.rglob("*.safetensors"):
                name = p.name
                scanned.append(str(p))
                if not _looks_nsfw(name) and "nsfw" not in str(p.parent).lower():
                    # only auto-pick if in nsfw folder or nsfw-ish name
                    if "nsfw" not in str(p).lower():
                        continue
                if _is_high(name) and found_high is None:
                    found_high = p
                elif _is_low(name) and found_low is None:
                    found_low = p

    return {
        "high": _rel_lora_path(found_high) if found_high else None,
        "low": _rel_lora_path(found_low) if found_low else None,
        "high_abs": str(found_high) if found_high else None,
        "low_abs": str(found_low) if found_low else None,
        "scanned_count": len(scanned),
    }


def list_lora_presets() -> dict[str, dict[str, Any]]:
    try:
        vb = load_video_backends()
        be = (vb.get("backends") or {}).get("wan22_nsfw_i2v") or {}
        return dict(be.get("nsfw_lora_presets") or {})
    except Exception:
        return {}


def resolve_nsfw_loras(
    *,
    lora_high: str | None = None,
    lora_low: str | None = None,
    lora_preset: str | None = None,
    auto_discover: bool = True,
) -> dict[str, Any]:
    """Merge CLI overrides, preset, video_backends config, env, then filesystem discover."""
    cfg_high = None
    cfg_low = None
    strength_high = 0.85
    strength_low = 0.9
    preset_id = (lora_preset or "").strip().lower() or None
    try:
        vb = load_video_backends()
        be = (vb.get("backends") or {}).get("wan22_nsfw_i2v") or {}
        presets = be.get("nsfw_lora_presets") or {}
        if preset_id and preset_id in presets:
            pr = presets[preset_id]
            cfg_high = pr.get("high")
            cfg_low = pr.get("low")
            if pr.get("strength_high") is not None:
                strength_high = float(pr["strength_high"])
            if pr.get("strength_low") is not None:
                strength_low = float(pr["strength_low"])
        else:
            nl = be.get("nsfw_loras") or {}
            cfg_high = nl.get("high") or nl.get("lora_high")
            cfg_low = nl.get("low") or nl.get("lora_low")
            if nl.get("strength_high") is not None:
                strength_high = float(nl["strength_high"])
            if nl.get("strength_low") is not None:
                strength_low = float(nl["strength_low"])
    except Exception:
        pass

    env_high = (os.environ.get("AGENT_WAN_NSFW_LORA_HIGH") or "").strip() or None
    env_low = (os.environ.get("AGENT_WAN_NSFW_LORA_LOW") or "").strip() or None

    high = lora_high or env_high or cfg_high
    low = lora_low or env_low or cfg_low
    source = "preset" if preset_id else "cli_or_env_or_config"
    if lora_high or lora_low:
        source = "cli"
    elif env_high or env_low:
        source = "env"

    if auto_discover and (not high or not low):
        disc = discover_nsfw_lora_pair()
        if not high and disc.get("high"):
            high = disc["high"]
            source = "discover"
        if not low and disc.get("low"):
            low = disc["low"]
            source = "discover"
        disc_meta = disc
    else:
        disc_meta = {}

    # Verify files exist under known lora roots (warn only)
    missing: list[str] = []
    for label, rel in (("high", high), ("low", low)):
        if not rel:
            continue
        found = False
        for root in _MODEL_ROOTS:
            if (root / rel.replace("\\", "/")).is_file() or (
                root / Path(rel)
            ).is_file():
                found = True
                break
            # Windows path
            p = root / Path(str(rel).replace("\\", os.sep))
            if p.is_file():
                found = True
                break
        if not found:
            missing.append(f"{label}:{rel}")

    return {
        "lora_high": high,
        "lora_low": low,
        "strength_high": strength_high,
        "strength_low": strength_low,
        "source": source,
        "preset": preset_id,
        "has_pair": bool(high and low),
        "has_any": bool(high or low),
        "missing_files": missing,
        "discover": disc_meta,
        "hint": (
            None
            if (high or low)
            else (
                "No NSFW LoRA pair found. Tool runs base Wan2.2 I2V only "
                "(weaker adult adherence). Install HIGH+LOW NSFW LoRAs under "
                "models/loras/Wan2.2/nsfw/ or set backends.wan22_nsfw_i2v.nsfw_loras / "
                "AGENT_WAN_NSFW_LORA_HIGH|LOW."
            )
        ),
    }


def nsfw_default_profile() -> str:
    try:
        vb = load_video_backends()
        be = (vb.get("backends") or {}).get("wan22_nsfw_i2v") or {}
        return str(be.get("default_speed_profile") or "quality")
    except Exception:
        return "quality"


def _unet_exists(rel: str) -> bool:
    rel_p = Path(str(rel).replace("\\", os.sep))
    for root in _DIFFUSION_ROOTS:
        if (root / rel_p).is_file():
            return True
    return False


def resolve_nsfw_unets(
    *,
    unet_profile: str | None = None,
    model_high: str | None = None,
    model_low: str | None = None,
) -> dict[str, Any]:
    """Resolve High/Low diffusion weights for the NSFW tool.

    Default: **remix** NSFW fp8 dual UNet when on disk.
    ``base`` / ``q4`` → official GGUF (then rely on NSFW LoRAs).
    """
    explicit_h = (model_high or "").strip() or None
    explicit_l = (model_low or "").strip() or None
    if explicit_h and explicit_l:
        return {
            "unet_profile": "custom",
            "model_high": explicit_h.replace("/", "\\"),
            "model_low": explicit_l.replace("/", "\\"),
            "on_disk": True,
            "source": "cli",
        }

    try:
        vb = load_video_backends()
        be = (vb.get("backends") or {}).get("wan22_nsfw_i2v") or {}
        default_prof = str(be.get("default_unet_profile") or "remix")
        remix_cfg = be.get("nsfw_unet_remix") or {}
    except Exception:
        default_prof = "remix"
        remix_cfg = {}

    prof = (unet_profile or default_prof or "remix").strip().lower()
    if prof in ("nsfw", "nsfw_remix", "full"):
        prof = "remix"

    if prof == "remix":
        high = (remix_cfg.get("high") or REMIX_UNET["high"]).replace("/", "\\")
        low = (remix_cfg.get("low") or REMIX_UNET["low"]).replace("/", "\\")
        ok = _unet_exists(high) and _unet_exists(low)
        if ok:
            return {
                "unet_profile": "remix",
                "model_high": high,
                "model_low": low,
                "on_disk": True,
                "source": "remix_nsfw",
                "uses_dedicated_nsfw_unet": True,
            }
        # fall through to base if missing
        return {
            "unet_profile": "q4",
            "model_high": None,
            "model_low": None,
            "on_disk": False,
            "source": "remix_missing_fallback_gguf",
            "uses_dedicated_nsfw_unet": False,
            "hint": f"Remix UNet missing ({high}); using base GGUF + LoRA",
        }

    # base / q4 / q5
    return {
        "unet_profile": prof if prof in ("q4", "q5", "base") else "q4",
        "model_high": None,
        "model_low": None,
        "on_disk": True,
        "source": "base_gguf",
        "uses_dedicated_nsfw_unet": False,
        "quant": "q4" if prof in ("base", "q4", "") else prof,
    }
