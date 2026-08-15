#!/usr/bin/env python3
"""Extract a harmonic skeleton (chords / BPM / key) for MIDI rearrangement.

  python scripts/extract_music_skeleton.py --chords "Am,F,C,G" --bpm 96 -o "%AGENT_WORKSPACE%/beds/s.json"
  python scripts/extract_music_skeleton.py -i demo.wav -o "%AGENT_WORKSPACE%/beds/s.json"

Guide: workflows/human/midi_cover/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import fail_result, ok_result
from lib.music_skeleton import (
    extract_skeleton,
    parse_chord_list,
    save_skeleton,
    skeleton_from_symbols,
)
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="음원 또는 코드 진행에서 화성 뼈대 JSON 추출")
    p.add_argument("--input", "-i", default=None, help="로컬 오디오 (WAV/MP3)")
    p.add_argument("--chords", default=None, help='쉼표 구분 코드 (예: "Am,F,C,G")')
    p.add_argument("--output", "-o", required=True, help="skeleton.json 경로")
    p.add_argument("--bpm", type=float, default=96.0)
    p.add_argument("--key", default="C")
    p.add_argument("--beats-per-chord", type=int, default=4)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        out_path = die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    if bool(args.input) == bool(args.chords):
        p.error("provide exactly one of --input/-i or --chords")

    try:
        if args.chords:
            sk = skeleton_from_symbols(
                parse_chord_list(args.chords),
                bpm=args.bpm,
                key=args.key,
                beats_per_chord=args.beats_per_chord,
            )
        else:
            sk = extract_skeleton(args.input)
            if sk.get("ok") is False:
                if args.json:
                    print(json.dumps(sk, indent=2, ensure_ascii=False))
                else:
                    print(f"[FAILED] {sk.get('error')}: {sk.get('message')}", file=sys.stderr)
                return 1
        path = save_skeleton(sk, out_path)
        res = ok_result(tool="extract_music_skeleton", path=path, output_path=path)
    except ToolboxWriteError:
        return 14
    except Exception as e:
        res = fail_result(error="EXTRACT_FAILED", message=str(e), tool="extract_music_skeleton")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] skeleton → {res.get('path')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
