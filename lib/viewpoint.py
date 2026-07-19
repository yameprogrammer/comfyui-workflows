"""
Depth / viewpoint exaggeration — CAMERA shelf (Comfy / Qwen multi-angle).

Research: docs/viewpoint_research.md
Backend: generate_qwen_angle (horizontal / vertical / zoom ports).
Optional: generate_qwen_edit instruction for extreme text-driven camera.
"""

from __future__ import annotations

import os
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta

# Intent presets → multi-angle camera ports
# h = azimuth degrees, v = elevation (+: high looking down, -: low looking up),
# zoom = distance port (higher ≈ closer in this factory's angle node).
VIEWPOINT_PRESETS: dict[str, dict[str, Any]] = {
    "eye_level": {
        "label": "Eye level",
        "h": 0,
        "v": 0,
        "zoom": 5.5,
        "view_key": "body_front",
        "extra": "eye-level camera, neutral perspective",
    },
    "high_angle": {
        "label": "High angle (looking down)",
        "h": 0,
        "v": 35,
        "zoom": 5.5,
        "view_key": "body_front",
        "extra": "high angle shot looking down at subject",
    },
    "birds_eye": {
        "label": "Bird's eye / top-down",
        "h": 0,
        "v": 70,
        "zoom": 4.0,
        "view_key": "body_front",
        "extra": "bird's eye view, strong top-down camera",
    },
    "low_angle": {
        "label": "Low angle (looking up)",
        "h": 0,
        "v": -30,
        "zoom": 5.5,
        "view_key": "body_front",
        "extra": "low angle shot looking up at subject, heroic perspective",
    },
    "worms_eye": {
        "label": "Worm's eye (extreme low)",
        "h": 0,
        "v": -55,
        "zoom": 6.5,
        "view_key": "body_front",
        "extra": "worm's eye extreme low angle, dramatic upward view",
    },
    "high_qf": {
        "label": "High angle three-quarter",
        "h": 40,
        "v": 30,
        "zoom": 5.5,
        "view_key": "body_qf",
        "extra": "high three-quarter view looking slightly down",
    },
    "low_qf": {
        "label": "Low angle three-quarter",
        "h": 40,
        "v": -28,
        "zoom": 5.5,
        "view_key": "body_qf",
        "extra": "low three-quarter view looking slightly up",
    },
    "side_low": {
        "label": "Profile low angle",
        "h": 90,
        "v": -25,
        "zoom": 5.5,
        "view_key": "body_side",
        "extra": "side profile, low angle",
    },
    "side_high": {
        "label": "Profile high angle",
        "h": 90,
        "v": 30,
        "zoom": 5.5,
        "view_key": "body_side",
        "extra": "side profile, high angle looking down",
    },
    "wide_establishing": {
        "label": "Wide establishing (more depth/env)",
        "h": 0,
        "v": 8,
        "zoom": 3.2,
        "view_key": "body_front",
        "extra": "wide establishing shot, more environment, deep perspective",
    },
    "tight_hero": {
        "label": "Tight hero (close + slight low)",
        "h": 0,
        "v": -18,
        "zoom": 8.5,
        "view_key": "head_front",
        "extra": "tight hero close-up, slight low angle, shallow depth feel",
    },
    "ot_s": {
        "label": "Over-the-shoulder-ish angle",
        "h": 25,
        "v": 5,
        "zoom": 6.0,
        "view_key": "body_qf",
        "extra": "over-the-shoulder style angle, conversational framing",
    },
    "dutch_hint": {
        "label": "Dutch / canted (instruction-heavy)",
        "h": 15,
        "v": -10,
        "zoom": 5.5,
        "view_key": "body_front",
        "extra": "slightly canted dutch angle, uneasy cinematic tilt",
        "prefer_edit": True,
    },
}

