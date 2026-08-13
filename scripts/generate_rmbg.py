#!/usr/bin/env python3
"""Remove image background (u2net human seg).

  python scripts/generate_rmbg.py -i person.png -o cutout.png

Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md (FINISH / post)
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

PRESET = "rmbg_u2net"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Remove background (rembg u2net_human_seg)")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    ensure_engine("rmbg", args.server, caller="generate_rmbg")
    from lib.output_policy import resolve_media_output

    out = resolve_media_output(args.output, default_name="rmbg_out.png")
    print(f"RMBG preset={PRESET} out={out}")
    r = run_workflow_api(
        PRESET,
        ports={"input_image": args.image, "filename_prefix": "rmbg"},
        output_path=out,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[rmbg] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[rmbg] ok → {r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
