#!/usr/bin/env python3
"""
Idle motion + optional seamless-ish loop (MOTION shelf).

Modes:
  idle      — subtle life I2V only (single play)
  pingpong  — I2V + reverse (reliable seamless loop)  [default]
  roundtrip — I2V + FLF return to start still + concat

  python scripts/generate_idle_loop.py -i key.png -o loop.mp4 --mode pingpong
  python scripts/generate_idle_loop.py --list-modes
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.idle_loop import DEFAULT_MOTION_PRESET, MODES, run_idle_loop
from lib.motion_presets import format_motion_presets_help
from lib.prompt_assembly import load_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Idle micro-motion I2V and optional loop packaging (Comfy + ffmpeg). "
            "Default mode=pingpong for seamless reverse loop."
        )
    )
    p.add_argument("--input", "-i", default=None, help="Still / keyframe")
    p.add_argument("--output", "-o", default=None, help="Output mp4")
    p.add_argument(
        "--mode",
        choices=list(MODES),
        default="pingpong",
        help="idle | pingpong (default) | roundtrip",
    )
    p.add_argument(
        "--list-modes",
        action="store_true",
        help="Explain modes and exit",
    )
    p.add_argument(
        "--motion-preset",
        default=DEFAULT_MOTION_PRESET,
        help=f"Base I2V motion preset (default {DEFAULT_MOTION_PRESET})",
    )
    p.add_argument(
        "--list-motion-presets",
        action="store_true",
        help="Same as generate_camera_move --list-presets",
    )
    p.add_argument("--extra", "-p", default="", help="Extra subject micro-action")
    p.add_argument("--extra-file", default=None)
    p.add_argument("--frames", type=int, default=49, help="Forward I2V frames")
    p.add_argument("--fps", type=int, default=16)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--backend", default=None, help="I2V backend for forward clip")
    p.add_argument(
        "--flf-backend",
        default="ltx23_aio_flf",
        help="FLF backend for roundtrip return (default ltx23_aio_flf)",
    )
    p.add_argument("--flf-frames", type=int, default=None, help="Return leg frames")
    p.add_argument("--format", dest="format_id", default=None)
    p.add_argument("--work-preset", default=None)
    p.add_argument(
        "--profile",
        choices=["preview", "deliver", "quality"],
        default="deliver",
    )
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--work-dir", default=None, help="Keep intermediate clips here")
    args = p.parse_args(argv)

    if args.list_modes:
        print(
            """modes:
  idle       Single-play subtle motion (motion_preset, default idle)
  pingpong   Forward I2V + reverse append — seamless for loop playback (default)
  roundtrip  Forward I2V + FLF last→start still + concat — forward loop (possible seam)

Requires: Comfy for I2V/FLF; ffmpeg on PATH for pingpong/roundtrip.
"""
        )
        return 0

    if args.list_motion_presets:
        print(format_motion_presets_help())
        return 0

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required")

    extra = load_text(args.extra_file) if args.extra_file else (args.extra or "")

    r = run_idle_loop(
        input_image=args.input,
        output_path=args.output,
        mode=args.mode,
        motion_preset=args.motion_preset,
        extra=extra,
        frames=args.frames,
        fps=args.fps,
        seed=args.seed,
        backend=args.backend,
        format_id=args.format_id,
        work_preset=args.work_preset,
        profile=args.profile,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        work_dir=args.work_dir,
        flf_backend=args.flf_backend,
        flf_frames=args.flf_frames,
    )

    if r.get("ok"):
        print(f"[idle_loop] ok mode={r.get('mode')} loop_kind={r.get('loop_kind')}")
        print(f"[idle_loop] → {r.get('output_path')}")
        if r.get("meta_path"):
            print(f"[idle_loop] meta → {r.get('meta_path')}")
        return 0
    print(
        f"[idle_loop] FAIL {r.get('error')} {r.get('message')}",
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
