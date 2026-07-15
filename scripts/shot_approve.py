#!/usr/bin/env python3
"""Approve episode keyframe and/or work-clip / SI2V lip visual gates.

Hard gate (Rule 7.3): keyframe/clip *approved* requires a prior visual QA
JSON with verdict=pass (see shot_qa_pack + shot_qa_record). File existence
alone is not enough.

  python scripts/shot_qa_pack.py -e EP -s S03
  # open boards/qa/S03_keyframe_pack.png
  python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict pass \\
    --pass-required --notes "anatomy OK; matches master_front"
  python scripts/shot_approve.py -e EP -s S03 --status approved
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.audio_package import shot_motion_driver
from lib.episode_status import CLIP_STATUS_VALUES
from lib.story_package import StoryPackage, validate_episode_id
from lib.visual_qa import (
    EXIT_VISUAL_QA,
    require_visual_qa_enabled,
    validate_qa_for_approve,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_KEYFRAME = 20
EXIT_CLIP = 21
EXIT_QA = EXIT_VISUAL_QA  # 23

LIP_STATUSES = ("pending", "in_review", "approved", "rejected")


def _work_clip_paths(story: StoryPackage, shot: dict, shot_id: str) -> list[str]:
    rels = [
        shot.get("clip_work_s2v"),
        shot.get("clip_work"),
        f"clips/work/{shot_id}_s2v.mp4",
        f"clips/work/{shot_id}.mp4",
    ]
    paths: list[str] = []
    seen: set[str] = set()
    for rel in rels:
        if not rel:
            continue
        p = story.path(*str(rel).replace("\\", "/").split("/"))
        if p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def _find_work_clip(story: StoryPackage, shot: dict, shot_id: str) -> str | None:
    for p in _work_clip_paths(story, shot, shot_id):
        if os.path.isfile(p):
            return p
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Approve keyframe (I2V gate), clip_status (assemble hard gate), "
            "and/or lip_status (SI2V sub-gate). "
            "approved requires visual QA JSON pass unless --force-approve."
        )
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--shot", "-s", required=True)
    parser.add_argument(
        "--status",
        choices=["draft", "in_review", "approved"],
        default=None,
        help="Keyframe status (default: approved when not using --lip/--clip alone)",
    )
    parser.add_argument(
        "--clip",
        choices=list(CLIP_STATUS_VALUES),
        default=None,
        help=(
            "Work-clip visual status after watching clips/work/* "
            "(face/motion/lip). Assemble requires approved."
        ),
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
    parser.add_argument(
        "--require-work-clip",
        action="store_true",
        default=True,
        help="When --clip approved, require work clip exists (default true)",
    )
    parser.add_argument(
        "--allow-missing-work-clip",
        action="store_true",
        help="Allow --clip approved without work file (debug)",
    )
    parser.add_argument(
        "--no-sync-lip",
        action="store_true",
        help="Do not set lip_status=approved when --clip approved on si2v shots",
    )
    parser.add_argument(
        "--require-qa",
        action="store_true",
        help="Force visual QA gate on (default already on)",
    )
    parser.add_argument(
        "--no-require-qa",
        action="store_true",
        help="Skip visual QA hard gate (debug only)",
    )
    parser.add_argument(
        "--force-approve",
        action="store_true",
        help="Alias for --no-require-qa (debug/emergency only)",
    )
    parser.add_argument(
        "--require-qa-pack",
        action="store_true",
        help="Also require boards/qa/<shot>_*_pack.png exists",
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

    require_qa = require_visual_qa_enabled()
    if args.no_require_qa or args.force_approve:
        require_qa = False
    elif args.require_qa:
        require_qa = True

    # If only --lip / --clip: do not force keyframe status change
    # If neither lip nor clip: default keyframe approved
    # If --status: update keyframe
    do_kf = args.status is not None or (args.lip is None and args.clip is None)
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
        if args.status == "approved" and require_qa:
            gate = validate_qa_for_approve(
                story,
                shot,
                "keyframe",
                require_pack=args.require_qa_pack,
            )
            if not gate.get("ok"):
                print(
                    f"[ERROR] code={EXIT_QA} {gate.get('error')}: {gate.get('message')}",
                    file=sys.stderr,
                )
                return EXIT_QA
            print(f"  visual_qa=pass path={gate.get('path')}")
        elif args.status == "approved" and not require_qa:
            print(
                "  [WARN] visual QA gate bypassed "
                "(--force-approve / --no-require-qa / AGENT_REQUIRE_VISUAL_QA=0)",
                file=sys.stderr,
            )
        fields["keyframe_status"] = args.status
        fields["keyframe"] = rel.replace("\\", "/")
        print(f"OK shot={args.shot} keyframe_status={args.status}")
        print(f"  file={path}")

    if args.clip is not None:
        work_path = _find_work_clip(story, shot, args.shot)
        need_file = (
            args.clip == "approved"
            and args.require_work_clip
            and not args.allow_missing_work_clip
        )
        if need_file and not work_path:
            print(
                f"[ERROR] code=21 work clip missing for clip approve: "
                f"clips/work/{args.shot}[_s2v].mp4",
                file=sys.stderr,
            )
            return EXIT_CLIP
        if args.clip == "approved" and require_qa:
            gate = validate_qa_for_approve(
                story,
                shot,
                "clip",
                require_pack=args.require_qa_pack,
            )
            if not gate.get("ok"):
                print(
                    f"[ERROR] code={EXIT_QA} {gate.get('error')}: {gate.get('message')}",
                    file=sys.stderr,
                )
                return EXIT_QA
            print(f"  visual_qa=pass path={gate.get('path')}")
        elif args.clip == "approved" and not require_qa:
            print(
                "  [WARN] visual QA gate bypassed "
                "(--force-approve / --no-require-qa / AGENT_REQUIRE_VISUAL_QA=0)",
                file=sys.stderr,
            )
        fields["clip_status"] = args.clip
        print(f"OK shot={args.shot} clip_status={args.clip}")
        if work_path:
            print(f"  clip={work_path}")
        print(
            "  contract: clip_status is a HUMAN/vision gate — "
            "face/motion/lip; tools do not auto-score"
        )
        # SI2V: clip approve implies lips were reviewed unless --no-sync-lip
        driver = shot_motion_driver(shot, story.doc)
        if (
            args.clip == "approved"
            and driver == "si2v"
            and not args.no_sync_lip
            and args.lip is None
        ):
            fields["lip_status"] = "approved"
            print("  synced lip_status=approved (si2v; use --no-sync-lip to skip)")
        elif args.clip in ("pending", "rejected", "in_review") and driver == "si2v":
            if args.lip is None and args.clip in ("pending", "rejected"):
                fields["lip_status"] = (
                    args.clip if args.clip != "in_review" else "in_review"
                )

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
        print(
            "[ERROR] nothing to update; pass --status and/or --clip and/or --lip",
            file=sys.stderr,
        )
        return EXIT_USAGE

    story.update_shot(args.shot, **fields)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
