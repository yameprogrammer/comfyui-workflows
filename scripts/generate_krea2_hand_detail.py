#!/usr/bin/env python3
"""Hand detailer pass (Impact SEGS + DetailerForEach on Krea2).

  python scripts/generate_krea2_hand_detail.py -i still_with_hands.png -o hands.png --seed 42
  python scripts/generate_krea2_hand_detail.py -i still.png -o out.png --denoise 0.28 --threshold 0.3

Requires visible hands in frame + bbox/hand_yolov8s.pt.
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
PRESET = "krea2_hand_detail_v70"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 hand DetailerForEach post-pass")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--prompt",
        "-p",
        default="detailed hands, correct fingers, natural skin",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=0.28)
    p.add_argument("--steps", type=int, default=12)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="hand bbox detection threshold",
    )
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_hand_detail")
    if not eng.get("ok"):
        print(f"[hand_detail] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    out = args.output or "dumps/krea2_hand_detail_out.png"
    ports = {
        "input_image": args.image,
        "positive": args.prompt,
        "denoise": args.denoise,
        "steps": args.steps,
        "threshold": args.threshold,
        "filename_prefix": "krea2_hand_detail",
    }
    print(f"Krea2 hand-detail preset={PRESET} denoise={args.denoise} thr={args.threshold}")
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        seed=args.seed,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[hand_detail] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[hand_detail] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
