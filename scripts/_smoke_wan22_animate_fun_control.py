#!/usr/bin/env python3
"""Smoke-render Wan2.2 Fun Control (+ optional Animate preprocess).

  python scripts/_smoke_wan22_animate_fun_control.py
  python scripts/_smoke_wan22_animate_fun_control.py --only fun
  python scripts/_smoke_wan22_animate_fun_control.py --only preprocess
"""
from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import shutil
import time
from pathlib import Path

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    ensure_comfy_running,
    get_comfy_input_dir,
    get_comfy_output_dir,
    history_execution_error,
    queue_prompt,
    wait_for_history,
)

OUT_DIR = Path("stories/_tool_smoke/wan22_animate_fun_control")
SEED = 42


def _extract_video(history_entry: dict) -> tuple[str, str, str]:
    outputs = history_entry.get("outputs") or {}
    for _nid, node_out in outputs.items():
        for key in ("gifs", "videos", "images"):
            items = node_out.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
    raise FileNotFoundError(f"No video/image in outputs: {list(outputs.keys())}")


def _stage_inputs() -> dict[str, str]:
    inp = Path(get_comfy_input_dir())
    inp.mkdir(parents=True, exist_ok=True)
    assets = Path("workflows/human/wan22/_fun_control_assets")
    start = "smoke_fun_control_start.jpg"
    control = "smoke_fun_control_control.mp4"
    shutil.copy2(assets / "input_start.jpg", inp / start)
    shutil.copy2(assets / "control_video.mp4", inp / control)
    return {"start": start, "control": control, "input_dir": str(inp)}


def build_fun_control_prompt(
    *,
    start_image: str,
    control_video: str,
    width: int = 512,
    height: int = 512,
    length: int = 33,
    steps: int = 12,
    cfg: float = 3.5,
    seed: int = SEED,
    filename_prefix: str = "smoke/wan22_fun_control",
) -> dict:
    """Native dual high/low Fun Control graph (no lightning LoRA)."""
    half = max(1, steps // 2)
    high = f"Wan2.2\\wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors"
    low = f"Wan2.2\\wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors"
    pos = (
        "A young woman dancing slowly, natural body motion, clear silhouette, "
        "soft daylight, realistic clothing folds, cinematic, smooth motion"
    )
    neg = (
        "blurry, static, frozen, deformed hands, extra fingers, bad anatomy, "
        "low quality, watermark, text, jitter"
    )
    return {
        "90": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "wan",
                "device": "default",
            },
        },
        "92": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "wan_2.1_vae.safetensors"},
        },
        "101": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": high, "weight_dtype": "default"},
        },
        "102": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": low, "weight_dtype": "default"},
        },
        "93": {
            "class_type": "ModelSamplingSD3",
            "inputs": {"model": ["101", 0], "shift": 8.0},
        },
        "94": {
            "class_type": "ModelSamplingSD3",
            "inputs": {"model": ["102", 0], "shift": 8.0},
        },
        "99": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["90", 0], "text": pos},
        },
        "91": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["90", 0], "text": neg},
        },
        "145": {
            "class_type": "LoadImage",
            "inputs": {"image": start_image},
        },
        "158": {
            "class_type": "LoadVideo",
            "inputs": {"file": control_video},
        },
        "156": {
            "class_type": "GetVideoComponents",
            "inputs": {"video": ["158", 0]},
        },
        "160": {
            "class_type": "Wan22FunControlToVideo",
            "inputs": {
                "positive": ["99", 0],
                "negative": ["91", 0],
                "vae": ["92", 0],
                "width": width,
                "height": height,
                "length": length,
                "batch_size": 1,
                "ref_image": ["145", 0],
                "control_video": ["156", 0],
            },
        },
        # High-noise stage: add noise, steps 0..half, keep residual noise
        "96": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": ["93", 0],
                "add_noise": "enable",
                "noise_seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "simple",
                "positive": ["160", 0],
                "negative": ["160", 1],
                "latent_image": ["160", 2],
                "start_at_step": 0,
                "end_at_step": half,
                "return_with_leftover_noise": "enable",
            },
        },
        # Low-noise stage: no new noise, half..end
        "95": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": ["94", 0],
                "add_noise": "disable",
                "noise_seed": 0,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "simple",
                "positive": ["160", 0],
                "negative": ["160", 1],
                "latent_image": ["96", 0],
                "start_at_step": half,
                "end_at_step": 10000,
                "return_with_leftover_noise": "disable",
            },
        },
        "97": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["95", 0], "vae": ["92", 0]},
        },
        "100": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["97", 0], "fps": 16.0},
        },
        "98": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["100", 0],
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
            },
        },
    }


