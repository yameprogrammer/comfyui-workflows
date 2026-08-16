#!/usr/bin/env python3
"""Flux.1 Dev Q4 T2I — prompt-following / illustration alternative to Krea.

NOT the cinematic default. Use generate_krea for photoreal keyframes.
Typography → generate_ideogram4. Anime tags → generate_illustrious / generate_anima.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.flux1_runner import check_flux1_models, generate_flux1_t2i
from lib.still_model_profiles import FLUX1_DEV_UNET


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Flux.1 Dev Q4 T2I (not Krea default, not Ideogram typography)"
    )
    p.add_argument("--prompt", "-p", required=False, default="", help="Natural-language prompt")
    p.add_argument("--negative", default="", help="Usually unused on Flux")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--guidance", type=float, default=3.5)
    p.add_argument("--unet-name", default=None, help=f"default {FLUX1_DEV_UNET}")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--check-models", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.check_models:
        chk = check_flux1_models(need_fill=False)
        print(json.dumps(chk, indent=2))
        return 0 if chk["ok"] else 11

    prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt required")

    out = args.output
    if not out:
        out = os.path.join(r"F:\generated_images", "flux1_dev.png")

    r = generate_flux1_t2i(
        prompt=prompt,
        output_path=out,
        negative=args.negative,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        guidance=args.guidance,
        unet_name=args.unet_name,
        timeout_sec=args.timeout,
        dry_run=args.dry_run,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    print("OK", r.get("output_path") or out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
