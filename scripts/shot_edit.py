#!/usr/bin/env python3
"""Create or patch a shot record in stories/<episode>/shots.json."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Edit episode shot fields in shots.json")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--shot", "-s", required=True)
    parser.add_argument("--action", default=None)
    parser.add_argument("--motion", dest="motion_prompt", default=None)
    parser.add_argument("--shot-type", default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--location", default=None)
    parser.add_argument(
        "--character",
        action="append",
        default=None,
        help="Set character_ids (repeatable; replaces list if any given)",
    )
    parser.add_argument("--order", type=int, default=None)
    parser.add_argument("--scene", dest="scene_id", default=None)
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create shot if missing (requires --action)",
    )
    parser.add_argument("--json", action="store_true", help="Print shot JSON after edit")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    fields = {}
    if args.action is not None:
        fields["action"] = args.action
    if args.motion_prompt is not None:
        fields["motion_prompt"] = args.motion_prompt
    if args.shot_type is not None:
        fields["shot_type"] = args.shot_type
    if args.duration is not None:
        fields["duration_sec"] = args.duration
    if args.location is not None:
        fields["location_id"] = args.location if args.location else None
    if args.character is not None:
        fields["character_ids"] = list(args.character)
    if args.order is not None:
        fields["order"] = args.order
    if args.scene_id is not None:
        fields["scene_id"] = args.scene_id

    try:
        shot = story.get_shot(args.shot)
        if not fields:
            if args.json:
                print(json.dumps(shot, ensure_ascii=False, indent=2))
            else:
                print(f"{args.shot} action={shot.get('action')!r} status={shot.get('keyframe_status')}")
            return EXIT_OK
        shot = story.update_shot(args.shot, **fields)
    except KeyError:
        if not args.create:
            print(
                f"[ERROR] code=2 shot missing {args.shot}; pass --create --action ...",
                file=sys.stderr,
            )
            return EXIT_USAGE
        if not args.action:
            print("[ERROR] code=2 --create requires --action", file=sys.stderr)
            return EXIT_USAGE
        shot = story.ensure_shot(
            args.shot,
            action=args.action,
            order=args.order,
            shot_type=args.shot_type,
            duration_sec=args.duration,
            location_id=args.location,
            character_ids=args.character or [],
            motion_prompt=args.motion_prompt,
            scene_id=args.scene_id,
        )

    print(f"OK shot={args.shot} updated")
    if args.json:
        print(json.dumps(shot, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
