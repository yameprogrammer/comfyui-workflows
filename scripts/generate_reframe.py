#!/usr/bin/env python3
"""
Shot-size reframe (CAMERA/TRANSFORM shelf) — pure geometry crop/zoom.

No Comfy required for default path. Use when you need wide/MCU/CU variants
of one still without regenerating identity.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.reframe import list_shot_sizes, reframe_image, reframe_pack


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Reframe still by shot size (center/upper-biased crop). No Comfy."
    )
    p.add_argument("--input", "-i", default=None)
    p.add_argument("--output", "-o", default=None, help="Single output path")
    p.add_argument(
        "--size",
        "-s",
        default="medium",
        help=f"Shot size: {', '.join(list_shot_sizes())}",
    )
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument(
        "--pack-dir",
        default=None,
        help="Write several sizes into a folder (default: wide,medium,mcu,cu)",
    )
    p.add_argument(
        "--sizes",
        default=None,
        help="Comma list for pack-dir (default wide,medium,medium_close,close_up)",
    )
    p.add_argument("--meta-out", default=None)
    p.add_argument("--list-sizes", action="store_true")
    args = p.parse_args(argv)

    if args.list_sizes:
        for s in list_shot_sizes():
            print(s)
        return 0

    if not args.input:
        p.error("--input/-i required")

    if args.pack_dir:
        sizes = (
            [x.strip() for x in args.sizes.split(",") if x.strip()]
            if args.sizes
            else None
        )
        r = reframe_pack(
            args.input,
            args.pack_dir,
            sizes=sizes,
            width=args.width,
            height=args.height,
        )
    else:
        if not args.output:
            p.error("--output required unless --pack-dir")
        r = reframe_image(
            args.input,
            args.output,
            shot_size=args.size,
            width=args.width,
            height=args.height,
            meta_out=args.meta_out,
        )

    if r.get("ok"):
        print(f"[reframe] ok → {r.get('output_path') or r.get('pack_dir')}")
        for a in (r.get("artifacts") or [])[:12]:
            print(f"  - {a.get('role')}: {a.get('path')}")
        return 0
    print(
        f"[reframe] FAIL {r.get('error')} {r.get('message')}",
        file=sys.stderr,
    )
    print(json.dumps({"ok": False, "error": r.get("error")}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
