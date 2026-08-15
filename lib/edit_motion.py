"""Composable overlay motion. Named motions are shortcuts only."""

from __future__ import annotations

from typing import Any

DIRECTIONS = ("none", "up", "down", "left", "right")
MOTION_NAMES = ("none", "fade", "pop", "slide", "slide_up", "slide_down", "custom")

# Shortcut recipes. Agent may omit these and pass parts.
MOTION_PRESETS: dict[str, dict[str, Any]] = {
    "none": {},
    "fade": {"fade_in": 0.12, "fade_out": 0.10},
    "pop": {
        "fade_in": 0.10,
        "fade_out": 0.10,
        "move": 0.16,
        "scale_from": 0.84,
        "scale_to": 1.0,
        "dy": 18,
    },
    "slide": {
        "fade_in": 0.14,
        "fade_out": 0.12,
        "move": 0.18,
        "direction": "up",
        "distance": 72,
    },
    "slide_up": {
        "fade_in": 0.14,
        "fade_out": 0.12,
        "move": 0.18,
        "direction": "up",
        "distance": 72,
    },
    "slide_down": {
        "fade_in": 0.14,
        "fade_out": 0.12,
        "move": 0.18,
        "direction": "down",
        "distance": 56,
    },
}


def list_motion_parts() -> dict[str, Any]:
    return {
        "shortcuts": list(MOTION_PRESETS.keys()),
        "shortcut_note": "optional start. compose the parts below.",
        "parts": [
            "fade_in",
            "fade_out",
            "move",
            "scale_from",
            "scale_to",
            "direction",
            "distance",
            "dx",
            "dy",
        ],
        "directions": list(DIRECTIONS),
        "units": {
            "fade_in": "seconds",
            "fade_out": "seconds",
            "move": "seconds (travel + scale)",
            "scale_from": "0.2–2.0 (1 = rest)",
            "scale_to": "0.2–2.0",
            "distance": "px, or 0–1 as fraction of frame",
            "dx": "px start offset (positive = from the right)",
            "dy": "px start offset (positive = from below)",
        },
    }


def _num(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    return float(value)


def _offset_from_direction(
    direction: str | None,
    distance: float | None,
    *,
    width: int,
    height: int,
) -> tuple[float, float]:
    if not direction or direction == "none" or distance is None:
        return 0.0, 0.0
    dist = float(distance)
    if 0 < abs(dist) <= 1.0:
        if direction in ("up", "down"):
            dist = dist * height
        else:
            dist = dist * width
    if direction == "up":
        return 0.0, abs(dist)
    if direction == "down":
        return 0.0, -abs(dist)
    if direction == "left":
        return abs(dist), 0.0
    if direction == "right":
        return -abs(dist), 0.0
    return 0.0, 0.0


def compose_motion(
    overlay: dict[str, Any],
    *,
    width: int = 1920,
    height: int = 1080,
) -> dict[str, Any]:
    """Merge a named shortcut with independent motion parts."""
    raw = str(overlay.get("motion") or "").strip().lower()
    warning = None
    has_parts = any(
        overlay.get(k) is not None
        for k in (
            "fade_in",
            "fade_out",
            "move",
            "scale_from",
            "scale_to",
            "direction",
            "distance",
            "dx",
            "dy",
        )
    )
    if raw in ("", "none"):
        base: dict[str, Any] = {}
        name = "custom" if has_parts else "none"
    elif raw in MOTION_PRESETS:
        base = dict(MOTION_PRESETS[raw])
        name = raw
    else:
        base = {}
        name = "custom" if has_parts else "fade"
        if name == "fade":
            base = dict(MOTION_PRESETS["fade"])
        warning = f"unknown motion {raw!r} → {name}"

    fade_in = _num(overlay.get("fade_in"), _num(base.get("fade_in"), 0.0)) or 0.0
    fade_out = _num(overlay.get("fade_out"), _num(base.get("fade_out"), 0.0)) or 0.0
    move = _num(overlay.get("move"), _num(base.get("move"), 0.0)) or 0.0
    scale_from = _num(overlay.get("scale_from"), _num(base.get("scale_from"), 1.0)) or 1.0
    scale_to = _num(overlay.get("scale_to"), _num(base.get("scale_to"), 1.0)) or 1.0
    direction = overlay.get("direction")
    if direction is None:
        direction = base.get("direction") or "none"
    direction = str(direction).strip().lower()
    if direction not in DIRECTIONS:
        direction = "none"
    distance = overlay.get("distance")
    if distance is None:
        distance = base.get("distance")

    dx = overlay.get("dx")
    dy = overlay.get("dy")
    if dx is None and dy is None:
        if "dx" in base or "dy" in base:
            dx = base.get("dx", 0.0)
            dy = base.get("dy", 0.0)
        else:
            dx, dy = _offset_from_direction(direction, _num(distance), width=width, height=height)
    else:
        dx = float(dx or 0.0)
        dy = float(dy or 0.0)

    s = float(overlay.get("start") or 0.0)
    e = float(overlay.get("end") or 0.0)
    out = {
        "name": name,
        "start": s,
        "end": e,
        "fade_in": max(0.0, fade_in),
        "fade_out": max(0.0, fade_out),
        "move": max(0.0, move),
        "scale_from": min(2.5, max(0.2, scale_from)),
        "scale_to": min(2.5, max(0.2, scale_to)),
        "direction": direction,
        "dx": float(dx or 0.0),
        "dy": float(dy or 0.0),
    }
    if warning:
        out["warning"] = warning
    return out
