"""Episode readiness report for agent commissions."""

from __future__ import annotations

import os
from typing import Any

from lib.audio_package import (
    probe_audio_duration,
    resolve_driving_audio,
    resolve_path,
    shot_motion_driver,
)
from lib.story_package import StoryPackage

CLIP_STATUS_VALUES = ("pending", "in_review", "approved", "rejected")
CLIP_STATUS_OK = frozenset({"approved", "ok"})

# Length health slacks (seconds)
_LENGTH_SHORT_SLACK = 0.35
_DRIVE_TTS_SLACK = 0.35


def _exists(story: StoryPackage, rel: str | None) -> bool:
    if not rel:
        return False
    path = story.path(*str(rel).replace("\\", "/").split("/"))
    return os.path.isfile(path)


def _work_rel_for_shot(shot: dict) -> str:
    sid = shot.get("shot_id")
    driver = shot.get("motion_driver")  # raw; full resolve needs doc
    if shot.get("clip_work_s2v"):
        return str(shot["clip_work_s2v"])
    if shot.get("clip_work"):
        return str(shot["clip_work"])
    if driver == "si2v":
        return f"clips/work/{sid}_s2v.mp4"
    return f"clips/work/{sid}.mp4"


def _rel_duration(story: StoryPackage, rel: str | None) -> float | None:
    if not rel:
        return None
    path = story.path(*str(rel).replace("\\", "/").split("/"))
    if not os.path.isfile(path):
        return None
    return probe_audio_duration(path)  # ffprobe format=duration works for video too


def _tts_path(story: StoryPackage, shot: dict) -> str | None:
    refs = shot.get("audio_refs") or {}
    if not isinstance(refs, dict):
        return None
    for key in ("tts", "dialogue"):
        raw = refs.get(key)
        if isinstance(raw, str):
            p = resolve_path(story.root, raw)
            if p:
                return p
        if isinstance(raw, dict):
            p = resolve_path(story.root, raw.get("path") or raw.get("file"))
            if p:
                return p
    return None


def _drive_path(story: StoryPackage, shot: dict) -> str | None:
    # Prefer materialized s2v_driving_audio, then audio_refs.driving
    rel = shot.get("s2v_driving_audio")
    if rel:
        p = resolve_path(story.root, str(rel))
        if p:
            return p
    ref = resolve_driving_audio(story.root, shot)
    return ref["path"] if ref else None


def length_health(
    story: StoryPackage,
    shot: dict,
    *,
    work_rel: str | None,
    work_ok: bool,
    driver: str,
) -> dict[str, Any]:
    """
    P1-1: per-shot duration health.

    Flags:
      SHORT — work clip shorter than drive/tts (dialogue cut risk)
      DRIVE_MISMATCH — prepared drive shorter than TTS stem
      DURATION_SHORT — declared duration_sec shorter than media (spill risk)
    """
    tts_sec = None
    drive_sec = None
    clip_sec = None
    tts_p = _tts_path(story, shot)
    if tts_p:
        tts_sec = probe_audio_duration(tts_p)
    if driver == "si2v":
        dp = _drive_path(story, shot)
        if dp:
            drive_sec = probe_audio_duration(dp)
    if work_ok and work_rel:
        clip_sec = _rel_duration(story, work_rel)

    try:
        duration_sec = float(shot["duration_sec"]) if shot.get("duration_sec") is not None else None
    except (TypeError, ValueError):
        duration_sec = None

    flags: list[str] = []
    # drive vs tts
    if drive_sec is not None and tts_sec is not None:
        if tts_sec - drive_sec > _DRIVE_TTS_SLACK:
            flags.append("DRIVE_MISMATCH")
    # clip vs longest audio source
    audio_need = None
    for v in (drive_sec, tts_sec):
        if v is not None:
            audio_need = v if audio_need is None else max(audio_need, v)
    if clip_sec is not None and audio_need is not None:
        if audio_need - clip_sec > _LENGTH_SHORT_SLACK:
            flags.append("SHORT")
    # declared shot duration vs audio (spill into next cut)
    if duration_sec is not None and audio_need is not None:
        if audio_need - duration_sec > _LENGTH_SHORT_SLACK:
            flags.append("DURATION_SHORT")

    # optional frames estimate @24
    frames = None
    if clip_sec is not None:
        frames = int(round(clip_sec * 24.0))

    return {
        "tts_sec": round(tts_sec, 3) if tts_sec is not None else None,
        "drive_sec": round(drive_sec, 3) if drive_sec is not None else None,
        "clip_sec": round(clip_sec, 3) if clip_sec is not None else None,
        "duration_sec": round(duration_sec, 3) if duration_sec is not None else None,
        "frames_est_24": frames,
        "flags": flags,
        "length_ok": len(flags) == 0,
    }


