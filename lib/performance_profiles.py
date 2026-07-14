"""Emotion-linked performance profiles for TTS + SI2V (P0-2).

Calm is the floor; emotion peaks only where the voice needs them.
Same key used for:
  - shot.performance / shot.emotion
  - episode_tts --performance (instruct)
  - episode_s2v motion_prompt + audio_scale

Not a hard schema — soft convention stored on the shot.
"""

from __future__ import annotations

from typing import Any

# Speak markers: if present, do NOT replace motion with a generic template.
# Prefer multi-word phrases — bare "mouth"/"lip" false-positives on "static mouth".
SPEAK_MARKERS: tuple[str, ...] = (
    "speaking",
    "speak with",
    "speak to",
    "lip sync",
    "lip-sync",
    "lipsync",
    "mouth opens",
    "mouth open",
    "jaw movement",
    "talking",
    "dialogue",
    "singing",
    "sing to",
    "on-camera vocal",
)

# Only strong anti-talk phrases (not bare "still" / "static")
ANTI_TALK_PHRASES: tuple[str, ...] = (
    "static mouth",
    "closed lips",
    "closed mouth",
    "frozen face",
    "frozen mouth",
    "no lip",
    "no mouth movement",
    "still image",
    "do not change",
    "do not move mouth",
    "mouth closed",
    "identity morph",
    "micro facial only",  # pure I2V idle without speech
)

# CLI / shot.emotion aliases → profile id
EMOTION_ALIASES: dict[str, str] = {
    "calm": "neutral_calm",
    "neutral": "neutral_calm",
    "default": "neutral_calm",
    "info": "neutral_calm",
    "greeting": "warm_greeting",
    "hello": "warm_greeting",
    "warm": "warm_greeting",
    "friendly": "warm_greeting",
    "unsatisfied": "mild_unsatisfied",
    "annoyed": "mild_unsatisfied",
    "awkward": "mild_unsatisfied",
    "embarrassed": "mild_unsatisfied",
    "think": "thoughtful",
    "thinking": "thoughtful",
    "thoughtful": "thoughtful",
    "ponder": "thoughtful",
    "cute": "cute_ask",
    "ask": "cute_ask",
    "question": "cute_ask",
    "sip": "sip_business",
    "business": "sip_business",
    "idle": "sip_business",
}

DEFAULT_PERFORMANCE = "neutral_calm"

# motion_prompt templates: lip always first; body intensity is the variable
PROFILES: dict[str, dict[str, Any]] = {
    "neutral_calm": {
        "label": "담담 정보",
        "tts_instruct": (
            "calm clear Korean speech, soft natural young woman tone, neutral informative, "
            "not dramatic, intimate close-mic"
        ),
        "motion_prompt": (
            "person speaking with natural lip sync only, mouth opens and closes with dialogue, "
            "jaw movement, almost fixed upper body, minimal micro blinks, locked camera, "
            "no big head turns, no gestures, no exaggerated expression, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "static mouth, closed lips, frozen face, exaggerated acting, big head sway, "
            "shoulder dance, identity morph, warp"
        ),
        "audio_scale": 1.25,
        "body": "lip-first, torso locked",
    },
    "warm_greeting": {
        "label": "밝은 인사",
        "tts_instruct": (
            "warm friendly Korean greeting, soft smile in the voice, polite bright, "
            "natural young woman, not shouty"
        ),
        "motion_prompt": (
            "person speaking with natural lip sync, warm soft smile, tiny polite head nod, "
            "mouth opens and closes with dialogue, very small upper-body ease, locked camera, "
            "no big gestures, no exaggerated bounce, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "static mouth, closed lips, frozen face, overacting, big head turns, "
            "wave arms, identity morph"
        ),
        "audio_scale": 1.35,
        "body": "micro smile + tiny nod",
    },
    "mild_unsatisfied": {
        "label": "가벼운 불만·당황",
        "tts_instruct": (
            "mildly unsatisfied or awkward Korean speech, soft complaint, not angry shout, "
            "slight sigh quality, natural young woman"
        ),
        "motion_prompt": (
            "person speaking with natural lip sync, slight furrowed brow micro-expression, "
            "mouth opens and closes with dialogue, arms stay as posed (e.g. crossed), "
            "minimal head shake only, locked camera, no big thrashing, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "static mouth, closed lips, frozen face, angry yelling face, big thrashing, "
            "identity morph, cartoon exaggerate"
        ),
        "audio_scale": 1.3,
        "body": "micro frown, pose hold",
    },
    "thoughtful": {
        "label": "차분 사고",
        "tts_instruct": (
            "thoughtful quiet Korean speech, slight pause feel, soft reflective, "
            "natural young woman, intimate"
        ),
        "motion_prompt": (
            "person speaking with natural lip sync, thoughtful soft eyes, tiny head tilt, "
            "mouth opens and closes with dialogue, otherwise still upper body, locked camera, "
            "no big gestures, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "static mouth, closed lips, frozen face, frantic motion, exaggerated nod, "
            "identity morph"
        ),
        "audio_scale": 1.25,
        "body": "micro head tilt",
    },
    "cute_ask": {
        "label": "귀여운 질문",
        "tts_instruct": (
            "cute soft Korean question tone, slightly rising intonation, gentle, "
            "natural young woman, not baby-voice extreme"
        ),
        "motion_prompt": (
            "person speaking with natural lip sync, soft curious expression, slight smile, "
            "mouth opens and closes with dialogue, micro lean-in only, locked camera, "
            "no big gestures, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "static mouth, closed lips, frozen face, big lean, exaggerated cute overact, "
            "identity morph"
        ),
        "audio_scale": 1.35,
        "body": "soft smile, micro lean",
    },
    "sip_business": {
        "label": "무대사 비지니스(소품)",
        "tts_instruct": "",  # usually no TTS
        "motion_prompt": (
            "natural business action with prop (e.g. sip drink), calm face, "
            "clear small prop motion, no talking mouth unless audio, keep identity wardrobe fixed"
        ),
        "negative_motion": (
            "exaggerated face, big head thrash, identity morph, lip flap without speech"
        ),
        "audio_scale": 1.2,
        "body": "prop action, face calm",
        "for_si2v": False,  # typically i2v
    },
}


