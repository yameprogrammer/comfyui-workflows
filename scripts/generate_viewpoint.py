#!/usr/bin/env python3
"""
Depth / viewpoint exaggeration (CAMERA shelf) — Comfy / Qwen multi-angle.

Presets: high_angle, low_angle, birds_eye, worms_eye, wide_establishing, tight_hero, …
Custom: --h --v --zoom
Engine: angle (default multi-angle LoRA) | edit (instruction extreme)
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.viewpoint import (
    ENGINES,
    format_viewpoints_help,
    list_viewpoint_ids,
    run_viewpoint,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Change camera height / pitch / distance on a still (Comfy Qwen multi-angle). "
            "Use --preset or custom --h/--v/--zoom."
        )
    )
    p.add_argument("--input", "-i", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--preset",
        default=None,
        help=f"Viewpoint intent: {', '.join(list_viewpoint_ids()[:6])}…",
    )
    p.add_argument(
        "--list-presets",
        action="store_true",
        help="Print viewpoint presets and exit",
    )
    p.add_argument(
        "--engine",
        choices=list(ENGINES),
        default="angle",
        help="angle=Qwen multi-angle ports (default); edit=instruction restyle",
    )
    p.add_argument(
        "--strength",
        choices=["soft", "medium", "hard"],
        default="medium",
        help="Exaggerate elevation / distance (default medium)",
    )
    p.add_argument("--h", dest="horizontal", type=int, default=None, help="Azimuth degrees")
    p.add_argument(
        "--v",
        dest="vertical",
        type=int,
        default=None,
        help="Elevation (+ high/down, - low/up)",
    )
    p.add_argument("--zoom", type=float, default=None, help="Distance port (higher≈closer)")
    p.add_argument("--extra", "-p", default="", help="Extra camera/subject direction")
    p.add_argument(
        "--no-identity",
        action="store_true",
        help="Relax identity lock (edit engine mainly)",
    )
    p.add_argument("--angles-strength", type=float, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--meta-out", default=None)
    args = p.parse_args(argv)

    if args.list_presets:
        print(format_viewpoints_help())
        return 0

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required")
    if not args.preset and args.horizontal is None and args.vertical is None and args.zoom is None:
        p.error("Need --preset or custom --h/--v/--zoom")

    r = run_viewpoint(
        input_image=args.input,
        output_path=args.output,
        preset=args.preset,
        engine=args.engine,
        strength=args.strength,
        horizontal_angle=args.horizontal,
        vertical_angle=args.vertical,
        zoom=args.zoom,
        extra=args.extra or "",
        preserve_identity=not args.no_identity,
        seed=args.seed,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        angles_strength=args.angles_strength,
    )

    if r.get("ok"):
        print(f"[viewpoint] ok → {r.get('output_path')}")
        print(f"  meta_keys={list((r.get('viewpoint') or {}).keys())}")
        return 0
    print(f"[viewpoint] FAIL {r.get('error')} {r.get('message')}", file=sys.stderr)
    print(json.dumps({"ok": False, "error": r.get("error"), "message": r.get("message")}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
