#!/usr/bin/env python3
"""Write a new-genre MIDI bed from a harmonic skeleton or typed chords.

  python scripts/generate_midi_arrangement.py --chords "Am,F,C,G" --genre acoustic_ballad -o "%AGENT_WORKSPACE%/beds/bed.mid"
  python scripts/generate_midi_arrangement.py --skeleton skel.json --genre lofi_hiphop -o "%AGENT_WORKSPACE%/beds/bed.mid"

Guide: workflows/human/midi_cover/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import fail_result, ok_result
from lib.midi_arrange import GENRES, KEEP_MODES, arrange, default_arrangement, validate_arrangement
from lib.midi_smf import write_smf
from lib.music_skeleton import load_skeleton, parse_chord_list, save_skeleton, skeleton_from_symbols
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="화성 뼈대로 새 장르 MIDI 반주 작성")
    p.add_argument("--skeleton", default=None, help="music_skeleton.v1 JSON")
    p.add_argument("--chords", default=None, help='쉼표 구분 코드 (skeleton 없을 때)')
    p.add_argument("--genre", default="piano_pop", choices=list(GENRES))
    p.add_argument("--keep", default="harmony_only", choices=list(KEEP_MODES))
    p.add_argument("--bpm", type=float, default=None)
    p.add_argument("--key", default="C")
    p.add_argument("--bars", type=int, default=8)
    p.add_argument("--transpose", type=int, default=0)
    p.add_argument("--output", "-o", required=True, help=".mid 경로")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        out_mid = die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    if not args.skeleton and not args.chords:
        p.error("provide --skeleton or --chords")

    try:
        if args.skeleton:
            sk = load_skeleton(args.skeleton)
        else:
            sk = skeleton_from_symbols(
                parse_chord_list(args.chords),
                bpm=args.bpm or 96.0,
                key=args.key,
            )
        bpm = float(args.bpm or sk.get("bpm") or 96)
        arr = default_arrangement(
            genre=args.genre,
            bpm=bpm,
            key=str(sk.get("key") or args.key),
            bars=args.bars,
            keep=args.keep,
        )
        arr["transpose"] = int(args.transpose)
        arr = validate_arrangement(arr)
        tracks = arrange(sk, arr)
        path = write_smf(out_mid, tracks, bpm=arr["bpm"])
        spec_path = os.path.splitext(path)[0] + ".json"
        # sibling arrangement.json (plan) plus same-basename json
        arr_path = os.path.join(os.path.dirname(path), "arrangement.json")
        if os.path.basename(path).lower() != "arrangement.mid":
            arr_path = spec_path
        parent = os.path.dirname(arr_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(arr_path, "w", encoding="utf-8") as f:
            json.dump(arr, f, indent=2, ensure_ascii=False)
            f.write("\n")
        sk_sidecar = os.path.join(os.path.dirname(path), "skeleton.json")
        if not os.path.isfile(sk_sidecar):
            save_skeleton(sk, sk_sidecar)
        res = ok_result(
            tool="generate_midi_arrangement",
            path=path,
            output_path=path,
            arrangement_path=arr_path,
            genre=arr["genre"],
            keep=arr["keep"],
        )
    except Exception as e:
        res = fail_result(error="ARRANGE_FAILED", message=str(e), tool="generate_midi_arrangement")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] MIDI → {res.get('path')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
