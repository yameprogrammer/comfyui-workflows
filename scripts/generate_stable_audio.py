#!/usr/bin/env python3
"""Stable Audio 3.0 — Production Instrumental & SFX Sound Generation Tool for AI Agent.

Generates studio-quality 44.1kHz stereo instrumental music (solo piano, guitar riffs,
chillhop beats, ambient soundscapes) or cinematic SFX sound effects (explosions, foley, weather).

Examples:
  # 1. Solo Piano Instrumental Music (Default mode: instrumental)
  python scripts/generate_stable_audio.py \
    --prompt "Emotional solo grand piano melody, neo-classical, intimate room acoustics, 80 BPM" \
    --duration 15 \
    -o workspace/piano_theme.flac

  # 2. Acoustic Guitar Riff / BGM
  python scripts/generate_stable_audio.py \
    --prompt "Solo acoustic guitar fingerstyle picking, warm studio room reverb, 90 BPM" \
    --duration 20 \
    -o workspace/acoustic_riff.flac

  # 3. Cinematic SFX Sound Effects Mode
  python scripts/generate_stable_audio.py \
    --mode sfx \
    --prompt "Cinematic heavy explosion with deep sub bass rumble, debris falling, realistic stereo reverb" \
    --duration 5 \
    -o workspace/explosion.flac

Guide: workflows/human/stable_audio/
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
from pathlib import Path

from lib.comfy_client import DEFAULT_SERVER
from lib.stable_audio_runner import generate_stable_audio


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Stable Audio 3.0 High-Fidelity Instrumental & SFX Generation Tool"
    )
    p.add_argument("--prompt", "-p", default=None, help="Audio description (instruments, style, mood, BPM, or SFX sound description)")
    p.add_argument("--prompt-file", default=None, help="Path to text file containing prompt")
    p.add_argument("--negative-prompt", "-n", default=None, help="Negative prompt")
    p.add_argument("--output", "-o", default=None, help="Output audio file path (.flac / .mp3 / .wav)")
    p.add_argument(
        "--mode",
        choices=["instrumental", "sfx", "music", "foley"],
        default="instrumental",
        help="Generation mode: instrumental (instruments/BGM) or sfx (sound effects/foley)",
    )
    p.add_argument("--duration", "-d", type=float, default=15.0, help="Duration in seconds (1.0 ~ 90.0, default: 15.0)")
    p.add_argument("--steps", type=int, default=30, help="Sampling steps (default: 30)")
    p.add_argument("--cfg", type=float, default=6.0, help="CFG scale (default: 6.0)")
    p.add_argument("--sampler", default="euler", help="KSampler name (default: euler)")
    p.add_argument("--scheduler", default="simple", help="Scheduler name (default: simple)")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--server", default=DEFAULT_SERVER, help=f"ComfyUI server URL (default: {DEFAULT_SERVER})")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON result")

    args = p.parse_args(argv)

    prompt_text = args.prompt
    if args.prompt_file and os.path.isfile(args.prompt_file):
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read().strip()

    try:
        res = generate_stable_audio(
            prompt=prompt_text,
            negative_prompt=args.negative_prompt,
            output_path=args.output,
            mode=args.mode,
            duration=args.duration,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg,
            sampler=args.sampler,
            scheduler=args.scheduler,
            server_url=args.server,
        )

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res.get("ok"):
                print(f"[OK] Stable Audio generation complete ({res.get('elapsed_seconds', 0)}s)")
                print(f"Output saved to: {res.get('path')}")
                try:
                    from lib.output_review import print_review_nudge

                    print_review_nudge(
                        str(res.get("path") or ""),
                        intent=str(prompt_text or ""),
                    )
                except Exception:
                    pass
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
