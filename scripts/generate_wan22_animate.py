#!/usr/bin/env python3
"""
Wan2.2 Animate dance/motion retarget (MOTION shelf).

Character still + RGB reference video → same choreography, keep character look.
Uses pose + face preprocess + CLIP ref + face_strength (validated 2026-08-02).

  python scripts/generate_wan22_animate.py -i character.png -v dance.mp4 -o out.mp4
  python scripts/generate_wan22_animate.py -i char.png -v ref.mp4 -o out.mp4 --no-headroom

Guide: workflows/human/wan22_animate_dance/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.wan22_animate import (
    DEFAULT_BLOCK_SWAP,
    DEFAULT_FACE_STRENGTH,
    DEFAULT_FRAMES,
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_POSE_STRENGTH,
    DEFAULT_STEPS,
    DEFAULT_WIDTH,
    generate_wan22_animate,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Wan2.2 Animate: retarget RGB dance/ref motion onto a character still. "
            "Better cross-cast identity than LTX V2V or Fun Control pose."
        )
    )
    p.add_argument("--input", "-i", required=True, help="Character / identity full-body still")
    p.add_argument("--video", "-v", required=True, help="RGB dance / motion reference video")
    p.add_argument("--output", "-o", required=True, help="Output mp4")
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--frames", type=int, default=DEFAULT_FRAMES, help="Frame count (prefer 4n+1)")
    p.add_argument("--fps", type=float, default=DEFAULT_FPS)
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--shift", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--pose-strength", type=float, default=DEFAULT_POSE_STRENGTH)
    p.add_argument(
        "--face-strength",
        type=float,
        default=DEFAULT_FACE_STRENGTH,
        help="Face lock strength (1.2–1.5 recommended)",
    )
    p.add_argument("--block-swap", type=int, default=DEFAULT_BLOCK_SWAP)
    p.add_argument(
        "--hook-sec",
        type=float,
        default=3.8,
        help="Trim ref video length when --headroom (default 3.8)",
    )
    p.add_argument(
        "--headroom",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pad still/video for headroom (default on; reduces head crop)",
    )
    p.add_argument(
        "--relight",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply WanAnimate relight LoRA (default on)",
    )
    p.add_argument("--prompt", "-p", default="", help="Optional positive motion/look notes")
    p.add_argument("--negative", default="")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--work-dir", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    r = generate_wan22_animate(
        character_image=args.input,
        reference_video=args.video,
        output_path=args.output,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        fps=args.fps,
        steps=args.steps,
        cfg=args.cfg,
        shift=args.shift,
        seed=args.seed,
        pose_strength=args.pose_strength,
        face_strength=args.face_strength,
        block_swap=args.block_swap,
        prompt=args.prompt or "",
        negative=args.negative or "",
        headroom=bool(args.headroom),
        hook_sec=args.hook_sec,
        use_relight=bool(args.relight),
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=args.dry_run,
        work_dir=args.work_dir,
    )

    if r.get("ok"):
        print(f"[wan22_animate] ok → {r.get('output_path') or '(dry-run)'}")
        if r.get("elapsed_sec") is not None:
            print(f"[wan22_animate] elapsed={r.get('elapsed_sec')}s")
        if r.get("meta_path"):
            print(f"[wan22_animate] meta → {r.get('meta_path')}")
        return 0

    print(
        f"[wan22_animate] FAIL {r.get('error')} {r.get('message')}",
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
