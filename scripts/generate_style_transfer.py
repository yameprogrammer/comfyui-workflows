#!/usr/bin/env python3
"""
Style transfer / restyle stills (TRANSFORM shelf).

Modes:
  ref     — content image + style reference image (Qwen multi-image edit)
  preset  — named style dialect (anime, oil_paint, noir, …)
  look    — looks/<id> positive_core as style dialect

Research: docs/style_transfer_research.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.style_transfer import (
    ENGINES,
    MODES,
    format_styles_help,
    list_style_ids,
    run_style_transfer,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Restyle a still while keeping content/identity. "
            "Default engine=qwen (instruction edit). mode=ref needs --style-image."
        )
    )
    p.add_argument("--input", "-i", default=None, help="Content / subject image")
    p.add_argument("--output", "-o", default=None, help="Output path")
    p.add_argument(
        "--mode",
        choices=list(MODES),
        default="preset",
        help="ref | preset | look (default preset)",
    )
    p.add_argument(
        "--style",
        "-s",
        default=None,
        help=f"Named style for mode=preset: {', '.join(list_style_ids()[:8])}…",
    )
    p.add_argument(
        "--style-image",
        default=None,
        help="Style reference image for mode=ref",
    )
    p.add_argument(
        "--look-id",
        default=None,
        help="looks/<id> for mode=look",
    )
    p.add_argument(
        "--engine",
        choices=list(ENGINES),
        default="qwen",
        help="qwen (default) | i2i (Lonecat soft restyle; not for ref)",
    )
    p.add_argument(
        "--strength",
        choices=["soft", "medium", "hard"],
        default="medium",
        help="Stylization intensity (default medium)",
    )
    p.add_argument(
        "--extra",
        "-p",
        default="",
        help="Extra style direction (optional)",
    )
    p.add_argument(
        "--no-identity",
        action="store_true",
        help="Do not emphasize face/identity lock in instruction",
    )
    p.add_argument("--denoise", "-d", type=float, default=None, help="I2I denoise only")
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--meta-out", default=None)
    p.add_argument(
        "--no-lightning",
        action="store_true",
        help="Qwen quality path (slower)",
    )
    p.add_argument("--list-styles", action="store_true")
    args = p.parse_args(argv)

    if args.list_styles:
        print(format_styles_help())
        return 0

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required")

    r = run_style_transfer(
        content_image=args.input,
        output_path=args.output,
        mode=args.mode,
        style=args.style,
        style_image=args.style_image,
        look_id=args.look_id,
        engine=args.engine,
        strength=args.strength,
        extra=args.extra or "",
        preserve_identity=not args.no_identity,
        denoise=args.denoise,
        model_type=args.model,
        seed=args.seed,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        no_lightning=args.no_lightning,
    )

    if r.get("ok"):
        print(f"[style_transfer] ok mode={args.mode} → {r.get('output_path')}")
        st = r.get("style_transfer") or {}
        if st:
            print(f"  style_meta={st}")
        return 0
    print(
        f"[style_transfer] FAIL {r.get('error')} {r.get('message')}",
        file=sys.stderr,
    )
    print(
        json.dumps(
            {"ok": False, "error": r.get("error"), "message": r.get("message")},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
