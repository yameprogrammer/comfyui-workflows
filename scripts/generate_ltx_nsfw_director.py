#!/usr/bin/env python3
"""LTX 2.3 Kenpechi Director v2.0 — NSFW multi-shot via **real UI workflow**.

SSOT: workflows/human/ltx23_nsfw/ltx23DirectorWorkflow_directorV20.json
Path: group switches → expand → port inject → /prompt

  python scripts/generate_ltx_nsfw_director.py -p "adult woman ..." -o out.mp4
  python scripts/generate_ltx_nsfw_director.py --list-profiles

Single-image clips: prefer generate_ltx_nsfw_i2v.
Adult 18+ only.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.ltx23_nsfw_workflow_runner import (
    DEFAULT_PROFILE,
    describe_profiles,
    generate_ltx_nsfw_director,
)

DEFAULT_OUT = r"F:\generated_videos\ltx23_nsfw_director_out.mp4"

BANNED = (
    "child",
    "kid",
    "loli",
    "shota",
    "underage",
    "teen boy",
    "teen girl",
    "schoolgirl",
    "schoolboy",
    "12 year",
    "14 year",
    "15 year",
    "16 year",
    "17 year",
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="LTX 2.3 Kenpechi Director v20 NSFW — real workflow + group switches"
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--motion", default=None)
    p.add_argument("--negative", default=None)
    p.add_argument("--output", "-o", default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--fps", type=int, default=None)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--profile", default=DEFAULT_PROFILE)
    p.add_argument("--rife", action="store_true")
    p.add_argument("--no-rife", action="store_true")
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        for pr in describe_profiles():
            print(f"{pr['id']}: {pr.get('description')}")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt or --prompt-file required")

    hit = [b for b in BANNED if b in prompt.lower()]
    if hit:
        print(f"FAIL AGE_POLICY: prompt hits {hit!r}. Adult 18+ only.", file=sys.stderr)
        return 11

    rife = True if args.rife else (False if args.no_rife else None)
    print(f"LTX NSFW Director real-WF profile={args.profile} rife={rife}")

    if args.dry_run:
        from lib.ltx23_nsfw_workflow_runner import build_director_api

        api, meta = build_director_api(
            prompt=prompt,
            motion_prompt=args.motion,
            negative=args.negative,
            seed=args.seed,
            width=args.width,
            height=args.height,
            fps=args.fps,
            profile=args.profile,
            rife=rife,
        )
        print(f"OK dry-run nodes={len(api)} switches={meta.get('switch_changes')}")
        return 0

    r = generate_ltx_nsfw_director(
        prompt=prompt,
        output_path=args.output,
        motion_prompt=args.motion,
        negative=args.negative,
        seed=args.seed,
        width=args.width,
        height=args.height,
        fps=args.fps,
        profile=args.profile,
        rife=rife,
        timeout_sec=args.timeout,
    )
    if r.get("ok"):
        print("OK", r.get("output_path") or args.output)
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
