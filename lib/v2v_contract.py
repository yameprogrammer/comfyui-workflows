"""V2V intent contracts: camera / motion / style.

See docs/v2v_intent_pipeline_design.md.
"""

from __future__ import annotations

from typing import Any

# motion_driver values (episode / schema)
V2V_DRIVERS = ("v2v_camera", "v2v_motion", "v2v_style")

# CLI / video_refs.intent
V2V_INTENTS = ("camera", "motion", "style")

INTENT_TO_DRIVER = {
    "camera": "v2v_camera",
    "motion": "v2v_motion",
    "style": "v2v_style",
}

DRIVER_TO_INTENT = {v: k for k, v in INTENT_TO_DRIVER.items()}

# Default strength guides (meta + future node mapping)
DEFAULT_STRENGTH: dict[str, float] = {
    "camera": 0.65,
    "motion": 0.75,
    "style": 0.40,
}

INTENT_PROMPT: dict[str, str] = {
    "camera": (
        "match camera movement, framing, and pacing from the reference video only; "
        "lock subject identity, wardrobe, and scene layout; subtle ambient motion; "
        "cinematic continuity, no new story action"
    ),
    "motion": (
        "match body motion, gesture timing, and camera from the reference video; "
        "keep face identity and clothing fixed; natural physics; "
        "do not copy reference face identity onto the subject"
    ),
    "style": (
        "preserve camera motion, composition, and timing from the reference video; "
        "restyle look, grade, and material to the target style; "
        "do not invent new actions or change shot structure"
    ),
}

INTENT_NEGATIVE_EXTRA: dict[str, str] = {
    "camera": "identity shift, wardrobe change, morphing face, extra limbs",
    "motion": "wrong identity, face swap, extra fingers, rubber limbs, still image",
    "style": "layout change, new camera path, different action, text, watermark",
}


def normalize_intent(raw: str | None) -> str:
    s = (raw or "camera").strip().lower().replace("-", "_")
    aliases = {
        "cam": "camera",
        "camera_ref": "camera",
        "camera_reference": "camera",
        "retarget": "motion",
        "motion_ref": "motion",
        "motion_reference": "motion",
        "dance": "motion",
        "style_transfer": "style",
        "style_ref": "style",
        "restyle": "style",
    }
    s = aliases.get(s, s)
    if s in DRIVER_TO_INTENT:
        return DRIVER_TO_INTENT[s]
    if s not in V2V_INTENTS:
        raise ValueError(f"unknown v2v intent {raw!r}; choose from {V2V_INTENTS}")
    return s


def intent_from_motion_driver(driver: str | None) -> str | None:
    d = (driver or "").strip().lower()
    return DRIVER_TO_INTENT.get(d)


def resolve_strength(intent: str, explicit: float | None = None) -> float:
    intent = normalize_intent(intent)
    if explicit is not None:
        return max(0.05, min(1.0, float(explicit)))
    return float(DEFAULT_STRENGTH[intent])


def build_prompt(intent: str, user_prompt: str | None = None) -> str:
    intent = normalize_intent(intent)
    base = INTENT_PROMPT[intent]
    extra = (user_prompt or "").strip()
    if not extra:
        return base
    return f"{base}, {extra}"


def build_negative(intent: str, user_negative: str | None = None) -> str:
    intent = normalize_intent(intent)
    parts = [
        "bright tones, overexposed, static, blurred details, subtitles, watermark, "
        "ugly, deformed, still picture",
        INTENT_NEGATIVE_EXTRA[intent],
    ]
    if user_negative and user_negative.strip():
        parts.append(user_negative.strip())
    return ", ".join(parts)


