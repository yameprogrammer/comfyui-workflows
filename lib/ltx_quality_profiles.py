"""
LTX 2.3 quality tiers for agents (draft / work / hero).

SSOT values may live in video_backends.json → ltx_quality_profiles;
this module provides defaults + apply helpers.

Research: docs/ltx23_quality_research_and_improvement.md
"""

from __future__ import annotations

from typing import Any

# Fallback if video_backends.json missing the block
# LoRA / face knobs (AIO Power Lora node 211) — community 4090 balance after Q6+720p+2-stage.
# distill 0.6–0.8 sweet; detailer for face; upscale IC mild for stage2 (not max).
_DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "draft": {
        "summary": "빠른 탐색 · ~540 work · 짧은 클립",
        "longer_edge": 960,
        "work_preset_16x9": "work_16x9_540",
        "work_preset_9x16": "work_9x16_540",
        "fps": 24,
        "face_stability": True,
        "detailer_on": True,
        "detailer_strength": 0.5,
        "distill_strength": 0.75,
        "upscale_ic_on": True,
        "upscale_ic_strength": 0.4,
        "omni_strength": 0.4,
        "max_pure_i2v_sec": 3.0,
        "prefer_speed": True,
        "notes": "scout/fast only; not default",
    },
    "work": {
        "summary": "에이전트 실무 기본 = 720p + 품질 LoRA 튜닝",
        "longer_edge": 1280,
        "work_preset_16x9": "work_16x9_720",
        "work_preset_9x16": "work_9x16_720",
        "fps": 24,
        "face_stability": True,
        "detailer_on": True,
        "detailer_strength": 0.55,
        "distill_strength": 0.7,
        "upscale_ic_on": True,
        "upscale_ic_strength": 0.45,
        "omni_strength": 0.45,
        "max_pure_i2v_sec": 5.0,
        "prefer_speed": False,
        "notes": "DEFAULT: Q6+720p+2-stage; distill 0.7 · detailer 0.55 · upscale IC 0.45",
    },
    "hero": {
        "summary": "히어로 ~1080 work · 강한 detailer",
        "longer_edge": 1920,
        "work_preset_16x9": "work_16x9_1080",
        "work_preset_9x16": "work_9x16_720",
        "fps": 24,
        "face_stability": True,
        "detailer_on": True,
        "detailer_strength": 0.62,
        "distill_strength": 0.65,
        "upscale_ic_on": True,
        "upscale_ic_strength": 0.5,
        "omni_strength": 0.5,
        "max_pure_i2v_sec": 4.0,
        "prefer_speed": False,
        "notes": "Higher res + stronger face/detail; short clips",
    },
}

PROFILE_IDS = tuple(_DEFAULT_PROFILES.keys())
DEFAULT_PROFILE_ID = "work"


def _load_from_video_backends() -> dict[str, Any] | None:
    try:
        from lib.video_backends import load_video_backends

        block = load_video_backends().get("ltx_quality_profiles")
        if isinstance(block, dict) and block.get("profiles"):
            return block
    except Exception:
        pass
    return None


def list_ltx_quality_profile_ids() -> list[str]:
    block = _load_from_video_backends()
    if block:
        return sorted((block.get("profiles") or {}).keys())
    return list(PROFILE_IDS)


def get_default_ltx_quality_profile_id() -> str:
    block = _load_from_video_backends()
    if block and block.get("default"):
        return str(block["default"]).strip() or DEFAULT_PROFILE_ID
    return DEFAULT_PROFILE_ID


def resolve_ltx_quality_profile(
    name: str | None = None,
    *,
    default: str | None = None,
) -> dict[str, Any]:
    """
    Resolve profile dict. name=None → default (work).
    Unknown name → ValueError.
    """
    block = _load_from_video_backends()
    profiles = dict(_DEFAULT_PROFILES)
    if block and isinstance(block.get("profiles"), dict):
        for k, v in block["profiles"].items():
            base = dict(profiles.get(k) or {})
            base.update(v if isinstance(v, dict) else {})
            profiles[str(k)] = base

    key = (name or default or get_default_ltx_quality_profile_id() or DEFAULT_PROFILE_ID)
    key = str(key).strip().lower() or DEFAULT_PROFILE_ID
    aliases = {
        "preview": "draft",
        "fast": "draft",
        "default": "work",
        "deliver": "work",
        "batch": "work",
        "quality": "hero",
        "max": "hero",
        "showcase": "hero",
    }
    key = aliases.get(key, key)
    if key not in profiles:
        known = ", ".join(sorted(profiles.keys()))
        raise ValueError(f"unknown LTX quality profile {name!r}; known: {known}")
    out = dict(profiles[key])
    out["id"] = key
    return out


