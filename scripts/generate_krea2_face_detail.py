#!/usr/bin/env python3
"""Face detailer pass on an existing still (Krea2 + Impact FaceDetailer).

  python scripts/generate_krea2_face_detail.py -i still.png -o face_fixed.png --seed 42
  python scripts/generate_krea2_face_detail.py -i still.png -o out.png --denoise 0.35 -p "sharp eyes"

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
PRESET = "krea2_face_detail_v70"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 FaceDetailer post-pass")
    p.add_argument("--image", "-i", required=True, help="input still")
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--prompt",
        "-p",
        default="detailed face, sharp eyes, natural skin",
        help="detailer positive prompt",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--denoise",
        type=float,
        default=0.22,
        help="FaceDetailer denoise (default 0.22 subtle; 0.35+ can over- freckle)",
    )
    p.add_argument("--steps", type=int, default=14)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_face_detail")
    if not eng.get("ok"):
        print(f"[face_detail] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    from lib.output_policy import resolve_media_output

    out = resolve_media_output(args.output, default_name="krea2_face_detail_out.png")
    ports = {
        "input_image": args.image,
        "positive": args.prompt,
        "denoise": args.denoise,
        "steps": args.steps,
        "filename_prefix": "krea2_face_detail",
    }
    print(f"Krea2 face-detail preset={PRESET} denoise={args.denoise} out={out}")
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        seed=args.seed,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[face_detail] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[face_detail] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
