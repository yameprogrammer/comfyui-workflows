#!/usr/bin/env python3
"""Image → Florence caption → optional Krea2 T2I (Lonecat v7 Img Prompt path).

  # Caption only
  python scripts/generate_krea2_img_prompt.py -i ref.png --caption-only

  # Caption then generate still
  python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png --seed 42
  python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png --extra "cinematic night, neon"

Requires Florence2 custom nodes. Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.krea2_img_prompt import caption_image, caption_then_krea


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Florence caption → Krea2 T2I")
    p.add_argument("--image", "-i", required=True, help="reference image to caption")
    p.add_argument("--output", "-o", default=None, help="output still (omit with --caption-only)")
    p.add_argument(
        "--caption-only",
        action="store_true",
        help="print Florence caption only (no T2I)",
    )
    p.add_argument(
        "--extra",
        default="",
        help="text appended after caption for T2I (direction / style notes)",
    )
    p.add_argument(
        "--task",
        default="detailed_caption",
        choices=(
            "caption",
            "detailed_caption",
            "more_detailed_caption",
            "region_caption",
        ),
        help="Florence2 task (default detailed_caption)",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=576)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    if args.caption_only:
        r = caption_image(
            args.image,
            task=args.task,
            seed=args.seed,
            server_address=args.server,
            timeout_sec=min(300.0, float(args.timeout)),
        )
        if not r.get("ok"):
            print(f"[img_prompt] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
            return 1
        print(r.get("caption"))
        return 0

    if not args.output:
        p.error("--output/-o required unless --caption-only")

    r = caption_then_krea(
        args.image,
        output_path=args.output,
        extra_prompt=args.extra,
        task=args.task,
        seed=args.seed,
        width=args.width,
        height=args.height,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(f"[img_prompt] FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        if r.get("caption"):
            print(f"[img_prompt] caption was: {r.get('caption')}", file=sys.stderr)
        return 1
    print(f"[img_prompt] caption: {r.get('caption')}")
    print(f"[img_prompt] prompt:  {r.get('prompt_used')}")
    print(f"[img_prompt] ok → {r.get('output_path')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
