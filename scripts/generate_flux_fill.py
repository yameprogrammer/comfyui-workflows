#!/usr/bin/env python3
"""Flux.1 Fill Dev Q4 — photoreal / general mask inpaint.

White/light in the mask = region to replace.
Instruction-without-mask → generate_qwen_edit.
Qwen InstantX look → generate_qwen_inpaint.
Anime mask → generate_anima --mode inpaint.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.flux1_runner import check_flux1_models, generate_flux1_fill
from lib.still_model_profiles import FLUX1_FILL_UNET


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Flux.1 Fill mask inpaint (not Qwen InstantX, not Anima)"
    )
    p.add_argument("--image", "-i", required=False, help="Source image")
    p.add_argument("--mask", "-m", required=False, help="Mask image (white = edit)")
    p.add_argument("--prompt", "-p", default="", help="What to put in the mask")
    p.add_argument("--negative", default="")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--guidance", type=float, default=3.5)
    p.add_argument("--grow-mask", type=int, default=6)
    p.add_argument("--unet-name", default=None, help=f"default {FLUX1_FILL_UNET}")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--check-models", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.check_models:
        chk = check_flux1_models(need_fill=True)
        print(json.dumps(chk, indent=2))
        return 0 if chk["ok"] else 11

    prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt required")
    if not args.image:
        p.error("--image required")
    if not args.mask:
        p.error("--mask required (white = inpaint region)")

    out = args.output
    if not out:
        out = os.path.join(r"F:\generated_images", "flux1_fill.png")

    r = generate_flux1_fill(
        prompt=prompt,
        image_path=args.image,
        mask_path=args.mask,
        output_path=out,
        negative=args.negative,
        seed=args.seed,
        steps=args.steps,
        guidance=args.guidance,
        grow_mask=args.grow_mask,
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
