#!/usr/bin/env python3
"""Check Illustrious Standard/Advanced/Detailer models + Comfy nodes.

  python scripts/illustrious_check.py
  python scripts/illustrious_check.py --pack advanced
  python scripts/illustrious_check.py --pack detailer --json
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.illustrious_health import check_pack, format_report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Illustrious pack dependency health")
    p.add_argument(
        "--pack",
        choices=("all", "standard", "advanced", "detailer"),
        default="all",
    )
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    result = check_pack(args.pack, server=args.server)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
    # exit 1 only if core standard models missing
    core_ids = {
        "ckpt_fabricated",
        "face_yolo",
        "ImpactSwitch",
        "FaceDetailerPipe",
    }
    core_miss = [
        r for r in result.get("rows") or [] if r["id"] in core_ids and not r["ok"]
    ]
    return 1 if core_miss or not result.get("comfy_reachable") else 0


if __name__ == "__main__":
    raise SystemExit(main())
