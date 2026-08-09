#!/usr/bin/env python3
"""MiniMax H3 — local open-weights video + native stereo audio (T2V / I2V / R2V).

ComfyUI ≥ 0.30.0 native nodes. Models: Comfy-Org/MiniMax-H3 pruned int8 pack
under F:\\model (extra_model_paths).

  # Text → video+audio (default work 864x480, 5s)
  python scripts/generate_minimax_h3.py -p "anime heroine on cliff at sunset..." -o out.mp4

  # Native canvas (~1344x768)
  python scripts/generate_minimax_h3.py -p "..." -o out.mp4 --profile native

  # Image → video (optional last frame = FL)
  python scripts/generate_minimax_h3.py --task i2v -i start.png -p "slow push in..." -o out.mp4
  python scripts/generate_minimax_h3.py --task i2v -i start.png --last end.png -p "..." -o out.mp4

  # Multi-reference (uses ref2va weights)
  python scripts/generate_minimax_h3.py --task r2v --ref-image a.png --ref-image b.png \\
      -p "Picture 1 is the heroine; she walks through Picture 2 city..." -o out.mp4

  python scripts/generate_minimax_h3.py --list-profiles
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.minimax_h3_runner import (
    FAMILY_MINIMAX_H3,
    PROFILES,
    UNET_FL2VA,
    UNET_REF2VA,
    CLIP_NAME,
    VAE_AUDIO,
    VAE_VIDEO,
    generate_minimax_h3,
    list_profiles,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="MiniMax H3 T2V/I2V/R2V with native stereo audio (ComfyUI native)"
    )
    p.add_argument("--prompt", "-p", default=None, help="shot + camera + audio description")
    p.add_argument("--prompt-file", default=None, help="read prompt from file")
    p.add_argument("--output", "-o", default=None, help="output .mp4 path")
    p.add_argument(
        "--task",
        choices=("t2v", "i2v", "r2v", "flf"),
        default="t2v",
        help="t2v=text, i2v=first frame, flf=first+last, r2v=multi-ref (default t2v)",
    )
    p.add_argument("--image", "-i", default=None, help="first frame (i2v/flf)")
    p.add_argument("--last", default=None, help="last frame (flf / optional i2v)")
    p.add_argument(
        "--ref-image",
        action="append",
        default=None,
        dest="ref_images",
        help="R2V reference image (repeat up to 9). Tag as <Picture 1> in prompt",
    )
    p.add_argument(
        "--ref-image-size",
        choices=("match", "max"),
        default="match",
        help="R2V: match=speed, max=stronger ID (slower)",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--duration", type=float, default=None, help="seconds (snapped to H3 grid)")
    p.add_argument(
        "--megapixels",
        type=float,
        default=None,
        help="ResolutionSelector megapixels (0.2–1.0+; 0.98≈native 1344x768)",
    )
    p.add_argument("--steps", type=int, default=None, help="sampler steps (default from profile)")
    p.add_argument(
        "--profile",
        choices=tuple(PROFILES.keys()),
        default="work",
        help="draft|work|native|hero (default work)",
    )
    p.add_argument(
        "--aspect",
        default="16:9",
        help="16:9 | 9:16 | 1:1 or format alias cinematic_16x9 / shorts_9x16",
    )
    p.add_argument("--timeout", type=int, default=1800, help="seconds (native can need 600+)")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument(
        "--free-policy",
        default=None,
        help="engine free policy: on_switch|always|never (default env AGENT_COMFY_FREE_POLICY)",
    )
    p.add_argument(
        "--free-after",
        action="store_true",
        help="POST /free unload after successful gen (helps H3 batch thrash)",
    )
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--list-models", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        print("=== MiniMax H3 profiles ===\n")
        for k, v in list_profiles().items():
            print(
                f"  {k}: megapixels={v['megapixels']} duration={v['duration']}s "
                f"steps={v['steps']}"
            )
            print(f"       {v['notes']}")
        print("\nBench RTX 4090: work ~113s · native ~378s for 5s clip (2026-08-07)")
        return 0

    if args.list_models:
        print("=== MiniMax H3 model files (via F:\\model + extra_model_paths) ===")
        print(f"  T2V/I2V unet : {UNET_FL2VA}")
        print(f"  R2V unet     : {UNET_REF2VA}")
        print(f"  text encoder : {CLIP_NAME}")
        print(f"  video vae    : {VAE_VIDEO}")
        print(f"  audio vae    : {VAE_AUDIO}")
        print(f"  engine family: {FAMILY_MINIMAX_H3}")
        print("  HF: https://huggingface.co/Comfy-Org/MiniMax-H3")
        print("  Docs: https://docs.comfy.org/tutorials/video/minimax/minimax-h3")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt / --prompt-file required")

    task = args.task
    if args.image and task == "t2v":
        task = "i2v"
    if args.ref_images:
        task = "r2v"
    if args.image and args.last and task == "i2v":
        task = "flf"

    out = args.output or os.path.join(r"F:\generated_videos", "minimax_h3_out.mp4")

    print(
        f"MiniMax H3 task={task} profile={args.profile} "
        f"duration={args.duration or PROFILES[args.profile]['duration']}s "
        f"mp={args.megapixels or PROFILES[args.profile]['megapixels']} "
        f"out={out}"
    )

    result = generate_minimax_h3(
        prompt=prompt,
        output_path=out,
        task=task,
        image_path=args.image,
        last_image_path=args.last,
        ref_images=args.ref_images,
        seed=args.seed,
        duration=args.duration,
        megapixels=args.megapixels,
        steps=args.steps,
        profile=args.profile,
        aspect=args.aspect,
        ref_image_size=args.ref_image_size,
        timeout_sec=float(args.timeout),
        server_address=args.server,
        free_policy=args.free_policy,
    )

    if not result.get("ok"):
        print(
            f"FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        return 1

    print(f"OK {result.get('output') or result.get('output_path')}")
    print(
        f"  seed={result.get('seed')} task={result.get('task')} "
        f"profile={result.get('profile')} elapsed={result.get('elapsed_sec')}s "
        f"prompt_id={result.get('prompt_id')}"
    )
    if result.get("meta_path"):
        print(f"  meta={result['meta_path']}")

    if args.free_after:
        try:
            from lib.comfy_engine_session import free_and_verify

            fr = free_and_verify(
                args.server, wait_idle_sec=10.0, enforce_threshold=False
            )
            print(
                f"  free_after: vram "
                f"{fr.get('before', {}).get('vram_free_mb')}→"
                f"{fr.get('after', {}).get('vram_free_mb')}MB"
            )
        except Exception as e:
            print(f"  free_after warn: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
