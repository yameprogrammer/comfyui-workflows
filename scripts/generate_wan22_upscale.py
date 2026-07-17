#!/usr/bin/env python3
"""Wan2.2 diffusion video upscale (opt-in; not default deliver).

Default delivery remains rtx_vsr / seedvr2 (upscale_backends.json).

  python scripts/generate_wan22_upscale.py -i clip.mp4 -o out.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys
import time

from lib.workflow_paths import AGENT_WORKFLOWS_DIR
from lib.workflow_video_runner import run_workflow_video

PRESET = "wan22_upscale"
PRESET_API = os.path.join(AGENT_WORKFLOWS_DIR, "presets", f"{PRESET}.api.json")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Wan2.2 video upscale (opt-in)")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print("FAIL SOURCE_MISSING", args.input, file=sys.stderr)
        return 1
    if not os.path.isfile(PRESET_API):
        print(
            "FAIL PRESET_MISSING — run: "
            "node scripts/_export_wan22_subgraph_preset.mjs upscale",
            file=sys.stderr,
        )
        return 11

    out = args.output or (os.path.splitext(args.input)[0] + "_wan_up.mp4")
    if args.dry_run:
        print(f"dry-run preset={PRESET} in={args.input} out={out}")
        return 0

    r = run_workflow_video(
        PRESET,
        ports={
            "input_video": args.input,
            "filename_prefix": f"wan_up_{int(time.time())}",
        },
        output_path=out,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        seed=args.seed,
    )
    if r.get("ok"):
        print("OK", r.get("output_path"))
        return 0
    print("FAIL", r.get("error"), r.get("message"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
