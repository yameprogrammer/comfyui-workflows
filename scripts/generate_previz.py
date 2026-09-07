#!/usr/bin/env python3
"""Block-geometry previz plate via Blender MCP, then feed H3 --ref-video.

Requires Blender running with MCP addon (default 127.0.0.1:9876, Allow Online Access).

  python scripts/generate_previz.py --probe
  python scripts/generate_previz.py --list-presets
  python scripts/generate_previz.py --preset corridor_follow -o plate.mp4
  python scripts/generate_previz.py --from-scene -o plate.mp4
  python scripts/generate_previz.py --exec-file build.py -o plate.mp4

  python scripts/generate_minimax_h3.py --task r2v -i hero.png --ref-video plate.mp4 \\
      --profile work --prompt-file prompt.txt -o clip.mp4

Guide: workflows/human/camera_previz/AGENT_GUIDE.md
Skill: skills/camera-previz/SKILL.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys
from pathlib import Path

from lib.blender_mcp import DEFAULT_HOST, DEFAULT_PORT, probe_blender
from lib.previz_blender import (
    DEFAULT_SECONDS,
    MAX_SECONDS,
    exec_then_render,
    h3_r2v_prompt,
    list_presets,
    render_open_scene,
    render_previz,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Blender MCP previz plate (block + camera path → mp4)"
    )
    p.add_argument("--output", "-o", default=None, help="output .mp4 path")
    p.add_argument(
        "--preset",
        default=None,
        help="corridor_follow | push_in | orbit | side_track (wipes the scene)",
    )
    p.add_argument(
        "--from-scene",
        action="store_true",
        help="playblast the live Blender scene (does not wipe)",
    )
    p.add_argument(
        "--exec-file",
        default=None,
        help="run this .py as bpy in Blender, then playblast (does not wipe first)",
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=None,
        help=f"length 1–{MAX_SECONDS:.0f}s at 24fps (preset default {DEFAULT_SECONDS:.0f}; "
        "--from-scene uses the scene range if omitted)",
    )
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--probe", action="store_true", help="check Blender MCP only")
    p.add_argument("--list-presets", action="store_true")
    p.add_argument(
        "--hero",
        choices=("character", "object"),
        default="character",
        help="stock H3 R2V prompt: person still vs object still",
    )
    p.add_argument(
        "--write-h3-prompt",
        default=None,
        help="write the stock H3 R2V V2V prompt to this .txt",
    )
    args = p.parse_args(argv)

    if args.list_presets:
        print("=== previz presets ===\n")
        for k, summary in list_presets().items():
            print(f"  {k}: {summary}")
        print("\nCustom shot: build in Blender (MCP bpy), then --from-scene")
        print("  or --exec-file build.py -o plate.mp4")
        return 0

    if args.probe:
        r = probe_blender(host=args.host, port=args.port)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    if args.write_h3_prompt:
        dest = Path(args.write_h3_prompt)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(h3_r2v_prompt(args.hero), encoding="utf-8")
        print(f"H3 prompt ({args.hero}) → {dest}")
        if not args.output:
            return 0

    if not args.output:
        p.error("--output/-o required (unless --probe / --list-presets / --write-h3-prompt)")

    modes = sum(
        [
            bool(args.preset),
            bool(args.from_scene),
            bool(args.exec_file),
        ]
    )
    if modes == 0:
        p.error("choose --preset, --from-scene, or --exec-file")
    if modes > 1:
        p.error("use only one of --preset, --from-scene, --exec-file")

    seconds = DEFAULT_SECONDS if args.seconds is None and args.preset else args.seconds
    common = dict(
        output_mp4=str(args.output),
        width=int(args.width),
        height=int(args.height),
        host=args.host,
        port=args.port,
        timeout_sec=float(args.timeout),
    )

    if args.preset:
        result = render_previz(preset=str(args.preset), seconds=float(seconds), **common)
    elif args.exec_file:
        path = Path(args.exec_file)
        if not path.is_file():
            print(f"[generate_previz] FAIL MISSING_FILE: {path}", file=sys.stderr)
            return 1
        code = path.read_text(encoding="utf-8")
        result = exec_then_render(code=code, seconds=seconds, **common)
    else:
        result = render_open_scene(seconds=seconds, **common)

    if not result.get("ok"):
        print(
            f"[generate_previz] FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[generate_previz] ok → {result.get('output')}")
    extra = ""
    if result.get("camera"):
        extra = f" camera={result.get('camera')} objects={result.get('objects')}"
    print(
        f"  preset={result.get('preset')} frames={result.get('frames')} "
        f"seconds={result.get('seconds'):.2f} bytes={result.get('bytes')}{extra}"
    )
    ident = "hero.png" if args.hero == "character" else "object.png"
    print(
        "Next: python scripts/generate_minimax_h3.py --task r2v "
        f"-i {ident} --ref-video "
        f"{result.get('output')} --profile work -o clip.mp4"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
