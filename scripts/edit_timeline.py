#!/usr/bin/env python3
"""Create / validate edit_timeline.v1 JSON.

  python scripts/edit_timeline.py init --fps 24 --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"
  python scripts/edit_timeline.py from-clips -i a.mp4 -i b.mp4 --xfade 0.25 -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"
  python scripts/edit_timeline.py validate --timeline "%AGENT_WORKSPACE%/edits/s01/timeline.json"

Guide: workflows/human/edit/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import fail_result, ok_result
from lib.edit_timeline import (
    empty_timeline,
    from_clips,
    load_timeline,
    save_timeline,
    timeline_duration,
)
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="edit_timeline.v1 생성·검증")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--fps", type=int, default=24)
    p_init.add_argument("--width", type=int, default=1920)
    p_init.add_argument("--height", type=int, default=1080)
    p_init.add_argument("--output", "-o", required=True)
    p_init.add_argument("--json", action="store_true")

    p_fc = sub.add_parser("from-clips")
    p_fc.add_argument("--input", "-i", action="append", default=[], dest="inputs")
    p_fc.add_argument("--xfade", type=float, default=0.0)
    p_fc.add_argument("--width", type=int, default=1920)
    p_fc.add_argument("--height", type=int, default=1080)
    p_fc.add_argument("--fps", type=int, default=24)
    p_fc.add_argument("--output", "-o", required=True)
    p_fc.add_argument("--json", action="store_true")

    p_val = sub.add_parser("validate")
    p_val.add_argument("--timeline", required=True)
    p_val.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    try:
        if args.cmd in ("init", "from-clips"):
            die_if_toolbox(args.output)
        if args.cmd == "init":
            tl = empty_timeline(fps=args.fps, width=args.width, height=args.height)
            path = save_timeline(tl, args.output)
            res = ok_result(tool="edit_timeline", path=path, duration=0.0)
        elif args.cmd == "from-clips":
            if not args.inputs:
                p_fc.error("provide at least one -i clip")
            tl = from_clips(
                args.inputs,
                xfade=args.xfade,
                width=args.width,
                height=args.height,
                fps=args.fps,
            )
            path = save_timeline(tl, args.output)
            res = ok_result(
                tool="edit_timeline",
                path=path,
                duration=timeline_duration(tl),
                clips=len(tl["clips"]),
            )
        else:
            tl = load_timeline(args.timeline)
            res = ok_result(
                tool="edit_timeline",
                path=os_abspath(args.timeline),
                duration=timeline_duration(tl),
                clips=len(tl["clips"]),
            )
    except SystemExit as e:
        return int(e.code or 14)
    except Exception as e:
        res = fail_result(error="TIMELINE_INVALID", message=str(e), tool="edit_timeline")
        print(json.dumps(res, indent=2, ensure_ascii=False) if getattr(args, "json", False) else f"[ERROR] {e}", file=sys.stderr if not getattr(args, "json", False) else sys.stdout)
        if getattr(args, "json", False) and res.get("ok") is False:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        return 1

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] timeline → {res.get('path')} duration={res.get('duration')}")
    return 0


def os_abspath(p: str) -> str:
    import os

    return os.path.abspath(p)


if __name__ == "__main__":
    sys.exit(main())
