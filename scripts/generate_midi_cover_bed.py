#!/usr/bin/env python3
"""Skeleton → new-genre MIDI bed pack for MiniMax / Suno handoff.

  python scripts/generate_midi_cover_bed.py --chords "Am,F,C,G" --genre acoustic_ballad -o "%AGENT_WORKSPACE%/beds/demo1"

Does not copy the source master into the pack.
Guide: workflows/human/midi_cover/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.midi_arrange import DENSITIES, GENRES, KEEP_MODES
from lib.midi_cover_pack import build_cover_bed
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="뼈대 채보 → 편곡 MIDI 반주 팩")
    p.add_argument("--input", "-i", default=None, help="로컬 오디오")
    p.add_argument("--chords", default=None, help='쉼표 구분 코드 (예: "Am,F,C,G")')
    p.add_argument("--from-url", dest="from_url", default=None, help="분석 전용 유튜브 URL (원음은 팩에 넣지 않음)")
    p.add_argument("--genre", default="piano_pop", choices=list(GENRES))
    p.add_argument("--keep", default="harmony_only", choices=list(KEEP_MODES))
    p.add_argument("--density", default="medium", choices=list(DENSITIES), help="sparse|medium|full")
    p.add_argument("--bpm", type=float, default=None)
    p.add_argument("--key", default="C")
    p.add_argument("--bars", type=int, default=8)
    p.add_argument("--transpose", type=int, default=0)
    p.add_argument("--lyrics-lang", default="ko", choices=["ko", "en", "ja", "other"])
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--soundfont", default=None)
    p.add_argument("--output", "-o", required=True, help="팩 디렉터리")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    res = build_cover_bed(
        out_dir=args.output,
        chords=args.chords,
        audio_path=args.input,
        from_url=args.from_url,
        genre=args.genre,
        keep=args.keep,
        density=args.density,
        bpm=args.bpm,
        key=args.key,
        bars=args.bars,
        transpose=args.transpose,
        lyrics_lang=args.lyrics_lang,
        skip_render=bool(args.skip_render),
        soundfont=args.soundfont,
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res.get("ok"):
        print(f"[OK] cover bed → {res.get('path')}")
        print(f"  midi={res.get('midi_path')}")
        if res.get("wav_path"):
            print(f"  wav={res.get('wav_path')}")
        elif res.get("render") and not res["render"].get("ok"):
            print(f"  render skipped: {res['render'].get('error')}")
    else:
        print(f"[FAILED] {res.get('error')}: {res.get('message')}", file=sys.stderr)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
