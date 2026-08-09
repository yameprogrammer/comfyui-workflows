#!/usr/bin/env python3
"""Krea Moodboard search/apply → optional T2I.

  # Expand prompt only
  python scripts/generate_krea2_moodboard.py --query "dark teal gothic" --prompt "woman standing" --prompt-only

  # Expand + generate still
  python scripts/generate_krea2_moodboard.py --query "golden hour cinematic" \\
      --prompt "portrait of a woman" -o out.png --seed 42

Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.krea2_moodboard import moodboard_expand, moodboard_then_krea


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea Moodboard → prompt / T2I")
    p.add_argument("--query", "-q", required=True, help="moodboard search words")
    p.add_argument("--prompt", "-p", default="", help="user main prompt")
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--prompt-only",
        action="store_true",
        help="print expanded prompt only (no T2I)",
    )
    p.add_argument(
        "--strength",
        choices=("concise", "normal", "strong"),
        default="normal",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    if args.prompt_only:
        r = moodboard_expand(
            args.query,
            user_prompt=args.prompt,
            seed=args.seed,
            strength=args.strength,
            server_address=args.server,
        )
        if not r.get("ok"):
            print(f"[moodboard] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
            return 1
        print(r.get("prompt"))
        if r.get("style_block"):
            print("--- style ---", file=sys.stderr)
            print(r.get("style_block"), file=sys.stderr)
        return 0

    if not args.output:
        p.error("--output/-o required unless --prompt-only")
    if not args.prompt.strip():
        p.error("--prompt required for T2I (or use --prompt-only)")

    r = moodboard_then_krea(
        args.query,
        user_prompt=args.prompt,
        output_path=args.output,
        seed=args.seed,
        strength=args.strength,
        width=args.width,
        height=args.height,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[moodboard] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        if r.get("prompt"):
            print(f"[moodboard] prompt was: {r.get('prompt')}", file=sys.stderr)
        return 1
    print(f"[moodboard] prompt: {r.get('prompt')}")
    print(f"[moodboard] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
