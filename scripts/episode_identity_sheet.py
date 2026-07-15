#!/usr/bin/env python3
"""Build episode-level identity contact sheet (all keyframes + master ref).

Cross-shot cast drift is invisible when reviewing one file at a time.
Open boards/identity_contact.png, then record:

  python scripts/shot_qa_record.py -e EP --stage identity --verdict pass \\
    --notes "same person / wardrobe continuous"

  python scripts/episode_identity_sheet.py -e EP
  python scripts/episode_identity_sheet.py -e EP --record-pass --notes "..."
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.contact_sheet import build_contact_sheet
from lib.story_package import StoryPackage, validate_episode_id
from lib.visual_qa import (
    identity_sheet_path,
    identity_sheet_rel,
    keyframe_abs,
    resolve_identity_ref,
    save_identity_qa,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_PARTIAL = 31


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Episode identity contact sheet for cross-shot cast QA"
    )
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--cols",
        type=int,
        default=4,
        help="Grid columns (default 4)",
    )
    p.add_argument(
        "--thumb",
        type=int,
        default=320,
        help="Max thumb edge (default 320)",
    )
    p.add_argument(
        "--record-pass",
        action="store_true",
        help="Also write identity QA pass (only after you opened the sheet)",
    )
    p.add_argument(
        "--record-fail",
        action="store_true",
        help="Write identity QA fail",
    )
    p.add_argument("--notes", default="", help="Required with --record-pass/fail")
    p.add_argument("--agent", default="")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    paths: list[str] = []
    labels: list[str] = []

    # Lead identity ref once
    ref = None
    for s in shots:
        ref = resolve_identity_ref(story, s)
        if ref:
            break
    if ref:
        paths.append(ref)
        labels.append("REF_master")

    shot_ids: list[str] = []
    for s in shots:
        kf = keyframe_abs(story, s)
        if not kf:
            continue
        sid = str(s.get("shot_id"))
        paths.append(kf)
        labels.append(sid)
        shot_ids.append(sid)

    if len(paths) < 1:
        print("[ERROR] no keyframes found", file=sys.stderr)
        return EXIT_MISSING

    out = identity_sheet_path(story)
    # build_contact_sheet uses basename labels — rename temps? use paths as-is
    # Better: write via custom labels by temp naming — contact_sheet uses basename.
    # Copy/symlink not needed: basename of keyframes is S0x.png which is fine;
    # ref may be master_front.png — OK.

    result = build_contact_sheet(
        paths,
        out,
        cols=max(1, args.cols),
        thumb_max=args.thumb,
    )
    if not result.get("ok"):
        print(f"[ERROR] {result.get('error')}: {result.get('message')}", file=sys.stderr)
        return EXIT_PARTIAL

    print(f"OK identity sheet shots={len(shot_ids)} +ref={bool(ref)}")
    print(f"  sheet={result['output_path']}")
    print(f"  rel={identity_sheet_rel()}")
    print(f"  included={','.join(shot_ids)}")
    print(
        "  next: open sheet → "
        f"python scripts/shot_qa_record.py -e {args.episode} "
        "--stage identity --verdict pass --notes \"...\""
    )

    if args.record_pass or args.record_fail:
        if not (args.notes or "").strip():
            print("[ERROR] --notes required with --record-*", file=sys.stderr)
            return EXIT_USAGE
        verdict = "pass" if args.record_pass else "fail"
        path = save_identity_qa(
            story,
            verdict=verdict,
            notes=args.notes,
            shot_ids=shot_ids,
            agent=args.agent,
        )
        print(f"  identity_qa={path} verdict={verdict}")

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
