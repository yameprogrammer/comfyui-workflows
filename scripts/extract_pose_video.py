#!/usr/bin/env python3
"""
Extract pose stick video from RGB footage (MOTION preprocess).

Uses ComfyUI-WanAnimatePreprocess (YOLO + ViTPose → DrawViTPose).

  python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4
  python scripts/extract_pose_video.py -v short.mp4 -o pose.mp4 --start 0 --duration 4 --width 544 --height 960

Output is a black-background skeleton plate for Fun Control / Animate retarget.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.pose_extract import (
    DEFAULT_ONNX_DEVICE,
    DEFAULT_VITPOSE,
    DEFAULT_YOLO,
    extract_pose_video,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "RGB video → pose stick mp4 (ViTPose wholebody). "
            "For dance retarget control plates (Fun Control / Animate)."
        )
    )
    p.add_argument(
        "--video",
        "-v",
        required=True,
        help="Source RGB video (dance ref / hook)",
    )
    p.add_argument("--output", "-o", required=True, help="Output pose plate mp4")
    p.add_argument("--width", type=int, default=544, help="Pose canvas width")
    p.add_argument("--height", type=int, default=960, help="Pose canvas height")
    p.add_argument("--fps", type=float, default=16.0, help="Output fps")
    p.add_argument("--start", type=float, default=0.0, help="Trim start sec")
    p.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Trim duration sec (omit = full remaining)",
    )
    p.add_argument("--vitpose", default=DEFAULT_VITPOSE, help="ViTPose onnx name")
    p.add_argument("--yolo", default=DEFAULT_YOLO, help="YOLO onnx name")
    p.add_argument(
        "--device",
        default=DEFAULT_ONNX_DEVICE,
        choices=["CUDAExecutionProvider", "CPUExecutionProvider"],
        help="ONNX execution provider",
    )
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--work-dir", default=None)
    p.add_argument(
        "--retarget",
        "-i",
        default=None,
        help="Target character still — retarget pose proportions onto this body",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build graph meta only; do not queue Comfy",
    )
    args = p.parse_args(argv)

    r = extract_pose_video(
        video_path=args.video,
        output_path=args.output,
        width=args.width,
        height=args.height,
        fps=args.fps,
        start_sec=args.start,
        duration_sec=args.duration,
        vitpose_model=args.vitpose,
        yolo_model=args.yolo,
        onnx_device=args.device,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=args.dry_run,
        work_dir=args.work_dir,
        retarget_image=args.retarget,
    )

    if r.get("ok"):
        print(f"[extract_pose] ok → {r.get('output_path') or '(dry-run)'}")
        if r.get("elapsed_sec") is not None:
            print(f"[extract_pose] elapsed={r.get('elapsed_sec')}s")
        if r.get("meta_path"):
            print(f"[extract_pose] meta → {r.get('meta_path')}")
        return 0

    print(
        f"[extract_pose] FAIL {r.get('error')} {r.get('message')}",
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
