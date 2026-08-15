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
from lib.edit_look import list_look_parts, list_looks
from lib.edit_motion import expand_stagger, list_motion_parts, load_glyphs
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

    p_lm = sub.add_parser("list-motions")
    p_lm.add_argument("--json", action="store_true")

    p_ll = sub.add_parser("list-looks")
    p_ll.add_argument("--json", action="store_true")

    p_st = sub.add_parser("stagger")
    p_st.add_argument("--timeline", required=True)
    p_st.add_argument("--glyphs", required=True, help="*.glyphs.json from render_title --split glyphs")
    p_st.add_argument("--start", type=float, required=True)
    p_st.add_argument("--end", type=float, required=True)
    p_st.add_argument("--stagger", type=float, default=0.06)
    p_st.add_argument("--motion", default="pop")
    p_st.add_argument("--fade-in", type=float, default=None)
    p_st.add_argument("--fade-out", type=float, default=None)
    p_st.add_argument("--move", type=float, default=None)
    p_st.add_argument("--scale-from", type=float, default=None)
    p_st.add_argument("--scale-to", type=float, default=None)
    p_st.add_argument("--direction", default=None)
    p_st.add_argument("--distance", type=float, default=None)
    p_st.add_argument("--output", "-o", required=True)
    p_st.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "list-motions":
        parts = list_motion_parts()
        if args.json:
            print(json.dumps(parts, indent=2, ensure_ascii=False))
        else:
            print("shortcuts\t" + ", ".join(parts["shortcuts"]))
            print("parts\t" + ", ".join(parts["parts"]))
            print("directions\t" + ", ".join(parts["directions"]))
            for k, v in parts["units"].items():
                print(f"  {k}\t{v}")
        return 0

    if args.cmd == "list-looks":
        data = {"looks": list_looks(), "parts": list_look_parts()}
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for row in data["looks"]:
                print(f"{row['name']}\t{row['use']}")
            print("parts\t" + ", ".join(data["parts"]["parts"]))
        return 0

    try:
        if args.cmd in ("init", "from-clips", "stagger"):
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
        elif args.cmd == "stagger":
            tl = load_timeline(args.timeline)
            pack = load_glyphs(args.glyphs)
            added = expand_stagger(
                pack,
                start=args.start,
                end=args.end,
                stagger=args.stagger,
                motion=args.motion,
                fade_in=args.fade_in,
                fade_out=args.fade_out,
                move=args.move,
                scale_from=args.scale_from,
                scale_to=args.scale_to,
                direction=args.direction,
                distance=args.distance,
                id_prefix=f"g{len(tl.get('overlays') or [])}_",
            )
            tl.setdefault("overlays", []).extend(added)
            path = save_timeline(tl, args.output)
            res = ok_result(
                tool="edit_timeline",
                path=path,
                duration=timeline_duration(tl),
                overlays=len(tl["overlays"]),
                stagger=args.stagger,
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