ALIASES = {
    "high": "high_angle",
    "low": "low_angle",
    "bird": "birds_eye",
    "birds": "birds_eye",
    "top_down": "birds_eye",
    "worm": "worms_eye",
    "hero": "tight_hero",
    "wide": "wide_establishing",
    "establishing": "wide_establishing",
    "ots": "ot_s",
    "dutch": "dutch_hint",
    "eye": "eye_level",
    "neutral": "eye_level",
}

STRENGTH_SCALE = {
    "soft": 0.65,
    "medium": 1.0,
    "hard": 1.35,
}

ENGINES = ("angle", "edit")


def list_viewpoint_ids() -> list[str]:
    return sorted(VIEWPOINT_PRESETS.keys())


def resolve_viewpoint_id(name: str) -> str:
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in VIEWPOINT_PRESETS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    known = ", ".join(list_viewpoint_ids())
    raise KeyError(f"Unknown viewpoint {name!r}. Known: {known}")


def get_viewpoint_preset(name: str) -> dict[str, Any]:
    pid = resolve_viewpoint_id(name)
    out = dict(VIEWPOINT_PRESETS[pid])
    out["id"] = pid
    return out


def format_viewpoints_help() -> str:
    lines = ["id                  label"]
    for pid in list_viewpoint_ids():
        lines.append(f"{pid:20s} {VIEWPOINT_PRESETS[pid]['label']}")
    lines.append("")
    lines.append("aliases: high→high_angle, low→low_angle, bird→birds_eye, worm→worms_eye, …")
    return "\n".join(lines)


def scale_viewpoint(
    preset: dict[str, Any],
    *,
    strength: str = "medium",
    h_override: int | None = None,
    v_override: int | None = None,
    zoom_override: float | None = None,
) -> tuple[int, int, float]:
    scale = STRENGTH_SCALE.get((strength or "medium").lower(), 1.0)
    h = int(h_override if h_override is not None else preset.get("h", 0))
    v0 = int(preset.get("v", 0))
    v = int(v_override if v_override is not None else round(v0 * scale))
    # clamp elevation to sensible range for multi-angle nodes
    v = max(-80, min(80, v))
    z0 = float(preset.get("zoom", 5.5))
    if zoom_override is not None:
        z = float(zoom_override)
    else:
        # hard strength: exaggerate distance contrast slightly
        if scale > 1.0:
            # if zoom is "close" (>6) push closer; if wide (<4.5) push wider
            if z0 >= 6.0:
                z = z0 + (scale - 1.0) * 1.5
            elif z0 <= 4.0:
                z = max(2.5, z0 - (scale - 1.0) * 0.8)
            else:
                z = z0
        elif scale < 1.0:
            z = z0 * 0.5 + 5.5 * 0.5  # pull toward neutral mid
        else:
            z = z0
    z = max(2.0, min(12.0, float(z)))
    return h, v, z


def build_edit_instruction(
    preset: dict[str, Any],
    *,
    strength: str = "medium",
    extra: str = "",
    preserve_identity: bool = True,
) -> str:
    label = preset.get("label") or preset.get("id")
    base_extra = (preset.get("extra") or "").strip()
    str_note = {
        "soft": "subtle camera change",
        "medium": "clear camera change",
        "hard": "strong dramatic camera change",
    }.get((strength or "medium").lower(), "clear camera change")
    id_line = (
        "Keep the same person identity, wardrobe, and scene content."
        if preserve_identity
        else "Scene content may adapt to the new camera."
    )
    instr = (
        f"Re-render this image from a different camera viewpoint: {label}. "
        f"Camera: {base_extra}. {str_note}. "
        f"{id_line} "
        "Change only camera height, pitch, and implied lens distance / perspective. "
        "Do not change the story subject into someone else."
    )
    extra = (extra or "").strip()
    if extra:
        instr = f"{instr} Additional: {extra}"
    return instr


