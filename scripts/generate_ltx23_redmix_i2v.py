#!/usr/bin/env python3
"""RedCraft LTX2.3 REDMix I2V — real UI from NEWKrea2 collection.

Civitai: https://civitai.red/models/579280/newkrea2-and-ltx23-and-ideogram-4-wf-in-collection
Version: LTX2.3REDMixKrea2 (animates stills; often fed by Krea2/Ideogram stills)

  python scripts/generate_ltx23_redmix_i2v.py -i start.png -p "..." -o out.mp4
  python scripts/generate_ltx23_redmix_i2v.py --list-backends

Default diffusion: LTX distilled GGUF (pack REDGTA int4 often missing).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.ltx23_redmix_runner import (
    BACKENDS,
    GGUF_DISTILLED,
    PACK_UNET,
    generate_ltx23_redmix_i2v,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="LTX2.3 REDMix I2V (RedCraft collection)")
    p.add_argument("--image", "-i", required=False, help="start frame image")
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", "-n", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--backend",
        default="gguf_distilled",
        choices=list(BACKENDS.keys()) + ["pack_redgta"],
        help="gguf_distilled (default) | gguf_10eros | gguf_dev | pack_redgta",
    )
    p.add_argument("--unet-name", default=None, help="override unet/gguf filename")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--frames", type=int, default=49, help="latent length / frames")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-backends", action="store_true")
    args = p.parse_args(argv)

    if args.list_backends:
        print("pack UNET (often missing):", PACK_UNET)
        print("gguf backends:")
        for k, v in BACKENDS.items():
            print(f"  {k}: {v}")
        print("  pack_redgta: uses UNETLoader", PACK_UNET)
        return 0

    if not args.image:
        p.error("--image required")
    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt / --prompt-file required")

    out = args.output or os.path.join(r"F:\generated_videos", "ltx23_redmix_out.mp4")
    backend = args.backend
    unet = args.unet_name
    if backend == "pack_redgta":
        backend = "pack"
        unet = unet or PACK_UNET

    print(f"REDMix I2V backend={backend} unet={unet or BACKENDS.get(backend, GGUF_DISTILLED)} out={out}")
    result = generate_ltx23_redmix_i2v(
        image_path=args.image,
        positive=prompt,
        negative=args.negative,
        output_path=out,
        seed=args.seed,
        backend=backend if backend != "pack" else "pack_redgta",
        unet_name=unet,
        width=args.width,
        height=args.height,
        duration_frames=args.frames,
        fps=args.fps,
        timeout_sec=args.timeout,
        server_address=args.server,
    )
    # fix backend key for pack
    if not result.get("ok") and backend == "pack":
        pass

    if not result.get("ok"):
        # retry pack path naming: use_gguf false
        if args.backend == "pack_redgta" and result.get("error") == "QUEUE_FAILED":
            print(result.get("message"), file=sys.stderr)
        print(f"FAIL {result.get('error')}: {result.get('message')}", file=sys.stderr)
        if result.get("build"):
            print(f"  build={result.get('build')}", file=sys.stderr)
        return 1

    print(f"OK {result.get('output') or result.get('output_path')}")
    print(f"  seed={result.get('seed')} backend={result.get('backend')} pid={result.get('prompt_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
