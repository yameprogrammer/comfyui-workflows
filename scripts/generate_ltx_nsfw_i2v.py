#!/usr/bin/env python3
"""LTX 2.3 Kenpechi I2V v2.0 — NSFW / 빨간맛 image-to-video via **real UI workflow**.

SSOT: workflows/human/ltx23_nsfw/ltx23I2VWorkflow_v20.json
Path: group switches (Fast Groups Bypasser) → expand → port inject → /prompt

  python scripts/generate_ltx_nsfw_i2v.py -i first.png -p "adult woman ..." -o out.mp4
  python scripts/generate_ltx_nsfw_i2v.py --list-profiles
  python scripts/generate_ltx_nsfw_i2v.py -i first.png -p "..." --profile as_saved

Adult 18+ only.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.ltx23_nsfw_workflow_runner import (
    DEFAULT_PROFILE,
    describe_profiles,
    generate_ltx_nsfw_i2v,
)

DEFAULT_OUT = r"F:\generated_videos\ltx23_nsfw_i2v_out.mp4"

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
        description="LTX 2.3 Kenpechi I2V v20 NSFW — real workflow + group switches"
    )
    p.add_argument("--image", "-i", default=None)
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", default=None)
    p.add_argument("--output", "-o", default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=None, help="Override Base Width slider")
    p.add_argument("--height", type=int, default=None, help="Override Base Height slider")
    p.add_argument("--length", type=float, default=None, help="Override Length (Seconds)")
    p.add_argument("--fps", type=int, default=None)
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"Switch profile (default {DEFAULT_PROFILE})",
    )
    p.add_argument("--rife", action="store_true", help="Enable RIFE group (disable Don't Use RIFE)")
    p.add_argument("--no-rife", action="store_true", help="Force Don't Use RIFE group")
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        for pr in describe_profiles():
            print(f"{pr['id']}: {pr.get('description')}")
            if pr.get("on"):
                print(f"  ON : {pr['on']}")
            if pr.get("off"):
                print(f"  OFF: {pr['off']}")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt or --prompt-file required")
    if not args.image:
        p.error("--image required")

    hit = [b for b in BANNED if b in prompt.lower()]
    if hit:
        print(f"FAIL AGE_POLICY: prompt hits {hit!r}. Adult 18+ only.", file=sys.stderr)
        return 11
    if not os.path.isfile(args.image):
        print(f"FAIL IMAGE_MISSING: {args.image}", file=sys.stderr)
        return 2

    rife = True if args.rife else (False if args.no_rife else None)

    print(
        f"LTX NSFW I2V real-WF profile={args.profile} "
        f"size={args.width}x{args.height} len={args.length} rife={rife}"
    )

    if args.dry_run:
        from lib.ltx23_nsfw_workflow_runner import build_i2v_api

        api, meta = build_i2v_api(
            image_path=args.image,
            prompt=prompt,
            negative=args.negative,
            seed=args.seed,
            width=args.width,
            height=args.height,
            length_sec=args.length,
            fps=args.fps,
            profile=args.profile,
            rife=rife,
        )
        print(
            f"OK dry-run nodes={len(api)} switches={meta.get('switch_changes')} "
            f"profile={meta.get('profile')}"
        )
        # show loaders present
        for nid, n in api.items():
            ct = n.get("class_type") or ""
            if any(
                x in ct
                for x in (
                    "Unet",
                    "CLIP",
                    "VAE",
                    "Checkpoint",
                    "Power",
                    "LoadImage",
                    "Sampler",
                )
            ):
                print(f"  {nid} {ct}")
        return 0

    r = generate_ltx_nsfw_i2v(
        image_path=args.image,
        prompt=prompt,
        output_path=args.output,
        negative=args.negative,
        seed=args.seed,
        width=args.width,
        height=args.height,
        length_sec=args.length,
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
