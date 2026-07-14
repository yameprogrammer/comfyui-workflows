"""Ideogram 4 structured JSON caption helpers (typography / layout slots).

Schema follows official ideogram-oss prompting guide:
https://github.com/ideogram-oss/ideogram4/blob/main/docs/prompting.md

Critical rules:
  - In-image letters use element type ``"text"`` with a dedicated ``text`` field
    (NOT type ``obj`` with text only mentioned in desc).
  - bbox is ``[y_min, x_min, y_max, x_max]`` in normalized **0–1000** coords
    (origin top-left). NOT pixel [x0,y0,x1,y1].
  - style_description key order:
      photo: aesthetics, lighting, photo, medium, [color_palette]
      art:   aesthetics, lighting, medium, art_style, [color_palette]
  - text element key order: type, bbox, text, desc, [color_palette]
  - obj element key order: type, bbox, desc, [color_palette]
  - hex colors uppercase #RRGGBB
  - serialize with separators=(",", ":"), ensure_ascii=False
"""

from __future__ import annotations

import json
from typing import Any

ASPECT_PRESETS: dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "square": (1024, 1024),
    "9:16": (768, 1344),
    "shorts": (768, 1344),
    "portrait": (768, 1344),
    "16:9": (1344, 768),
    "landscape": (1344, 768),
    "4:5": (896, 1120),
    "3:4": (896, 1152),
    "title_wide": (1280, 720),
}

QUALITY_PRESETS: dict[str, dict[str, float | int]] = {
    "turbo": {"steps": 12, "mu": 0.5, "std": 1.75, "cfg": 7.0},
    "default": {"steps": 20, "mu": 0.0, "std": 1.75, "cfg": 7.0},
    "quality": {"steps": 48, "mu": 0.0, "std": 1.5, "cfg": 7.0},
}

SLOT_DEFAULTS: dict[str, dict[str, Any]] = {
    "title_card": {
        "background": (
            "Soft clean solid cream field with gentle soft-focus bokeh at the bottom edge, "
            "uncluttered negative space, no busy patterns behind the main type."
        ),
        "aesthetics": "clean modern graphic design, high legibility, quiet luxury, minimal",
        "lighting": "soft even studio light, flat readable contrast on type",
        "medium": "graphic_design",
        "art_style": "contemporary horizontal Korean display typography, refined poster layout",
    },
    "end_card": {
        "background": (
            "Minimal end-card field, subtle brand-friendly wash, plenty of negative space "
            "around center type."
        ),
        "aesthetics": "minimal outro card, soft, professional",
        "lighting": "gentle even lighting, high text contrast",
        "medium": "graphic_design",
        "art_style": "simple horizontal end card typography",
    },
    "menu_board": {
        "background": (
            "Cafe interior wall or chalk/menu board surface, shallow depth of field, "
            "realistic materials, soft ambient cafe light."
        ),
        "aesthetics": "photoreal cafe, warm cozy, readable menu typography",
        "lighting": "warm cafe ambient light, soft shadows",
        "medium": "photograph",
        "photo": "35mm, natural cafe interior, f/2.8",
    },
    "signage": {
        "background": (
            "Outdoor or storefront facade where a physical sign is mounted, "
            "photoreal, stable perspective."
        ),
        "aesthetics": "photoreal signage, sharp lettering on physical board",
        "lighting": "daylight or soft storefront lighting, clear readable type",
        "medium": "photograph",
        "photo": "35mm street photography, sharp focus on sign",
    },
    "thumbnail": {
        "background": (
            "Bold short-form thumbnail canvas, strong focal hierarchy, "
            "uncluttered enough for large overlay type."
        ),
        "aesthetics": "YouTube shorts thumbnail, high contrast, punchy but not spammy",
        "lighting": "bright key light, clear subject separation",
        "medium": "graphic_design",
        "art_style": "thumbnail poster with bold horizontal display type",
    },
    "free": {
        "background": "Scene environment matching the high-level description.",
        "aesthetics": "cohesive, clean, high quality",
        "lighting": "natural balanced lighting",
        "medium": "photograph",
        "photo": "35mm, sharp",
    },
}


