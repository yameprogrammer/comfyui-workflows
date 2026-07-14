#!/usr/bin/env python3
"""Generate episode SRT from shot dialogue and optionally soft-burn into final video (P2-2).

  python scripts/episode_subtitles.py -e cafe_gomin_ep01
  python scripts/episode_subtitles.py -e cafe_gomin_ep01 --burn \\
    --video stories/cafe_gomin_ep01/exports/final/cafe_gomin_ep01_final_1080.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.story_package import StoryPackage, validate_episode_id
from lib.subtitles import burn_subtitles, write_episode_srt

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Episode SRT + optional soft burn-in")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="SRT path (default: exports/final/<ep>.srt)",
    )
    p.add_argument(
        "--burn",
        action="store_true",
        help="Soft-burn SRT into a video (requires --video or default final)",
    )
    p.add_argument(
        "--video",
        default=None,
        help="Input video for burn (default: exports/final/<ep>_final.mp4 or _final_1080.mp4)",
    )
    p.add_argument(
        "--burn-out",
        default=None,
        help="Burned video path (default: <video stem>_subs.mp4)",
    )
    p.add_argument("--font-size", type=int, default=22)
    p.add_argument("--margin-v", type=int, default=90, help="Bottom margin for 9:16")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    out_srt = args.output or story.path(
        "exports", "final", f"{args.episode}.srt"
    )
    print(f"episode_subtitles episode={args.episode}")
    wr = write_episode_srt(story, out_path=out_srt)
    if not wr.get("ok"):
        print(f"[ERROR] SRT write failed", file=sys.stderr)
        return EXIT_FAIL
    print(f"  srt={wr['path']} cues={wr['cue_count']}")
    for c in wr.get("cues") or []:
        print(
            f"    {c['shot_id']}: {c['start']:.2f}-{c['end']:.2f}s  "
            f"{(c.get('raw_text') or '')[:48]!r}"
        )

    burn_path = None
    if args.burn:
        vid = args.video
        if not vid:
            for name in (
                f"{args.episode}_final_1080.mp4",
                f"{args.episode}_final.mp4",
                f"{args.episode}_work_final.mp4",
            ):
                cand = story.path("exports", "final", name)
                if os.path.isfile(cand):
                    vid = cand
                    break
        if not vid or not os.path.isfile(vid):
            print(
                "[ERROR] --burn needs a final video (pass --video or assemble first)",
                file=sys.stderr,
            )
            return EXIT_MISSING
        burn_path = args.burn_out
        if not burn_path:
            root, ext = os.path.splitext(vid)
            burn_path = f"{root}_subs{ext or '.mp4'}"
        print(f"  burn in={vid}")
        print(f"  burn out={burn_path}")
        br = burn_subtitles(
            vid,
            wr["path"],
            burn_path,
            font_size=args.font_size,
            margin_v=args.margin_v,
        )
        if not br.get("ok"):
            print(f"[ERROR] burn {br.get('error')}: {br.get('message')}", file=sys.stderr)
            return EXIT_FAIL
        print(f"  OK burned={br.get('output_path') or burn_path}")

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "srt": wr["path"],
                    "cue_count": wr["cue_count"],
                    "cues": wr.get("cues"),
                    "burned": burn_path,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    # light export to workspace if configured
    try:
        from lib.workspace_export import maybe_export_episode

        maybe_export_episode(
            args.episode,
            export_flag=None,
            parts=["exports/final", "shots.json"],
            quiet=True,
        )
    except Exception:
        pass

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
