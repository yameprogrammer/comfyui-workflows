#!/usr/bin/env python3
"""
Build / cut highlights from an existing youtube_ingest package.

  python scripts/youtube_highlights.py -i dumps/yt_demo
  python scripts/youtube_highlights.py -i dumps/yt_demo --cut --max-clips 5
  python scripts/youtube_highlights.py -i dumps/yt_demo --rebuild --cut
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.youtube_ingest import (
    cut_highlights_from_package,
    load_package,
    propose_highlights,
    write_package,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="YouTube ref package → highlights / clips")
    p.add_argument("-i", "--package", required=True, help="Package dir from youtube_ingest")
    p.add_argument("--max-clips", type=int, default=5)
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="Recompute highlight windows from chapters/transcript",
    )
    p.add_argument(
        "--cut",
        action="store_true",
        help="ffmpeg-cut clips (downloads source.mp4 if missing)",
    )
    p.add_argument("--reencode", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if not os.path.isdir(args.package):
        print(f"FAIL package missing: {args.package}", file=sys.stderr)
        return 1

    if args.cut or args.rebuild:
        r = cut_highlights_from_package(
            args.package,
            max_clips=args.max_clips,
            reencode=args.reencode,
            rebuild_highlights=args.rebuild,
        )
    else:
        # write highlights only
        try:
            pkg = load_package(args.package)
        except Exception as e:
            print(f"FAIL {e}", file=sys.stderr)
            return 1
        hl = propose_highlights(
            pkg["meta"], pkg["segments"], max_clips=args.max_clips
        )
        write_package(
            args.package,
            meta=pkg["meta"],
            segments=pkg["segments"],
            highlights=hl,
        )
        r = {
            "ok": True,
            "package_dir": args.package,
            "highlights": hl,
            "clips": [],
        }

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    else:
        if not r.get("ok"):
            print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
            return 1
        print(f"OK package={r.get('package_dir')}")
        print(f"  highlights={len(r.get('highlights') or [])}")
        for h in r.get("highlights") or []:
            print(
                f"    {h.get('id')}  {h.get('start')}-{h.get('end')}s  "
                f"{(h.get('label') or '')[:60]}"
            )
        if r.get("clips"):
            print(f"  clips={len(r['clips'])}")
            for c in r["clips"]:
                print(f"    {c}")
        elif args.cut:
            print("  (no clips written — check media download / ffmpeg)")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
