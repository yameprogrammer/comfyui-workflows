"""One-take continuity helpers: last-frame keyframe from previous work clip.

Used by chain_one_take.py and shot_compose --from-prev-shot (P1-2).
Rule 7.2: previous clip_status must be approved unless force.
"""

from __future__ import annotations

import os
from typing import Any

from lib.episode_status import CLIP_STATUS_OK, normalize_clip_status
from lib.ffmpeg_util import run_ffmpeg
from lib.story_package import StoryPackage


def work_clip_path(story: StoryPackage, shot: dict, sid: str | None = None) -> str:
    sid = sid or str(shot.get("shot_id") or "")
    drv = (shot.get("motion_driver") or "i2v").lower()
    if drv in ("si2v", "s2v"):
        rel = shot.get("clip_work_s2v") or f"clips/work/{sid}_s2v.mp4"
    else:
        rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
    return story.path(*str(rel).replace("\\", "/").split("/"))


def extract_last_frame(video: str, png: str) -> dict[str, Any]:
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    r = run_ffmpeg(
        ["-y", "-sseof", "-0.08", "-i", video, "-frames:v", "1", "-q:v", "2", png],
        timeout_sec=120,
    )
    if r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 1000:
        return r
    return run_ffmpeg(
        [
            "-y",
            "-i",
            video,
            "-vf",
            "select=eq(n\\,N-1)",
            "-vsync",
            "vfr",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            png,
        ],
        timeout_sec=180,
    )


def fit_png(src: str, dst: str, w: int, h: int) -> None:
    from PIL import Image

    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    im.crop((left, top, left + w, top + h)).save(dst)


def previous_shot(story: StoryPackage, shot_id: str) -> dict | None:
    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    for i, s in enumerate(shots):
        if s.get("shot_id") == shot_id:
            return shots[i - 1] if i > 0 else None
    return None


def check_prev_clip_gate(
    story: StoryPackage,
    prev_shot: dict,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Return {ok, error?, message?, prev_clip, clip_status}."""
    prev_sid = str(prev_shot.get("shot_id") or "?")
    # always re-read status from package
    try:
        prev_shot = story.get_shot(prev_sid)
    except KeyError:
        pass
    prev_clip = work_clip_path(story, prev_shot, prev_sid)
    if not os.path.isfile(prev_clip):
        return {
            "ok": False,
            "error": "PREV_CLIP_MISSING",
            "message": f"previous work clip missing: {prev_clip}",
            "prev_clip": prev_clip,
            "prev_sid": prev_sid,
        }
    if force:
        return {
            "ok": True,
            "prev_clip": prev_clip,
            "prev_sid": prev_sid,
            "clip_status": prev_shot.get("clip_status"),
            "forced": True,
        }
    pst = normalize_clip_status(prev_shot, work_ok=True)
    if pst not in CLIP_STATUS_OK:
        return {
            "ok": False,
            "error": "CLIP_GATE",
            "message": (
                f"cannot chain from {prev_sid}: clip_status={pst!r}. "
                f"Approve first: python scripts/shot_approve.py -e {story.episode_id} "
                f"-s {prev_sid} --clip approved"
            ),
            "prev_clip": prev_clip,
            "prev_sid": prev_sid,
            "clip_status": pst,
            "exit_code": 22,
        }
    return {
        "ok": True,
        "prev_clip": prev_clip,
        "prev_sid": prev_sid,
        "clip_status": pst,
    }


def keyframe_from_prev_clip(
    story: StoryPackage,
    shot_id: str,
    *,
    width: int,
    height: int,
    force_clip_gate: bool = False,
    prev_shot_id: str | None = None,
) -> dict[str, Any]:
    """
    Write keyframes/<shot_id>.png from previous shot's last frame.

    Returns {ok, keyframe_path, prev_sid, prev_clip, error?, message?}
    """
    try:
        shot = story.get_shot(shot_id)
    except KeyError:
        return {"ok": False, "error": "SHOT_MISSING", "message": shot_id}

    if prev_shot_id:
        try:
            prev = story.get_shot(prev_shot_id)
        except KeyError:
            return {"ok": False, "error": "PREV_SHOT_MISSING", "message": prev_shot_id}
    else:
        prev = previous_shot(story, shot_id)
        if not prev:
            return {
                "ok": False,
                "error": "NO_PREV_SHOT",
                "message": f"{shot_id} is first shot — no previous clip",
            }

    gate = check_prev_clip_gate(story, prev, force=force_clip_gate)
    if not gate.get("ok"):
        return gate

    prev_clip = gate["prev_clip"]
    prev_sid = gate["prev_sid"]
    kf_rel = f"keyframes/{shot_id}.png"
    kf_path = story.path(*kf_rel.split("/"))
    tmp = kf_path + ".tmp.png"
    r = extract_last_frame(prev_clip, tmp)
    if not r.get("ok"):
        return {
            "ok": False,
            "error": "EXTRACT_FAILED",
            "message": str(r.get("message") or r),
            "prev_clip": prev_clip,
        }
    fit_png(tmp, kf_path, int(width), int(height))
    try:
        os.remove(tmp)
    except OSError:
        pass

    return {
        "ok": True,
        "keyframe_path": kf_path,
        "keyframe_rel": kf_rel,
        "prev_sid": prev_sid,
        "prev_clip": prev_clip,
        "clip_status": gate.get("clip_status"),
    }
