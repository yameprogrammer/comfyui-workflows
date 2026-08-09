#!/usr/bin/env python3
"""18+ anatomy region detailer (Impact SEGS + Krea2).

**Adult only.** Not for minors / CSAM.

  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region penis --i-am-18
  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region vagina --i-am-18

Regions map to ultralytics bbox models under models/ultralytics.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

FAMILY = "krea2_still"
PRESET = "krea2_anatomy_detail_v70"

REGION_MODELS = {
    "penis": "bbox/penis.pt",
    "vagina": "bbox/vagina-v4.1.pt",
    # breast is segm — not wired to BboxDetectorSEGS; document skip
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="18+ anatomy detailer (Krea2)")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--region",
        choices=tuple(REGION_MODELS.keys()),
        required=True,
        help="anatomy region detector",
    )
    p.add_argument(
        "--i-am-18",
        action="store_true",
        required=True,
        help="required adult confirmation flag",
    )
    p.add_argument("--prompt", "-p", default="detailed anatomy, natural skin, photoreal")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=0.28)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    if not args.i_am_18:
        print("[anatomy] refuse: pass --i-am-18 for adult content", file=sys.stderr)
        return 2

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_anatomy_detail")
    if not eng.get("ok"):
        print(f"[anatomy] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    det = REGION_MODELS[args.region]
    out = args.output or f"dumps/krea2_anatomy_{args.region}.png"
    ports = {
        "input_image": args.image,
        "positive": args.prompt,
        "denoise": args.denoise,
        "detector_model": det,
        "filename_prefix": f"krea2_anatomy_{args.region}",
    }
    print(f"anatomy-detail region={args.region} model={det} denoise={args.denoise}")
    r = run_workflow_api(
        PRESET,
        ports=ports,
        output_path=out,
        seed=args.seed,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[anatomy] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"[anatomy] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
