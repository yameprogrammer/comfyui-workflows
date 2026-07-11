#!/usr/bin/env python3
"""Batch I2V for approved episode keyframes → clips/work/."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_i2v import generate_i2v
from lib.comfy_client import utc_now_iso, write_meta
from lib.story_package import StoryPackage, validate_episode_id

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


def _frames_for_shot(duration_sec: float, fps: float) -> int:
    n = max(9, int(round(float(duration_sec) * float(fps))))
    # prefer odd counts common in video diffusion
    if n % 2 == 0:
        n += 1
    return n


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run I2V for episode keyframes (approved by default)"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--shots",
        default="all_approved",
        help="all_approved | all | S01,S02,... (default all_approved)",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Include non-approved keyframes when selecting by id/all",
    )
    parser.add_argument("--backend", default=None, help="I2V backend (default episode/wan22)")
    parser.add_argument("--fps", type=float, default=None, help="I2V frame rate (default 16)")
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort on first failed shot (default: continue)",
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    require_approved = not args.allow_draft
    if args.shots == "all" and not args.allow_draft:
        # 'all' still filters to approved unless --allow-draft
        require_approved = True

    try:
        selected = _select_shots(story, args.shots, require_approved=require_approved)
    except KeyError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    if not selected:
        print(
            "[ERROR] code=21 no shots to run "
            "(need keyframe_status=approved, or pass --allow-draft / explicit ids)",
            file=sys.stderr,
        )
        return EXIT_NONE

    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    backend = args.backend or story.doc.get("default_backend_i2v") or "wan22"
    fps = float(args.fps if args.fps is not None else 16)

    print(
        f"episode_i2v episode={args.episode} format={format_id} "
        f"backend={backend} shots={len(selected)} fps={fps}"
    )

    ok = 0
    fail = 0
    for shot in selected:
        sid = shot.get("shot_id")
        kf_rel = shot.get("keyframe") or f"keyframes/{sid}.png"
        kf_path = story.path(*kf_rel.replace("\\", "/").split("/"))
        clip_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
        clip_path = story.path(*clip_rel.replace("\\", "/").split("/"))
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        motion = (shot.get("motion_prompt") or "").strip() or "gentle natural motion"
        neg = (shot.get("negative_motion") or "").strip()
        duration = float(shot.get("duration_sec") or 4)
        frames = _frames_for_shot(duration, fps)
        meta_path = story.path("meta", f"{sid}_i2v.json")

        print(f"\n=== {sid} status={shot.get('keyframe_status')} frames={frames} ===")
        print(f"  keyframe={kf_path}")
        print(f"  out={clip_path}")
        print(f"  motion={motion[:100]}")

        if not os.path.isfile(kf_path):
            print(f"  FAIL keyframe file missing")
            fail += 1
            if args.stop_on_error:
                break
            continue

        if args.dry_run:
            print("  [dry-run] skip generate_i2v")
            ok += 1
            continue

        result = generate_i2v(
            input_image_path=kf_path,
            prompt_text=motion,
            negative_text=neg or "",
            output_filename=clip_path,
            num_frames=frames,
            frame_rate=int(fps) if fps == int(fps) else 16,
            steps=args.steps,
            cfg=args.cfg,
            backend=backend,
            format_id=format_id,
            preset=work_preset,
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )

        if result.get("ok"):
            ok += 1
            story.update_shot(
                sid,
                clip_work=clip_rel.replace("\\", "/"),
                i2v_status="ok",
                i2v_at=utc_now_iso(),
                i2v_backend=backend,
                i2v_frames=frames,
            )
            print(f"  OK {clip_path}")
        else:
            fail += 1
            story.update_shot(
                sid,
                i2v_status="failed",
                i2v_error=result.get("error"),
                i2v_at=utc_now_iso(),
            )
            print(f"  FAIL {result.get('error')} {result.get('message')}")
            if args.stop_on_error:
                break

    print(f"\nDone ok={ok} fail={fail} total={len(selected)}")
    if ok == 0:
        return EXIT_PARTIAL if fail else EXIT_NONE
    if fail:
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
