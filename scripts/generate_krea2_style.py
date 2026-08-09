#!/usr/bin/env python3
"""Krea2 T2I with native style reference (Lonecat v7 feature slice).

Uses Krea2StyleReference + Krea2StyleTransfer on the Krea2 turbo stack.

  python scripts/generate_krea2_style.py -i style.png -p "cinematic portrait..." -o out.png --seed 42
  python scripts/generate_krea2_style.py -i mood.png -p "..." -o out.png --style-strength 0.8 --width 1024 --height 576

Requires: ComfyUI-Krea2-StyleTransfer (with Comfy 0.30+ kwargs-compatible patch).
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
PRESET = "krea2_style_ref_v70"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 style-reference still generation")
    p.add_argument("--prompt", "-p", required=True, help="generation prompt")
    p.add_argument(
        "--style-image",
        "-i",
        required=True,
        help="style reference image (color/mood/composition cues)",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=576)
    p.add_argument(
        "--style-strength",
        type=float,
        default=1.0,
        help="Krea2StyleTransfer style_strength (0 disables ref path)",
    )
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_style")
    if not eng.get("ok"):
        print(f"[krea2_style] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    out = args.output or "dumps/krea2_style_out.png"
    ports = {
        "positive": args.prompt,
        "style_image": args.style_image,
        "width": args.width,
        "height": args.height,
        "style_strength": args.style_strength,
        "filename_prefix": "krea2_style_ref",
    }
    print(
        f"Krea2 style-ref preset={PRESET} strength={args.style_strength} "
        f"size={args.width}x{args.height} out={out}"
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
            f"[krea2_style] FAIL {r.get('error')}: {r.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[krea2_style] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