def build_animate_preprocess_prompt(
    *,
    control_video: str,
    filename_prefix: str = "smoke/wan22_animate_pose",
    max_frames: int = 48,
) -> dict:
    """Pose extract only — proves WanAnimatePreprocess + detection weights.

    Uses first N frames via ImageFromBatch-less path: LoadVideo whole clip is OK
    for short samples; long clips still fine for smoke on 152-frame sample.
    """
    return {
        "1": {
            "class_type": "LoadVideo",
            "inputs": {"file": control_video},
        },
        "2": {
            "class_type": "GetVideoComponents",
            "inputs": {"video": ["1", 0]},
        },
        "3": {
            "class_type": "OnnxDetectionModelLoader",
            "inputs": {
                "vitpose_model": "vitpose-l-wholebody.onnx",
                "yolo_model": "yolov10m.onnx",
                "onnx_device": "CUDAExecutionProvider",
            },
        },
        "4": {
            "class_type": "PoseAndFaceDetection",
            "inputs": {
                "model": ["3", 0],
                "images": ["2", 0],
                "width": 512,
                "height": 512,
            },
        },
        "5": {
            "class_type": "DrawViTPose",
            "inputs": {
                "pose_data": ["4", 0],
                "width": 512,
                "height": 512,
                "retarget_padding": 16,
                "body_stick_width": -1,
                "hand_stick_width": -1,
                "draw_head": True,
            },
        },
        "6": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["5", 0], "fps": 16.0},
        },
        "7": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["6", 0],
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
            },
        },
    }


def run_prompt(api_prompt: dict, *, label: str, timeout_sec: int) -> dict:
    api_prompt = {k: v for k, v in api_prompt.items() if not str(k).startswith("_")}
    t0 = time.time()
    print(f"\n=== QUEUE {label} ===")
    try:
        pid = queue_prompt(DEFAULT_SERVER, api_prompt)
    except Exception as e:
        return {"ok": False, "label": label, "error": f"queue: {e}"}
    print(f"prompt_id={pid}")
    try:
        hist = wait_for_history(DEFAULT_SERVER, pid, timeout_sec=timeout_sec)
    except Exception as e:
        return {"ok": False, "label": label, "prompt_id": pid, "error": f"wait: {e}"}
    err = history_execution_error(hist)
    if err:
        return {"ok": False, "label": label, "prompt_id": pid, "error": err}
    try:
        fn, sub, typ = _extract_video(hist)
    except Exception as e:
        return {
            "ok": False,
            "label": label,
            "prompt_id": pid,
            "error": f"extract: {e}",
            "outputs": list((hist.get("outputs") or {}).keys()),
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"{label}_{fn}"
    # prefer direct filesystem copy from Comfy output
    comfy_out = Path(get_comfy_output_dir())
    src = comfy_out / sub / fn if sub else comfy_out / fn
    if src.is_file():
        shutil.copy2(src, dest)
    else:
        download_image(DEFAULT_SERVER, fn, sub, typ, str(dest))
    elapsed = time.time() - t0
    print(f"OK {label}: {dest} ({elapsed:.1f}s)")
    return {
        "ok": True,
        "label": label,
        "prompt_id": pid,
        "output_path": str(dest),
        "elapsed_sec": round(elapsed, 1),
        "comfy_filename": fn,
        "subfolder": sub,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "fun", "preprocess"], default="all")
    ap.add_argument("--frames", type=int, default=33)
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    ensure_comfy_running(DEFAULT_SERVER)
    staged = _stage_inputs()
    results = []

    if args.only in ("all", "fun"):
        fun = build_fun_control_prompt(
            start_image=staged["start"],
            control_video=staged["control"],
            width=args.size,
            height=args.size,
            length=args.frames,
            steps=args.steps,
        )
        results.append(run_prompt(fun, label="fun_control", timeout_sec=args.timeout))

    if args.only in ("all", "preprocess"):
        prep = build_animate_preprocess_prompt(control_video=staged["control"])
        results.append(
            run_prompt(
                prep, label="animate_preprocess", timeout_sec=min(600, args.timeout)
            )
        )

    summary_path = OUT_DIR / "smoke_summary.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps(results, indent=2))
    print(f"wrote {summary_path}")
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
