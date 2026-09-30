#!/usr/bin/env python3
"""LTX 2.5 All-In-One Video Generator CLI.

Supports T2V, TA2V, I2V, IA2V, FLF, FLFA, FML, FMLA, V2V with LTX-2.5 models.

Examples:
  # Smoke test (fast, 768px, 2s)
  python scripts/generate_ltx25_aio.py --smoke -o workspace/smoke_test/ltx25_smoke.mp4

  # Text to Video
  python scripts/generate_ltx25_aio.py --mode t2v -p "a cinematic drone shot of snowy mountains" -o out.mp4

  # Image + Audio to Video (S2V)
  python scripts/generate_ltx25_aio.py --mode i2v_audio -i hero.png -a voice.wav -p "character speaking naturally" -o out.mp4
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

# Safe utf-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_comfy_running,
    free_comfy_memory,
    get_comfy_data_dir,
    get_comfy_input_dir,
    get_comfy_output_dir,
    queue_prompt,
    wait_for_history,
)
from lib.ltx_aio_workflow_runner import build_aio_switched_api

DEFAULT_UI_WF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workflows",
    "human",
    "ltx25AllInOneWorkflowForRTX_custom.json",
)


def _stage_input_file(file_path: str | None, comfy_input_dir: str) -> str | None:
    """Ensure file is inside ComfyUI input directory; copy if external."""
    if not file_path:
        return None
    src = Path(file_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    target_dir = Path(comfy_input_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    dst = target_dir / src.name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        shutil.copy2(src, dst)
    return src.name


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="LTX 2.5 All-In-One Generator CLI")
    p.add_argument("--mode", default="t2v", choices=[
        "t2v", "t2v_audio", "i2v", "i2v_audio",
        "flf", "flf_audio", "fml", "fml_audio",
        "v2v", "v2v_audio"
    ], help="Generation mode (default: t2v)")
    p.add_argument("-p", "--prompt", default="", help="Positive prompt")
    p.add_argument("-n", "--negative", default="animation, cartoon, text, blurry, distorted", help="Negative prompt")
    p.add_argument("-i", "--image", default=None, help="Input initial frame (I2V / FLF / V2V)")
    p.add_argument("-a", "--audio", default=None, help="Input driving audio file (S2V)")
    p.add_argument("--last", default=None, help="Last frame image (FLF)")
    p.add_argument("--mid", default=None, help="Mid frame image (FML)")
    p.add_argument("--video", default=None, help="Input video (V2V)")
    p.add_argument("-o", "--output", default="ltx25_output.mp4", help="Output MP4 path")
    p.add_argument("--clip-length", type=float, default=None, help="Clip length in seconds (default: 3.0, recommended max: 10.0s @ 24fps 768p)")
    p.add_argument("--longer-edge", type=int, default=None, help="Longer edge in pixels (e.g. 768, 960, 1280)")
    p.add_argument("--seed", type=int, default=None, help="Random seed")
    p.add_argument("--fps", type=int, default=24, help="Frames per second (default: 24)")
    p.add_argument("--server", default=DEFAULT_SERVER, help=f"ComfyUI host:port (default: {DEFAULT_SERVER})")
    p.add_argument("--smoke", action="store_true", help="Fast smoke test mode (768px, 2.0s duration)")

    args = p.parse_args(argv)

    if args.smoke:
        if not args.prompt:
            args.prompt = "a glowing bioluminescent jellyfish floating slowly in the deep dark abyss, cinematic lighting, 4k"
        if args.clip_length is None:
            args.clip_length = 2.0
        if args.longer_edge is None:
            args.longer_edge = 768
    else:
        if args.clip_length is None:
            args.clip_length = 3.0
        if args.longer_edge is None:
            args.longer_edge = 1280

    MAX_RECOMMENDED_CLIP_SEC = 10.0
    if args.clip_length > MAX_RECOMMENDED_CLIP_SEC:
        print(
            f"\n[WARNING] Requested clip_length ({args.clip_length}s) exceeds the recommended single-clip maximum of {MAX_RECOMMENDED_CLIP_SEC}s (24fps @ 768p)."
            f"\n          Longer single clips may lead to temporal drift, motion blur, or VRAM pressure. Consider splitting into multiple shots or last-frame chaining.\n",
            file=sys.stderr,
        )

    print("=" * 60)
    print("[LTX 2.5 All-In-One Generator]")
    print(f"  Mode:        {args.mode}")
    print(f"  Prompt:      {args.prompt}")
    print(f"  Clip Length: {args.clip_length}s @ {args.fps}fps")
    print(f"  Longer Edge: {args.longer_edge}px")
    print(f"  Server:      {args.server}")
    print("=" * 60)

    # 1. ComfyUI server check
    run_check = ensure_comfy_running(server_address=args.server)
    if not run_check.get("ok"):
        print(f"[ERROR] ComfyUI server {args.server} is not reachable: {run_check}")
        return 1

    input_dir = get_comfy_input_dir(server_address=args.server)

    # 2. Stage media files
    img_name = _stage_input_file(args.image, input_dir)
    audio_name = _stage_input_file(args.audio, input_dir)
    last_name = _stage_input_file(args.last, input_dir)
    mid_name = _stage_input_file(args.mid, input_dir)
    vid_name = _stage_input_file(args.video, input_dir)

    # 3. Build API workflow
    print("[1/3] Building API workflow from LTX 2.5 custom schema...")
    api, meta = build_aio_switched_api(
        mode=args.mode,
        image_name=img_name,
        audio_name=audio_name,
        last_image_name=last_name,
        mid_image_name=mid_name,
        video_name=vid_name,
        prompt=args.prompt,
        negative=args.negative,
        seed=args.seed,
        clip_length_sec=args.clip_length,
        longer_edge=args.longer_edge,
        fps=args.fps,
        filename_prefix="agent_ltx25",
        video_vae="ltx-2.5-video-vae-bf16.safetensors",
        vbvr=False,
        face_stability=False,
        ui_workflow_path=DEFAULT_UI_WF,
    )

    # 4. Pre-flight memory cleanup and submit prompt
    print("[2/3] Cleaning stale VRAM and submitting prompt to ComfyUI queue...")
    free_comfy_memory(server_address=args.server, unload_models=True, free_memory=True)
    prompt_id = queue_prompt(args.server, api)
    print(f"  Queue successful! Prompt ID: {prompt_id}")

    # 5. Wait for history
    print("[3/3] Waiting for generation to complete...")
    t0 = time.time()
    history = wait_for_history(args.server, prompt_id, timeout_sec=600)
    elapsed = time.time() - t0

    if not history:
        print("[ERROR] Timed out or execution failed.")
        return 1

    # Extract output video
    outputs = history.get("outputs", {})
    output_files = []
    for nid, out_data in outputs.items():
        if "gifs" in out_data:
            for g in out_data["gifs"]:
                output_files.append(g.get("filename"))
        if "images" in out_data:
            for img in out_data["images"]:
                if img.get("filename", "").endswith((".mp4", ".mkv", ".webm")):
                    output_files.append(img.get("filename"))

    out_dir = get_comfy_output_dir(server_address=args.server)
    found_path = None
    for fname in output_files:
        p = Path(out_dir) / fname
        if p.is_file():
            found_path = p
            break

    if found_path:
        out_dst = Path(args.output).resolve()
        out_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(found_path, out_dst)
        print("=" * 60)
        print(f"[SUCCESS] Generation Completed in {elapsed:.1f}s!")
        print(f"  Output saved to: {out_dst}")
        print(f"  File size:       {out_dst.stat().st_size:,} bytes")
        print("=" * 60)
        return 0
    else:
        print(f"[WARN] Completed in {elapsed:.1f}s, but no video file found in outputs: {output_files}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
