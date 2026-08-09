#!/usr/bin/env python3
"""Krea2 T2I with native ControlLoRA (Lonecat v7 control slice).

Default LoRA: Krea2/depth-control-lora.safetensors (depth/structure map).

  python scripts/generate_krea2_control.py -i depth_or_pose.png -p "hero standing..." -o out.png --seed 42
  python scripts/generate_krea2_control.py -i map.png -p "..." -o out.png --control-strength 0.85

Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

FAMILY = "krea2_still"
PRESET = "krea2_control_v70"
DEFAULT_LORA = r"Krea2\depth-control-lora.safetensors"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 ControlLoRA still generation")
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument(
        "--control-image",
        "-i",
        required=True,
        help="control map (depth / structure / pose plate)",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=576)
    p.add_argument(
        "--control-strength",
        type=float,
        default=0.5,
        help="ControlLoRA strength (default 0.5; prefer depth/structure maps or photo→grayscale encode)",
    )
    p.add_argument(
        "--control-lora",
        default=DEFAULT_LORA,
        help=f"LoRA path under models/loras (default {DEFAULT_LORA})",
    )
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_control")
    if not eng.get("ok"):
        print(f"[krea2_control] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    out = args.output or "dumps/krea2_control_out.png"
    ports = {
        "positive": args.prompt,
        "control_image": args.control_image,
        "width": args.width,
        "height": args.height,
        "control_strength": args.control_strength,
        "control_lora": args.control_lora,
        "filename_prefix": "krea2_control",
    }
    print(
        f"Krea2 control preset={PRESET} lora={args.control_lora} "
        f"strength={args.control_strength} out={out}"
    )
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        seed=args.seed,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(
            f"[krea2_control] FAIL {r.get('error')}: {r.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[krea2_control] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
