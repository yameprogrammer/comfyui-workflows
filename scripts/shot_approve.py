#!/usr/bin/env python3
"""Mark an episode keyframe as approved (or other status)."""

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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Approve episode keyframe for I2V")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--shot", "-s", required=True)
    parser.add_argument(
        "--status",
        choices=["draft", "in_review", "approved"],
        default="approved",
    )
    parser.add_argument(
        "--require-file",
        action="store_true",
        default=True,
        help="Require keyframe image exists (default true)",
    )
    parser.add_argument("--allow-missing-file", action="store_true")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        print(f"[ERROR] code=2 shot missing {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    rel = shot.get("keyframe") or f"keyframes/{args.shot}.png"
    path = story.path(*rel.replace("\\", "/").split("/"))
    require = args.require_file and not args.allow_missing_file
    if require and not os.path.isfile(path):
        print(f"[ERROR] code=20 keyframe file missing: {path}", file=sys.stderr)
        return EXIT_KEYFRAME

    story.update_shot(args.shot, keyframe_status=args.status, keyframe=rel.replace("\\", "/"))
    print(f"OK shot={args.shot} keyframe_status={args.status}")
    print(f"  file={path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
