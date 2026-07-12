#!/usr/bin/env python3
"""Prepare SI2V driving audio (speech-band / center emphasis) without demucs."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.ffmpeg_util import DRIVING_PREP_MODES, prepare_driving_audio
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Prepare driving audio for SI2V (voicey / center / vocal_band)"
    )
    p.add_argument("--input", "-i", required=True, help="Source wav/mp3 (mix or VO)")
    p.add_argument("--output", "-o", default=None, help="Output wav path")
    p.add_argument(
        "--mode",
        "-m",
        default="center_voicey",
        choices=list(DRIVING_PREP_MODES),
        help="Prep filter mode (default center_voicey)",
    )
    p.add_argument(
        "--episode",
        "-e",
        default=None,
        help="If set without --output: write under audio/exports/s2v_drive/",
    )
    p.add_argument("--name", default=None, help="Output basename without .wav")
    p.add_argument("--stereo", action="store_true", help="Keep stereo (default mono)")
    p.add_argument("--sr", type=int, default=48000, help="Sample rate (default 48000)")
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"[ERROR] input missing: {args.input}", file=sys.stderr)
        return EXIT_USAGE

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
            label = args.name or f"{os.path.splitext(os.path.basename(args.input))[0]}_{args.mode}"
            out = story.path("audio", "exports", "s2v_drive", f"{label}.wav")
        else:
            base, _ = os.path.splitext(args.input)
            out = f"{base}_{args.mode}.wav"

    r = prepare_driving_audio(
        args.input,
        out,
        mode=args.mode,
        sample_rate=args.sr,
        mono=not args.stereo,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return EXIT_FAIL
    print(f"OK {r['output_path']}")
    print(f"  mode={r.get('mode')} sr={r.get('sample_rate')} ch={r.get('channels')}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