def normalize_clip_status(shot: dict, *, work_ok: bool) -> str | None:
    """Human gate for work clip quality. Missing + work file ⇒ pending."""
    raw = str(shot.get("clip_status") or "").strip().lower() or None
    if work_ok and not raw:
        return "pending"
    return raw


def clip_visual_ok(shot: dict, *, work_ok: bool) -> bool:
    if not work_ok:
        return False
    return normalize_clip_status(shot, work_ok=work_ok) in CLIP_STATUS_OK


def check_clip_approve_blockers(
    shots: list[dict],
    *,
    work_ok_by_id: dict[str, bool] | None = None,
) -> list[dict[str, Any]]:
    """Return [{shot_id, clip_status, reason}] for shots that need clip approve.

    If work_ok_by_id is provided, only those with work_ok True are checked.
    If None, infer work from clip_status pending convention via work file flags
    already embedded: pass work_ok_by_id from caller for accuracy.
    """
    blockers: list[dict[str, Any]] = []
    for shot in shots:
        sid = str(shot.get("shot_id") or "?")
        if work_ok_by_id is not None:
            work_ok = bool(work_ok_by_id.get(sid))
        else:
            # Without path checks: treat explicit statuses only; skip unknown
            work_ok = bool(shot.get("_work_ok")) or bool(
                shot.get("clip_work") or shot.get("clip_work_s2v")
            )
            # Prefer explicit work_ok if status helper already set
            if "work_clip" in shot and isinstance(shot.get("work_clip"), bool):
                work_ok = bool(shot["work_clip"])
        if not work_ok:
            continue
        st = normalize_clip_status(shot, work_ok=True)
        if st not in CLIP_STATUS_OK:
            blockers.append(
                {
                    "shot_id": sid,
                    "clip_status": st or "pending",
                    "reason": (
                        f"clip_status={st or 'pending'!r} — watch work clip then: "
                        f"shot_approve -e EP -s {sid} --clip approved"
                    ),
                }
            )
    return blockers