def resolve_size(aspect: str | None, width: int | None, height: int | None) -> tuple[int, int]:
    if width and height:
        w, h = int(width), int(height)
    elif aspect:
        key = aspect.strip().lower()
        if key not in ASPECT_PRESETS:
            raise ValueError(
                f"unknown aspect {aspect!r}; choose one of {sorted(ASPECT_PRESETS)}"
            )
        w, h = ASPECT_PRESETS[key]
    else:
        w, h = ASPECT_PRESETS["9:16"]
    w = max(256, (w + 15) // 16 * 16)
    h = max(256, (h + 15) // 16 * 16)
    return w, h


def _norm_hex(colors: list[str] | None) -> list[str]:
    out: list[str] = []
    for c in colors or []:
        c = (c or "").strip()
        if not c:
            continue
        if not c.startswith("#"):
            c = "#" + c
        out.append(c.upper())
    return out


def _bbox_norm(
    y0: float, x0: float, y1: float, x1: float
) -> list[int]:
    """Fractions 0..1 → Ideogram bbox [y_min, x_min, y_max, x_max] in 0..1000."""
    return [
        int(max(0, min(1000, round(y0 * 1000)))),
        int(max(0, min(1000, round(x0 * 1000)))),
        int(max(0, min(1000, round(y1 * 1000)))),
        int(max(0, min(1000, round(x1 * 1000)))),
    ]


def _text_element(
    *,
    text: str,
    bbox: list[int],
    desc: str,
    color_palette: list[str] | None = None,
) -> dict[str, Any]:
    """Official key order: type, bbox, text, desc, [color_palette]."""
    el: dict[str, Any] = {
        "type": "text",
        "bbox": bbox,
        "text": text,
        "desc": desc,
    }
    pal = _norm_hex(color_palette)
    if pal:
        el["color_palette"] = pal[:5]
    return el


def _obj_element(
    *,
    bbox: list[int] | None,
    desc: str,
    color_palette: list[str] | None = None,
) -> dict[str, Any]:
    el: dict[str, Any] = {"type": "obj"}
    if bbox is not None:
        el["bbox"] = bbox
    el["desc"] = desc
    pal = _norm_hex(color_palette)
    if pal:
        el["color_palette"] = pal[:5]
    return el


def _style_description(
    *,
    aesthetics: str,
    lighting: str,
    medium: str,
    art_style: str = "",
    photo: str = "",
    color_palette: list[str] | None = None,
    prefer_photo: bool = False,
) -> dict[str, Any]:
    """Strict key order per official schema."""
    pal = _norm_hex(color_palette)
    if prefer_photo or medium == "photograph" or photo:
        style: dict[str, Any] = {
            "aesthetics": aesthetics,
            "lighting": lighting,
            "photo": photo or "35mm, sharp",
            "medium": "photograph",
        }
    else:
        style = {
            "aesthetics": aesthetics,
            "lighting": lighting,
            "medium": medium or "graphic_design",
            "art_style": art_style or "graphic design",
        }
    if pal:
        style["color_palette"] = pal[:16]
    return style


def build_caption(
    *,
    slot: str = "free",
    text: str = "",
    subtitle: str = "",
    scene: str = "",
    high_level: str = "",
    background: str = "",
    aesthetics: str = "",
    lighting: str = "",
    medium: str = "",
    art_style: str = "",
    photo: str = "",
    color_palette: list[str] | None = None,
    width: int = 768,
    height: int = 1344,
    extra_elements: list[dict[str, Any]] | None = None,
    raw_json: str | dict | None = None,
    horizontal_text: bool = True,
) -> dict[str, Any]:
    """Build Ideogram 4 caption dict (schema-faithful).

    ``width``/``height`` are kept for API symmetry but bboxes are aspect-agnostic
    normalized 0–1000 coords.
    """
    del width, height  # bbox is normalized; pixel size is sampler-side only

    if raw_json is not None:
        if isinstance(raw_json, dict):
            return raw_json
        data = json.loads(str(raw_json))
        if not isinstance(data, dict):
            raise ValueError("raw_json must be a JSON object")
        return data

    slot_key = (slot or "free").strip().lower()
    if slot_key not in SLOT_DEFAULTS:
        raise ValueError(f"unknown slot {slot!r}; choose {sorted(SLOT_DEFAULTS)}")

    base = dict(SLOT_DEFAULTS[slot_key])
    text = (text or "").strip()
    subtitle = (subtitle or "").strip()
    scene = (scene or "").strip()
    orient = (
        "horizontal left-to-right line (not vertical stacked letters)"
        if horizontal_text
        else "layout as appropriate"
    )

    if not high_level:
        if slot_key in ("title_card", "thumbnail", "end_card") and text:
            high_level = (
                f"A clean short-form title card. Large {orient} Korean/Latin display type "
                f'reading exactly "{text}"'
                + (f', with smaller subtitle "{subtitle}"' if subtitle else "")
                + (f". Mood: {scene}." if scene else ".")
            )
        elif slot_key == "menu_board" and text:
            high_level = (
                f"A photoreal cafe menu board with clearly readable printed menu text "
                f'including exactly: {text}.'
            )
        elif slot_key == "signage" and text:
            high_level = (
                f'A photoreal storefront sign with legible lettering that reads exactly "{text}".'
            )
        else:
            high_level = scene or "A carefully composed image with clear readable typography."

    bg = background or base.get("background") or "simple clean background"
    aes = aesthetics or base.get("aesthetics") or "clean"
    lit = lighting or base.get("lighting") or "soft even light"
    med = medium or base.get("medium") or "graphic_design"
    prefer_photo = med == "photograph" or bool(base.get("photo") or photo)

    style_desc = _style_description(
        aesthetics=aes,
        lighting=lit,
        medium=med,
        art_style=art_style or base.get("art_style") or "",
        photo=photo or base.get("photo") or "",
        color_palette=color_palette,
        prefer_photo=prefer_photo,
    )

    ink = _norm_hex(color_palette)
    text_ink = [c for c in ink if c not in ("#F5F0E8", "#FFFFFF", "#EFEFEF", "#FDFDFD")][:3]
    if not text_ink:
        text_ink = ["#2C2C2C"]

    elements: list[dict[str, Any]] = []
    if text:
        if slot_key in ("title_card", "thumbnail", "end_card"):
            # center title band: y 0.32–0.52, x 0.08–0.92
            elements.append(
                _text_element(
                    text=text,
                    bbox=_bbox_norm(0.32, 0.08, 0.52, 0.92),
                    desc=(
                        f"Large bold {orient} display typography. "
                        f'The letters must spell exactly "{text}" with correct Hangul/Latin '
                        "spelling, no extra characters, no vertical letter stacking, "
                        "high contrast, sharp edges."
                    ),
                    color_palette=text_ink,
                )
            )
            if subtitle:
                elements.append(
                    _text_element(
                        text=subtitle,
                        bbox=_bbox_norm(0.54, 0.15, 0.66, 0.85),
                        desc=(
                            f"Smaller secondary {orient} typography spelling exactly "
                            f'"{subtitle}". Clear, legible, no misspellings.'
                        ),
                        color_palette=text_ink,
                    )
                )
        elif slot_key == "menu_board":
            elements.append(
                _text_element(
                    text=text,
                    bbox=_bbox_norm(0.15, 0.18, 0.85, 0.82),
                    desc=(
                        f"Menu board lettering. Lines of text must include exactly: {text}. "
                        "Sharp printed or chalk letters, correct spelling, readable."
                    ),
                    color_palette=text_ink or ["#F5F5F5", "#1A1A1A"],
                )
            )
        elif slot_key == "signage":
            elements.append(
                _text_element(
                    text=text,
                    bbox=_bbox_norm(0.22, 0.18, 0.48, 0.82),
                    desc=(
                        f'Physical sign lettering spelling exactly "{text}". '
                        "Sharp, correct spelling, no extra characters."
                    ),
                    color_palette=text_ink,
                )
            )
        else:
            elements.append(
                _text_element(
                    text=text,
                    bbox=_bbox_norm(0.30, 0.10, 0.55, 0.90),
                    desc=(
                        f'Typography spelling exactly "{text}". '
                        f"{orient}. Sharp, correct spelling."
                    ),
                    color_palette=text_ink,
                )
            )

    if extra_elements:
        elements.extend(extra_elements)

    # Ordered top-level keys
    caption: dict[str, Any] = {}
    if high_level.strip():
        caption["high_level_description"] = high_level
    caption["style_description"] = style_desc
    caption["compositional_deconstruction"] = {
        "background": bg,
        "elements": elements,
    }
    return caption


def caption_to_prompt_string(caption: dict[str, Any]) -> str:
    """Serialize for CLIPTextEncode — compact, no \\u escapes, official separators."""
    return json.dumps(caption, ensure_ascii=False, separators=(",", ":"))


def build_prompt_string(**kwargs: Any) -> str:
    w = int(kwargs.pop("width", None) or 768)
    h = int(kwargs.pop("height", None) or 1344)
    cap = build_caption(width=w, height=h, **kwargs)
    return caption_to_prompt_string(cap)