def size_from_ltx_profile(
    profile: dict[str, Any],
    *,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """
    Pick width/height/longer_edge for a profile.
    Explicit width+height win; else work preset by aspect/format; hero bumps longer_edge.
    """
    from lib.video_backends import get_format, load_video_backends, resolve_i2v_job

    prof = profile
    edge_target = int(prof.get("longer_edge") or 960)

    # Explicit size
    if width is not None and height is not None and int(width) > 0 and int(height) > 0:
        w, h = int(width), int(height)
        return {
            "width": w,
            "height": h,
            "longer_edge": max(w, h),
            "source": "explicit",
            "profile_id": prof.get("id"),
        }

    # Aspect from format
    resolved_aspect = aspect
    fid = format_id
    if not resolved_aspect and format_id:
        try:
            fmt = get_format(format_id)
            resolved_aspect = str(fmt.get("aspect") or "16:9")
        except Exception:
            resolved_aspect = "16:9"
    if not resolved_aspect:
        try:
            vcfg = load_video_backends()
            fid = str(vcfg.get("default_format") or "cinematic_16x9")
            fmt = get_format(fid)
            resolved_aspect = str(fmt.get("aspect") or "16:9")
        except Exception:
            resolved_aspect = "16:9"
            fid = "cinematic_16x9"

    # Work preset key
    is_portrait = False
    if resolved_aspect:
        try:
            a, b = resolved_aspect.replace("x", ":").split(":")
            is_portrait = int(b) > int(a)
        except Exception:
            is_portrait = "9:16" in resolved_aspect or "3:4" in resolved_aspect

    preset = (
        prof.get("work_preset_9x16") if is_portrait else prof.get("work_preset_16x9")
    ) or "work_16x9_540"

    try:
        job = resolve_i2v_job(
            backend="wan22",
            format_id=fid,
            preset=str(preset),
            width=None,
            height=None,
        )
        w, h = int(job["width"]), int(job["height"])
    except Exception:
        if is_portrait:
            w, h = 544, 960
        else:
            w, h = 960, 544

    # Scale so longer edge matches profile target (hero 1280 etc.)
    cur_long = max(w, h)
    if cur_long > 0 and edge_target > 0 and abs(cur_long - edge_target) > 32:
        scale = edge_target / float(cur_long)
        w = max(64, int(round(w * scale / 32.0) * 32))
        h = max(64, int(round(h * scale / 32.0) * 32))
        # re-snap longer edge
        if max(w, h) != edge_target:
            if w >= h:
                w = int(round(edge_target / 32.0) * 32)
                h = max(64, int(round(w * (h / max(w, 1)) / 32.0) * 32))
            else:
                h = int(round(edge_target / 32.0) * 32)
                w = max(64, int(round(h * (w / max(h, 1)) / 32.0) * 32))

    return {
        "width": w,
        "height": h,
        "longer_edge": max(w, h),
        "source": f"profile:{prof.get('id')}:{preset}",
        "profile_id": prof.get("id"),
        "format_id": fid,
        "aspect": resolved_aspect,
        "work_preset": preset,
    }


def apply_ltx_quality_profile(
    *,
    profile_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    face_stability: bool | None = None,
    detailer_strength: float | None = None,
    fps: float | None = None,
    num_frames: int | None = None,
    has_audio: bool = False,
    user_explicit_size: bool = False,
) -> dict[str, Any]:
    """
    Merge profile into run knobs. Does not run Comfy.

    user_explicit_size=True → keep width/height; only face/detailer/fps/cap hints.
    """
    prof = resolve_ltx_quality_profile(profile_name)
    out: dict[str, Any] = {
        "profile_id": prof["id"],
        "profile": prof,
        "warnings": [],
    }

    if user_explicit_size and width and height:
        out["width"] = int(width)
        out["height"] = int(height)
        out["longer_edge"] = max(int(width), int(height))
        out["size_source"] = "explicit"
    else:
        size = size_from_ltx_profile(
            prof,
            format_id=format_id,
            aspect=aspect,
            width=width if user_explicit_size else None,
            height=height if user_explicit_size else None,
        )
        # If caller passed non-default size without flag, still prefer explicit numbers
        if width and height and (int(width), int(height)) != (640, 640):
            out["width"] = int(width)
            out["height"] = int(height)
            out["longer_edge"] = max(int(width), int(height))
            out["size_source"] = "caller"
            # hero: if caller size is smaller than profile edge, warn
            if prof["id"] == "hero" and out["longer_edge"] < int(prof.get("longer_edge") or 1280) * 0.9:
                out["warnings"].append(
                    f"hero profile expects longer_edge~{prof.get('longer_edge')}; "
                    f"caller size {width}x{height} is smaller — pass no size or use work_16x9_720"
                )
        else:
            out["width"] = size["width"]
            out["height"] = size["height"]
            out["longer_edge"] = size["longer_edge"]
            out["size_source"] = size.get("source")
            out["work_preset"] = size.get("work_preset")

    # Face defaults from profile when unset
    if face_stability is None:
        out["face_stability"] = bool(prof.get("face_stability", True))
    else:
        out["face_stability"] = face_stability

    if detailer_strength is None:
        out["detailer_strength"] = float(prof.get("detailer_strength") or 0.55)
    else:
        out["detailer_strength"] = float(detailer_strength)

    if fps is None or float(fps) <= 0 or abs(float(fps) - 16.0) < 0.01:
        out["fps"] = float(prof.get("fps") or 24)
    else:
        out["fps"] = float(fps)

    # Pure I2V duration cap (soft): suggest frames if over max and no audio
    max_sec = prof.get("max_pure_i2v_sec")
    out["max_pure_i2v_sec"] = max_sec
    out["num_frames"] = num_frames
    if (
        not has_audio
        and max_sec
        and num_frames is not None
        and out["fps"] > 0
    ):
        sec = float(num_frames) / float(out["fps"])
        if sec > float(max_sec) + 0.25:
            out["warnings"].append(
                f"pure I2V ~{sec:.1f}s exceeds {prof['id']} max_pure_i2v_sec={max_sec} "
                f"(face drift risk). Prefer shorter clip or split shots."
            )
            # Soft cap frames for draft/hero defaults when clearly over
            if prof["id"] in ("draft", "hero", "work"):
                import math

                capped = int(math.floor(float(max_sec) * float(out["fps"])))
                # LTX frames often 8k+1 style; leave exact snap to caller
                out["num_frames_capped"] = max(17, capped)
                out["warnings"].append(
                    f"suggested frames ≤ {out['num_frames_capped']} "
                    f"(~{max_sec}s @ {out['fps']}fps); pass --frames to force longer"
                )

    out["summary"] = prof.get("summary")
    out["notes"] = prof.get("notes")
    return out


def format_ltx_profiles_table() -> str:
    lines = [
        f"{'id':8s} {'edge':5s} {'face':5s} {'det':5s} {'maxI2V':6s}  summary",
        "-" * 72,
    ]
    for pid in list_ltx_quality_profile_ids():
        p = resolve_ltx_quality_profile(pid)
        lines.append(
            f"{pid:8s} {str(p.get('longer_edge')):5s} "
            f"{'on' if p.get('face_stability') else 'off':5s} "
            f"{str(p.get('detailer_strength')):5s} "
            f"{str(p.get('max_pure_i2v_sec')):6s}  {p.get('summary') or ''}"
        )
    lines.append("")
    lines.append("CLI: python scripts/generate_i2v.py ... --ltx-profile work|hero|draft")
    lines.append("Docs: docs/ltx23_quality_research_and_improvement.md")
    return "\n".join(lines)
