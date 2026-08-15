#!/usr/bin/env python3
"""Render a Hangul caption/title PNG from composable parts (presets are shortcuts).

  python scripts/render_title.py --list-parts
  python scripts/render_title.py --text "조금만 더" --layout caption --color cyan --size xl \\
    --bubble yellow --tilt -4 --y 0.82 --width 1080 --height 1920 -o cap.png
  python scripts/render_title.py --preset yt_hook --text "포기하지 마" --width 1080 --height 1920 -o cap.png
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.edit_fonts import list_fonts
from lib.edit_title import LAYOUTS, STYLES, list_parts, list_styles, render_title
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="타이틀/캡션 PNG — 부품 조립 (프리셋은 바로가기)")
    p.add_argument("--text", default=None)
    p.add_argument("--subtext", default="")
    p.add_argument("--preset", default=None, help=f"optional shortcut: {', '.join(list_styles())}")
    p.add_argument("--layout", default=None, help=f"{', '.join(LAYOUTS)}")
    p.add_argument("--color", default=None, help="#RRGGBB or yellow/white/red/cyan/…")
    p.add_argument("--outline", default=None, help="#RRGGBB or none")
    p.add_argument("--outline-width", type=int, default=None)
    p.add_argument("--size", default=None, help="sm|md|lg|xl|hook or px")
    p.add_argument("--weight", default=None, help="regular|bold")
    p.add_argument("--tilt", type=float, default=None, help="degrees, e.g. -4")
    p.add_argument("--box", default=None, help="plate color, or none")
    p.add_argument("--bubble", default=None, help="rounded plate color, or none")
    p.add_argument("--bar", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--react-color", default=None)
    p.add_argument("--x", type=float, default=None, help="0-1, text center X")
    p.add_argument("--y", type=float, default=None, help="0-1, text center Y")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--font", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--list-styles", action="store_true")
    p.add_argument("--list-parts", action="store_true")
    p.add_argument("--list-fonts", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.list_fonts:
        rows = list_fonts()
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            for row in rows:
                mark = "ok" if row["ready"] else "need-setup"
                print(f"{row['name']}\t{mark}\t{row['use']}\t{row['path'] or '-'}")
        return 0

    if args.list_parts:
        parts = list_parts()
        if args.json:
            print(json.dumps(parts, indent=2, ensure_ascii=False))
        else:
            print(f"layouts\t{', '.join(parts['layouts'])}")
            print(f"sizes\t{', '.join(parts['sizes'])}")
            print(f"colors\t{', '.join(parts['colors'])}")
            print(f"chrome\t{', '.join(parts['chrome'])}")
            print(f"place\t{', '.join(parts['place'])}  ({parts['place_note']})")
            print(f"fonts\t{', '.join(parts['fonts'])}  ({parts['font_note']})")
            print(f"presets\t{', '.join(parts['presets'])}  ({parts['preset_note']})")
        return 0

    if args.list_styles:
        for name, spec in STYLES.items():
            print(f"{name}\t{spec.get('size')}\t{spec.get('color')}\t{spec.get('layout')}")
        return 0

    if not args.text or not args.output:
        p.error("--text and --output required (unless --list-styles / --list-parts / --list-fonts)")
    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)
    res = render_title(
        args.text,
        args.output,
        preset=args.preset,
        width=args.width,
        height=args.height,
        subtext=args.subtext,
        font=args.font,
        color=args.color,
        outline=args.outline,
        outline_width=args.outline_width,
        size=args.size,
        tilt=args.tilt,
        layout=args.layout,
        weight=args.weight,
        box=args.box,
        bubble=args.bubble,
        bar=args.bar,
        react_color=args.react_color,
        x=args.x,
        y=args.y,
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res.get("ok"):
        print(f"[OK] title → {res.get('path')} preset={res.get('preset')}")
    else:
        print(f"[FAILED] {res.get('error')}: {res.get('message')}", file=sys.stderr)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
