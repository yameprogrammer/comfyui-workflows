#!/usr/bin/env python3
"""LTX 2.3 spatial x2 upscale for video clips (MiniMax H3 low-res → HD pattern).

Community-proven path: generate MiniMax at work/draft MP, then LTX latent spatial
upscaler (+ short refine) instead of native high-res H3.

  python scripts/upscale_ltx_spatial.py -i minimax_work.mp4 -o out_hd.mp4
  python scripts/upscale_ltx_spatial.py -i clip.mp4 -o out.mp4 --steps 4 --guide-strength 0.45
  python scripts/upscale_ltx_spatial.py -i clip.mp4 -o out.mp4 -p "preserve face, sharp anime lines"

Chain with MiniMax:
  python scripts/generate_minimax_h3.py -p "..." -o work.mp4 --profile work
  python scripts/upscale_ltx_spatial.py -i work.mp4 -o deliver.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.ltx_spatial_upscale import DEFAULT_PROMPT, ltx_spatial_upscale_video


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="LTX 2.3 spatial x2 video upscale (MiniMax H3 low-res → HD)"
    )
    p.add_argument("--input", "-i", required=True, help="source video (e.g. MiniMax work mp4)")
    p.add_argument("--output", "-o", default=None, help="output mp4 path")
    p.add_argument(
        "--prompt",
        "-p",
        default=None,
        help="refine prompt (default: preserve quality / identity)",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--steps",
        type=int,
        default=4,
        help="CRT unified sampler steps (community often 3–6 for upscale)",
    )
    p.add_argument(
        "--guide-strength",
        type=float,
        default=0.45,
        help="V2V guide strength; lower = freer, higher = stick to source",
    )
    p.add_argument(
        "--megapixels",
        type=float,
        default=1.5,
        help="target megapixels hint for CRT (e.g. 1.5 ≈ ~1728x960 class)",
    )
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--low-vram", action="store_true", help="tiled VAE decode + unload")
    p.add_argument("--no-ic-lora", action="store_true", help="skip upscale IC LoRA")
    p.add_argument("--ic-strength", type=float, default=0.75)
    p.add_argument(
        "--path",
        choices=("full", "core"),
        default="full",
        help="full=community IC-LoRA refine (default, quality); core=spatial x2 only (fast)",
    )
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"FAIL missing input: {args.input}", file=sys.stderr)
        return 1

    out = args.output
    if not out:
        base, _ = os.path.splitext(args.input)
        out = f"{base}_ltx_spatial_x2.mp4"

    print(
        f"LTX spatial path={args.path} in={args.input} out={out} steps={args.steps} "
        f"guide={args.guide_strength} mp={args.megapixels}"
    )

    result = ltx_spatial_upscale_video(
        input_path=args.input,
        output_path=out,
        prompt=args.prompt or DEFAULT_PROMPT,
        seed=args.seed,
        steps=args.steps,
        guide_strength=args.guide_strength,
        megapixels_target=args.megapixels,
        fps=args.fps,
        low_vram=args.low_vram,
        use_upscale_ic_lora=not args.no_ic_lora,
        upscale_ic_strength=args.ic_strength,
        path=args.path,
        timeout_sec=float(args.timeout),
        server_address=args.server,
    )

    if not result.get("ok"):
        print(f"FAIL {result.get('error')}: {result.get('message')}", file=sys.stderr)
        return 1

    print(f"OK {result.get('output') or result.get('output_path')}")
    print(
        f"  seed={result.get('seed')} elapsed={result.get('elapsed_sec')}s "
        f"prompt_id={result.get('prompt_id')}"
    )
    if result.get("meta_path"):
        print(f"  meta={result['meta_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
