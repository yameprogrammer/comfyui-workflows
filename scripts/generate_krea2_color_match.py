#!/usr/bin/env python3
"""Match target image colors to a reference look (ColorMatch mkl).

  python scripts/generate_krea2_color_match.py -i target.png --ref mood.png -o out.png
  python scripts/generate_krea2_color_match.py -i target.png --ref mood.png -o out.png --strength 0.5
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

PRESET = "krea2_color_match_v70"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="ColorMatch target → reference look")
    p.add_argument("--image", "-i", required=True, help="target image to regrade")
    p.add_argument("--ref", required=True, help="color/mood reference image")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--strength", type=float, default=0.65)
    p.add_argument("--timeout", type=float, default=180)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    ensure_engine("post_polish", args.server, caller="generate_krea2_color_match")
    out = args.output or "dumps/krea2_color_match_out.png"
    ports = {
        "input_image": args.image,
        "ref_image": args.ref,
        "strength": args.strength,
        "filename_prefix": "krea2_color_match",
    }
    print(f"color-match preset={PRESET} strength={args.strength} out={out}")
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[color_match] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[color_match] ok → {r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
