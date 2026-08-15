#!/usr/bin/env python3
"""Render a MIDI file to WAV.

  python scripts/generate_midi_render.py -i bed.mid -o bed.wav
  python scripts/generate_midi_render.py -i bed.mid -o bed.wav --soundfont GeneralUser.sf2

Default engine=auto: FluidSynth+sf2 if present, else built-in electronic synth.
Guide: workflows/human/midi_cover/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.midi_render import render_midi
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MIDI → WAV (FluidSynth 또는 내장 전자음 신스)")
    p.add_argument("--input", "-i", required=True, help=".mid")
    p.add_argument("--output", "-o", required=True, help=".wav")
    p.add_argument("--soundfont", default=None, help=".sf2 경로 (또는 SOUNDFONT env)")
    p.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "fluidsynth", "synth"],
        help="auto=FluidSynth 있으면 사용, 없으면 내장 신스",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        out_wav = die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    res = render_midi(args.input, out_wav, soundfont=args.soundfont, engine=args.engine)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res.get("ok"):
        print(f"[OK] WAV → {res.get('path')}")
    else:
        print(f"[FAILED] {res.get('error')}: {res.get('message')}", file=sys.stderr)
    return 0 if res.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
