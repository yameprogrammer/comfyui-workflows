"""
I2V motion **intent** presets — toolbox MOTION shelf.

Agents pick a short id instead of inventing camera language every time.
Compose with free-text ``extra`` for scene-specific action.

First-class CLI: ``scripts/generate_camera_move.py --preset <id>``.
Also: ``generate_i2v --motion-preset`` · ``episode_i2v --motion-preset`` · shot.``motion_preset``.
"""

from __future__ import annotations

from typing import Any

# id → motion-only language (I2V: do not re-describe face/wardrobe)
MOTION_PRESETS: dict[str, dict[str, Any]] = {
    "idle": {
        "label": "Subtle life",
        "prompt": (
            "subtle natural motion, gentle breathing, micro facial life, "
            "camera locked, no pan no zoom, continuous small movement"
        ),
        "negative_extra": "big camera move, whip pan, morphing face, teleport",
    },
    "push_in": {
        "label": "Slow push-in",
        "prompt": (
            "slow cinematic push-in toward subject, smooth dolly forward, "
            "stable framing, natural subject micro-motion"
        ),
        "negative_extra": "snap zoom, handheld shake, rotating camera wildly",
    },
    "pull_out": {
        "label": "Slow pull-out",
        "prompt": (
            "slow cinematic pull-out revealing environment, smooth dolly back, "
            "subject remains clear, natural motion"
        ),
        "negative_extra": "crash zoom, snap cut, identity change",
    },
    "pan_left": {
        "label": "Gentle pan left",
        "prompt": (
            "gentle camera pan left, smooth horizontal move, "
            "subject stays in frame, natural ambient motion"
        ),
        "negative_extra": "whip pan, roll, tilt chaos",
    },
    "pan_right": {
        "label": "Gentle pan right",
        "prompt": (
            "gentle camera pan right, smooth horizontal move, "
            "subject stays in frame, natural ambient motion"
        ),
        "negative_extra": "whip pan, roll, tilt chaos",
    },
    "orbit_subtle": {
        "label": "Subtle arc/orbit",
        "prompt": (
            "subtle arc move around subject, slight parallax, "
            "slow controlled orbit fragment, face readable"
        ),
        "negative_extra": "full 360 spin, dizzy whip, face smear",
    },
    "talk_gesture": {
        "label": "Talking + light gesture",
        "prompt": (
            "person speaking naturally, clear mouth and jaw motion for dialogue, "
            "small head nods, light hand gesture if visible, "
            "camera mostly locked with micro drift"
        ),
        "negative_extra": "static closed mouth, frozen face, huge body thrash",
    },
    "smile_turn": {
        "label": "Smile + slight head turn",
        "prompt": (
            "soft smile forming, slight head turn, natural eye movement, "
            "gentle hair and cloth motion, camera locked"
        ),
        "negative_extra": "identity morph, exaggerated cartoon face",
    },
    "walk_toward": {
        "label": "Walk toward camera",
        "prompt": (
            "subject walks slowly toward camera, natural gait, "
            "stable horizon, continuous motion, medium full body if visible"
        ),
        "negative_extra": "sliding feet, teleport, broken legs, static pose",
    },
    "look_away": {
        "label": "Gaze shift",
        "prompt": (
            "eyes and head slowly look toward frame edge then settle, "
            "subtle expression change, camera locked"
        ),
        "negative_extra": "face warp, multiple faces",
    },
    "wind_hair": {
        "label": "Wind / atmosphere",
        "prompt": (
            "gentle wind moving hair and clothing, ambient particle or light flicker, "
            "subject mostly still, cinematic atmosphere, camera locked"
        ),
        "negative_extra": "hurricane, face deformation",
    },
    "product_orbit": {
        "label": "Object/product micro orbit",
        "prompt": (
            "slow controlled product-style turntable motion, "
            "clean lighting continuity, camera arcs slightly around subject"
        ),
        "negative_extra": "human face morph, chaotic spin",
    },
}

ALIASES: dict[str, str] = {
    "push": "push_in",
    "pushin": "push_in",
    "dolly_in": "push_in",
    "pull": "pull_out",
    "pullout": "pull_out",
    "dolly_out": "pull_out",
    "pan-l": "pan_left",
    "pan-r": "pan_right",
    "orbit": "orbit_subtle",
    "talk": "talk_gesture",
    "speak": "talk_gesture",
    "dialogue": "talk_gesture",
    "smile": "smile_turn",
    "walk": "walk_toward",
    "gaze": "look_away",
    "wind": "wind_hair",
    "product": "product_orbit",
    "still": "idle",
    "breathing": "idle",
}


def list_motion_preset_ids() -> list[str]:
    return sorted(MOTION_PRESETS.keys())


def resolve_motion_preset_id(name: str | None) -> str | None:
    if not name or not str(name).strip():
        return None
    key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if key in MOTION_PRESETS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    return None


def get_motion_preset(name: str) -> dict[str, Any]:
    pid = resolve_motion_preset_id(name)
    if not pid:
        known = ", ".join(list_motion_preset_ids())
        raise KeyError(f"Unknown motion preset {name!r}. Known: {known}")
    out = dict(MOTION_PRESETS[pid])
    out["id"] = pid
    return out


def compose_motion_prompt(
    preset: str | None,
    extra: str | None = None,
    *,
    preset_first: bool = True,
) -> tuple[str, str | None]:
    """
    Return (positive_motion, negative_extra_or_none).

    If preset is None, returns (extra or "", None).
    """
    extra_s = (extra or "").strip()
    if not preset:
        return extra_s, None
    p = get_motion_preset(preset)
    base = str(p.get("prompt") or "").strip()
    neg = str(p.get("negative_extra") or "").strip() or None
    if extra_s and base:
        if preset_first:
            pos = f"{base}, {extra_s}"
        else:
            pos = f"{extra_s}, {base}"
    else:
        pos = base or extra_s
    return pos, neg


def format_motion_presets_help() -> str:
    lines = ["id                  label"]
    for pid in list_motion_preset_ids():
        lab = MOTION_PRESETS[pid].get("label", "")
        lines.append(f"{pid:20s} {lab}")
    lines.append("")
    lines.append("aliases: " + ", ".join(f"{k}→{v}" for k, v in sorted(ALIASES.items())[:12]) + ", …")
    return "\n".join(lines)
