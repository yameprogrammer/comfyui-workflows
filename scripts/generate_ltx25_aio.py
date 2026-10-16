#!/usr/bin/env python3
"""LTX 2.5 All-In-One Video Generator CLI.

Supports T2V, TA2V, I2V, IA2V, FLF, FLFA, FML, FMLA, V2V, V2VA with LTX-2.5 models.

Examples:
  # Smoke test (fast, 768px, 2s)
  python scripts/generate_ltx25_aio.py --smoke -o workspace/smoke_test/ltx25_smoke.mp4

  # Text to Video
  python scripts/generate_ltx25_aio.py --mode t2v -p "a cinematic drone shot of snowy mountains" -o out.mp4

  # Image + Audio to Video (S2V)
  python scripts/generate_ltx25_aio.py --mode i2v_audio -i hero.png -a voice.wav -p "character speaking naturally" -o out.mp4
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401

import argparse
import json
import urllib.request
import os
import shutil
import time

# Safe utf-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lib.comfy_client import (
    DEFAULT_SERVER,
    free_comfy_memory,
    get_comfy_input_dir,
    get_comfy_output_dir,
    queue_prompt,
    wait_for_history,
)
from lib.ltx_aio_workflow_runner import build_aio_switched_api
from lib.ltx25_contract import check_ltx25_graph, find_completed_media, active_loras

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

    p.add_argument("--export-api", type=Path, help="Build/export API JSON only; never stage inputs, free memory or queue")
    p.add_argument("--object-info", type=Path, help="Saved object_info JSON for offline export")
    p.add_argument("--lora-policy", choices=["quality", "workflow", "none"], default="quality", help="quality: preserve original profile tuning; workflow: saved UI switches; none: explicit no-LoRA comparison")
    p.add_argument("--ltx-profile", choices=["draft", "work", "hero"], default="work", help="Existing quality-LoRA profile; 2.5 quality benefit remains unverified")
    args = p.parse_args(argv)
    required = []
    if args.mode.startswith(("i2v", "flf", "fml")): required.append((args.image, "--image"))
    if args.mode.endswith("_audio"): required.append((args.audio, "--audio"))
    if args.mode.startswith(("flf", "fml")): required.append((args.last, "--last"))
    if args.mode.startswith("fml"): required.append((args.mid, "--mid"))
    if args.mode.startswith("v2v"): required.append((args.video, "--video"))
    for value, flag in required:
        if not value or not Path(value).is_file(): p.error(f"{args.mode} requires an existing {flag} file")
    if not args.export_api and Path(args.output).resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        p.error("--output must point outside the toolbox repository")

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

    # No auto-start/restart: shared ComfyUI must already be available.
    object_info = json.loads(args.object_info.read_text(encoding="utf-8")) if args.object_info else None
    if args.export_api:
        img_name, audio_name, last_name, mid_name, vid_name = [
            Path(value).name if value else None
            for value in (args.image, args.audio, args.last, args.mid, args.video)
        ]
    else:
        with urllib.request.urlopen(f"http://{args.server}/system_stats", timeout=10) as response:
            json.load(response)
        input_dir = get_comfy_input_dir(server_address=args.server)
        img_name, audio_name, last_name, mid_name, vid_name = [
            _stage_input_file(value, input_dir)
            for value in (args.image, args.audio, args.last, args.mid, args.video)
        ]

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
        apply_legacy_loras=args.lora_policy == "quality",
        ltx_profile=args.ltx_profile,
        object_info=object_info,
        ui_workflow_path=DEFAULT_UI_WF,
    )

    if args.lora_policy == "none":
        for node in api.values():
            for key, value in node.get("inputs", {}).items():
                if key.startswith("lora_") and isinstance(value, dict):
                    value["on"] = False
    selected = check_ltx25_graph(api, lora_policy=args.lora_policy)
    meta["lora_policy"] = args.lora_policy
    meta["active_loras"] = active_loras(api)
    if args.export_api:
        args.export_api.parent.mkdir(parents=True, exist_ok=True)
        args.export_api.write_text(json.dumps({"prompt": api, "metadata": meta, "models": selected}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[EXPORTED, NOT EXECUTED] {args.export_api}")
        return 0

    free_comfy_memory(server_address=args.server, unload_models=True, free_memory=True)
    prompt_id = queue_prompt(args.server, api)
    print(f"Prompt ID: {prompt_id}")
    started = time.time()
    history = wait_for_history(args.server, prompt_id, timeout_sec=1800)
    source = find_completed_media(history, get_comfy_output_dir(server_address=args.server))
    destination = Path(args.output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source != destination:
        shutil.copy2(source, destination)
    evidence = {"model_family": "ltx25", "prompt_id": prompt_id, "mode": args.mode,
                "models": selected, "workflow": DEFAULT_UI_WF, "metadata": meta,
                "status": history.get("status"), "output": str(destination),
                "size_bytes": destination.stat().st_size, "elapsed_sec": time.time() - started,
                "execution": "completed", "quality_review": "not_run"}
    destination.with_suffix(destination.suffix + ".run.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RENDER COMPLETE; QA REQUIRED] {destination}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)
