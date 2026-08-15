"""Composable grade / look. Named looks are shortcuts.

  python scripts/comp_shot.py --list-looks
  python scripts/comp_shot.py --look night -i clip.mp4 -o graded.mp4
"""

from __future__ import annotations

import os
from typing import Any

LOOKS: dict[str, dict[str, Any]] = {
    "punch": {
        "use": "쇼츠·예능 기본",
        "contrast": 1.08,
        "saturation": 1.10,
    },
    "night": {
        "use": "밤·네온",
        "contrast": 1.10,
        "saturation": 1.04,
        "brightness": -0.05,
        "temperature": -0.16,
    },
    "warm": {
        "use": "석양·살색",
        "contrast": 1.04,
        "saturation": 1.08,
        "temperature": 0.18,
    },
    "cool": {
        "use": "청량·도시",
        "contrast": 1.05,
        "saturation": 0.98,
        "temperature": -0.20,
    },
    "soft": {
        "use": "소프트·인터뷰",
        "contrast": 0.94,
        "saturation": 0.92,
        "brightness": 0.04,
    },
    "bleach": {
        "use": "탈색",
        "contrast": 1.12,
        "saturation": 0.45,
    },
    "none": {
        "use": "그레이드 없음",
        "contrast": 1.0,
        "saturation": 1.0,
        "brightness": 0.0,
        "gamma": 1.0,
        "temperature": 0.0,
    },
}

_KEY_COLORS = {
    "green": "#00FF00",
    "blue": "#0000FF",
    "magenta": "#FF00FF",
    "black": "#000000",
    "white": "#FFFFFF",
}


def list_looks() -> list[dict[str, Any]]:
    rows = []
    for name, spec in LOOKS.items():
        rows.append(
            {
                "name": name,
                "use": spec.get("use"),
                "contrast": spec.get("contrast", 1.0),
                "saturation": spec.get("saturation", 1.0),
                "temperature": spec.get("temperature", 0.0),
            }
        )
    return rows


def list_look_parts() -> dict[str, Any]:
    return {
        "shortcuts": list(LOOKS.keys()),
        "parts": [
            "contrast",
            "saturation",
            "brightness",
            "gamma",
            "temperature",
            "lut",
            "key_color",
            "key_similarity",
            "key_blend",
            "key_background",
        ],
        "part_note": "look name is a shortcut. compose parts. key_* only when punching a background.",
        "temperature": "-1 cool … +1 warm (use about ±0.2)",
        "key_colors": list(_KEY_COLORS.keys()) + ["#RRGGBB"],
    }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _as_look_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        return {"name": raw.strip().lower()}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def compose_look(raw: Any) -> dict[str, Any]:
    src = _as_look_dict(raw)
    name = str(src.get("name") or src.get("look") or "").strip().lower()
    warning = None
    if name and name not in LOOKS:
        warning = f"unknown look {name!r} → punch"
        name = "punch"
    if not name:
        name = "punch" if not any(
            src.get(k) is not None
            for k in (
                "contrast",
                "saturation",
                "brightness",
                "gamma",
                "temperature",
                "lut",
            )
        ) else "custom"
    base = dict(LOOKS[name]) if name in LOOKS else {}
    contrast = _clamp(src["contrast"] if src.get("contrast") is not None else base.get("contrast", 1.0), 0.4, 2.0)
    saturation = _clamp(
        src["saturation"] if src.get("saturation") is not None else base.get("saturation", 1.0),
        0.0,
        3.0,
    )
    brightness = _clamp(
        src["brightness"] if src.get("brightness") is not None else base.get("brightness", 0.0),
        -0.5,
        0.5,
    )
    gamma = _clamp(src["gamma"] if src.get("gamma") is not None else base.get("gamma", 1.0), 0.3, 3.0)
    temperature = _clamp(
        src["temperature"] if src.get("temperature") is not None else base.get("temperature", 0.0),
        -0.5,
        0.5,
    )
    lut = src.get("lut") or base.get("lut")
    if lut:
        lut = os.path.abspath(str(lut))
        if not os.path.isfile(lut):
            warning = (warning + "; " if warning else "") + f"LUT missing {lut}"
            lut = None
    out = {
        "name": name,
        "contrast": contrast,
        "saturation": saturation,
        "brightness": brightness,
        "gamma": gamma,
        "temperature": temperature,
        "lut": lut,
    }
    if warning:
        out["warning"] = warning
    return out


def parse_key_color(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip().lower()
    if raw in {"none", "off", "-"}:
        return None
    if raw in _KEY_COLORS:
        raw = _KEY_COLORS[raw]
    if raw.startswith("#") and len(raw) == 7:
        return "0x" + raw[1:].upper()
    if raw.startswith("0x") and len(raw) == 8:
        return raw.upper()
    raise ValueError(f"bad key color {value!r}")


def compose_key(raw: Any) -> dict[str, Any] | None:
    if not raw:
        return None
    if isinstance(raw, str):
        raw = {"color": raw}
    if not isinstance(raw, dict):
        return None
    color = parse_key_color(raw.get("color") or raw.get("key_color"))
    if not color:
        return None
    bg = raw.get("background") or raw.get("key_background") or "#000000"
    if isinstance(bg, str) and bg.startswith("#") and len(bg) == 7:
        bg_ff = "0x" + bg[1:]
    elif isinstance(bg, str) and os.path.isfile(bg):
        bg_ff = os.path.abspath(bg)
    else:
        bg_ff = "0x000000"
    return {
        "color": color,
        "similarity": _clamp(raw.get("similarity", raw.get("key_similarity", 0.18)), 0.01, 0.8),
        "blend": _clamp(raw.get("blend", raw.get("key_blend", 0.06)), 0.0, 0.5),
        "background": bg_ff,
    }


def look_filter(look: dict[str, Any]) -> str:
    """eq + optional colorbalance + optional lut3d. Empty if identity."""
    parts: list[str] = []
    c, s, b, g = look["contrast"], look["saturation"], look["brightness"], look["gamma"]
    if abs(c - 1.0) > 1e-3 or abs(s - 1.0) > 1e-3 or abs(b) > 1e-3 or abs(g - 1.0) > 1e-3:
        parts.append(
            f"eq=contrast={c:.3f}:brightness={b:.3f}:saturation={s:.3f}:gamma={g:.3f}"
        )
    t = float(look.get("temperature") or 0.0)
    if abs(t) > 0.01:
        parts.append(
            f"colorbalance=rs={t:.3f}:gs={t * 0.25:.3f}:bs={-t:.3f}"
            f":rm={t:.3f}:gm={t * 0.2:.3f}:bm={-t:.3f}"
        )
    lut = look.get("lut")
    if lut:
        path = str(lut).replace("\\", "/")
        parts.append(f"lut3d=file='{path}'")
    return ",".join(parts)