def shot_status(story: StoryPackage, shot: dict) -> dict[str, Any]:
    sid = shot.get("shot_id")
    driver = shot_motion_driver(shot, story.doc)
    kf_rel = shot.get("keyframe") or f"keyframes/{sid}.png"
    work_rel = _work_rel_for_shot(shot)
    # si2v: also accept either _s2v or legacy clip_work path
    deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"

    kf_ok = _exists(story, kf_rel)
    work_ok = _exists(story, work_rel)
    if not work_ok and driver == "si2v":
        # fall back: clip_work or clips/work/Sxx.mp4
        for alt in (
            shot.get("clip_work"),
            f"clips/work/{sid}.mp4",
            f"clips/work/{sid}_s2v.mp4",
        ):
            if alt and _exists(story, str(alt)):
                work_ok = True
                work_rel = str(alt)
                break
    if not work_ok and driver != "si2v":
        for alt in (
            shot.get("clip_work_s2v"),
            f"clips/work/{sid}_s2v.mp4",
        ):
            if alt and _exists(story, str(alt)):
                work_ok = True
                work_rel = str(alt)
                break
    deliver_ok = _exists(story, deliver_rel)
    kf_status = shot.get("keyframe_status") or ("draft" if kf_ok else "missing")

    driving_ok = True
    if driver == "si2v":
        driving_ok = resolve_driving_audio(story.root, shot) is not None

    lip_status = str(shot.get("lip_status") or "").strip().lower() or None
    if driver == "si2v" and work_ok and not lip_status:
        lip_status = "pending"
    lip_ok = lip_status in ("approved", "ok") if driver == "si2v" else True

    clip_status = normalize_clip_status(shot, work_ok=work_ok)
    clip_ok = clip_visual_ok(shot, work_ok=work_ok)

    # P1-1 length health (tts / drive / clip)
    lh = length_health(
        story,
        shot,
        work_rel=work_rel,
        work_ok=work_ok,
        driver=driver,
    )

    blockers: list[str] = []
    if not kf_ok:
        blockers.append("keyframe_file")
    if kf_status != "approved":
        blockers.append(f"keyframe_status={kf_status}")
    if driver == "si2v" and not driving_ok:
        blockers.append("si2v_driving_audio")
    if not work_ok:
        blockers.append("work_clip")
    if work_ok and not clip_ok:
        blockers.append(f"clip_status={clip_status or 'pending'}")
    if driver == "si2v" and work_ok and not lip_ok:
        blockers.append(f"lip_status={lip_status or 'pending'}")
    for fl in lh.get("flags") or []:
        blockers.append(f"length:{fl}")

    next_action = "done"
    if not kf_ok:
        next_action = "shot_compose"
    elif kf_status != "approved":
        next_action = "shot_approve"
    elif driver == "si2v" and not driving_ok:
        next_action = "audio_bind_driving"
    elif not work_ok:
        next_action = "episode_s2v" if driver == "si2v" else "episode_i2v"
    elif "DRIVE_MISMATCH" in (lh.get("flags") or []):
        next_action = "fix_driving_length"
    elif "SHORT" in (lh.get("flags") or []):
        next_action = "regen_s2v_longer"
    elif work_ok and not clip_ok:
        next_action = "shot_approve_clip"
    elif driver == "si2v" and work_ok and not lip_ok:
        next_action = "shot_approve_lip"
    elif work_ok:
        # work-res ship is valid; upscale is optional deliver tier
        next_action = "assemble_or_package" if not deliver_ok else "done"
    else:
        next_action = "assemble_or_package"

    return {
        "shot_id": sid,
        "order": shot.get("order"),
        "motion_driver": driver,
        "keyframe_status": kf_status,
        "keyframe_file": kf_ok,
        "work_clip": work_ok,
        "work_rel": work_rel,
        "deliver_clip": deliver_ok,
        "driving_audio": driving_ok,
        "clip_status": clip_status,
        "clip_visual_ok": clip_ok,
        "lip_status": lip_status,
        "lip_visual_ok": lip_ok,
        "character_ids": shot.get("character_ids") or [],
        "location_id": shot.get("location_id"),
        "motion_prompt": bool((shot.get("motion_prompt") or "").strip()),
        "performance": shot.get("performance") or shot.get("s2v_performance"),
        "length": lh,
        "tts_sec": lh.get("tts_sec"),
        "drive_sec": lh.get("drive_sec"),
        "clip_sec": lh.get("clip_sec"),
        "length_flags": list(lh.get("flags") or []),
        "blockers": blockers,
        "next_action": next_action,
        "i2v_ready": kf_ok and kf_status == "approved" and driver in ("i2v",),
        "s2v_ready": (
            kf_ok
            and kf_status == "approved"
            and driver == "si2v"
            and driving_ok
            and "DRIVE_MISMATCH" not in (lh.get("flags") or [])
        ),
        "upscale_ready": work_ok,
        "assemble_ready": (deliver_ok or work_ok) and clip_ok and lh.get("length_ok", True),
    }


