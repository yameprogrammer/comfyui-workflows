#!/usr/bin/env python3
"""Batch V2V for episode shots with motion_driver=v2v_* or video_refs.driving.

  python scripts/episode_v2v.py -e EP --dry-run
  python scripts/episode_v2v.py -e EP --shots S03

See docs/v2v_intent_pipeline_design.md.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_v2v import generate_v2v
from lib.audio_package import shot_motion_driver
from lib.comfy_client import utc_now_iso, write_meta
from lib.story_package import StoryPackage, validate_episode_id
from lib.v2v_contract import V2V_DRIVERS, shot_v2v_plan
from lib.workspace_export import (
    CLIP_PARTS,
    add_export_workspace_args,
    export_flag_from_args,
    maybe_export_episode,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_NONE = 21
EXIT_PARTIAL = 31


def _select_shots(story: StoryPackage, shots_arg: str, require_approved: bool) -> list[dict]:
    all_shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if shots_arg in ("all", "all_approved", "*"):
        selected = all_shots
    else:
        want = {x.strip() for x in shots_arg.split(",") if x.strip()}
        selected = [s for s in all_shots if s.get("shot_id") in want]
        missing = want - {s.get("shot_id") for s in selected}
        if missing:
            raise KeyError(f"unknown shots: {sorted(missing)}")
    if require_approved or shots_arg == "all_approved":
        selected = [s for s in selected if s.get("keyframe_status") == "approved"]
    return selected


def _resolve_path(story: StoryPackage, rel_or_abs: str | None) -> str | None:
    if not rel_or_abs:
        return None
    if os.path.isfile(rel_or_abs):
        return os.path.abspath(rel_or_abs)
    cand = os.path.join(story.root, rel_or_abs)
    if os.path.isfile(cand):
        return cand
    return rel_or_abs


def _keyframe_path(story: StoryPackage, shot: dict, plan: dict) -> str | None:
    sid = shot.get("shot_id")
    for key in (
        plan.get("keyframe"),
        shot.get("keyframe"),
        shot.get("keyframe_path"),
        f"keyframes/approved/{sid}.png",
        f"keyframes/approved/{sid}.jpg",
    ):
        p = _resolve_path(story, key)
        if p and os.path.isfile(p):
            return p
    # StoryPackage helpers if present
    for attr in ("approved_keyframe_path", "keyframe_path"):
        fn = getattr(story, attr, None)
        if callable(fn):
            try:
                p = fn(sid)
                if p and os.path.isfile(p):
                    return p
            except Exception:
                pass
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run V2V for episode shots (v2v_camera|v2v_motion|v2v_style)"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--shots",
        default="all_approved",
        help="all_approved | all | S01,S02 (default all_approved)",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Include non-approved keyframes",
    )
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument(
        "--allow-dialogue",
        action="store_true",
        help="Allow V2V on shots that have dialogue/vo (default: skip)",
    )
    add_export_workspace_args(parser)
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    try:
        selected = _select_shots(story, args.shots, require_approved=not args.allow_draft)
    except KeyError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    # work size from format if possible
    w = args.width
    h = args.height
    if w is None or h is None:
        fmt = (story.doc or {}).get("format") or "shorts_9x16"
        if "9x16" in str(fmt) or "9:16" in str(fmt):
            w, h = w or 544, h or 960
        else:
            w, h = w or 960, h or 544

    run_list: list[tuple[dict, dict]] = []
    skipped: list[dict] = []
    for s in selected:
        plan = shot_v2v_plan(s)
        driver = shot_motion_driver(s, story.doc)
        if plan is None and driver not in V2V_DRIVERS:
            skipped.append({"shot_id": s.get("shot_id"), "reason": f"driver={driver}"})
            continue
        if plan is None:
            continue
        if not args.allow_dialogue:
            dlg = (s.get("dialogue") or s.get("vo") or "").strip()
            if dlg:
                skipped.append(
                    {
                        "shot_id": s.get("shot_id"),
                        "reason": "has_dialogue_use_si2v",
                    }
                )
                continue
        run_list.append((s, plan))

    if not run_list:
        print(
            f"[WARN] code=21 no v2v shots (selected={len(selected)} skipped={len(skipped)})"
        )
        return EXIT_NONE

    ok_n = 0
    fail_n = 0
    results = []
    work_dir = os.path.join(story.root, "clips", "work")
    os.makedirs(work_dir, exist_ok=True)

    for shot, plan in run_list:
        sid = shot.get("shot_id") or "Sxx"
        video = _resolve_path(story, plan.get("driving"))
        image = _keyframe_path(story, shot, plan)
        out = os.path.join(work_dir, f"{sid}_v2v.mp4")
        print(
            f"=== {sid} intent={plan.get('intent')} video={video} image={image} → {out}"
        )
        if not video or not os.path.isfile(video):
            print(f"[ERROR] {sid} VIDEO_MISSING {video}", file=sys.stderr)
            fail_n += 1
            results.append({"shot_id": sid, "ok": False, "error": "VIDEO_MISSING"})
            if args.stop_on_error:
                break
            continue
        if not image:
            print(f"[ERROR] {sid} KEYFRAME_MISSING", file=sys.stderr)
            fail_n += 1
            results.append({"shot_id": sid, "ok": False, "error": "KEYFRAME_MISSING"})
            if args.stop_on_error:
                break
            continue

        r = generate_v2v(
            video,
            image,
            out,
            intent=plan["intent"],
            strength=plan.get("strength"),
            width=int(w),
            height=int(h),
            fps=float(args.fps),
            duration_sec=(
                float(plan["trim_duration_sec"])
                if plan.get("trim_duration_sec") is not None
                else shot.get("duration_sec")
            ),
            trim_start_sec=float(plan.get("trim_start_sec") or 0.0),
            dry_run=args.dry_run,
            timeout_sec=args.timeout,
        )
        results.append({"shot_id": sid, **{k: r.get(k) for k in ("ok", "error", "output_path", "message")}})
        if r.get("ok"):
            ok_n += 1
        else:
            fail_n += 1
            print(f"[ERROR] {sid} {r.get('error')} {r.get('message')}", file=sys.stderr)
            if args.stop_on_error:
                break

    summary = {
        "ok": fail_n == 0 and ok_n > 0,
        "episode_id": args.episode,
        "tool": "episode_v2v",
        "ok_count": ok_n,
        "fail_count": fail_n,
        "skipped": skipped,
        "results": results,
        "dry_run": bool(args.dry_run),
        "created_at": utc_now_iso(),
    }
    meta_path = os.path.join(story.root, "meta", "episode_v2v_result.json")
    write_meta(meta_path, summary)
    print(f"summary ok={ok_n} fail={fail_n} skipped={len(skipped)} meta={meta_path}")

    if not args.dry_run and ok_n > 0:
        ex = maybe_export_episode(
            args.episode,
            export_flag=export_flag_from_args(args),
            dest=getattr(args, "export_dest", None),
            parts=list(CLIP_PARTS),
        )
        if not ex.get("skipped") and not ex.get("ok"):
            print(f"[WARN] export-workspace: {ex.get('error')}: {ex.get('message')}")

    if fail_n and ok_n:
        return EXIT_PARTIAL
    if fail_n and not ok_n:
        return 1
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
