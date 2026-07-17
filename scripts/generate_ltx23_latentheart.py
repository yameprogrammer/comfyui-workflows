#!/usr/bin/env python3
"""LatentHeart LTX2.3 AIO (Director) — real UI, GGUF-first tool.

Civitai: https://civitai.red/models/2553704/ltx23-all-in-one-sfw-nsfw-ltx-director-id-lora-controlnet-detailer-upscaler-interpolator

Local SSOT:
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector2.json
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector13.json

  python scripts/generate_ltx23_latentheart.py --list-profiles
  python scripts/generate_ltx23_latentheart.py --list-features
  python scripts/generate_ltx23_latentheart.py -p "..." -o out.mp4 --profile gguf_distilled
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.ltx23_latentheart_runner import (
    DEFAULT_PROFILE,
    GGUF_10EROS,
    GGUF_DISTILLED,
    generate_ltx23_latentheart,
)
from lib.ltx23_latentheart_switches import FEATURE_GROUPS, list_profiles


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="LatentHeart LTX2.3 AIO Director — real UI, GGUF default"
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", "-n", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="gguf_distilled | gguf_10eros | gguf_half_upscale | as_saved",
    )
    p.add_argument(
        "--director-version",
        default="2",
        choices=("2", "13"),
        help="2 = LTX23LTXDirector2, 13 = LTX23LTXDirector13",
    )
    p.add_argument("--model", default=None, help="gguf | standard | 10eros")
    p.add_argument("--gguf-name", default=None, help=f"default {GGUF_DISTILLED}")
    p.add_argument("--feature", action="append", default=[], help="feature_id to enable")
    p.add_argument("--no-feature", action="append", default=[], help="feature_id to disable")
    p.add_argument("--image", "-i", default=None)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--list-features", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        for k, v in list_profiles().items():
            print(f"{k}: {v}")
        return 0
    if args.list_features:
        print("=== optional feature groups (Fast Groups Bypasser) ===")
        for fid, title in FEATURE_GROUPS.items():
            print(f"  {fid}: {title}")
        print("\n=== model exclusive (QUICK MODEL SELECTOR) ===")
        print("  standard | gguf | 10eros")
        print("\n=== local GGUF examples ===")
        print(f"  distilled: {GGUF_DISTILLED}")
        print(f"  10eros:    {GGUF_10EROS}")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt / --prompt-file required")

    out = args.output or os.path.join(r"F:\generated_videos", "ltx23_lh_aio_out.mp4")
    print(
        f"LatentHeart AIO director={args.director_version} profile={args.profile} "
        f"gguf={args.gguf_name or 'profile-default'} out={out}"
    )

    result = generate_ltx23_latentheart(
        positive=prompt,
        negative=args.negative,
        output_path=out,
        seed=args.seed,
        profile=args.profile,
        director_version=args.director_version,
        features_on=args.feature or None,
        features_off=args.no_feature or None,
        model=args.model,
        gguf_name=args.gguf_name,
        image_path=args.image,
        timeout_sec=args.timeout,
        server_address=args.server,
    )
    if not result.get("ok"):
        print(f"FAIL {result.get('error')}: {result.get('message')}", file=sys.stderr)
        if result.get("build"):
            print(f"  build={result.get('build')}", file=sys.stderr)
        return 1
    print(f"OK {result.get('output') or result.get('output_path')}")
    print(f"  seed={result.get('seed')} profile={result.get('profile')} pid={result.get('prompt_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
