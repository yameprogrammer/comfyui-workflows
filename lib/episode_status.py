"""Episode readiness report for agent commissions."""

from __future__ import annotations

import os
from typing import Any

from lib.audio_package import resolve_driving_audio, shot_motion_driver
from lib.story_package import StoryPackage


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
    deliver_ok = _exists(story, deliver_rel)
    kf_status = shot.get("keyframe_status") or ("draft" if kf_ok else "missing")

    driving_ok = True
    if driver == "si2v":
        driving_ok = resolve_driving_audio(story.root, shot) is not None

    lip_status = str(shot.get("lip_status") or "").strip().lower() or None
    if driver == "si2v" and work_ok and not lip_status:
        lip_status = "pending"
    lip_ok = lip_status in ("approved", "ok") if driver == "si2v" else True

    blockers: list[str] = []
    if not kf_ok:
        blockers.append("keyframe_file")
    if kf_status != "approved":
        blockers.append(f"keyframe_status={kf_status}")
    if driver == "si2v" and not driving_ok:
        blockers.append("si2v_driving_audio")
    if not work_ok:
        blockers.append("work_clip")
    if driver == "si2v" and work_ok and not lip_ok:
        blockers.append(f"lip_status={lip_status or 'pending'}")

    next_action = "done"
    if not kf_ok:
        next_action = "shot_compose"
    elif kf_status != "approved":
        next_action = "shot_approve"
    elif driver == "si2v" and not driving_ok:
        next_action = "audio_bind_driving"
    elif not work_ok:
        next_action = "episode_s2v" if driver == "si2v" else "episode_i2v"
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
        "lip_status": lip_status,
        "lip_visual_ok": lip_ok,
        "character_ids": shot.get("character_ids") or [],
        "location_id": shot.get("location_id"),
        "motion_prompt": bool((shot.get("motion_prompt") or "").strip()),
        "blockers": blockers,
        "next_action": next_action,
        "i2v_ready": kf_ok and kf_status == "approved" and driver in ("i2v",),
        "s2v_ready": (
            kf_ok and kf_status == "approved" and driver == "si2v" and driving_ok
        ),
        "upscale_ready": work_ok,
        "assemble_ready": deliver_ok or work_ok,
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
            "need_lip_approve": n_need_lip,
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
            "assemble_video": n_deliver > 0 or n_work > 0,
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
        f"deliver={report['counts']['deliver_clips']}",
        f"final_export={'yes' if report['final_export'] else 'no'}  "
        f"last_delivery={report.get('last_delivery') or 'none'}",
        f"overall_next={report['overall_next']}",
        "",
        f"{'SHOT':<6} {'DRV':<6} {'KF':<8} {'FILE':<5} {'WORK':<5} {'LIP':<8} NEXT",
    ]
    for s in report["shots"]:
        lip = s.get("lip_status") or ("-" if s.get("motion_driver") != "si2v" else "?")
        lines.append(
            f"{str(s['shot_id']):<6} "
            f"{str(s.get('motion_driver') or '?'):<6} "
            f"{str(s['keyframe_status']):<8} "
            f"{'Y' if s['keyframe_file'] else 'N':<5} "
            f"{'Y' if s['work_clip'] else 'N':<5} "
            f"{str(lip):<8} "
            f"{s['next_action']}"
        )
    return "\n".join(lines)
