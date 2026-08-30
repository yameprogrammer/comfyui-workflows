#!/usr/bin/env python3
"""MiniMax Music 3 — Production Music & Song Generation CLI Tool for AI Agent.

Generates complete, high-fidelity (32kHz stereo) songs with vocals,
or instrumental background soundtracks up to 5 minutes (300s) long.

Examples:
  # 1. Full Song with Korean Lyrics (Default mode: song)
  python scripts/generate_minimax_music.py \
    --caption-file cap.txt \
    --lyrics "[Intro]\n(기타 선율)\n[Verse]\n창가에 비가 내리면...\n[Chorus]\n너를 기억해" \
    -o workspace/kpop_ballad.flac

  # 2. Instrumental BGM / Soundtrack Mode
  python scripts/generate_minimax_music.py \
    --mode bgm \
    --caption "Cyberpunk Lo-fi chillhop, 90 BPM, analog synths, vinyl crackle" \
    --duration 120 \
    -o workspace/cyber_bgm.flac

  # 3. Long song: ceiling 300s, tiled VAE decode for VRAM
  python scripts/generate_minimax_music.py \
    --caption-file cap.txt --lyrics-file lyr.txt \
    --duration 300 --tiled-decode \
    -o workspace/full_song.flac

Guide: workflows/human/minimax_music/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
from pathlib import Path

from lib.comfy_client import DEFAULT_SERVER
from lib.minimax_music_runner import generate_minimax_music


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="MiniMax Music 3 Full Song & Instrumental BGM Generation Tool"
    )
    p.add_argument("--caption", "-c", default=None, help="Structured music description (Global Metadata, Vocal Details, Arrangement)")
    p.add_argument("--caption-file", default=None, help="Path to text file containing music description")
    p.add_argument("--lyrics", "-l", default=None, help="Song lyrics with [Intro], [Verse], [Chorus] section tags")
    p.add_argument("--lyrics-file", default=None, help="Path to text file containing structured lyrics")
    p.add_argument("--output", "-o", default=None, help="Output audio file path (.flac / .mp3 / .wav)")
    p.add_argument(
        "--mode",
        choices=["song", "bgm", "instrumental"],
        default="song",
        help="Generation mode: song (with vocals) or bgm (instrumental only)",
    )
    p.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Max duration in seconds (ceiling, 4–300). Song default 180, BGM default 60. Output may be shorter.",
    )
    p.add_argument("--steps", type=int, default=30, help="KSampler steps (official template: 30)")
    p.add_argument("--cfg", type=float, default=1.7, help="KSampler CFG (official template: 1.7)")
    p.add_argument("--sampler", default="euler", help="KSampler name (default: euler)")
    p.add_argument("--scheduler", default="simple", help="Scheduler name (default: simple)")
    p.add_argument(
        "--tiled-decode",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Tiled audio VAE decode. Default: on when duration >= 240s. Use --no-tiled-decode on a 4090 for 3-min songs.",
    )
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--server", default=DEFAULT_SERVER, help=f"ComfyUI server URL (default: {DEFAULT_SERVER})")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON result")
    p.add_argument("--force-prompt", action="store_true", help="Allow visual-language captions (debug)")

    args = p.parse_args(argv)

    # Read caption from file if provided
    caption_text = args.caption
    if args.caption_file and os.path.isfile(args.caption_file):
        with open(args.caption_file, "r", encoding="utf-8") as f:
            caption_text = f.read().strip()

    # Read lyrics from file if provided
    lyrics_text = args.lyrics
    if args.lyrics_file and os.path.isfile(args.lyrics_file):
        with open(args.lyrics_file, "r", encoding="utf-8") as f:
            lyrics_text = f.read().strip()

    from lib.prompt_dialect_gate import check_music_caption, refuse_or_hint

    _ck = check_music_caption(caption_text)
    if refuse_or_hint(_ck, force=bool(getattr(args, "force_prompt", False)), stream=sys.stderr):
        return 2

    try:
        res = generate_minimax_music(
            caption=caption_text,
            lyrics=lyrics_text,
            output_path=args.output,
            mode=args.mode,
            duration=args.duration,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg,
            sampler=args.sampler,
            scheduler=args.scheduler,
            server_url=args.server,
            tiled_decode=args.tiled_decode,
        )

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res.get("ok"):
                print(f"[OK] MiniMax Music generation complete ({res.get('elapsed_seconds', 0)}s)")
                print(f"Output saved to: {res.get('path')}")
            else:
                print(f"[FAILED] {res.get('error')}: {res.get('message')}", file=sys.stderr)

        return 0 if res.get("ok") else 1

    except Exception as e:
        if args.json:
            print(json.dumps({"ok": False, "error": "EXCEPTION", "message": str(e)}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
