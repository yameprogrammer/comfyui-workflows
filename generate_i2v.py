#!/usr/bin/env python3
"""
Image-to-Video via Wan2.2 I2V A14B (ComfyUI-WanVideoWrapper).

Uses local GGUF High/Low noise models + lightx2v 4-step LoRAs when available.
Workflow template: I2V-wan22-a14b.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    WORKSPACE_ROOT,
    ensure_parent_dir,
    fail_result,
    ok_result,
    resolve_meta_out,
    utc_now_iso,
    write_meta,
)
from lib.comfy_ui_convert import convert_ui_to_api, fetch_object_info
from lib.prompt_assembly import load_text

DEFAULT_WORKFLOW = os.path.join(WORKSPACE_ROOT, "I2V-wan22-a14b.json")
DEFAULT_NEGATIVE = (
    "static, still image, blurry, low quality, worst quality, deformed, "
    "bad anatomy, watermark, text, logo, jitter, flicker"
)

# Comfy output folder for VHS saves
COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"


def _find_nodes(api_prompt: dict, class_type: str) -> list[str]:
    return [nid for nid, n in api_prompt.items() if n.get("class_type") == class_type]


def generate_i2v(
    input_image_path: str,
    prompt_text: str,
    negative_text: str = DEFAULT_NEGATIVE,
    output_filename: str | None = None,
    width: int = 640,
    height: int = 640,
    num_frames: int = 49,
    seed: int | None = None,
    steps: int = 6,
    cfg: float = 1.0,
    frame_rate: int = 16,
    workflow_path: str = DEFAULT_WORKFLOW,
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 1800,
):
    if not os.path.exists(input_image_path):
        print(f"Error: input image not found: {input_image_path}")
        return fail_result(error="SOURCE_MISSING", message=input_image_path)
    if not os.path.exists(workflow_path):
        print(f"Error: workflow not found: {workflow_path}")
        return fail_result(error="WORKFLOW_MISSING", message=workflow_path)

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_videos", "output_i2v.mp4")
    ensure_parent_dir(output_filename)

    # Copy image into Comfy input
    temp_name = "temp_i2v_input.png"
    try:
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_name))
        print(f"Copied input to ComfyUI input: {temp_name}")
    except Exception as e:
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    print(f"Loading I2V workflow: {workflow_path}")
    with open(workflow_path, "r", encoding="utf-8") as f:
        ui_data = json.load(f)

    try:
        object_info = fetch_object_info(server_address)
    except Exception as e:
        print(f"[WARN] object_info fetch failed: {e}; conversion may be incomplete")
        object_info = {}

    api_prompt = convert_ui_to_api(ui_data, object_info, server_address)

    new_seed = seed if seed is not None else random.randint(1, 2**31 - 1)

    # Force local model paths (Windows Comfy uses backslash relative names)
    model_high = r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf"
    model_low = r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf"
    lora_high = r"Wan2.2\Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
    lora_low = r"Wan2.2\Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
    loaders = _find_nodes(api_prompt, "WanVideoModelLoader")
    if len(loaders) >= 2:
        # first high, second low by conventional example ids order
        api_prompt[loaders[0]]["inputs"]["model"] = model_high
        api_prompt[loaders[0]]["inputs"]["quantization"] = "disabled"
        api_prompt[loaders[0]]["inputs"]["attention_mode"] = "sdpa"
        api_prompt[loaders[1]]["inputs"]["model"] = model_low
        api_prompt[loaders[1]]["inputs"]["quantization"] = "disabled"
        api_prompt[loaders[1]]["inputs"]["attention_mode"] = "sdpa"
    loras = _find_nodes(api_prompt, "WanVideoLoraSelect")
    # map by current lora name if possible
    for nid in loras:
        cur = str(api_prompt[nid]["inputs"].get("lora", ""))
        if "LOW" in cur.upper() or "low" in cur:
            api_prompt[nid]["inputs"]["lora"] = lora_low
        else:
            api_prompt[nid]["inputs"]["lora"] = lora_high
        api_prompt[nid]["inputs"]["merge_loras"] = False
    for nid in _find_nodes(api_prompt, "WanVideoVAELoader"):
        api_prompt[nid]["inputs"]["model_name"] = "wan_2.1_vae.safetensors"
    for nid in _find_nodes(api_prompt, "LoadWanVideoT5TextEncoder"):
        # prefer bf16 encoder if listed
        api_prompt[nid]["inputs"]["model_name"] = "umt5-xxl-enc-bf16.safetensors"

    # LoadImage
    for nid in _find_nodes(api_prompt, "LoadImage"):
        api_prompt[nid]["inputs"]["image"] = temp_name

    # Text encode
    for nid in _find_nodes(api_prompt, "WanVideoTextEncode"):
        api_prompt[nid]["inputs"]["positive_prompt"] = prompt_text
        api_prompt[nid]["inputs"]["negative_prompt"] = negative_text or DEFAULT_NEGATIVE

    # Image resize target (keep multiple of 32 later applied by node)
    for nid in _find_nodes(api_prompt, "ImageResizeKJv2"):
        api_prompt[nid]["inputs"]["width"] = width
        api_prompt[nid]["inputs"]["height"] = height

    # I2V encode size / frames
    for nid in _find_nodes(api_prompt, "WanVideoImageToVideoEncode"):
        inp = api_prompt[nid]["inputs"]
        inp["width"] = width
        inp["height"] = height
        inp["num_frames"] = num_frames

    # Samplers (dual high/low) — only set seed/cfg when not link-fed
    for nid in _find_nodes(api_prompt, "WanVideoSampler"):
        inp = api_prompt[nid]["inputs"]
        # seed is usually a widget
        if not (isinstance(inp.get("seed"), list) and len(inp.get("seed") or []) == 2):
            inp["seed"] = new_seed
        if not (isinstance(inp.get("cfg"), list) and len(inp.get("cfg") or []) == 2):
            inp["cfg"] = cfg
        # steps often linked from INTConstant — do not clobber split-stage end_step graph

    # Optionally bump total step constant nodes (not start/end stage markers)
    for nid in _find_nodes(api_prompt, "INTConstant"):
        val = api_prompt[nid]["inputs"].get("value")
        # example uses small constants for stage splits (3/6/10); only replace pure step total if labeled via value==30 default style
        if val == 30:
            api_prompt[nid]["inputs"]["value"] = steps

    # Video combine
    for nid in _find_nodes(api_prompt, "VHS_VideoCombine"):
        inp = api_prompt[nid]["inputs"]
        inp["frame_rate"] = frame_rate
        inp["filename_prefix"] = "agent_i2v"
        inp["save_output"] = True
        inp["format"] = inp.get("format") or "video/h264-mp4"

    # Strip invalid leftover keys
    for nid, node in api_prompt.items():
        node["inputs"].pop("_widgets_values", None)

    print(
        f"Queue I2V: {width}x{height} frames={num_frames} steps={steps} cfg={cfg} seed={new_seed}"
    )
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server_address}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            prompt_id = res["prompt_id"]
            print(f"Prompt queued: {prompt_id}")
            if res.get("node_errors"):
                print(f"[WARN] node_errors: {res['node_errors']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] queue failed HTTP {e.code}: {body[:2000]}")
        return fail_result(error="QUEUE_FAILED", message=body[:500], seed=new_seed)
    except Exception as e:
        print(f"[ERROR] queue failed: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    # Poll history
    deadline = time.time() + timeout_sec
    history_entry = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server_address}/history/{prompt_id}", timeout=30
            ) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
                if prompt_id in hist:
                    history_entry = hist[prompt_id]
                    print("Generation completed!")
                    break
        except Exception:
            pass
        time.sleep(2)
    if history_entry is None:
        return fail_result(error="COMFY_TIMEOUT", message="I2V timeout", seed=new_seed, prompt_id=prompt_id)

    status = history_entry.get("status") or {}
    if status.get("status_str") == "error" or status.get("completed") is False:
        # extract last execution_error
        err_msg = "execution error"
        for msg in status.get("messages") or []:
            if msg and msg[0] == "execution_error":
                err_msg = msg[1].get("exception_message") or err_msg
                print(f"[ERROR] node={msg[1].get('node_id')} {msg[1].get('node_type')}: {str(err_msg)[:500]}")
        return fail_result(error="EXECUTION_ERROR", message=str(err_msg)[:500], seed=new_seed, prompt_id=prompt_id)

    # Find video in outputs (VHS)
    video_info = None
    outputs = history_entry.get("outputs") or {}
    for _nid, out in outputs.items():
        for key in ("gifs", "videos"):
            if key in out and out[key]:
                video_info = out[key][0]
                break
        if video_info:
            break

    if not video_info:
        # Fallback: scan output/temp for newest agent_i2v mp4
        candidates = []
        for folder in (COMFY_OUTPUT_DIR, COMFY_TEMP_DIR):
            if not os.path.isdir(folder):
                continue
            for root, _dirs, files in os.walk(folder):
                for fn in files:
                    if fn.lower().endswith(".mp4") and "agent_i2v" in fn.lower():
                        fp = os.path.join(root, fn)
                        candidates.append((os.path.getmtime(fp), fp))
        if candidates:
            candidates.sort(reverse=True)
            src = candidates[0][1]
            shutil.copy2(src, output_filename)
            print(f"Copied newest agent_i2v mp4: {src} -> {output_filename}")
        else:
            print("[ERROR] No video in history outputs")
            return fail_result(
                error="COMFY_NO_OUTPUT",
                message="no video output",
                seed=new_seed,
                prompt_id=prompt_id,
            )
    else:
        filename = video_info.get("filename")
        subfolder = video_info.get("subfolder", "")
        ftype = video_info.get("type", "output")
        # Prefer filesystem copy over /view for large videos
        base = COMFY_OUTPUT_DIR if ftype == "output" else COMFY_TEMP_DIR
        src = os.path.join(base, subfolder, filename) if subfolder else os.path.join(base, filename)
        if os.path.exists(src):
            shutil.copy2(src, output_filename)
            print(f"Copied video: {src} -> {output_filename}")
        else:
            view_url = (
                f"http://{server_address}/view?filename={urllib.parse.quote(filename)}"
                f"&subfolder={urllib.parse.quote(subfolder)}&type={ftype}"
            )
            print(f"Downloading video via API: {filename}")
            urllib.request.urlretrieve(view_url, output_filename)

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": "i2v",
        "workflow": os.path.basename(workflow_path),
        "prompt": prompt_text,
        "negative": negative_text,
        "seed": new_seed,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "steps": steps,
        "cfg": cfg,
        "frame_rate": frame_rate,
        "source_image": os.path.abspath(input_image_path),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")

    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=new_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wan2.2 Image-to-Video (ComfyUI)")
    parser.add_argument("--input", "-i", required=True, help="Keyframe image path")
    parser.add_argument("--prompt", "-p", default=None, help="Motion / scene prompt")
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--negative-file", default=None)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=640)
    parser.add_argument("--frames", type=int, default=49, help="Frame count (odd-ish; rounded by model)")
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--meta-out", default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    prompt = load_text(args.prompt_file) if args.prompt_file else (args.prompt or "")
    if not prompt:
        parser.error("--prompt or --prompt-file required")
    negative = load_text(args.negative_file) if args.negative_file else args.negative

    result = generate_i2v(
        input_image_path=args.input,
        prompt_text=prompt,
        negative_text=negative,
        output_filename=args.output,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        frame_rate=args.fps,
        workflow_path=args.workflow,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
    )
    sys.exit(0 if result.get("ok") else 1)
