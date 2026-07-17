#!/usr/bin/env python3
"""YAW Wan 2.2 MoE v0.50 — real UI T2V/I2V (GGUF diffusion by default).

Source: https://civitai.red/models/2008892/yet-another-workflow-easy-t2v-i2v-yaw-wan-22
Purpose: easy T2V + I2V template for Wan 2.2 MoE (high/low noise).

  python scripts/generate_yaw_wan22.py --task t2v -p "a cat walking..." -o out.mp4
  python scripts/generate_yaw_wan22.py --task i2v -i start.png -p "..." -o out.mp4
  python scripts/generate_yaw_wan22.py --list-features

Keeps real UI; toggles green T2V/I2V groups; swaps UNETLoader → UnetLoaderGGUF.
No mini-graph rebuild.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.yaw_wan22_runner import generate_yaw_wan22, GGUF, FP16


FEATURES = {
    "task_t2v": "Green group T2V (default) — dual T2V high/low UNET",
    "task_i2v": "Green group I2V — start image + dual I2V high/low UNET",
    "end_image": "End Image group (optional last frame for I2V)",
    "lightx2v": "AccelerationSelector High+Low (default ON in pack)",
    "vfi_gimm": "GIMM-VFI interpolator (default OFF for agent; pack may show GIMM on)",
    "vfi_rife": "RIFE VFI (purple max-one with GIMM)",
    "fps_32_60": "Final framerate purple groups 32/60 fps",
    "post_sharpen_grain": "Post Processing sharpen + film grain",
    "backend_gguf": "Default: UnetLoaderGGUF Q4_K_M (local Wan2.2/*)",
    "backend_fp16": "--fp16 pack UNETLoader names (large; often not installed)",
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="YAW Wan 2.2 MoE — real UI T2V/I2V with GGUF diffusion"
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", "-n", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--task", choices=("t2v", "i2v"), default="t2v")
    p.add_argument("--image", "-i", default=None, help="I2V start image")
    p.add_argument("--end-image", default=None, help="optional end frame")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--length-seconds", type=float, default=None, help="mxSlider seconds")
    p.add_argument("--steps", type=int, default=None, help="accelerated step budget")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--fp16", action="store_true", help="use pack fp16 UNET names (heavy)")
    p.add_argument("--vfi", action="store_true", help="enable GIMM-VFI interpolator group")
    p.add_argument(
        "--acceleration",
        default=None,
        help="AccelerationSelector value e.g. 'High + Low' / 'None'",
    )
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-features", action="store_true")
    args = p.parse_args(argv)

    if args.list_features:
        print("=== YAW Wan 2.2 MoE feature switches ===\n")
        for k, v in FEATURES.items():
            print(f"  {k}: {v}")
        print("\n=== Default GGUF files ===")
        for k, v in GGUF.items():
            print(f"  {k}: {v}")
        print("\n=== Pack fp16 names (--fp16) ===")
        for k, v in FP16.items():
            print(f"  {k}: {v}")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt / --prompt-file required")

    task = args.task
    if args.image:
        task = "i2v"

    out = args.output or os.path.join(r"F:\generated_videos", "yaw_wan22_out.mp4")

    print(
        f"YAW real-UI task={task} backend={'fp16' if args.fp16 else 'gguf'} "
        f"vfi={args.vfi} out={out}"
    )

    result = generate_yaw_wan22(
        positive=prompt,
        negative=args.negative,
        output_path=out,
        task=task,
        seed=args.seed,
        image_path=args.image,
        end_image_path=args.end_image,
        length_seconds=args.length_seconds,
        steps=args.steps,
        width=args.width,
        height=args.height,
        use_fp16=args.fp16,
        enable_vfi=args.vfi,
        acceleration=args.acceleration,
        timeout_sec=args.timeout,
        server_address=args.server,
    )

    if not result.get("ok"):
        print(
            f"FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        if result.get("build"):
            print(f"  build={result.get('build')}", file=sys.stderr)
        return 1

    print(f"OK {result.get('output') or result.get('output_path')}")
    print(
        f"  seed={result.get('seed')} task={result.get('task')} "
        f"backend={result.get('backend')} prompt_id={result.get('prompt_id')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
