#!/usr/bin/env python3
"""
Dance / reference-motion one-shot tool (MOTION shelf) — v1.

  # Ref video drives body timing (V2V motion) + character still for identity
  python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o out.mp4

  # No ref video: I2V with dance style dialect
  python scripts/generate_dance_ref.py -i hero.png --mode i2v --style kpop -o out.mp4

See docs/dance_challenge_pipeline_design.md (full challenge pipe is separate).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.dance_ref import (
    MODES,
    format_dance_styles_help,
    list_dance_styles,
    run_dance_ref,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Dance / ref-motion: character still + optional dance video → clip. "
            "Default mode=ref uses Comfy LTX V2V intent=motion."
        )
    )
    p.add_argument("--input", "-i", default=None, help="Character / identity still")
    p.add_argument("--output", "-o", default=None, help="Output mp4")
    p.add_argument(
        "--reference",
        "-v",
        dest="reference",
        default=None,
        help="Reference dance / motion video (required for mode=ref)",
    )
    p.add_argument(
        "--mode",
        choices=list(MODES),
        default="ref",
        help="ref=V2V from video (default) | i2v=text dance style only",
    )
    p.add_argument(
        "--style",
        default="general",
        help=f"Dance flavor: {', '.join(list_dance_styles())}",
    )
    p.add_argument(
        "--list-styles",
        action="store_true",
        help="List i2v dance styles and exit",
    )
    p.add_argument("--extra", "-p", default="", help="Extra motion notes")
    p.add_argument("--trim-start", type=float, default=0.0, help="Ref video start sec")
    p.add_argument(
        "--hook-sec",
        type=float,
        default=None,
        help="Use only first N seconds of ref (or i2v duration target)",
    )
    p.add_argument("--strength", type=float, default=None, help="V2V strength guide 0–1")
    p.add_argument("--width", type=int, default=544)
    p.add_argument("--height", type=int, default=960)
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--backend", default=None, help="V2V backend override")
    p.add_argument("--i2v-backend", default=None, help="I2V backend when mode=i2v")
    p.add_argument("--audio", "-a", default=None, help="Optional audio for v2v_audio")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--work-dir", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.list_styles:
        print(format_dance_styles_help())
        print("")
        print("modes: ref (needs -v) | i2v (style text only)")
        return 0

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required")
    if args.mode == "ref" and not args.reference:
        p.error("mode=ref requires --reference/-v dance video")

    r = run_dance_ref(
        character_image=args.input,
        output_path=args.output,
        mode=args.mode,
        reference_video=args.reference,
        dance_style=args.style,
        extra=args.extra or "",
        trim_start_sec=args.trim_start,
        hook_sec=args.hook_sec,
        strength=args.strength,
        width=args.width,
        height=args.height,
        fps=args.fps,
        seed=args.seed,
        backend=args.backend,
        i2v_backend=args.i2v_backend,
        audio_path=args.audio,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=args.dry_run,
        work_dir=args.work_dir,
    )

    if r.get("ok"):
        print(f"[dance_ref] ok mode={r.get('mode')} → {r.get('output_path')}")
        if r.get("dry_run"):
            print("[dance_ref] dry-run (no Comfy queue or partial)")
        if r.get("meta_path"):
            print(f"[dance_ref] meta → {r.get('meta_path')}")
        return 0
    print(
        f"[dance_ref] FAIL {r.get('error')} {r.get('message')}",
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
