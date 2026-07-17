#!/usr/bin/env python3
"""First–Last Frame to Video (FLF2V) via Wan2.2 agent API preset.

Thin wrapper around generate_i2v with end/last frame required.

  python scripts/generate_flf2v.py -i start.png --last end.png -p "slow push-in" -o out.mp4
  python scripts/generate_i2v.py -i start.png --last end.png ...   # equivalent
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from generate_i2v import generate_i2v
from lib.prompt_assembly import load_text
from lib.workflow_paths import resolve_workflow


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Wan2.2 FLF2V: start keyframe + end keyframe → bridge clip"
    )
    p.add_argument("--input", "-i", required=True, help="Start frame image")
    p.add_argument(
        "--last",
        "--end-image",
        dest="end_image",
        required=True,
        help="End/last frame image",
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", default="")
    p.add_argument("--negative-file", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--frames", type=int, default=49)
    p.add_argument("--fps", type=int, default=16)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--format", dest="format_id", default=None)
    p.add_argument("--preset", default=None)
    p.add_argument("--profile", default="deliver")
    p.add_argument(
        "--backend",
        default="ltx23_aio_flf",
        help="Quality default: ltx23_aio_flf (A/B 2026-07-17). Wan fallback: wan22_flf",
    )
    p.add_argument("--workflow", default=None)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    prompt = load_text(args.prompt_file) if args.prompt_file else (args.prompt or "")
    if not prompt:
        p.error("--prompt or --prompt-file required")
    negative = load_text(args.negative_file) if args.negative_file else args.negative

    wf = resolve_workflow(args.workflow) if args.workflow else None
    r = generate_i2v(
        input_image_path=args.input,
        end_image_path=args.end_image,
        prompt_text=prompt,
        negative_text=negative or "",
        output_filename=args.output,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        frame_rate=args.fps,
        backend=args.backend,
        format_id=args.format_id,
        preset=args.preset,
        workflow_path=wf,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        dry_run=bool(args.dry_run),
        profile=args.profile,
    )
    if r.get("ok"):
        print("OK", r.get("output_path") or r.get("message") or "flf2v")
        return 0
    print("FAIL", r.get("error"), r.get("message"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