def validate_v2v_inputs(
    *,
    intent: str,
    video_path: str | None,
    image_path: str | None,
    require_image_for_style: bool = False,
) -> list[dict[str, Any]]:
    """Return list of issue dicts {code, message}. Empty = ok."""
    issues: list[dict[str, Any]] = []
    try:
        intent = normalize_intent(intent)
    except ValueError as e:
        return [{"code": "BAD_INTENT", "message": str(e)}]

    if not video_path:
        issues.append({"code": "VIDEO_REQUIRED", "message": "driving/reference video path required (-v)"})
    if intent in ("camera", "motion") and not image_path:
        issues.append(
            {
                "code": "IMAGE_REQUIRED",
                "message": f"intent={intent} needs identity/scene still (-i)",
            }
        )
    if intent == "style" and require_image_for_style and not image_path:
        issues.append(
            {
                "code": "IMAGE_REQUIRED",
                "message": "style intent configured to require still (-i)",
            }
        )
    return issues


def resolve_clip_duration_sec(
    *,
    video_duration_sec: float | None,
    trim_start_sec: float = 0.0,
    trim_duration_sec: float | None = None,
    explicit_duration_sec: float | None = None,
    max_sec: float = 20.0,
) -> tuple[float, dict[str, Any]]:
    """Resolve output/trim length for V2V.

    Priority: explicit_duration → trim_duration → (video_duration - start).
    """
    meta: dict[str, Any] = {
        "video_duration_sec": video_duration_sec,
        "trim_start_sec": float(trim_start_sec or 0.0),
        "trim_duration_sec": trim_duration_sec,
        "explicit_duration_sec": explicit_duration_sec,
    }
    start = max(0.0, float(trim_start_sec or 0.0))
    if explicit_duration_sec is not None and float(explicit_duration_sec) > 0:
        dur = float(explicit_duration_sec)
    elif trim_duration_sec is not None and float(trim_duration_sec) > 0:
        dur = float(trim_duration_sec)
    elif video_duration_sec is not None and float(video_duration_sec) > 0:
        dur = max(0.1, float(video_duration_sec) - start)
    else:
        dur = 3.0
        meta["assumed_default_sec"] = 3.0

    if video_duration_sec is not None and float(video_duration_sec) > 0:
        avail = float(video_duration_sec) - start
        if avail <= 0.05:
            raise ValueError(
                f"V2V_TRIM_EMPTY: trim_start={start}s exceeds video {video_duration_sec}s"
            )
        if dur > avail + 0.05:
            raise ValueError(
                f"V2V_TRIM_EXCEEDS: need {dur:.2f}s from t={start:.2f} but only {avail:.2f}s left "
                f"(video={video_duration_sec:.2f}s). Shorten --duration / trim."
            )
        dur = min(dur, avail)

    dur = max(0.1, min(float(max_sec), dur))
    meta["resolved_duration_sec"] = dur
    return dur, meta


def shot_v2v_plan(shot: dict[str, Any]) -> dict[str, Any] | None:
    """If shot is a V2V driver, return normalized plan; else None."""
    driver = (shot.get("motion_driver") or "").strip().lower()
    refs = shot.get("video_refs") if isinstance(shot.get("video_refs"), dict) else {}
    intent = None
    if driver in V2V_DRIVERS:
        intent = DRIVER_TO_INTENT[driver]
    elif refs.get("intent") or refs.get("driving"):
        try:
            intent = normalize_intent(refs.get("intent") or "camera")
        except ValueError:
            intent = "camera"
    if not intent:
        return None
    driving = refs.get("driving") or refs.get("video") or refs.get("path")
    return {
        "intent": intent,
        "motion_driver": INTENT_TO_DRIVER[intent],
        "driving": driving,
        "trim_start_sec": float(refs.get("trim_start_sec") or 0.0),
        "trim_duration_sec": refs.get("trim_duration_sec"),
        "strength": resolve_strength(intent, refs.get("strength")),
        "keyframe": shot.get("keyframe") or shot.get("keyframe_path"),
        "look_id": shot.get("look_id"),
        "shot_id": shot.get("shot_id"),
    }
