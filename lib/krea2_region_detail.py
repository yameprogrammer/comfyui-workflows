"""Lonecat Krea2 v7 region detailers — agent map for Eyes/Spare/NSFW body slots.

Mirrors UI groups:
  # ::Eyes 👀 · # ::Spare 🛞 · # ;Breasts · # ;Female Body · # ;Male Junk · # ;Vajayjay
plus Face/Hands aliases to dedicated CLIs.

Detector models live under ComfyUI/models/ultralytics/{bbox,segm}/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Comfy portable default (override via COMFY_MODELS if needed)
_DEFAULT_ULTRA = Path(
    r"F:/ComfyUI_windows_portable/ComfyUI/models/ultralytics"
)

# region_id -> config
# mode: bbox | segm | sam | alias
REGIONS: dict[str, dict[str, Any]] = {
    # --- SFW ---
    "eyes": {
        "ui_group": "# ::Eyes 👀",
        "mode": "sam",
        "adult": False,
        "sam_prompt": "eyes",
        "fallback_point_mode": "face_region",
        "positive": "sharp detailed eyes, clear iris, natural catchlight, photoreal",
        "denoise": 0.32,
        "note": "UI SAM Smart Inpainter path (sam3). Use eyes_yolo for Eyeful bbox.",
    },
    "eyes_yolo": {
        "ui_group": "# ::Eyes 👀 (Eyeful YOLO)",
        "mode": "bbox",
        "adult": False,
        "model": "bbox/Eyeful_v2-Individual.pt",
        "positive": "sharp detailed eyes, clear iris, natural catchlight, photoreal",
        "denoise": 0.3,
        "threshold": 0.3,
        "guide_size": 384,
    },
    "eyes_paired": {
        "ui_group": "# ::Eyes 👀 (paired)",
        "mode": "bbox",
        "adult": False,
        "model": "bbox/Eyeful_v2-Paired.pt",
        "positive": "matched sharp eyes, clear irises, natural catchlights",
        "denoise": 0.3,
        "threshold": 0.3,
        "guide_size": 448,
    },
    "spare": {
        "ui_group": "# ::Spare 🛞",
        "mode": "sam",
        "adult": False,
        "sam_prompt": None,  # required via --sam-prompt
        "fallback_point_mode": "center",
        "positive": "high detail, natural texture, photoreal",
        "denoise": 0.35,
        "note": "Custom SAM text prompt required (--sam-prompt). Or --model for YOLO path.",
    },
    "face": {
        "ui_group": "# ::Face 🙂",
        "mode": "alias",
        "adult": False,
        "alias_cli": "python scripts/generate_krea2_face_detail.py",
        "alias_preset": "krea2_face_detail_v70",
    },
    "hands": {
        "ui_group": "# ::Hands ✋",
        "mode": "alias",
        "adult": False,
        "alias_cli": "python scripts/generate_krea2_hand_detail.py",
        "alias_preset": "krea2_hand_detail_v70",
    },
    # --- NSFW 18+ (Lonecat anatomy groups) ---
    "breasts": {
        "ui_group": "# ;Breasts 🍒 / Boobie Detailer",
        "mode": "segm",
        "adult": True,
        "model": "segm/female-breast-v4.7.pt",
        "positive": "detailed natural breasts, realistic skin, photoreal",
        "denoise": 0.3,
        "threshold": 0.35,
    },
    "female_body": {
        "ui_group": "# ;Female Body",
        "mode": "segm",
        "adult": True,
        "model": "segm/femaleBodyDetection_typea.pt",
        "positive": "detailed female body, natural skin, photoreal anatomy",
        "denoise": 0.28,
        "threshold": 0.3,
        "guide_size": 640,
    },
    "vajayjay": {
        "ui_group": "# ;Vajayjay 🕳️",
        "mode": "bbox",
        "adult": True,
        "model": "bbox/vagina-v4.1.pt",
        "positive": "detailed anatomy, natural skin, photoreal",
        "denoise": 0.3,
        "threshold": 0.25,
    },
    "vagina": {
        "ui_group": "# ;Vajayjay 🕳️ (alias)",
        "mode": "bbox",
        "adult": True,
        "model": "bbox/vagina-v4.1.pt",
        "positive": "detailed anatomy, natural skin, photoreal",
        "denoise": 0.3,
        "threshold": 0.25,
    },
    "male_junk": {
        "ui_group": "# ;Male Junk 🍆",
        "mode": "segm",
        "adult": True,
        "model": "segm/CockAndBallYolo8x.pt",
        "positive": "detailed male anatomy, natural skin, photoreal",
        "denoise": 0.3,
        "threshold": 0.3,
    },
    "penis": {
        "ui_group": "# ;Male Junk 🍆 (bbox penis)",
        "mode": "bbox",
        "adult": True,
        "model": "bbox/penis.pt",
        "positive": "detailed anatomy, natural skin, photoreal",
        "denoise": 0.3,
        "threshold": 0.3,
    },
}

PRESET_BY_MODE = {
    "bbox": "krea2_bbox_detail_v70",
    "segm": "krea2_segm_detail_v70",
    "sam": "krea2_sam_region_v70",
}


def list_regions(*, adult_only: bool | None = None) -> list[dict[str, Any]]:
    rows = []
    for rid, cfg in REGIONS.items():
        if adult_only is True and not cfg.get("adult"):
            continue
        if adult_only is False and cfg.get("adult"):
            continue
        rows.append(
            {
                "id": rid,
                "ui_group": cfg.get("ui_group"),
                "mode": cfg.get("mode"),
                "adult": bool(cfg.get("adult")),
                "model": cfg.get("model"),
                "alias_cli": cfg.get("alias_cli"),
                "note": cfg.get("note"),
            }
        )
    return rows


def resolve_model_path(model_name: str, ultra_root: Path | None = None) -> Path:
    root = ultra_root or _DEFAULT_ULTRA
    # model_name like bbox/foo.pt or segm/bar.pt
    return root / model_name.replace("\\", "/")


def model_exists(model_name: str, ultra_root: Path | None = None) -> bool:
    return resolve_model_path(model_name, ultra_root).is_file()


def get_region(region: str) -> dict[str, Any]:
    key = (region or "").strip().lower().replace("-", "_").replace(" ", "_")
    # synonyms
    synonyms = {
        "eye": "eyes",
        "boobie": "breasts",
        "breast": "breasts",
        "boobs": "breasts",
        "body": "female_body",
        "female": "female_body",
        "junk": "male_junk",
        "male": "male_junk",
        "cock": "male_junk",
        "balls": "male_junk",
        "vajay": "vajayjay",
        "pussy": "vajayjay",
    }
    key = synonyms.get(key, key)
    if key not in REGIONS:
        known = ", ".join(sorted(REGIONS))
        raise KeyError(f"unknown region {region!r}; known: {known}")
    return {"id": key, **REGIONS[key]}
