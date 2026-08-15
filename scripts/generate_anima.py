#!/usr/bin/env python3
"""Anima & Anima-LLLite — Production CLI Tool for AI Agent.

Generates state-of-the-art 2D anime, manga, and cel-shaded illustrations
using CircleStone Labs & Comfy Org's Anima DiT 2B and Anima-LLLite ControlNet adapters.

Examples:
  # 1. Base Text to Image (Default)
  python scripts/generate_anima.py -p "1girl, anime masterpiece, exquisite eyes" -o out.png

  # 2. Ultra-Fast Turbo Mode (8 steps)
  python scripts/generate_anima.py --turbo -p "1boy, cyber ninja, neon katana" -o out_turbo.png

  # 3. Lineart / Manga Sketch Auto-Coloring
  python scripts/generate_anima.py --mode lineart -i sketch.png -p "vibrant pastel colors" -o colored.png

  # 4. Spatial Depth Control
  python scripts/generate_anima.py --mode depth -i depth.png -p "anime sci-fi city" -o depth_out.png

  # 5. OpenPose Body Pose Lock
  python scripts/generate_anima.py --mode pose -i pose_stick.png -p "dynamic action pose" -o pose_out.png

  # 6. 4-Channel Anime Inpainting
  python scripts/generate_anima.py --mode inpaint -i char.png -m mask.png -p "cute smiling expression" -o inpaint.png

  # 7. Hi-Res 2K Upscale & Detailer
  python scripts/generate_anima.py --mode hires -p "masterpiece anime landscape" -o hires_2k.png

Guide: workflows/human/anima/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.anima_runner import DEFAULT_NEGATIVE, DEFAULT_POSITIVE, generate_anima
from lib.comfy_client import DEFAULT_SERVER


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Anima & Anima-LLLite 2D Anime Image & Control Generation Tool"
    )
    p.add_argument("--prompt", "-p", default=DEFAULT_POSITIVE, help="Positive text prompt")
    p.add_argument("--negative", "-n", default=DEFAULT_NEGATIVE, help="Negative text prompt")
    p.add_argument("--output", "-o", default=None, help="Output image file path")
    p.add_argument(
        "--mode",
        choices=["t2i", "lineart", "depth", "pose", "inpaint", "all-control", "hires", "upscale"],
        default="t2i",
        help="Generation mode (default: t2i)",
    )
    p.add_argument("--image", "-i", default=None, help="Input source image (for lineart, depth, pose, inpaint)")
    p.add_argument("--mask", "-m", default=None, help="Inpainting mask image (white=modify)")
    p.add_argument("--lineart-img", default=None, help="Specific lineart source for all-control mode")
    p.add_argument("--depth-img", default=None, help="Specific depth map for all-control mode")
    p.add_argument("--pose-img", default=None, help="Specific OpenPose map for all-control mode")
    p.add_argument("--control-strength", type=float, default=1.0, help="LLLite ControlNet strength (0.0~1.0)")
    p.add_argument("--turbo", action="store_true", help="Enable 8-step Anima Turbo LoRA mode for sub-2s generation")
    p.add_argument("--width", type=int, default=832, help="Width in pixels (default: 832)")
    p.add_argument("--height", type=int, default=1216, help="Height in pixels (default: 1216)")
    p.add_argument("--steps", type=int, default=28, help="Sampling steps (default: 28, turbo: 8)")
    p.add_argument("--cfg", type=float, default=4.0, help="CFG Scale (default: 4.0, turbo: 1.0)")
    p.add_argument("--sampler", default="euler", help="KSampler name (default: euler)")
    p.add_argument("--scheduler", default="simple", help="Scheduler name (default: simple)")
    p.add_argument("--denoise", "-d", type=float, default=1.0, help="Denoising strength (default: 1.0)")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--server", default=DEFAULT_SERVER, help=f"ComfyUI server URL (default: {DEFAULT_SERVER})")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON result")

    args = p.parse_args(argv)

    try:
        res = generate_anima(
            prompt=args.prompt,
            negative=args.negative,
            output_path=args.output,
            mode=args.mode,
            image=args.image,
            mask=args.mask,
            lineart_image=args.lineart_img,
            depth_image=args.depth_img,
            pose_image=args.pose_img,
            width=args.width,
            height=args.height,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg,
            sampler=args.sampler,
            scheduler=args.scheduler,
            denoise=args.denoise,
            control_strength=args.control_strength,
            turbo=args.turbo,
            server_url=args.server,
        )

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res.get("ok"):
                print(f"[OK] Anima generation complete ({res.get('elapsed_seconds', 0)}s)")
                print(f"Output saved to: {res.get('path')}")
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
