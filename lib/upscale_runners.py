"""Comfy API + SeedVR2 CLI runners for image/video upscale."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    ensure_parent_dir,
    extract_first_image,
    fail_result,
    ok_result,
    resolve_meta_out,
    utc_now_iso,
    write_meta,
)

COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"


def _queue_api(server: str, api_prompt: dict) -> str:
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if res.get("node_errors"):
        raise RuntimeError(f"node_errors: {res['node_errors']}")
    return res["prompt_id"]


def _wait_history(server: str, prompt_id: str, timeout_sec: float) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server}/history/{prompt_id}", timeout=30
            ) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
                if prompt_id in hist:
                    return hist[prompt_id]
        except Exception:
            pass
        time.sleep(1.5)
    raise TimeoutError(f"Comfy timeout waiting for {prompt_id}")


def _copy_to_comfy_input(src: str, temp_name: str) -> str:
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, temp_name)
    shutil.copy2(src, dest)
    return temp_name


def _download_image(server: str, info: dict, out_path: str) -> None:
    filename = info["filename"]
    subfolder = info.get("subfolder", "")
    ftype = info.get("type", "output")
    base = COMFY_OUTPUT_DIR if ftype == "output" else COMFY_TEMP_DIR
    src = os.path.join(base, subfolder, filename) if subfolder else os.path.join(base, filename)
    if os.path.isfile(src):
        ensure_parent_dir(out_path)
        shutil.copy2(src, out_path)
        return
    url = (
        f"http://{server}/view?filename={urllib.parse.quote(filename)}"
        f"&subfolder={urllib.parse.quote(subfolder)}&type={ftype}"
    )
    ensure_parent_dir(out_path)
    urllib.request.urlretrieve(url, out_path)


def _find_video_in_history(history_entry: dict) -> dict | None:
    outputs = history_entry.get("outputs") or {}
    for _nid, out in outputs.items():
        for key in ("gifs", "videos"):
            if key in out and out[key]:
                return out[key][0]
    return None


def _copy_video_info(info: dict, out_path: str) -> None:
    filename = info.get("filename")
    subfolder = info.get("subfolder", "")
    ftype = info.get("type", "output")
    base = COMFY_OUTPUT_DIR if ftype == "output" else COMFY_TEMP_DIR
    src = os.path.join(base, subfolder, filename) if subfolder else os.path.join(base, filename)
    ensure_parent_dir(out_path)
    if os.path.isfile(src):
        shutil.copy2(src, out_path)
        return
    # fallback newest agent_upscale mp4
    raise FileNotFoundError(f"Video not found on disk: {src}")


def build_esrgan_image_prompt(
    image_name: str,
    model_name: str,
    width: int,
    height: int,
    prefix: str = "agent_upscale",
) -> dict:
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": model_name},
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]},
        },
        "4": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["3", 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "disabled",
            },
        },
        "5": {
            "class_type": "SaveImage",
            "inputs": {"images": ["4", 0], "filename_prefix": prefix},
        },
    }


def build_seedvr2_image_prompt(
    image_name: str,
    *,
    resolution: int,
    dit_model: str = "seedvr2_ema_7b_fp8_e4m3fn_mixed_block35_fp16.safetensors",
    vae_model: str = "ema_vae_fp16.safetensors",
    seed: int = 42,
    color_correction: str = "lab",
    encode_tiled: bool = False,
    decode_tiled: bool = False,
    prefix: str = "ups_seedvr2",
) -> dict:
    """Comfy API graph for SeedVR2 still upscale (batch_size=1)."""
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "SeedVR2LoadDiTModel",
            "inputs": {
                "model": dit_model,
                "device": "cuda:0",
                "blocks_to_swap": 0,
                "swap_io_components": False,
                "offload_device": "none",
                "cache_model": False,
                "attention_mode": "sdpa",
            },
        },
        "3": {
            "class_type": "SeedVR2LoadVAEModel",
            "inputs": {
                "model": vae_model,
                "device": "cuda:0",
                "encode_tiled": bool(encode_tiled),
                "encode_tile_size": 1024,
                "encode_tile_overlap": 128,
                "decode_tiled": bool(decode_tiled),
                "decode_tile_size": 1024,
                "decode_tile_overlap": 128,
                "tile_debug": "false",
                "offload_device": "none",
                "cache_model": False,
            },
        },
        "4": {
            "class_type": "SeedVR2VideoUpscaler",
            "inputs": {
                "image": ["1", 0],
                "dit": ["2", 0],
                "vae": ["3", 0],
                "seed": int(seed),
                "resolution": int(resolution),
                "max_resolution": 0,
                "batch_size": 1,
                "uniform_batch_size": False,
                "color_correction": color_correction,
                "temporal_overlap": 0,
                "prepend_frames": 0,
                "input_noise_scale": 0.0,
                "latent_noise_scale": 0.0,
                "offload_device": "cpu",
                "enable_debug": False,
            },
        },
        "5": {
            "class_type": "SaveImage",
            "inputs": {"images": ["4", 0], "filename_prefix": prefix},
        },
    }


def _rtx_resize_inputs(width: int, height: int, quality: str = "ULTRA") -> dict:
    """RTXVideoSuperResolution uses COMFY_DYNAMICCOMBO_V3 for resize_type.

    Flat width/height or nested dict validate poorly / fail at execute.
    Working API form (verified): dotted subkeys under resize_type.
    """
    return {
        "resize_type": "target dimensions",
        "resize_type.width": int(width),
        "resize_type.height": int(height),
        "quality": quality,
    }


def build_rtx_image_prompt(
    image_name: str,
    width: int,
    height: int,
    quality: str = "ULTRA",
    prefix: str = "agent_upscale",
) -> dict:
    rtx = _rtx_resize_inputs(width, height, quality)
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "RTXVideoSuperResolution",
            "inputs": {
                "images": ["1", 0],
                **rtx,
            },
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {"images": ["2", 0], "filename_prefix": prefix},
        },
    }


def build_esrgan_video_prompt(
    video_path: str,
    model_name: str,
    width: int,
    height: int,
    frame_rate: float,
    prefix: str = "agent_upscale_vid",
) -> dict:
    return {
        "1": {
            "class_type": "VHS_LoadVideoPath",
            "inputs": {
                "video": video_path.replace("/", "\\"),
                "force_rate": 0,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "None",
            },
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": model_name},
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]},
        },
        "4": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["3", 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "disabled",
            },
        },
        "5": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["4", 0],
                "frame_rate": float(frame_rate),
                "loop_count": 0,
                "filename_prefix": prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def build_rtx_video_prompt(
    video_path: str,
    width: int,
    height: int,
    frame_rate: float,
    quality: str = "ULTRA",
    prefix: str = "agent_upscale_vid",
) -> dict:
    rtx = _rtx_resize_inputs(width, height, quality)
    return {
        "1": {
            "class_type": "VHS_LoadVideoPath",
            "inputs": {
                "video": video_path.replace("/", "\\"),
                "force_rate": 0,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "None",
            },
        },
        "2": {
            "class_type": "RTXVideoSuperResolution",
            "inputs": {
                "images": ["1", 0],
                **rtx,
            },
        },
        "3": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["2", 0],
                "frame_rate": float(frame_rate),
                "loop_count": 0,
                "filename_prefix": prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def run_comfy_image(
    api_prompt: dict,
    output_path: str,
    *,
    server: str = DEFAULT_SERVER,
    timeout_sec: float = 1800,
) -> dict[str, Any]:
    try:
        prompt_id = _queue_api(server, api_prompt)
        print(f"Queued Comfy image upscale: {prompt_id}")
        hist = _wait_history(server, prompt_id, timeout_sec)
    except Exception as e:
        return fail_result(error="COMFY_UPSCALE_FAILED", message=str(e))

    status = hist.get("status") or {}
    if status.get("status_str") == "error":
        return fail_result(error="EXECUTION_ERROR", message=str(status)[:500], prompt_id=prompt_id)

    try:
        filename, subfolder, ftype = extract_first_image(hist)
    except FileNotFoundError:
        return fail_result(error="COMFY_NO_OUTPUT", message="no image", prompt_id=prompt_id)
    try:
        _download_image(
            server,
            {"filename": filename, "subfolder": subfolder, "type": ftype},
            output_path,
        )
    except Exception as e:
        return fail_result(error="SAVE_FAILED", message=str(e), prompt_id=prompt_id)
    return ok_result(output_path=os.path.abspath(output_path), prompt_id=prompt_id)


def run_comfy_video(
    api_prompt: dict,
    output_path: str,
    *,
    server: str = DEFAULT_SERVER,
    timeout_sec: float = 7200,
    prefix_hint: str = "agent_upscale_vid",
) -> dict[str, Any]:
    try:
        prompt_id = _queue_api(server, api_prompt)
        print(f"Queued Comfy video upscale: {prompt_id}")
        hist = _wait_history(server, prompt_id, timeout_sec)
    except Exception as e:
        return fail_result(error="COMFY_UPSCALE_FAILED", message=str(e))

    status = hist.get("status") or {}
    if status.get("status_str") == "error":
        return fail_result(error="EXECUTION_ERROR", message=str(status)[:500], prompt_id=prompt_id)

    vinfo = _find_video_in_history(hist)
    try:
        if vinfo:
            _copy_video_info(vinfo, output_path)
        else:
            # newest matching prefix
            candidates = []
            for folder in (COMFY_OUTPUT_DIR, COMFY_TEMP_DIR):
                if not os.path.isdir(folder):
                    continue
                for root, _d, files in os.walk(folder):
                    for fn in files:
                        if fn.lower().endswith(".mp4") and prefix_hint.lower() in fn.lower():
                            fp = os.path.join(root, fn)
                            candidates.append((os.path.getmtime(fp), fp))
            if not candidates:
                return fail_result(
                    error="COMFY_NO_OUTPUT", message="no video", prompt_id=prompt_id
                )
            candidates.sort(reverse=True)
            ensure_parent_dir(output_path)
            shutil.copy2(candidates[0][1], output_path)
    except Exception as e:
        return fail_result(error="SAVE_FAILED", message=str(e), prompt_id=prompt_id)

    return ok_result(output_path=os.path.abspath(output_path), prompt_id=prompt_id)


def run_seedvr2_cli(
    input_path: str,
    output_path: str,
    *,
    short_edge: int,
    backend_cfg: dict[str, Any],
    root_cfg: dict[str, Any],
    media: str,
    timeout_sec: float = 14400,
) -> dict[str, Any]:
    py = root_cfg.get("comfy_python") or r"F:\ComfyUI_windows_portable\python_embeded\python.exe"
    cli = root_cfg.get("seedvr2_cli")
    model_dir = root_cfg.get("seedvr2_model_dir")
    if not cli or not os.path.isfile(cli):
        return fail_result(error="SEEDVR2_CLI_MISSING", message=str(cli))
    if not os.path.isfile(py):
        return fail_result(error="COMFY_PYTHON_MISSING", message=str(py))

    ensure_parent_dir(output_path)
    dit = backend_cfg.get("dit_model")
    batch = (
        backend_cfg.get("batch_size_image", 1)
        if media == "image"
        else backend_cfg.get("batch_size_video", 5)
    )
    # enforce 4n+1
    batch = int(batch)
    if batch > 1 and (batch - 1) % 4 != 0:
        # snap down to valid
        batch = max(1, ((batch - 1) // 4) * 4 + 1)

    cmd = [
        py,
        cli,
        os.path.abspath(input_path),
        "--output",
        os.path.abspath(output_path),
        "--resolution",
        str(int(short_edge)),
        "--batch_size",
        str(batch),
        "--color_correction",
        str(backend_cfg.get("color_correction") or "lab"),
        "--attention_mode",
        str(backend_cfg.get("attention_mode") or "sdpa"),
        "--seed",
        "42",
    ]
    if dit:
        cmd.extend(["--dit_model", str(dit)])
    if model_dir:
        cmd.extend(["--model_dir", str(model_dir)])
    if media == "video":
        cmd.extend(["--video_backend", "ffmpeg"])

    tile = bool(backend_cfg.get("force_vae_tiled"))
    thr = int(backend_cfg.get("vae_tile_short_edge_threshold") or 1440)
    if tile or short_edge >= thr:
        cmd.extend(
            [
                "--vae_encode_tiled",
                "--vae_decode_tiled",
                "--vae_encode_tile_size",
                "1024",
                "--vae_decode_tile_size",
                "1024",
            ]
        )
    blocks = int(backend_cfg.get("blocks_to_swap") or 0)
    if blocks > 0:
        cmd.extend(["--blocks_to_swap", str(blocks), "--dit_offload_device", "cpu"])

    print("SeedVR2 CLI:", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=os.path.dirname(cli),
        )
    except subprocess.TimeoutExpired:
        return fail_result(error="SEEDVR2_TIMEOUT", message=f">{timeout_sec}s")
    except Exception as e:
        return fail_result(error="SEEDVR2_FAILED", message=str(e))

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2000:]
        print(err)
        return fail_result(error="SEEDVR2_FAILED", message=err[:500], returncode=proc.returncode)

    # CLI may write beside input or exact --output; accept either
    if not os.path.isfile(output_path):
        # search sibling
        parent = os.path.dirname(os.path.abspath(output_path))
        stem = os.path.splitext(os.path.basename(input_path))[0]
        candidates = []
        if os.path.isdir(parent):
            for fn in os.listdir(parent):
                if stem in fn and (fn.lower().endswith(".png") or fn.lower().endswith(".mp4")):
                    candidates.append(os.path.join(parent, fn))
        if candidates:
            candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            shutil.copy2(candidates[0], output_path)
        else:
            return fail_result(
                error="SEEDVR2_NO_OUTPUT",
                message="CLI finished but output missing",
                stdout=(proc.stdout or "")[-500:],
            )

    return ok_result(output_path=os.path.abspath(output_path))


def copy_input_for_image(path: str) -> str:
    ext = os.path.splitext(path)[1].lower() or ".png"
    name = f"temp_upscale_input{ext}"
    return _copy_to_comfy_input(path, name)
