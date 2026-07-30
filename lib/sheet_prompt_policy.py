"""Sheet-role prompt policy for character expand / full_sheet.

Casting positive_core often includes headshot framing (head-and-shoulders,
85mm portrait). That must not be injected into full-body / detail plates.
"""

from __future__ import annotations

import re
from typing import Any

# Phrases that force face-CU / portrait framing (case-insensitive strip)
FRAMING_PHRASES: list[str] = [
    "head-and-shoulders",
    "head and shoulders",
    "casting portrait",
    "photoreal cinematic casting portrait",
    "eye-level 85mm feel",
    "eye-level 85mm",
    "85mm feel",
    "portrait crop",
    "close-up portrait",
    "upper body portrait",
    "bust portrait",
]

FULLBODY_FRAMING_LOCK = (
    "full body head-to-toe visible, feet in frame, not a close-up, not headshot"
)

DETAIL_FRAMING_LOCK = (
    "product detail crop of the requested region only, not a face portrait, not headshot"
)


def strip_framing_clauses(core: str) -> str:
    """Remove portrait/headshot framing phrases; keep identity descriptors."""
    text = (core or "").strip()
    if not text:
        return ""
    out = text
    for phrase in FRAMING_PHRASES:
        out = re.sub(re.escape(phrase), " ", out, flags=re.IGNORECASE)
    # collapse leftover punctuation/spaces
    out = re.sub(r"\s*,\s*,+", ", ", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r",\s*,+", ", ", out)
    return out.strip(" ,")


def _sheet_view(preset: dict[str, Any], preset_id: str = "") -> tuple[str, str]:
    sheet = str(preset.get("sheet") or "").lower()
    view = str(preset.get("view") or "").lower()
    if not sheet and preset_id:
        sheet = preset_id.split(".", 1)[0].lower()
    return sheet, view


def needs_identity_only_core(preset: dict[str, Any], *, preset_id: str = "") -> bool:
    """True when full cast portrait framing must not lead the prompt."""
    if preset.get("product_plate"):
        return False
    sheet, view = _sheet_view(preset, preset_id)
    pref = str(preset.get("source_pref") or "").lower()
    if sheet in ("expression", "head"):
        return False
    if pref == "face" and sheet not in ("costume", "pose", "turnaround", "props"):
        return False
    if sheet in ("costume", "pose", "turnaround", "props", "master"):
        return True
    if view in ("full",) or view.startswith("detail"):
        return True
    return False


def core_for_preset(
    positive_core: str,
    preset: dict[str, Any],
    *,
    preset_id: str = "",
) -> str:
    """Return core_prefix appropriate for this sheet preset."""
    if preset.get("product_plate") or str(preset.get("engine") or "").lower() == "t2i":
        return ""
    if not (positive_core or "").strip():
        return ""

    sheet, view = _sheet_view(preset, preset_id)
    if not needs_identity_only_core(preset, preset_id=preset_id):
        return positive_core.strip()

    identity = strip_framing_clauses(positive_core)
    locks: list[str] = []
    # Footwear / foot details: long face essays defeat crop intent — use minimal id only.
    if sheet == "costume" and view in ("detail_feet", "detail_foot", "detail_shoes"):
        identity = (
            "same character wardrobe continuity, matching skin tone on legs, "
            "do not show face or head"
        )
        locks.append(
            "crop from mid-shin or lower only, shoes and feet fill the frame, "
            "camera looking down at footwear, zero face pixels"
        )
    elif sheet == "costume" and view.startswith("detail"):
        # upper/acc details: keep short identity, hard anti-portrait
        if len(identity) > 280:
            identity = identity[:280].rsplit(",", 1)[0]
        locks.append(DETAIL_FRAMING_LOCK)
    elif sheet in ("costume", "pose", "turnaround", "master") and (
        view in ("full", "flat_front", "flat_back", "") or not view.startswith("detail")
    ):
        locks.append(FULLBODY_FRAMING_LOCK)
    elif sheet == "props" and view not in ("hero", "turn_3view"):
        locks.append(FULLBODY_FRAMING_LOCK)

    parts = [p for p in [identity, *locks] if p]
    return ", ".join(parts)
