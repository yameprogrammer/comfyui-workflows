#!/usr/bin/env python3
"""Batch upscale episode work clips → clips/deliver/."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import utc_now_iso
from lib.story_package import StoryPackage, validate_episode_id
from lib.upscale_backends import resolve_upscale_job
from upscale_video import upscale_video

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_NONE = 21
EXIT_PARTIAL = 31


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Upscale episode work clips to deliver tier")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--shots",
        default="all_with_work",
        help="all_with_work | all | S01,S02,...",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="deliver tier (default episode default_deliver_tier / deliver_1080)",
    )
    parser.add_argument("--backend", default=None, help="upscale backend (default seedvr2)")
    parser.add_argument("--fps", type=float, default=16.0)
    parser.add_argument("--two-pass", action="store_true")
    parser.add_argument("--no-two-pass", action="store_true")
    parser.add_argument("--timeout", type=int, default=14400)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    all_shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if args.shots in ("all", "all_with_work", "*"):
        selected = all_shots
    else:
        want = {x.strip() for x in args.shots.split(",") if x.strip()}
        selected = [s for s in all_shots if s.get("shot_id") in want]

    if args.shots == "all_with_work" or args.shots in ("all", "*"):
        filtered = []
        for s in selected:
            rel = s.get("clip_work") or f"clips/work/{s.get('shot_id')}.mp4"
            path = story.path(*rel.replace("\\", "/").split("/"))
            if os.path.isfile(path) or args.dry_run:
                filtered.append(s)
        if not args.dry_run:
            selected = filtered

    if not selected:
        print("[ERROR] code=21 no work clips found", file=sys.stderr)
        return EXIT_NONE

    format_id = story.format_id()
    preset = args.preset or story.doc.get("default_deliver_tier") or "deliver_1080"
    backend = args.backend or "seedvr2"
    two = True if args.two_pass else (False if args.no_two_pass else None)

    try:
        job = resolve_upscale_job(
            backend=backend, preset=preset, format_id=format_id
        )
    except Exception as e:
        print(f"[ERROR] code=2 upscale config: {e}", file=sys.stderr)
        return EXIT_USAGE

    print(
        f"episode_upscale episode={args.episode} format={format_id} "
        f"preset={job['preset_id']} {job['width']}x{job['height']} "
        f"backend={backend} shots={len(selected)}"
    )

    ok = 0
    fail = 0
    for shot in selected:
        sid = shot.get("shot_id")
        work_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
        deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"
        work_path = story.path(*work_rel.replace("\\", "/").split("/"))
        deliver_path = story.path(*deliver_rel.replace("\\", "/").split("/"))
        os.makedirs(os.path.dirname(deliver_path), exist_ok=True)

        print(f"\n=== {sid} ===")
        print(f"  in={work_path}")
        print(f"  out={deliver_path}")

        if args.dry_run:
            print("  [dry-run] skip upscale_video")
            ok += 1
            continue

        if not os.path.isfile(work_path):
            print("  FAIL work clip missing")
            fail += 1
            if args.stop_on_error:
                break
            continue

        result = upscale_video(
            work_path,
            deliver_path,
            backend=backend,
            preset=preset,
            format_id=format_id,
            fps=args.fps,
            two_pass=two,
            timeout_sec=args.timeout,
            meta_out=story.path("meta", f"{sid}_upscale.json"),
        )
        if result.get("ok"):
            ok += 1
            story.update_shot(
                sid,
                clip_deliver=deliver_rel.replace("\\", "/"),
                upscale_status="ok",
                upscale_at=utc_now_iso(),
                upscale_preset=job["preset_id"],
                upscale_backend=backend,
            )
            print(f"  OK {deliver_path}")
        else:
            fail += 1
            story.update_shot(
                sid,
                upscale_status="failed",
                upscale_error=result.get("error"),
                upscale_at=utc_now_iso(),
            )
            print(f"  FAIL {result.get('error')}")
            if args.stop_on_error:
                break

    print(f"\nDone ok={ok} fail={fail}")
    if ok == 0:
        return EXIT_PARTIAL if fail else EXIT_NONE
    if fail:
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
