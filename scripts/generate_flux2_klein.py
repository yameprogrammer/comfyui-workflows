#!/usr/bin/env python3
"""Flux.2 Klein 9B GGUF — T2I and I2I.

No native Klein *edit* weights on disk. --mode i2i is denoise, not Qwen instruction edit.
Cinematic default still: generate_krea. Instruction edit: generate_qwen_edit.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.flux2_klein_runner import check_klein_models, generate_flux2_klein
from lib.still_model_profiles import FLUX2_KLEIN_UNET


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Flux.2 Klein 9B T2I / I2I (GGUF). Not Qwen edit, not Krea default."
    )
    p.add_argument("--mode", choices=["t2i", "i2i"], default="t2i")
    p.add_argument("--prompt", "-p", default="", help="Natural-language prompt")
    p.add_argument("--image", "-i", default=None, help="Required for --mode i2i")
    p.add_argument("--negative", default="")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--cfg", type=float, default=5.0)
    p.add_argument("--denoise", type=float, default=0.65, help="I2I only")
    p.add_argument("--unet-name", default=None, help=f"default {FLUX2_KLEIN_UNET}")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--check-models", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.check_models:
        chk = check_klein_models()
        print(json.dumps(chk, indent=2))
        return 0 if chk["ok"] else 11

    prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt required")

    out = args.output
    if not out:
        out = os.path.join(r"F:\generated_images", f"flux2_klein_{args.mode}.png")

    r = generate_flux2_klein(
        prompt=prompt,
        output_path=out,
        mode=args.mode,
        image_path=args.image,
        negative=args.negative,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        denoise=args.denoise,
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
