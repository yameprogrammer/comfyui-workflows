#!/usr/bin/env python3
"""Grade / key a single clip (EDIT v3 look pass).

  python scripts/comp_shot.py --list-looks
  python scripts/comp_shot.py --look night -i clip.mp4 -o "%AGENT_WORKSPACE%/graded.mp4"
  python scripts/comp_shot.py --look punch --temperature -0.1 --saturation 1.2 -i clip.mp4 -o out.mp4
  python scripts/comp_shot.py --key-color green -i fg.mp4 -o keyed.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import fail_result, ok_result
from lib.edit_compile_ffmpeg import compile_ffmpeg
from lib.edit_look import compose_look, list_look_parts, list_looks
from lib.edit_timeline import from_clips
from lib.ffmpeg_util import probe_duration, run_ffmpeg
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="클립 룩/키 (부품 조립)")
    p.add_argument("--input", "-i", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--look", default=None, help="punch|night|warm|cool|soft|bleach|none")
    p.add_argument("--contrast", type=float, default=None)
    p.add_argument("--saturation", type=float, default=None)
    p.add_argument("--brightness", type=float, default=None)
    p.add_argument("--gamma", type=float, default=None)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--amount", type=float, default=None, help="0–1 look strength")
    p.add_argument("--lut", default=None)
    p.add_argument("--key-color", default=None)
    p.add_argument("--key-similarity", type=float, default=None)
    p.add_argument("--key-blend", type=float, default=None)
    p.add_argument("--key-background", default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--list-looks", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.list_looks:
        data = {"looks": list_looks(), "parts": list_look_parts()}
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for row in data["looks"]:
                print(f"{row['name']}\t{row['use']}\tc={row['contrast']}\ts={row['saturation']}\tt={row['temperature']}")
            print("parts\t" + ", ".join(data["parts"]["parts"]))
        return 0

    if not args.input or not args.output:
        p.error("--input and --output required (unless --list-looks)")
    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    look = {
        "name": args.look,
        "contrast": args.contrast,
        "saturation": args.saturation,
        "brightness": args.brightness,
        "gamma": args.gamma,
        "temperature": args.temperature,
        "amount": args.amount,
        "lut": args.lut,
    }
    look = {k: v for k, v in look.items() if v is not None}
    resolved = compose_look(look or None)
    w, h = args.width or 1920, args.height or 1080
    tl = from_clips([args.input], width=w, height=h, fps=args.fps)
    tl["look"] = resolved
    if args.key_color:
        key = {"color": args.key_color}
        if args.key_similarity is not None:
            key["similarity"] = args.key_similarity
        if args.key_blend is not None:
            key["blend"] = args.key_blend
        if args.key_background:
            key["background"] = args.key_background
        tl["clips"][0]["key"] = key

    try:
        spec = compile_ffmpeg(tl, args.output)
    except Exception as e:
        res = fail_result(error="LOOK_INVALID", message=str(e), tool="comp_shot")
        print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else f"[ERROR] {e}", file=sys.stderr)
        return 1
    ff = run_ffmpeg(spec["argv"], timeout_sec=3600)
    if not ff.get("ok"):
        res = fail_result(error="FFMPEG_FAILED", message=ff.get("message"), tool="comp_shot")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[FAILED] FFMPEG_FAILED {ff.get('message')}", file=sys.stderr)
        return 1
    res = ok_result(
        tool="comp_shot",
        path=args.output,
        look=resolved,
        duration=spec["duration"] or probe_duration(args.output),
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] look={resolved.get('name')} → {res['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
