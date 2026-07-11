#!/usr/bin/env python3
"""Initialize a story/episode package from template."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import utc_now_iso
from lib.story_package import (
    copy_template,
    load_json,
    package_dir,
    save_json,
    validate_episode_id,
)
from lib.video_backends import get_format, list_format_ids, load_video_backends

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EXISTS = 10
EXIT_TEMPLATE = 12


def main(argv=None) -> int:
    try:
        formats = list_format_ids()
    except Exception:
        formats = ["cinematic_16x9", "shorts_9x16"]

    parser = argparse.ArgumentParser(description="Create episode package under stories/")
    parser.add_argument("--id", required=True, help="episode_id (snake_case)")
    parser.add_argument(
        "--format",
        dest="format_id",
        default="cinematic_16x9",
        help=f"format id (default cinematic_16x9). known: {', '.join(formats)}",
    )
    parser.add_argument(
        "--look",
        dest="look_id",
        default="cinematic_moody_v1",
        help="look_id under looks/ (default cinematic_moody_v1)",
    )
    parser.add_argument("--title", default=None, help="optional title for bible.md")
    parser.add_argument(
        "--seed-shots",
        type=int,
        default=0,
        help="Create N placeholder shots S01.. (default 0)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    episode_id = args.id.strip()
    if not validate_episode_id(episode_id):
        print(f"[ERROR] code=2 invalid episode id: {episode_id}", file=sys.stderr)
        return EXIT_USAGE

    try:
        get_format(args.format_id)
    except KeyError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    from lib.comfy_client import WORKSPACE_ROOT

    look_path = os.path.join(WORKSPACE_ROOT, "looks", args.look_id)
    if not os.path.isdir(look_path):
        print(f"[ERROR] code=2 look not found: {args.look_id}", file=sys.stderr)
        return EXIT_USAGE

    dest = package_dir(episode_id)
    if args.dry_run:
        print(f"[dry-run] would create {dest}")
        print(f"  format={args.format_id} look={args.look_id} seed_shots={args.seed_shots}")
        return EXIT_OK

    try:
        copy_template(episode_id, force=args.force)
    except FileExistsError:
        print(f"[ERROR] code=10 exists: {dest}", file=sys.stderr)
        return EXIT_EXISTS
    except FileNotFoundError:
        print("[ERROR] code=12 template missing", file=sys.stderr)
        return EXIT_TEMPLATE

    shots = load_json(os.path.join(dest, "shots.json"))
    shots["episode_id"] = episode_id
    shots["format"] = args.format_id
    shots["look_id"] = args.look_id
    cfg = load_video_backends()
    fmt = get_format(args.format_id, cfg)
    shots["default_work_preset"] = fmt.get("default_work_preset")
    shots["default_deliver_tier"] = (
        fmt.get("default_deliver_tier") or cfg.get("default_deliver_tier") or "deliver_1080"
    )

    if args.seed_shots > 0:
        shots["shots"] = []
        for i in range(1, args.seed_shots + 1):
            sid = f"S{i:02d}"
            shots["shots"].append(
                {
                    "shot_id": sid,
                    "scene_id": "SC01",
                    "order": i,
                    "duration_sec": 4,
                    "shot_type": "medium" if i > 1 else "establishing",
                    "camera": {"angle": "eye_level", "move": "static", "lens_feel": "35mm"},
                    "action": f"(edit action for {sid})",
                    "dialogue": "",
                    "vo": "",
                    "sfx": [],
                    "music_cue": "",
                    "character_ids": [],
                    "character_refs": {},
                    "location_id": None,
                    "location_ref": None,
                    "lighting": "",
                    "appearance_prompt": "",
                    "motion_prompt": "gentle natural motion, cinematic camera",
                    "negative_motion": "warp, identity morph, flicker",
                    "board_panel": f"boards/panels/{sid}.png",
                    "keyframe": f"keyframes/{sid}.png",
                    "keyframe_status": "missing",
                    "clip_work": f"clips/work/{sid}.mp4",
                    "clip_deliver": f"clips/deliver/{sid}.mp4",
                    "seed": None,
                    "continuity": {},
                }
            )

    save_json(os.path.join(dest, "shots.json"), shots)

    bible_path = os.path.join(dest, "bible.md")
    title = args.title or episode_id
    with open(bible_path, "w", encoding="utf-8") as f:
        f.write(
            f"# {title}\n\n"
            f"- **episode_id**: {episode_id}\n"
            f"- **format**: {args.format_id}\n"
            f"- **look_id**: {args.look_id}\n"
            f"- **created**: {utc_now_iso()}\n\n"
            f"## Logline\n\n(edit me)\n"
        )

    print(f"OK stories/{episode_id}/")
    print(f"  format={args.format_id} look={args.look_id}")
    print(f"  shots={len(shots.get('shots') or [])}")
    print(f"  edit: stories/{episode_id}/shots.json")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
