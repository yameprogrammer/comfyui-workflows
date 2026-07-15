#!/usr/bin/env python3
"""Build side-by-side QA packs so agents can actually compare identity/anatomy.

  keyframe pack: identity_ref | keyframe | prev_keyframe
  clip pack:     first | mid | last  (+ optional identity_ref)

Does NOT approve. Open the pack, then shot_qa_record, then shot_approve.

  python scripts/shot_qa_pack.py -e EP -s S03
  python scripts/shot_qa_pack.py -e EP -s S03 --stage clip
  python scripts/shot_qa_pack.py -e EP --all
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.story_package import StoryPackage, validate_episode_id
from lib.visual_qa import (
    build_compare_strip,
    extract_video_frame,
    keyframe_abs,
    prev_keyframe_abs,
    qa_pack_path,
    qa_pack_rel,
    resolve_identity_ref,
    work_clip_abs,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_PARTIAL = 31


def _pack_keyframe(story: StoryPackage, shot: dict) -> dict:
    sid = shot.get("shot_id") or "?"
    kf = keyframe_abs(story, shot)
    if not kf:
        return {"ok": False, "shot_id": sid, "error": "NO_KEYFRAME"}
    ref = resolve_identity_ref(story, shot)
    prev = prev_keyframe_abs(story, shot)
    out = qa_pack_path(story, sid, "keyframe")
    panels = [
        ("identity_ref", ref or ""),
        (f"{sid} keyframe", kf),
        ("prev_keyframe", prev or ""),
    ]
    result = build_compare_strip(panels, out, thumb_h=480)
    result["shot_id"] = sid
    result["stage"] = "keyframe"
    result["rel"] = qa_pack_rel(sid, "keyframe")
    result["ref"] = ref
    result["keyframe"] = kf
    return result


def _pack_clip(story: StoryPackage, shot: dict) -> dict:
    sid = shot.get("shot_id") or "?"
    clip = work_clip_abs(story, shot)
    if not clip:
        return {"ok": False, "shot_id": sid, "error": "NO_CLIP"}
    sample_dir = story.path("boards", "qa", f"{sid}_clip_frames")
    os.makedirs(sample_dir, exist_ok=True)
    first = os.path.join(sample_dir, "first.png")
    mid = os.path.join(sample_dir, "mid.png")
    last = os.path.join(sample_dir, "last.png")
    ok_f = extract_video_frame(clip, first, at="first")
    ok_m = extract_video_frame(clip, mid, at="mid")
    ok_l = extract_video_frame(clip, last, at="last")
    if not (ok_f or ok_m or ok_l):
        return {"ok": False, "shot_id": sid, "error": "FRAME_EXTRACT_FAIL"}

    ref = resolve_identity_ref(story, shot)
    out = qa_pack_path(story, sid, "clip")
    panels = [
        ("identity_ref", ref or ""),
        (f"{sid} first", first if ok_f else ""),
        (f"{sid} mid", mid if ok_m else ""),
        (f"{sid} last", last if ok_l else ""),
    ]
    result = build_compare_strip(panels, out, thumb_h=360)
    result["shot_id"] = sid
    result["stage"] = "clip"
    result["rel"] = qa_pack_rel(sid, "clip")
    result["clip"] = clip
    result["frames"] = {"first": first, "mid": mid, "last": last}
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Build visual QA comparison packs (ref | current | prev)"
    )
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shot", "-s", default=None, help="Shot id (or use --all)")
    p.add_argument(
        "--all",
        action="store_true",
        help="Pack all shots that have keyframe/clip for the stage",
    )
    p.add_argument(
        "--stage",
        choices=["keyframe", "clip", "both"],
        default="keyframe",
        help="Pack type (default keyframe)",
    )
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE
    if not args.shot and not args.all:
        print("[ERROR] pass --shot S0x or --all", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    if args.all:
        shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    else:
        try:
            shots = [story.get_shot(args.shot)]
        except KeyError:
            print(f"[ERROR] shot missing {args.shot}", file=sys.stderr)
            return EXIT_USAGE

    stages = (
        ["keyframe", "clip"] if args.stage == "both" else [args.stage]
    )
    ok_n = 0
    fail_n = 0
    for shot in shots:
        for stage in stages:
            if stage == "keyframe":
                r = _pack_keyframe(story, shot)
            else:
                r = _pack_clip(story, shot)
            if r.get("ok"):
                ok_n += 1
                print(f"OK {r.get('shot_id')} stage={stage}")
                print(f"  pack={r.get('output_path')}")
                if r.get("ref"):
                    print(f"  identity_ref={r['ref']}")
            else:
                fail_n += 1
                print(
                    f"[WARN] {r.get('shot_id')} stage={stage} "
                    f"error={r.get('error')}",
                    file=sys.stderr,
                )

    print(f"done ok={ok_n} fail={fail_n}")
    if ok_n == 0:
        return EXIT_PARTIAL
    return EXIT_OK if fail_n == 0 else EXIT_PARTIAL


if __name__ == "__main__":
    raise SystemExit(main())