def run_viewpoint(
    *,
    input_image: str,
    output_path: str,
    preset: str | None = None,
    engine: str = "angle",
    strength: str = "medium",
    horizontal_angle: int | None = None,
    vertical_angle: int | None = None,
    zoom: float | None = None,
    extra: str = "",
    preserve_identity: bool = True,
    seed: int | None = None,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    angles_strength: float | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)

    engine = (engine or "angle").lower().strip()
    if engine not in ENGINES:
        return fail_result(error="BAD_ENGINE", message=f"engine must be one of {ENGINES}")

    # Resolve preset or custom ports
    if preset:
        try:
            vp = get_viewpoint_preset(preset)
        except KeyError as e:
            return fail_result(error="BAD_PRESET", message=str(e))
    else:
        if horizontal_angle is None and vertical_angle is None and zoom is None:
            return fail_result(
                error="PRESET_OR_ANGLES",
                message="Need --preset or at least one of --h/--v/--zoom",
            )
        vp = {
            "id": "custom",
            "label": "custom",
            "h": horizontal_angle or 0,
            "v": vertical_angle or 0,
            "zoom": zoom if zoom is not None else 5.5,
            "view_key": "body_front",
            "extra": extra or "custom camera",
        }

    h, v, z = scale_viewpoint(
        vp,
        strength=strength,
        h_override=horizontal_angle,
        v_override=vertical_angle,
        zoom_override=zoom,
    )
    prefer_edit = bool(vp.get("prefer_edit")) and engine == "angle"
    if prefer_edit:
        engine = "edit"

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    view_key = str(vp.get("view_key") or "body_front")
    extra_combined = ", ".join(
        x for x in ((vp.get("extra") or "").strip(), (extra or "").strip()) if x
    )

    # angles_strength: soft 0.85 / medium 1.0 / hard 1.15
    if angles_strength is None:
        angles_strength = {
            "soft": 0.85,
            "medium": 1.0,
            "hard": 1.15,
        }.get((strength or "medium").lower(), 1.0)

    if engine == "edit":
        from generate_qwen_edit import generate_qwen_edit

        instruction = build_edit_instruction(
            {**vp, "id": vp.get("id")},
            strength=strength,
            extra=extra,
            preserve_identity=preserve_identity,
        )
        r = generate_qwen_edit(
            input_image,
            instruction,
            output_filename=output_path,
            seed=seed,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
            raw_prompt=True,
        )
        backend_meta = {"engine": "edit", "instruction_preview": instruction[:300]}
    else:
        from generate_qwen_angle import generate_qwen_angle

        r = generate_qwen_angle(
            input_image,
            view_key,
            output_filename=output_path,
            seed=seed,
            extra_prompt=extra_combined,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
            horizontal_angle=h,
            vertical_angle=v,
            zoom=z,
            angles_strength=float(angles_strength),
        )
        backend_meta = {
            "engine": "angle",
            "view_key": view_key,
            "horizontal_angle": h,
            "vertical_angle": v,
            "zoom": z,
            "angles_strength": angles_strength,
            "extra": extra_combined,
        }

    if not r.get("ok"):
        return r

    meta = r.get("meta") or {}
    meta.update(
        {
            "tool": "generate_viewpoint",
            "viewpoint_preset": vp.get("id"),
            "viewpoint_label": vp.get("label"),
            "strength": strength,
            "source_image": os.path.abspath(input_image),
            "research": "docs/viewpoint_research.md",
            "created_at": utc_now_iso(),
            **backend_meta,
        }
    )
    meta_path = r.get("meta_path")
    if meta_path:
        write_meta(meta_path, meta)
    else:
        mp = os.path.splitext(output_path)[0] + ".json"
        write_meta(mp, meta)
        meta_path = mp

    return ok_result(
        output_path=r.get("output_path") or os.path.abspath(output_path),
        seed=r.get("seed"),
        prompt_id=r.get("prompt_id"),
        meta=meta,
        meta_path=meta_path,
        viewpoint=backend_meta,
    )
