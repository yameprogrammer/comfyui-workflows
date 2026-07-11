"""Episode readiness report for agent commissions."""

from __future__ import annotations

import os
from typing import Any

from lib.story_package import StoryPackage


def _exists(story: StoryPackage, rel: str | None) -> bool:
    if not rel:
        return False
    path = story.path(*str(rel).replace("\\", "/").split("/"))
    return os.path.isfile(path)


def shot_status(story: StoryPackage, shot: dict) -> dict[str, Any]:
    sid = shot.get("shot_id")
    kf_rel = shot.get("keyframe") or f"keyframes/{sid}.png"
    work_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
    deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"

    kf_ok = _exists(story, kf_rel)
    work_ok = _exists(story, work_rel)
    deliver_ok = _exists(story, deliver_rel)
    kf_status = shot.get("keyframe_status") or ("draft" if kf_ok else "missing")

    blockers: list[str] = []
    if not kf_ok:
        blockers.append("keyframe_file")
    if kf_status != "approved":
        blockers.append(f"keyframe_status={kf_status}")
    if not work_ok:
        blockers.append("work_clip")
    # deliver optional until upscale
    next_action = "done"
    if not kf_ok:
        next_action = "shot_compose"
    elif kf_status != "approved":
        next_action = "shot_approve"
    elif not work_ok:
        next_action = "episode_i2v"
    elif not deliver_ok:
        next_action = "episode_upscale"
    else:
        next_action = "assemble_or_package"

    return {
        "shot_id": sid,
        "order": shot.get("order"),
        "keyframe_status": kf_status,
        "keyframe_file": kf_ok,
        "work_clip": work_ok,
        "deliver_clip": deliver_ok,
        "character_ids": shot.get("character_ids") or [],
        "location_id": shot.get("location_id"),
        "motion_prompt": bool((shot.get("motion_prompt") or "").strip()),
        "blockers": blockers,
        "next_action": next_action,
        "i2v_ready": kf_ok and kf_status == "approved",
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
    n_work = sum(1 for s in per if s["work_clip"])
    n_deliver = sum(1 for s in per if s["deliver_clip"])

    final_path = story.path("exports", "final", f"{episode_id}_final.mp4")
    fe = story.doc.get("final_export") or {}
    if fe.get("path"):
        alt = story.path(*str(fe["path"]).replace("\\", "/").split("/"))
        if os.path.isfile(alt):
            final_path = alt
    final_ok = os.path.isfile(final_path)

    last_delivery = story.doc.get("last_delivery")

    # overall next (progress as far as possible; draft shots still surface approve)
    if n == 0:
        overall = "add_shots"
    elif n_kf < n:
        overall = "shot_compose"
    elif n_approved < n:
        overall = "shot_approve"
    elif n_work < n_approved:
        overall = "episode_i2v"
    elif n_deliver < n_work:
        overall = "episode_upscale"
    elif not final_ok:
        overall = "assemble_video"
    elif not last_delivery:
        overall = "package_delivery"
    else:
        overall = "complete"

    return {
        "episode_id": episode_id,
        "format": story.format_id(),
        "look_id": story.look_id(),
        "shot_count": n,
        "counts": {
            "keyframes": n_kf,
            "approved": n_approved,
            "i2v_ready": n_i2v_ready,
            "work_clips": n_work,
            "deliver_clips": n_deliver,
        },
        "final_export": final_ok,
        "final_path": final_path if final_ok else None,
        "last_delivery": last_delivery,
        "overall_next": overall,
        "shots": per,
        "ready_for": {
            "episode_i2v": n_i2v_ready > 0,
            "episode_upscale": n_work > 0,
            "assemble_video": n_deliver > 0 or n_work > 0,
            "package_delivery": final_ok or n_work > 0 or n_kf > 0,
        },
    }


def format_status_text(report: dict[str, Any]) -> str:
    lines = [
        f"episode={report['episode_id']} format={report['format']} look={report['look_id']}",
        f"shots={report['shot_count']}  "
        f"kf={report['counts']['keyframes']}  "
        f"approved={report['counts']['approved']}  "
        f"i2v_ready={report['counts']['i2v_ready']}  "
        f"work={report['counts']['work_clips']}  "
        f"deliver={report['counts']['deliver_clips']}",
        f"final_export={'yes' if report['final_export'] else 'no'}  "
        f"last_delivery={report.get('last_delivery') or 'none'}",
        f"overall_next={report['overall_next']}",
        "",
        f"{'SHOT':<6} {'KF':<8} {'FILE':<5} {'WORK':<5} {'DELIV':<5} NEXT",
    ]
    for s in report["shots"]:
        lines.append(
            f"{str(s['shot_id']):<6} "
            f"{str(s['keyframe_status']):<8} "
            f"{'Y' if s['keyframe_file'] else 'N':<5} "
            f"{'Y' if s['work_clip'] else 'N':<5} "
            f"{'Y' if s['deliver_clip'] else 'N':<5} "
            f"{s['next_action']}"
        )
    return "\n".join(lines)
