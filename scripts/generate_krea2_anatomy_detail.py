#!/usr/bin/env python3
"""18+ anatomy region detailer — thin wrapper over generate_krea2_region_detail.

**Adult only.** Not for minors / CSAM.

  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region penis --i-am-18
  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region vagina --i-am-18
  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region breasts --i-am-18
  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region female_body --i-am-18
  python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region male_junk --i-am-18

Prefer the full region tool for Eyes/Spare:
  python scripts/generate_krea2_region_detail.py --list
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from generate_krea2_region_detail import main as region_main

# keep historical names + full nsfw set
ADULT_REGIONS = (
    "penis",
    "vagina",
    "vajayjay",
    "breasts",
    "female_body",
    "male_junk",
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="18+ anatomy detailer (Krea2) → region_detail")
    p.add_argument("--image", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--region", choices=ADULT_REGIONS, required=True)
    p.add_argument("--i-am-18", action="store_true", required=True)
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=None)
    args = p.parse_args(argv)

    if not args.i_am_18:
        print("[anatomy] refuse: pass --i-am-18 for adult content", file=sys.stderr)
        return 2

    # map vagina → vajayjay region id (same model)
    region = "vajayjay" if args.region == "vagina" else args.region
    fwd = ["-i", args.image, "--region", region, "--i-am-18"]
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
