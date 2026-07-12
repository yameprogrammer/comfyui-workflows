#!/usr/bin/env python3
"""Approve episode keyframe and/or SI2V lip visual gate."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_KEYFRAME = 20
EXIT_CLIP = 21

LIP_STATUSES = ("pending", "in_review", "approved", "rejected")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Approve keyframe (I2V gate) and/or lip_status (SI2V visual gate)"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--shot", "-s", required=True)
    parser.add_argument(
        "--status",
        choices=["draft", "in_review", "approved"],
        default=None,
        help="Keyframe status (default: approved when not using --lip alone)",
    )
    parser.add_argument(
        "--lip",
        choices=list(LIP_STATUSES),
        default=None,
        help="SI2V lip visual status after watching clips/work/*_s2v.mp4",
    )
    parser.add_argument(
        "--require-file",
        action="store_true",
        default=True,
        help="Require keyframe image when setting keyframe status (default true)",
    )
    parser.add_argument("--allow-missing-file", action="store_true")
    parser.add_argument(
        "--require-s2v-clip",
        action="store_true",
        help="When --lip approved, require SI2V work clip exists",
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print("[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        print(f"[ERROR] code=2 shot missing {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    # If only --lip: do not force keyframe status change
    # If neither: default keyframe approved
    # If --status: update keyframe
    do_kf = args.status is not None or args.lip is None
    if do_kf and args.status is None:
        args.status = "approved"

    fields: dict = {}
    if do_kf and args.status is not None:
        rel = shot.get("keyframe") or f"keyframes/{args.shot}.png"
        path = story.path(*rel.replace("\\", "/").split("/"))
        require = args.require_file and not args.allow_missing_file
        if require and not os.path.isfile(path):
            print(f"[ERROR] code=20 keyframe file missing: {path}", file=sys.stderr)
            return EXIT_KEYFRAME
        fields["keyframe_status"] = args.status
        fields["keyframe"] = rel.replace("\\", "/")
        print(f"OK shot={args.shot} keyframe_status={args.status}")
        print(f"  file={path}")

    if args.lip is not None:
        if args.lip == "approved" or args.require_s2v_clip:
            clip_rel = (
                shot.get("clip_work_s2v")
                or shot.get("clip_work")
                or f"clips/work/{args.shot}_s2v.mp4"
            )
            cpath = story.path(*str(clip_rel).replace("\\", "/").split("/"))
            alt = story.path("clips", "work", f"{args.shot}_s2v.mp4")
            if args.lip == "approved" and not (
                os.path.isfile(cpath) or os.path.isfile(alt)
            ):
                print(
                    f"[ERROR] code=21 SI2V clip missing for lip approve: {cpath}",
                    file=sys.stderr,
                )
                return EXIT_CLIP
        fields["lip_status"] = args.lip
        print(f"OK shot={args.shot} lip_status={args.lip}")
        print(
            "  contract: lip_status is a HUMAN/vision gate — tools do not auto-score lips"
        )

    if not fields:
        print("[ERROR] nothing to update; pass --status and/or --lip", file=sys.stderr)
        return EXIT_USAGE

    story.update_shot(args.shot, **fields)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