def episode_status_report(episode_id: str) -> dict[str, Any]:
    story = StoryPackage.load(episode_id)
    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    per = [shot_status(story, s) for s in shots]

    n = len(per)
    n_kf = sum(1 for s in per if s["keyframe_file"])
    n_approved = sum(1 for s in per if s["keyframe_status"] == "approved")
    n_i2v_ready = sum(1 for s in per if s["i2v_ready"])
    n_s2v_ready = sum(1 for s in per if s["s2v_ready"])
    n_work = sum(1 for s in per if s["work_clip"])
    n_deliver = sum(1 for s in per if s["deliver_clip"])
    n_need_motion = sum(
        1
        for s in per
        if s["keyframe_status"] == "approved" and not s["work_clip"]
    )
    n_need_s2v = sum(
        1
        for s in per
        if s["keyframe_status"] == "approved"
        and s["motion_driver"] == "si2v"
        and not s["work_clip"]
    )
    n_need_i2v = sum(
        1
        for s in per
        if s["keyframe_status"] == "approved"
        and s["motion_driver"] != "si2v"
        and not s["work_clip"]
    )
    n_need_driving = sum(
        1
        for s in per
        if s["motion_driver"] == "si2v" and not s["driving_audio"]
    )
    n_need_lip = sum(
        1
        for s in per
        if s["motion_driver"] == "si2v"
        and s.get("work_clip")
        and not s.get("lip_visual_ok")
    )
    n_need_clip = sum(
        1 for s in per if s.get("work_clip") and not s.get("clip_visual_ok")
    )
    n_clip_approved = sum(1 for s in per if s.get("clip_visual_ok"))
    n_length_warn = sum(1 for s in per if s.get("length_flags"))
    n_short = sum(1 for s in per if "SHORT" in (s.get("length_flags") or []))
    n_drive_mismatch = sum(
        1 for s in per if "DRIVE_MISMATCH" in (s.get("length_flags") or [])
    )

    final_path = story.path("exports", "final", f"{episode_id}_final.mp4")
    # also accept smoke naming
    for name in (
        f"{episode_id}_av_final.mp4",
        f"{episode_id}_work_final.mp4",
        f"{episode_id}_final.mp4",
    ):
        cand = story.path("exports", "final", name)
        if os.path.isfile(cand):
            final_path = cand
            break
    fe = story.doc.get("final_export") or {}
    if fe.get("path"):
        alt = story.path(*str(fe["path"]).replace("\\", "/").split("/"))
        if os.path.isfile(alt):
            final_path = alt
    final_ok = os.path.isfile(final_path)

    last_delivery = story.doc.get("last_delivery")

    if n == 0:
        overall = "add_shots"
    elif n_kf < n:
        overall = "shot_compose"
    elif n_approved < n:
        overall = "shot_approve"
    elif n_need_driving > 0:
        overall = "audio_bind_driving"
    elif n_need_s2v > 0:
        overall = "episode_s2v"
    elif n_need_i2v > 0:
        overall = "episode_i2v"
    elif n_need_motion > 0:
        overall = "episode_i2v"
    elif n_drive_mismatch > 0:
        overall = "fix_driving_length"
    elif n_short > 0:
        overall = "regen_s2v_longer"
    elif n_need_clip > 0:
        overall = "shot_approve_clip"
    elif n_need_lip > 0:
        overall = "shot_approve_lip"
    elif n_deliver < n_work and n_work > 0:
        # upscale optional for agent work-path ship; prefer assemble if no deliver
        overall = "assemble_video"
    elif not final_ok:
        overall = "assemble_video"
    elif not last_delivery:
        overall = "package_delivery"
    else:
        overall = "complete"

    look_id = story.look_id()
    look_ok = True
    look_missing: list[str] = []
    try:
        from lib.look_package import look_readiness

        lr = look_readiness(look_id)
        look_ok = bool(lr.get("ok"))
        look_missing = list(lr.get("missing") or [])
    except Exception as e:
        look_ok = False
        look_missing = [str(e)]

    return {
        "episode_id": episode_id,
        "format": story.format_id(),
        "look_id": look_id,
        "look_ok": look_ok,
        "look_missing": look_missing,
        "production_mode": story.doc.get("production_mode"),
        "default_backend_s2v": story.doc.get("default_backend_s2v"),
        "shot_count": n,
        "counts": {
            "keyframes": n_kf,
            "approved": n_approved,
            "i2v_ready": n_i2v_ready,
            "s2v_ready": n_s2v_ready,
            "work_clips": n_work,
            "deliver_clips": n_deliver,
            "need_s2v": n_need_s2v,
            "need_i2v": n_need_i2v,
            "need_driving": n_need_driving,
            "need_clip_approve": n_need_clip,
            "clip_approved": n_clip_approved,
            "need_lip_approve": n_need_lip,
            "length_warn": n_length_warn,
            "length_short": n_short,
            "drive_mismatch": n_drive_mismatch,
        },
        "final_export": final_ok,
        "final_path": final_path if final_ok else None,
        "last_delivery": last_delivery,
        "overall_next": overall,
        "shots": per,
        "ready_for": {
            "episode_i2v": n_i2v_ready > 0,
            "episode_s2v": n_s2v_ready > 0,
            "episode_upscale": n_work > 0,
            "assemble_video": n_need_clip == 0 and (n_deliver > 0 or n_work > 0),
            "package_delivery": final_ok or n_work > 0 or n_kf > 0,
        },
    }


