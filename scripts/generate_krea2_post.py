#!/usr/bin/env python3
"""Light post polish: brightness/contrast + film grain + Lucy sharpen.

  python scripts/generate_krea2_post.py -i still.png -o polished.png
  python scripts/generate_krea2_post.py -i still.png -o out.png --contrast 1.08 --grain 0.3

Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

PRESET = "krea2_post_polish_v70"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 post polish (BC + grain + sharpen)")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--brightness", type=float, default=1.0)
    p.add_argument("--contrast", type=float, default=1.05)
    p.add_argument("--saturation", type=float, default=1.05)
    p.add_argument("--grain", type=float, default=0.15, help="grain intensity (also density); light film look")
    p.add_argument("--sharpen", type=int, default=1, help="Lucy sharpen iterations")
    p.add_argument("--timeout", type=float, default=180)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    ensure_engine("post_polish", args.server, caller="generate_krea2_post")
    out = args.output or "dumps/krea2_post_out.png"
    g = max(0.01, min(1.0, float(args.grain)))
    ports = {
        "input_image": args.image,
        "brightness": args.brightness,
        "contrast": args.contrast,
        "saturation": args.saturation,
        "grain_density": g,
        "grain_intensity": g,
        "sharpen_iterations": max(1, int(args.sharpen)),
        "filename_prefix": "krea2_post",
    }
    print(f"post polish preset={PRESET} grain={g} contrast={args.contrast} out={out}")
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[post] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[post] ok → {r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
