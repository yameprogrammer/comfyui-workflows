#!/usr/bin/env python3
"""YuE2 — Full Song & Music Cover Generation CLI Tool for AI Agent.

Generates complete, high-fidelity songs with vocals or arranges existing music
into brand new covers using M·A·P YuE2 (3B model) with ABC symbolic notation planning
and SheetSage2 audio transcription.

Examples:
  # 1. Full Song with Korean Lyrics (Default mode: text2music)
  python scripts/generate_yue2_music.py \\
    --style "female vocals, emotional pop ballad, grand piano, acoustic guitar, slow tempo 75 bpm" \\
    --lyrics "[Intro]\\n(piano intro)\\n\\n[Verse]\\n창밖에 스며든 불빛 사이로...\\n\\n[Chorus]\\n다시 부르는 이 노래" \\
    -o workspace/ballad.flac

  # 2. Text to Music using Style & Lyrics text files
  python scripts/generate_yue2_music.py \\
    --style-file style.txt \\
    --lyrics-file lyrics.txt \\
    --duration 180 \\
    -o workspace/full_song.flac

  # 3. Music Cover Mode (Transcribe reference audio with SheetSage2 -> Arrange into new style)
  python scripts/generate_yue2_music.py \\
    --mode cover \\
    -i original_melody.mp3 \\
    --style "acoustic jazz lounge, smooth saxophone, upright bass, brushed drums, relaxed 85 bpm" \\
    --lyrics "[Verse]\\nNew lyrics or original lyrics..." \\
    -o workspace/jazz_cover.flac

Guide: workflows/human/yue2_music/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
from pathlib import Path

from lib.comfy_client import DEFAULT_SERVER
from lib.yue2_music_runner import (
    DEFAULT_AUDIO_ENCODER,
    DEFAULT_CKPT,
    DEFAULT_DURATION,
    DEFAULT_SAMPLER,
    DEFAULT_SCHEDULER,
    DEFAULT_STEPS,
    generate_yue2_music,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="YuE2 Full Song & Music Cover Generation Tool for AI Agents"
    )
    p.add_argument(
        "--mode",
        "-m",
        choices=["text2music", "cover"],
        default="text2music",
        help="Generation mode: text2music (new song from text/lyrics) or cover (arrange audio with SheetSage2)",
    )
    p.add_argument(
        "--style",
        "-s",
        default=None,
        help="Music style/genre description (e.g. 'female vocals, K-pop dance, synthwave, 128 bpm')",
    )
    p.add_argument(
        "--style-file",
        default=None,
        help="Path to text file containing style description",
    )
    p.add_argument(
        "--lyrics",
        "-l",
        default=None,
        help="Song lyrics with [Intro], [Verse], [Chorus] section tags",
    )
    p.add_argument(
        "--lyrics-file",
        default=None,
        help="Path to text file containing structured lyrics",
    )
    p.add_argument(
        "--audio",
        "-i",
        default=None,
        help="Path to input reference audio file for cover mode (.wav / .mp3 / .flac)",
    )
    p.add_argument(
        "--duration",
        "-d",
        type=float,
        default=DEFAULT_DURATION,
        help="Duration ceiling in seconds (4 ~ 360, default: 120.0). Output may finish earlier.",
    )
    p.add_argument(
        "--abc-planning",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate ABC symbolic notation first for melodic/harmonic structure (default: True)",
    )
    p.add_argument(
        "--abc-mode",
        choices=["full", "melody"],
        default="full",
        help="ABC notation mode: 'full' (melody + chords) or 'melody' (melody only, recommended for covers)",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output audio file path (.flac / .mp3 / .wav)",
    )
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="KSampler steps (default: 32)")
    p.add_argument("--cfg", type=float, default=1.0, help="KSampler CFG scale (default: 1.0)")
    p.add_argument("--sampler", default=DEFAULT_SAMPLER, help=f"KSampler name (default: {DEFAULT_SAMPLER})")
    p.add_argument("--scheduler", default=DEFAULT_SCHEDULER, help=f"Scheduler name (default: {DEFAULT_SCHEDULER})")
    p.add_argument("--ckpt", default=DEFAULT_CKPT, help=f"Checkpoint file name (default: {DEFAULT_CKPT})")
    p.add_argument("--audio-encoder", default=DEFAULT_AUDIO_ENCODER, help=f"Audio encoder file name for cover mode (default: {DEFAULT_AUDIO_ENCODER})")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--server", default=DEFAULT_SERVER, help=f"ComfyUI server URL (default: {DEFAULT_SERVER})")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON result")

    args = p.parse_args(argv)

    # Read style from file if provided
    style_text = args.style
    if args.style_file and os.path.isfile(args.style_file):
        with open(args.style_file, "r", encoding="utf-8") as f:
            style_text = f.read().strip()

    # Read lyrics from file if provided
    lyrics_text = args.lyrics
    if args.lyrics_file and os.path.isfile(args.lyrics_file):
        with open(args.lyrics_file, "r", encoding="utf-8") as f:
            lyrics_text = f.read().strip()

    if args.mode == "cover" and not args.audio:
        sys.stderr.write("[ERROR] --mode cover requires an input audio path via --audio / -i\n")
        return 1

    try:
        res = generate_yue2_music(
            style=style_text,
            lyrics=lyrics_text,
            audio_path=args.audio,
            output_path=args.output,
            mode=args.mode,
            duration=args.duration,
            seed=args.seed,
            abc_planning=args.abc_planning,
            abc_mode="melody" if args.mode == "cover" and args.abc_mode == "full" else args.abc_mode,
            steps=args.steps,
            cfg=args.cfg,
            sampler=args.sampler,
            scheduler=args.scheduler,
            ckpt_name=args.ckpt,
            audio_encoder_name=args.audio_encoder,
            server_url=args.server,
        )

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res.get("ok"):
                print(f"[OK] YuE2 music generation complete ({res.get('elapsed_seconds', 0)}s)")
                print(f"Output saved to: {res.get('path')}")
                try:
                    from lib.output_review import print_review_nudge

                    print_review_nudge(
                        str(res.get("path") or ""),
                        intent=str(style_text or ""),
                    )
                except Exception:
                    pass
            else:
                print(f"[FAIL] YuE2 generation failed: {res.get('message', 'Unknown error')}")
                return 1

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"ok": False, "error": type(e).__name__, "message": str(e)}, indent=2))
        else:
            print(f"[EXCEPTION] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
