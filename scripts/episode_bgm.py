#!/usr/bin/env python3
"""
Generate BGM into an episode's audio/music/ stem for assemble mix.

Usage:
  python scripts/episode_bgm.py -e sonagi_cafe_smoke_v1 \\
    --prompt "soft piano rainy cafe lo-fi instrumental, warm pads, no vocals" \\
    --seconds 40 --bpm 85
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_bgm import generate_bgm
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Episode BGM via ACE-Step / Sonilo")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument("--lyrics", default="")
    p.add_argument("--seconds", "-d", type=float, default=45.0)
    p.add_argument("--bpm", type=int, default=90)
    p.add_argument("--engine", choices=["ace", "sonilo"], default="ace")
    p.add_argument("--profile", choices=["turbo", "base"], default="turbo")
    p.add_argument("--name", default=None, help="Basename without ext (default bgm_ace)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--with-vocals", action="store_true")
    p.add_argument("--language", default="en")
    p.add_argument("--keyscale", default="A minor")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    label = args.name or f"bgm_{args.engine}_{args.profile}"
    out_rel = f"audio/music/{label}.mp3"
    out_path = story.path(*out_rel.split("/"))
    meta_path = story.path("meta", f"{label}.json")

    print(f"episode_bgm episode={args.episode} engine={args.engine}")
    print(f"  out={out_path}")
    if args.dry_run:
        return EXIT_OK

    r = generate_bgm(
        args.prompt,
        lyrics=args.lyrics,
        seconds=args.seconds,
        bpm=args.bpm,
        engine=args.engine,
        profile=args.profile,
        seed=args.seed,
        language=args.language,
        keyscale=args.keyscale,
        instrumental=not args.with_vocals,
        output_filename=out_path,
        timeout_sec=args.timeout,
        meta_out=meta_path,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return EXIT_FAIL

    # Light touch: record path on episode audio block if present
    audio = story.doc.setdefault("audio", {})
    if not audio.get("bgm"):
        audio["bgm"] = out_rel.replace("\\", "/")
        story.save()
        print(f"  shots.json audio.bgm={audio['bgm']}")

    print(f"OK bgm={out_path}")
    print("  mix: assemble with dialogue_sfx_first_bgm_late (or set mix_policy)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
