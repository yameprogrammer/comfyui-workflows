#!/usr/bin/env python3
"""
Wan-Animate-2 motion transfer (MOTION shelf).

Character still + driving video → same performance, new background from prompt.
No pose/skeleton extract. Distinct from generate_wan22_animate (ViTPose path).

  python scripts/generate_wan_animate2.py -i character.png -v dance.mp4 -o out.mp4
  python scripts/generate_wan_animate2.py -i c.png -v d.mp4 -o o.mp4 --look "pink hair mech girl" --background "gray studio"

Guide: workflows/human/wan_animate2/AGENT_GUIDE.md
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.wan_animate2 import (
    DEFAULT_FRAMES,
    DEFAULT_HEIGHT,
    DEFAULT_POSE_STRENGTH,
    DEFAULT_REF_STRENGTH,
    DEFAULT_STEPS,
    DEFAULT_WIDTH,
    generate_wan_animate2,
    snap_wan_frames,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Wan-Animate-2: transfer driving-video motion onto a character still. "
            "No pose extract. Prompt controls look + background/camera."
        )
    )
    p.add_argument("--input", "-i", required=True, help="Character / identity still")
    p.add_argument("--video", "-v", required=True, help="Driving / dance RGB video")
    p.add_argument("--output", "-o", required=True, help="Output mp4 (caller project path)")
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument(
        "--frames",
        type=int,
        default=DEFAULT_FRAMES,
        help="Frame count (snapped to 4n+1, default 81)",
    )
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--shift", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--pose-strength", type=float, default=DEFAULT_POSE_STRENGTH)
    p.add_argument(
        "--ref-strength",
        type=float,
        default=DEFAULT_REF_STRENGTH,
        help="How tightly output attends to the still (identity)",
    )
    p.add_argument(
        "--prompt",
        "-p",
        default="",
        help="Full positive, or look text if --look omitted",
    )
    p.add_argument("--look", default="", help="Character appearance only (no motion words)")
    p.add_argument("--background", default="", help="Output set / lighting (generated, not from still)")
    p.add_argument(
        "--pose-prompt",
        default="",
        help="Motion description for the pose branch (default: a person dancing)",
    )
    p.add_argument("--negative", default="")
    p.add_argument(
        "--cache-device",
        choices=("cpu", "gpu"),
        default="cpu",
        help="WanAnimate2Cache store (cpu on 24GB)",
    )
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    frames = snap_wan_frames(args.frames)
    r = generate_wan_animate2(
        character_image=args.input,
        reference_video=args.video,
        output_path=args.output,
        width=args.width,
        height=args.height,
        num_frames=frames,
        steps=args.steps,
        cfg=args.cfg,
        shift=args.shift,
        seed=args.seed,
        pose_strength=args.pose_strength,
        reference_image_strength=args.ref_strength,
        prompt=args.prompt or "",
        look=args.look or "",
        background=args.background or "",
        pose_prompt=args.pose_prompt or "",
        negative=args.negative or "",
        cache_device=args.cache_device,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=bool(args.dry_run),
    )

    if r.get("ok"):
        print(f"[wan_animate2] ok → {r.get('output_path') or '(dry-run)'}")
        if r.get("elapsed_sec") is not None:
            print(f"[wan_animate2] elapsed={r.get('elapsed_sec')}s frames={frames}")
        if r.get("meta_path"):
            print(f"[wan_animate2] meta → {r.get('meta_path')}")
        return 0

    print(
        f"[wan_animate2] FAIL {r.get('error')} {r.get('message')}",
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
