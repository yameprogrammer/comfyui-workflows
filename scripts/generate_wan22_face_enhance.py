#!/usr/bin/env python3
"""Wan2.2 FaceEnhance post-process (CLIPSeg face crop + Wan refine).

Human UI: workflows/human/wan22/wan22_face_enhance.json
Agent API: workflows/agent/presets/wan22_face_enhance.api.json

  python scripts/generate_wan22_face_enhance.py -i clip.mp4 -o out.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys
import time

from lib.comfy_client import COMFYUI_INPUT_DIR
from lib.workflow_paths import AGENT_WORKFLOWS_DIR
from lib.workflow_video_runner import run_workflow_video

PRESET = "wan22_face_enhance"
PRESET_API = os.path.join(AGENT_WORKFLOWS_DIR, "presets", f"{PRESET}.api.json")
HUMAN_UI = os.path.join(
    os.path.dirname(AGENT_WORKFLOWS_DIR), "human", "wan22", "wan22_face_enhance.json"
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Wan2.2 FaceEnhance video polish")
    p.add_argument("--input", "-i", required=True, help="Input video (mp4)")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--frame-cap", type=int, default=None, help="Optional VHS frame_load_cap")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print("FAIL SOURCE_MISSING", args.input, file=sys.stderr)
        return 1

    if not os.path.isfile(PRESET_API):
        print("FAIL FACE_ENHANCE_PRESET_MISSING", file=sys.stderr)
        print(
            f"  Human UI: {HUMAN_UI}\n"
            f"  Export: node scripts/_export_wan22_subgraph_preset.mjs face_enhance",
            file=sys.stderr,
        )
        return 11

    out = args.output or (os.path.splitext(args.input)[0] + "_face.mp4")
    ports = {
        "input_video": args.input,
        "filename_prefix": f"face_enh_{int(time.time())}",
    }

    if args.dry_run:
        print(
            f"dry-run preset={PRESET} in={args.input} out={out} "
            f"api={PRESET_API}"
        )
        return 0

    # optional frame cap patch after load
    r = run_workflow_video(
        PRESET,
        ports=ports,
        output_path=out,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        seed=args.seed,
    )
    if args.frame_cap is not None and r.get("ok"):
        pass  # cap applied only if we extend runner; skip for now

    if r.get("ok"):
        print("OK", r.get("output_path"))
        return 0
    print("FAIL", r.get("error"), r.get("message"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
