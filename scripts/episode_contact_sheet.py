#!/usr/bin/env python3
"""Build boards/contact_sheet.png from episode keyframes."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.contact_sheet import build_contact_sheet
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Contact sheet from episode stills")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--thumb", type=int, default=512)
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Default: stories/<ep>/boards/contact_sheet.png",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    paths = []
    for s in sorted(story.shots(), key=lambda x: x.get("order", 0)):
        sid = s.get("shot_id")
        rel = s.get("keyframe") or f"keyframes/{sid}.png"
        p = story.path(*rel.replace("\\", "/").split("/"))
        if os.path.isfile(p):
            paths.append(p)

    out = args.output or story.path("boards", "contact_sheet.png")
    print(f"contact_sheet episode={args.episode} stills={len(paths)} out={out}")
    if args.dry_run:
        for p in paths:
            print(f"  {p}")
        return EXIT_OK

    result = build_contact_sheet(paths, out, cols=args.cols, thumb_max=args.thumb)
    if not result.get("ok"):
        print(f"[ERROR] {result.get('error')} {result.get('message')}", file=sys.stderr)
        return EXIT_FAIL
    print(f"OK {result['output_path']} ({result['count']} panels)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
