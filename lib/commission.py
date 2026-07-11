"""Commission brief → episode scaffold for agent video jobs."""

from __future__ import annotations

import json
import os
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso
from lib.audio_package import (
    MODE_DEFAULTS,
    ensure_audio_dirs,
    normalize_production_mode,
)
from lib.story_package import (
    StoryPackage,
    copy_template,
    load_json,
    package_dir,
    save_json,
    validate_episode_id,
)
from lib.video_backends import get_format, load_video_backends


def load_brief(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("brief must be a JSON object")
    return data


def validate_brief(brief: dict[str, Any]) -> list[str]:
    """Return list of error strings (empty = ok)."""
    errs: list[str] = []
    eid = str(brief.get("episode_id") or "").strip()
    if not eid or not validate_episode_id(eid):
        errs.append("episode_id must match ^[a-z][a-z0-9_]*$")
    fmt = brief.get("format")
    if not fmt:
        errs.append("format is required")
    else:
        try:
            get_format(str(fmt))
        except Exception as e:
            errs.append(f"format: {e}")
    shots = brief.get("shots")
    if not isinstance(shots, list) or not shots:
        errs.append("shots must be a non-empty array")
    else:
        seen = set()
        for i, s in enumerate(shots):
            if not isinstance(s, dict):
                errs.append(f"shots[{i}] must be object")
                continue
            sid = s.get("shot_id")
            if not sid:
                errs.append(f"shots[{i}].shot_id required")
            elif sid in seen:
                errs.append(f"duplicate shot_id {sid}")
            else:
                seen.add(sid)
            if not (s.get("action") or "").strip():
                errs.append(f"shots[{sid or i}].action required")
    look = brief.get("look_id") or "cinematic_moody_v1"
    look_path = os.path.join(WORKSPACE_ROOT, "looks", str(look))
    if not os.path.isdir(look_path):
        errs.append(f"look_id not found: {look}")
    return errs


def warn_assets(brief: dict[str, Any]) -> list[str]:
    """Non-fatal warnings (missing character/location packs)."""
    warns: list[str] = []
    chars = set(brief.get("characters") or [])
    locs = set(brief.get("locations") or [])
    for s in brief.get("shots") or []:
        for c in s.get("character_ids") or []:
            chars.add(c)
        if s.get("location_id"):
            locs.add(str(s["location_id"]))
    for c in sorted(chars):
        p = os.path.join(WORKSPACE_ROOT, "characters", c)
        if not os.path.isdir(p):
            warns.append(f"character pack missing: characters/{c}/")
    for loc in sorted(locs):
        p = os.path.join(WORKSPACE_ROOT, "locations", loc)
        if not os.path.isdir(p):
            warns.append(f"location pack missing: locations/{loc}/ (create later ok)")
    return warns


def build_shot_record(
    shot: dict[str, Any],
    *,
    index: int,
    default_chars: list[str],
) -> dict[str, Any]:
    sid = str(shot["shot_id"])
    order = int(shot.get("order") if shot.get("order") is not None else index + 1)
    char_ids = list(shot.get("character_ids") if shot.get("character_ids") is not None else default_chars)
    return {
        "shot_id": sid,
        "scene_id": shot.get("scene_id") or "SC01",
        "order": order,
        "duration_sec": float(shot.get("duration_sec") or 4),
        "shot_type": shot.get("shot_type") or "medium",
        "camera": shot.get("camera")
        or {"angle": "eye_level", "move": "static", "lens_feel": "35mm"},
        "action": str(shot.get("action") or "").strip(),
        "dialogue": shot.get("dialogue") or "",
        "vo": shot.get("vo") or "",
        "sfx": shot.get("sfx") or [],
        "music_cue": shot.get("music_cue") or "",
        "motion_driver": shot.get("motion_driver") or None,
        "audio_refs": shot.get("audio_refs") or {},
        "character_ids": char_ids,
        "character_refs": shot.get("character_refs") or {},
        "location_id": shot.get("location_id"),
        "location_ref": shot.get("location_ref"),
        "lighting": shot.get("lighting") or "",
        "appearance_prompt": "",
        "motion_prompt": shot.get("motion_prompt")
        or "gentle natural motion, cinematic camera",
        "negative_motion": shot.get("negative_motion")
        or "warp, identity morph, flicker, morphing face",
        "board_panel": f"boards/panels/{sid}.png",
        "keyframe": f"keyframes/{sid}.png",
        "keyframe_status": "missing",
        "clip_work": f"clips/work/{sid}.mp4",
        "clip_deliver": f"clips/deliver/{sid}.mp4",
        "seed": None,
        "continuity": shot.get("continuity") or {},
    }


def apply_commission(
    brief: dict[str, Any],
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    errs = validate_brief(brief)
    if errs:
        return {"ok": False, "errors": errs}

    episode_id = str(brief["episode_id"]).strip()
    format_id = str(brief["format"]).strip()
    look_id = str(brief.get("look_id") or "cinematic_moody_v1")
    default_chars = list(brief.get("characters") or [])
    warns = warn_assets(brief)

    cfg = load_video_backends()
    fmt = get_format(format_id, cfg)
    work_preset = fmt.get("default_work_preset")
    deliver_tier = (
        brief.get("default_deliver_tier")
        or fmt.get("default_deliver_tier")
        or cfg.get("default_deliver_tier")
        or "deliver_1080"
    )

    shots_out = [
        build_shot_record(s, index=i, default_chars=default_chars)
        for i, s in enumerate(brief["shots"])
    ]
    shots_out.sort(key=lambda s: s.get("order", 0))

    dest = package_dir(episode_id)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "episode_id": episode_id,
            "path": dest,
            "format": format_id,
            "look_id": look_id,
            "shot_count": len(shots_out),
            "warnings": warns,
        }

    if os.path.exists(dest) and not force:
        return {
            "ok": False,
            "errors": [f"episode exists: {dest} (use --force)"],
            "warnings": warns,
        }

    copy_template(episode_id, force=force)
    shots_doc = load_json(os.path.join(dest, "shots.json"))
    shots_doc["episode_id"] = episode_id
    shots_doc["format"] = format_id
    shots_doc["look_id"] = look_id
    shots_doc["default_work_preset"] = work_preset
    shots_doc["default_deliver_tier"] = deliver_tier
    shots_doc["default_backend_i2v"] = brief.get("default_backend_i2v") or "wan22"
    shots_doc["default_backend_s2v"] = brief.get("default_backend_s2v")
    shots_doc["default_model"] = brief.get("default_model") or "pro"
    prod_mode = normalize_production_mode(brief.get("production_mode") or "story")
    shots_doc["production_mode"] = prod_mode
    if brief.get("mix_policy"):
        shots_doc["mix_policy"] = brief.get("mix_policy")
    else:
        shots_doc["mix_policy"] = MODE_DEFAULTS[prod_mode]["mix_policy"]
    shots_doc["default_motion_driver"] = (
        brief.get("default_motion_driver")
        or MODE_DEFAULTS[prod_mode]["default_motion_driver"]
    )
    if brief.get("audio"):
        base_audio = dict(shots_doc.get("audio") or {})
        base_audio.update(brief["audio"])
        shots_doc["audio"] = base_audio
    shots_doc["commission"] = {
        "title": brief.get("title") or episode_id,
        "logline": brief.get("logline") or "",
        "characters": default_chars,
        "locations": list(brief.get("locations") or []),
        "production_mode": prod_mode,
        "created_at": utc_now_iso(),
    }
    shots_doc["shots"] = shots_out
    save_json(os.path.join(dest, "shots.json"), shots_doc)
    ensure_audio_dirs(dest)

    title = brief.get("title") or episode_id
    logline = brief.get("logline") or ""
    with open(os.path.join(dest, "bible.md"), "w", encoding="utf-8") as f:
        f.write(
            f"# {title}\n\n"
            f"- **episode_id**: {episode_id}\n"
            f"- **format**: {format_id}\n"
            f"- **look_id**: {look_id}\n"
            f"- **created**: {utc_now_iso()}\n\n"
            f"## Logline\n\n{logline}\n\n"
            f"## Commission assets\n\n"
            f"- characters: {', '.join(default_chars) or '(none)'}\n"
            f"- locations: {', '.join(brief.get('locations') or []) or '(none)'}\n"
        )

    beats_lines = ["# Beats (from commission shots)\n"]
    for s in shots_out:
        beats_lines.append(f"{s['order']}. **{s['shot_id']}** ({s.get('shot_type')}): {s['action']}\n")
    with open(os.path.join(dest, "beats.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(beats_lines))

    return {
        "ok": True,
        "episode_id": episode_id,
        "path": dest,
        "format": format_id,
        "look_id": look_id,
        "shot_count": len(shots_out),
        "warnings": warns,
        "next": [
            "python scripts/episode_status.py --episode " + episode_id,
            "python scripts/shot_compose.py --episode " + episode_id + " --shot S01 ...",
            "python scripts/episode_pipeline.py --episode " + episode_id,
        ],
    }
