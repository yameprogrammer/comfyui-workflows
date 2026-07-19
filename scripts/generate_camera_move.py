#!/usr/bin/env python3
"""
Camera move / motion-intent I2V (MOTION shelf) — first-class wrapper.

Wraps generate_i2v + lib.motion_presets so agents pick camera intent by id
without hand-writing motion prose every time.

  python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4
  python scripts/generate_camera_move.py --list-presets
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from generate_i2v import DEFAULT_NEGATIVE, generate_i2v
from lib.comfy_client import write_meta
from lib.motion_presets import (
    compose_motion_prompt,
    format_motion_presets_help,
    resolve_motion_preset_id,
)
from lib.prompt_assembly import load_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Image-to-video with a camera/motion intent preset (Comfy I2V). "
            "Same backends as generate_i2v; preset is required unless listing."
        )
    )
    p.add_argument("--input", "-i", default=None, help="Keyframe / still path")
    p.add_argument("--output", "-o", default=None, help="Output mp4 path")
    p.add_argument(
        "--preset",
        "--motion-preset",
        dest="preset",
        default=None,
        help="Motion intent id: push_in, pan_left, idle, talk_gesture, …",
    )
    p.add_argument(
        "--list-presets",
        action="store_true",
        help="Print camera/motion presets and exit",
    )
    p.add_argument(
        "--extra",
        "-p",
        default=None,
        help="Optional extra action/scene motion (not face re-essay)",
    )
    p.add_argument("--extra-file", default=None, help="Extra prompt from file")
    p.add_argument("--negative", default=DEFAULT_NEGATIVE)
    p.add_argument("--negative-file", default=None)
    p.add_argument("--backend", default=None, help="I2V backend (default from video_backends.json)")
    p.add_argument("--format", dest="format_id", default=None, help="Aspect format id")
    p.add_argument("--work-preset", dest="work_preset", default=None, help="Work resolution preset")
    p.add_argument("--frames", type=int, default=49)
    p.add_argument("--fps", type=int, default=16)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--profile",
        choices=["preview", "deliver", "quality"],
        default="deliver",
        help="I2V speed profile (default deliver)",
    )
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--meta-out", default=None)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compose prompt only; print and exit 0 without Comfy",
    )
    args = p.parse_args(argv)

    if args.list_presets:
        print(format_motion_presets_help())
        print("")
        print("CLI: generate_camera_move.py -i still.png --preset <id> -o out.mp4")
        print("Same presets: generate_i2v --motion-preset · episode_i2v --motion-preset")
        return 0

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required")
    if not args.preset:
        p.error("--preset required (see --list-presets)")

    pid = resolve_motion_preset_id(args.preset)
    if not pid:
        p.error(f"Unknown --preset {args.preset!r} (use --list-presets)")

    extra = load_text(args.extra_file) if args.extra_file else (args.extra or "")
    prompt, neg_extra = compose_motion_prompt(pid, extra)
    negative = load_text(args.negative_file) if args.negative_file else (args.negative or "")
    if neg_extra:
        negative = f"{negative}, {neg_extra}" if negative else neg_extra

    print(f"[camera_move] preset={pid}")
    print(f"[camera_move] prompt={prompt[:160]}{'…' if len(prompt) > 160 else ''}")

    if args.dry_run:
        print("[camera_move] dry-run (no Comfy)")
        out = {
            "ok": True,
            "dry_run": True,
            "preset": pid,
            "prompt": prompt,
            "negative": negative,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if not os.path.isfile(args.input):
        print(f"[camera_move] FAIL input missing: {args.input}", file=sys.stderr)
        return 1

    parent = os.path.dirname(os.path.abspath(args.output))
    if parent:
        os.makedirs(parent, exist_ok=True)

    r = generate_i2v(
        input_image_path=args.input,
        prompt_text=prompt,
        negative_text=negative,
        output_filename=args.output,
        num_frames=args.frames,
        frame_rate=args.fps,
        steps=args.steps,
        cfg=args.cfg,
        seed=args.seed,
        backend=args.backend,
        format_id=args.format_id,
        preset=args.work_preset,
        profile=args.profile,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
    )

    if not r.get("ok"):
        print(
            f"[camera_move] FAIL {r.get('error')} {r.get('message')}",
            file=sys.stderr,
        )
        print(json.dumps({"ok": False, "error": r.get("error"), "message": r.get("message")}))
        return 1

    # Enrich meta with tool identity
    meta = r.get("meta") or {}
    meta.update(
        {
            "tool": "generate_camera_move",
            "camera_move_preset": pid,
            "camera_move_extra": (extra or "")[:200],
            "motion_prompt_composed": prompt[:400],
        }
    )
    meta_path = r.get("meta_path") or args.meta_out
    if not meta_path and args.output:
        meta_path = os.path.splitext(args.output)[0] + ".json"
    if meta_path:
        write_meta(meta_path, meta)

    print(f"[camera_move] ok preset={pid} → {r.get('output_path')}")
    if meta_path:
        print(f"[camera_move] meta → {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
