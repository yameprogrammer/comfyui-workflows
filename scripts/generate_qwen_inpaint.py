#!/usr/bin/env python3
"""Qwen InstantX Inpainting ControlNet — real UI workflow.

SSOT: workflows/human/image_qwen_image_instantx_inpainting_controlnet.json

  python scripts/generate_qwen_inpaint.py -i photo.png --mask mask.png -p "red dress" -o out.png
  python scripts/generate_qwen_inpaint.py -i photo.png -p "..." --dry-run

Mask: white/light = region to inpaint. Optional; if omitted uses LoadImage.MASK
from the source (Comfy painted mask / alpha when present).

Default path = pack **Inpainting** branch (20 step, CFG 2.5). Outpaint branch
stays bypassed. --lightning optionally enables 4-step LoRA (if model present).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.qwen_instantx_inpaint_runner import generate_qwen_instantx_inpaint

DEFAULT_OUT = r"F:\generated_images\qwen_instantx_inpaint_out.png"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Qwen InstantX inpaint — real workflow + ports (not mini graph)"
    )
    p.add_argument("--image", "-i", required=True, help="Source image")
    p.add_argument(
        "--mask",
        "-m",
        default=None,
        help="Optional mask image (white/red = edit). Else LoadImage.MASK from source",
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", default=" ")
    p.add_argument("--output", "-o", default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None, help="Default pack: 20")
    p.add_argument("--cfg", type=float, default=None, help="Default pack: 2.5")
    p.add_argument("--denoise", type=float, default=None, help="Default pack: 1.0")
    p.add_argument("--cn-strength", type=float, default=None, help="ControlNet strength 0-1")
    p.add_argument("--max-dim", type=int, default=None, help="ImageScaleToMaxDimension (pack 1536)")
    p.add_argument("--grow-mask", type=int, default=None, help="GrowMask expand px")
    p.add_argument("--blur-radius", type=int, default=None, help="Mask blur radius")
    p.add_argument(
        "--lightning",
        action="store_true",
        help="Enable Lightning LoRA path (pack default is OFF / quality 20-step)",
    )
    p.add_argument("--lightning-lora", default=None)
    p.add_argument(
        "--gguf",
        default=None,
        help="LoaderGGUF name (default QwenImage\\\\Qwen-Image-Edit-2509-Q5_K_M.gguf)",
    )
    p.add_argument(
        "--gguf-light",
        action="store_true",
        help="Use Q4_K_M 2511 GGUF (lower VRAM)",
    )
    p.add_argument(
        "--fp8",
        action="store_true",
        help="Use pack UNETLoader fp8 (~20GB) instead of GGUF",
    )
    p.add_argument("--unet-name", default=None, help="Only with --fp8")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt or --prompt-file required")
    if not os.path.isfile(args.image):
        print(f"FAIL IMAGE_MISSING: {args.image}", file=sys.stderr)
        return 2
    if args.mask and not os.path.isfile(args.mask):
        print(f"FAIL MASK_MISSING: {args.mask}", file=sys.stderr)
        return 2

    from lib.qwen_instantx_inpaint_runner import GGUF_DEFAULT, GGUF_LIGHT

    gguf = args.gguf
    if args.gguf_light and not gguf:
        gguf = GGUF_LIGHT
    if not gguf and not args.fp8:
        gguf = GGUF_DEFAULT

    print(
        f"Qwen InstantX inpaint image={args.image} mask={args.mask} "
        f"lightning={args.lightning} fp8={args.fp8} gguf={gguf if not args.fp8 else None}"
    )

    if args.dry_run:
        from lib.qwen_instantx_inpaint_runner import (
            apply_ports,
            build_api_from_ui,
            _stage,
        )

        api = build_api_from_ui(gguf_name=gguf, use_fp8=args.fp8)
        img = _stage(args.image, "dry_img")
        msk = _stage(args.mask, "dry_mask") if args.mask else None
        meta = apply_ports(
            api,
            image_name=img,
            prompt=prompt,
            negative=args.negative,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg,
            denoise=args.denoise,
            cn_strength=args.cn_strength,
            max_dim=args.max_dim,
            grow_mask=args.grow_mask,
            blur_radius=args.blur_radius,
            mask_name=msk,
            unet_name=args.unet_name,
            gguf_name=None if args.fp8 else gguf,
            enable_lightning=args.lightning,
            lightning_lora=args.lightning_lora,
        )
        print(f"OK dry-run nodes={len(api)} seed={meta.get('seed')} model={meta.get('model')}")
        for nid in ("71", "6", "3", "108", "37", "84", "121:199", "163"):
            if nid in api:
                print(f"  {nid} {api[nid].get('class_type')} {api[nid].get('inputs')}")
        return 0

    r = generate_qwen_instantx_inpaint(
        image_path=args.image,
        prompt=prompt,
        output_path=args.output,
        mask_path=args.mask,
        negative=args.negative,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        denoise=args.denoise,
        cn_strength=args.cn_strength,
        max_dim=args.max_dim,
        grow_mask=args.grow_mask,
        blur_radius=args.blur_radius,
        enable_lightning=args.lightning,
        lightning_lora=args.lightning_lora,
        unet_name=args.unet_name,
        gguf_name=gguf,
        use_fp8=args.fp8,
        timeout_sec=args.timeout,
    )
    if r.get("ok"):
        print("OK", r.get("output_path") or args.output)
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
