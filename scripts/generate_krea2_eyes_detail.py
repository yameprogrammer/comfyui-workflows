#!/usr/bin/env python3
"""Eyes detailer (Lonecat v7 # ::Eyes) — SAM Smart Inpainter by default.

  python scripts/generate_krea2_eyes_detail.py -i still.png -o eyes.png
  python scripts/generate_krea2_eyes_detail.py -i still.png -o eyes.png --engine yolo
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from generate_krea2_region_detail import main as region_main


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 eyes detailer")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--engine",
        choices=("sam", "yolo", "paired"),
        default="sam",
        help="sam=SAM3 UI path · yolo=Eyeful individual · paired=Eyeful paired",
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=None)
    args = p.parse_args(argv)

    region = {"sam": "eyes", "yolo": "eyes_yolo", "paired": "eyes_paired"}[args.engine]
    fwd = ["-i", args.image, "--region", region]
    if args.output:
        fwd += ["-o", args.output]
    if args.prompt:
        fwd += ["-p", args.prompt]
    if args.seed is not None:
        fwd += ["--seed", str(args.seed)]
    if args.denoise is not None:
        fwd += ["--denoise", str(args.denoise)]
    if args.timeout is not None:
        fwd += ["--timeout", str(args.timeout)]
    if args.server:
        fwd += ["--server", args.server]
    return region_main(fwd)


if __name__ == "__main__":
    raise SystemExit(main())
