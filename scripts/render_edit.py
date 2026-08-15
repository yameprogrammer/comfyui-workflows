#!/usr/bin/env python3
"""Render edit_timeline.v1 to a master mp4 (FFmpeg).

  python scripts/render_edit.py --timeline "%AGENT_WORKSPACE%/edits/s01/timeline.json" -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import fail_result, ok_result
from lib.edit_compile_ffmpeg import compile_ffmpeg
from lib.edit_timeline import load_timeline
from lib.ffmpeg_util import run_ffmpeg
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="타임라인 → 마스터 mp4")
    p.add_argument("--timeline", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--print-graph", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    try:
        tl = load_timeline(args.timeline)
        spec = compile_ffmpeg(tl, args.output, timeline_path=args.timeline)
    except FileNotFoundError as e:
        res = fail_result(error="CLIP_MISSING", message=str(e), tool="render_edit")
        print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else f"[FAILED] CLIP_MISSING {e}", file=sys.stderr if not args.json else sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        return 1
    except Exception as e:
        res = fail_result(error="TIMELINE_INVALID", message=str(e), tool="render_edit")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if args.print_graph:
        print(spec["graph"])
        if args.json:
            print(json.dumps({"ok": True, "graph": spec["graph"], "duration": spec["duration"]}, indent=2))
        return 0

    ff = run_ffmpeg(spec["argv"], timeout_sec=3600)
    if not ff.get("ok"):
        res = fail_result(error="FFMPEG_FAILED", message=ff.get("message"), tool="render_edit")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[FAILED] FFMPEG_FAILED {ff.get('message')}", file=sys.stderr)
        return 1
    res = ok_result(
        tool="render_edit",
        path=os_ab(args.output),
        duration=spec["duration"],
        graph=spec["graph"],
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] master → {res['path']} duration={res['duration']:.2f}s")
    return 0


def os_ab(p: str) -> str:
    import os

    return os.path.abspath(p)


if __name__ == "__main__":
    sys.exit(main())