def list_profiles() -> list[str]:
    return sorted(PROFILES.keys())


def normalize_performance_id(name: str | None) -> str | None:
    if not name:
        return None
    key = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        return None
    if key in PROFILES:
        return key
    if key in EMOTION_ALIASES:
        return EMOTION_ALIASES[key]
    return None


def get_profile(name: str | None) -> dict[str, Any] | None:
    pid = normalize_performance_id(name)
    if not pid:
        return None
    p = dict(PROFILES[pid])
    p["id"] = pid
    return p


def resolve_performance(
    shot: dict[str, Any] | None = None,
    *,
    cli: str | None = None,
    default: str = DEFAULT_PERFORMANCE,
) -> str:
    """Order: CLI → shot.performance → shot.emotion → default."""
    for cand in (cli, (shot or {}).get("performance"), (shot or {}).get("emotion")):
        pid = normalize_performance_id(cand if cand is None else str(cand))
        if pid:
            return pid
    return normalize_performance_id(default) or DEFAULT_PERFORMANCE


def has_speak_markers(motion: str) -> bool:
    low = (motion or "").lower()
    return any(k in low for k in SPEAK_MARKERS)


def is_anti_talk_prompt(motion: str) -> bool:
    low = (motion or "").lower()
    if not low:
        return False
    return any(p in low for p in ANTI_TALK_PHRASES)


def resolve_si2v_motion_prompt(
    shot: dict[str, Any] | None = None,
    *,
    performance: str | None = None,
    force_profile: bool = False,
) -> dict[str, Any]:
    """
    Pick SI2V motion_prompt + negative + audio_scale for a shot.

    Returns:
      performance, motion_prompt, negative_motion, audio_scale, source, overridden
    """
    shot = shot or {}
    pid = resolve_performance(shot, cli=performance)
    prof = get_profile(pid) or get_profile(DEFAULT_PERFORMANCE)
    assert prof is not None

    existing = (shot.get("motion_prompt") or "").strip()
    neg_existing = (shot.get("negative_motion") or "").strip()
    scale_shot = shot.get("audio_scale")
    try:
        scale_shot_f = float(scale_shot) if scale_shot is not None else None
    except (TypeError, ValueError):
        scale_shot_f = None

    speak = has_speak_markers(existing)
    anti = is_anti_talk_prompt(existing)

    # P0-2 fix: speak markers win — never full-replace a lip-aware prompt
    if force_profile or (not existing) or (anti and not speak):
        motion = str(prof["motion_prompt"])
        source = f"profile:{pid}"
        overridden = bool(existing)
    else:
        motion = existing
        source = "shot.motion_prompt"
        overridden = False

    neg = neg_existing or str(prof.get("negative_motion") or "")
    scale = scale_shot_f if scale_shot_f is not None else float(prof.get("audio_scale") or 1.25)

    return {
        "performance": pid,
        "motion_prompt": motion,
        "negative_motion": neg,
        "audio_scale": scale,
        "tts_instruct": str(prof.get("tts_instruct") or ""),
        "source": source,
        "overridden": overridden,
        "profile_label": prof.get("label"),
        "for_si2v": prof.get("for_si2v", True),
    }


def tts_instruct_for(
    performance: str | None,
    *,
    override: str | None = None,
) -> str:
    """CLI --instruct wins; else profile default."""
    if override and str(override).strip():
        return str(override).strip()
    prof = get_profile(performance)
    if not prof:
        prof = get_profile(DEFAULT_PERFORMANCE)
    return str((prof or {}).get("tts_instruct") or "")