def format_status_text(report: dict[str, Any]) -> str:
    look_flag = "ok" if report.get("look_ok", True) else f"BAD:{report.get('look_missing')}"
    lines = [
        f"episode={report['episode_id']} format={report['format']} "
        f"look={report['look_id']} ({look_flag})",
        f"production_mode={report.get('production_mode') or '?'}  "
        f"default_backend_s2v={report.get('default_backend_s2v') or '?'}",
        f"shots={report['shot_count']}  "
        f"kf={report['counts']['keyframes']}  "
        f"approved={report['counts']['approved']}  "
        f"i2v_ready={report['counts']['i2v_ready']}  "
        f"s2v_ready={report['counts'].get('s2v_ready', 0)}  "
        f"work={report['counts']['work_clips']}  "
        f"clip_ok={report['counts'].get('clip_approved', 0)}  "
        f"need_clip={report['counts'].get('need_clip_approve', 0)}  "
        f"deliver={report['counts']['deliver_clips']}  "
        f"len_warn={report['counts'].get('length_warn', 0)} "
        f"(short={report['counts'].get('length_short', 0)} "
        f"drive={report['counts'].get('drive_mismatch', 0)})",
        f"final_export={'yes' if report['final_export'] else 'no'}  "
        f"last_delivery={report.get('last_delivery') or 'none'}",
        f"overall_next={report['overall_next']}",
        "",
        f"{'SHOT':<6} {'DRV':<6} {'TTS':>6} {'DRIVE':>6} {'CLIP':>6} {'FLAGS':<16} {'WORK':<5} NEXT",
    ]
    for s in report["shots"]:
        def _f(v):
            if isinstance(v, (int, float)):
                return f"{v:6.2f}"
            return f"{'—':>6}"

        flags = ",".join(s.get("length_flags") or []) or "-"
        lines.append(
            f"{str(s['shot_id']):<6} "
            f"{str(s.get('motion_driver') or '?'):<6} "
            f"{_f(s.get('tts_sec'))} "
            f"{_f(s.get('drive_sec'))} "
            f"{_f(s.get('clip_sec'))} "
            f"{flags:<16} "
            f"{'Y' if s['work_clip'] else 'N':<5} "
            f"{s['next_action']}"
        )
    return "\n".join(lines)
