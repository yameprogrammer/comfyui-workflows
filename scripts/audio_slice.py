#!/usr/bin/env python3
"""Slice a segment from a master audio (e.g. music video track) for SI2V / dialogue."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.ffmpeg_util import slice_audio
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract audio slice for SI2V / stems")
    p.add_argument("--input", "-i", required=True, help="Source wav/mp3")
    p.add_argument("--output", "-o", default=None, help="Output path")
    p.add_argument("--start", type=float, default=0.0, help="Start sec")
    p.add_argument("--end", type=float, default=None, help="End sec (exclusive)")
    p.add_argument("--duration", type=float, default=None, help="Duration sec (alt to --end)")
    p.add_argument(
        "--episode",
        "-e",
        default=None,
        help="If set, default out under stories/<ep>/audio/…",
    )
    p.add_argument(
        "--stem",
        default="dialogue",
        choices=["dialogue", "vo", "sfx", "music", "masters", "exports"],
        help="With --episode: subfolder under audio/",
    )
    p.add_argument("--name", default=None, help="Output filename stem (default slice_t0-t1)")
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"[ERROR] input missing: {args.input}", file=sys.stderr)
        return EXIT_USAGE

    if args.end is None and args.duration is None:
        print("[ERROR] provide --end or --duration", file=sys.stderr)
        return EXIT_USAGE

    end = args.end
    if end is None and args.duration is not None:
        end = float(args.start) + float(args.duration)

    out = args.output
    if out is None:
        if args.episode:
            if not validate_episode_id(args.episode):
                print("[ERROR] bad episode id", file=sys.stderr)
                return EXIT_USAGE
            try:
                story = StoryPackage.load(args.episode)
            except FileNotFoundError:
                print("[ERROR] episode missing", file=sys.stderr)
                return EXIT_USAGE
            label = args.name or f"slice_{args.start:.2f}_{end:.2f}".replace(".", "p")
            out = story.path("audio", args.stem, f"{label}.wav")
        else:
            base, _ = os.path.splitext(args.input)
            out = f"{base}_slice_{args.start:.0f}_{end:.0f}.wav"

    r = slice_audio(
        args.input,
        out,
        start_sec=args.start,
        end_sec=end,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return EXIT_FAIL
    print(f"OK {out}")
    print(f"  start={args.start} end={end}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
