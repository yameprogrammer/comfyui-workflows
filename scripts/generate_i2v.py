#!/usr/bin/env python3
"""
Image-to-Video via ComfyUI (multi-backend entry).

Default backend: wan22 (Wan2.2 I2V A14B GGUF + lightx2v).
Presets / backends SSOT: video_backends.json (see docs/video_delivery_and_backends.md).

Delivery policy:
  - Generate at work resolution with final aspect ratio (default work_16x9_540).
  - Upscale to at least 1080p in a later pipeline stage — do not treat work-res as final.
"""

from __future__ import annotations
import _bootstrap  # noqa: F401  # repo root + scripts on path

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
    ensure_parent_dir,
    fail_result,
    ok_result,
    resolve_meta_out,
    utc_now_iso,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine, family_for_i2v_backend
from lib.comfy_ui_convert import convert_ui_to_api, fetch_object_info
from lib.prompt_assembly import load_text
from lib.video_backends import (
    BackendNotReady,
    list_backend_ids,
    list_format_ids,
    list_preset_ids,
    load_video_backends,
    resolve_i2v_job,
)
from lib.workflow_paths import resolve_workflow

DEFAULT_NEGATIVE = (
    "static, still image, blurry, low quality, worst quality, deformed, "
    "bad anatomy, watermark, text, logo, jitter, flicker"
)

# Comfy output folder for VHS saves
COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"


def _find_nodes(api_prompt: dict, class_type: str) -> list[str]:
    return [nid for nid, n in api_prompt.items() if n.get("class_type") == class_type]


def _snap_dim(n: int, multiple: int = 16) -> int:
    """Round dimension to nearest multiple (min = multiple). Wan latent needs %16==0."""
    if n < multiple:
        return multiple
    return max(multiple, int(round(n / multiple) * multiple))


def _snap_frames(n: int) -> int:
    """Wan / many video DiTs prefer 4n+1 frame counts (min 9)."""
    n = max(9, int(n))
    # nearest 4k+1
    base = ((n - 1) // 4) * 4 + 1
    alt = base + 4
    if abs(alt - n) < abs(base - n):
        return alt
    return base


def generate_i2v(
    input_image_path: str,
    prompt_text: str,
    negative_text: str = DEFAULT_NEGATIVE,
    output_filename: str | None = None,
    width: int | None = None,
    height: int | None = None,
    num_frames: int = 49,
    seed: int | None = None,
    steps: int = 6,
    cfg: float = 1.0,
    frame_rate: int = 16,
    backend: str | None = None,
    format_id: str | None = None,
    preset: str | None = None,
    workflow_path: str | None = None,
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 1800,
):
    if not os.path.exists(input_image_path):
        print(f"Error: input image not found: {input_image_path}")
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    try:
        job = resolve_i2v_job(
            backend=backend,
            format_id=format_id,
            preset=preset,
            width=width,
            height=height,
            workflow=workflow_path,
        )
    except BackendNotReady as e:
        print(f"Error: backend not ready: {e}")
        return fail_result(error="BACKEND_NOT_READY", message=str(e), backend=e.backend_id)
    except (KeyError, ValueError, FileNotFoundError) as e:
        print(f"Error: I2V config: {e}")
        return fail_result(error="I2V_CONFIG", message=str(e))

    backend_id = job["backend_id"]
    preset_id = job["preset_id"]
    format_id = job.get("format_id")
    aspect = job.get("aspect")
    width = int(job["width"])
    height = int(job["height"])
    wf_path = job["workflow_path"]

    eng = ensure_engine(
        family_for_i2v_backend(backend_id),
        server_address,
        caller=f"generate_i2v:{backend_id}",
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
            backend=backend_id,
        )

    # WanVideoSampler fails when latent spatial dims disagree (classic 960x540:
    # 540 % 16 != 0). Snap both axes; also normalize frame count to 4n+1.
    orig_w, orig_h, orig_f = width, height, num_frames
    width = _snap_dim(width, 16)
    height = _snap_dim(height, 16)
    num_frames = _snap_frames(num_frames)
    if (width, height, num_frames) != (orig_w, orig_h, orig_f):
        print(
            f"[WARN] I2V snap for Wan: {orig_w}x{orig_h} f={orig_f} "
            f"-> {width}x{height} f={num_frames} (dims %16, frames 4n+1)"
        )

    if backend_id != "wan22" and not workflow_path:
        # Only wan22 runner path is implemented in this module for now.
        # Explicit --workflow can still force a graph for experiments.
        if job["status"] != "ready":
            return fail_result(
                error="BACKEND_NOT_READY",
                message=f"Backend {backend_id} not implemented in generate_i2v runner",
                backend=backend_id,
            )

    if not os.path.exists(wf_path):
        print(f"Error: workflow not found: {wf_path}")
        return fail_result(error="WORKFLOW_MISSING", message=wf_path)

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

    print(
        f"I2V job backend={backend_id} format={format_id or '-'} "
        f"aspect={aspect or '-'} preset={preset_id} "
        f"{width}x{height} workflow={os.path.basename(wf_path)}"
    )
    print(f"Loading I2V workflow: {wf_path}")
    with open(wf_path, "r", encoding="utf-8") as f:
        ui_data = json.load(f)

    try:
        object_info = fetch_object_info(server_address)
    except Exception as e:
        print(f"[WARN] object_info fetch failed: {e}; conversion may be incomplete")
        object_info = {}

    api_prompt = convert_ui_to_api(ui_data, object_info, server_address)

    new_seed = seed if seed is not None else random.randint(1, 2**31 - 1)

    # --- wan22-specific graph injection (default path) ---
    if backend_id == "wan22" or "wan" in os.path.basename(wf_path).lower():
        model_high = r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf"
        model_low = r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf"
        lora_high = r"Wan2.2\Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
        lora_low = r"Wan2.2\Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
        loaders = _find_nodes(api_prompt, "WanVideoModelLoader")
        if len(loaders) >= 2:
            api_prompt[loaders[0]]["inputs"]["model"] = model_high
            api_prompt[loaders[0]]["inputs"]["quantization"] = "disabled"
            api_prompt[loaders[0]]["inputs"]["attention_mode"] = "sdpa"
            api_prompt[loaders[1]]["inputs"]["model"] = model_low
            api_prompt[loaders[1]]["inputs"]["quantization"] = "disabled"
            api_prompt[loaders[1]]["inputs"]["attention_mode"] = "sdpa"
        loras = _find_nodes(api_prompt, "WanVideoLoraSelect")
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
            api_prompt[nid]["inputs"]["model_name"] = "umt5-xxl-enc-bf16.safetensors"

        for nid in _find_nodes(api_prompt, "LoadImage"):
            api_prompt[nid]["inputs"]["image"] = temp_name

        for nid in _find_nodes(api_prompt, "WanVideoTextEncode"):
            api_prompt[nid]["inputs"]["positive_prompt"] = prompt_text
            api_prompt[nid]["inputs"]["negative_prompt"] = negative_text or DEFAULT_NEGATIVE

        for nid in _find_nodes(api_prompt, "ImageResizeKJv2"):
            api_prompt[nid]["inputs"]["width"] = width
            api_prompt[nid]["inputs"]["height"] = height

        for nid in _find_nodes(api_prompt, "WanVideoImageToVideoEncode"):
            inp = api_prompt[nid]["inputs"]
            inp["width"] = width
            inp["height"] = height
            inp["num_frames"] = num_frames

        for nid in _find_nodes(api_prompt, "WanVideoSampler"):
            inp = api_prompt[nid]["inputs"]
            if not (isinstance(inp.get("seed"), list) and len(inp.get("seed") or []) == 2):
                inp["seed"] = new_seed
            if not (isinstance(inp.get("cfg"), list) and len(inp.get("cfg") or []) == 2):
                inp["cfg"] = cfg

        for nid in _find_nodes(api_prompt, "INTConstant"):
            val = api_prompt[nid]["inputs"].get("value")
            if val == 30:
                api_prompt[nid]["inputs"]["value"] = steps

        for nid in _find_nodes(api_prompt, "VHS_VideoCombine"):
            inp = api_prompt[nid]["inputs"]
            inp["frame_rate"] = frame_rate
            inp["filename_prefix"] = "agent_i2v"
            inp["save_output"] = True
            inp["format"] = inp.get("format") or "video/h264-mp4"
    else:
        print(
            f"[ERROR] Runner has no inject path for backend={backend_id}. "
            "Add graph wiring or wait for backend implementation."
        )
        return fail_result(
            error="BACKEND_RUNNER_MISSING",
            message=f"no inject path for {backend_id}",
            backend=backend_id,
        )

    for _nid, node in api_prompt.items():
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
        err_msg = "execution error"
        for msg in status.get("messages") or []:
            if msg and msg[0] == "execution_error":
                err_msg = msg[1].get("exception_message") or err_msg
                print(
                    f"[ERROR] node={msg[1].get('node_id')} {msg[1].get('node_type')}: "
                    f"{str(err_msg)[:500]}"
                )
        return fail_result(
            error="EXECUTION_ERROR", message=str(err_msg)[:500], seed=new_seed, prompt_id=prompt_id
        )

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
        "backend": backend_id,
        "format": format_id,
        "preset": preset_id,
        "aspect": aspect or job["preset"].get("aspect"),
        "stage": job["preset"].get("stage"),
        "deliver_preset_hint": job.get("deliver_preset_id") or job.get("default_deliver_preset"),
        "workflow": os.path.basename(wf_path),
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
        backend=backend_id,
        preset=preset_id,
    )


def _build_parser() -> argparse.ArgumentParser:
    try:
        cfg = load_video_backends()
        backends = list_backend_ids(cfg)
        presets = list_preset_ids(cfg)
        formats = list_format_ids(cfg)
        default_backend = cfg.get("default_backend", "wan22")
        # None → resolve_i2v_job applies default_format from JSON
        default_format = None
        default_preset = None
    except Exception:
        backends = ["wan22", "ltx23"]
        presets = ["work_16x9_540"]
        formats = ["cinematic_16x9", "shorts_9x16", "classic_4x3", "portrait_3x4"]
        default_backend = "wan22"
        default_format = None
        default_preset = None

    parser = argparse.ArgumentParser(
        description=(
            "Image-to-Video multi-backend CLI. "
            "Aspect comes from --format (16:9 / 9:16 / 4:3 / 3:4 / 1:1), not a fixed global ratio."
        )
    )
    parser.add_argument("--input", "-i", required=True, help="Keyframe image path")
    parser.add_argument("--prompt", "-p", default=None, help="Motion / scene prompt")
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--negative-file", default=None)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument(
        "--backend",
        default=default_backend,
        help=f"I2V backend id (default: {default_backend}). Known: {', '.join(backends)}",
    )
    parser.add_argument(
        "--format",
        dest="format_id",
        default=default_format,
        help=(
            "Aspect/format profile (optional; default from video_backends.json "
            f"default_format). Known: {', '.join(formats)}. "
            "Examples: cinematic_16x9, shorts_9x16, classic_4x3, portrait_3x4."
        ),
    )
    parser.add_argument(
        "--preset",
        default=default_preset,
        help=(
            "Work resolution preset override (optional). "
            f"If omitted, format's default work preset is used. Known: {', '.join(presets)}"
        ),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Override preset width (use with --height)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Override preset height (use with --width)",
    )
    parser.add_argument("--frames", type=int, default=49, help="Frame count")
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--workflow",
        default=None,
        help="Override workflow path or catalog alias (skips backend workflow map)",
    )
    parser.add_argument("--meta-out", default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print presets from video_backends.json and exit",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Print backends from video_backends.json and exit",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="Print aspect/format profiles and exit",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    # allow --list-* without --input
    if any(a in ("--list-presets", "--list-backends", "--list-formats") for a in sys.argv[1:]):
        pre = argparse.ArgumentParser(add_help=False)
        pre.add_argument("--list-presets", action="store_true")
        pre.add_argument("--list-backends", action="store_true")
        pre.add_argument("--list-formats", action="store_true")
        pre_args, _ = pre.parse_known_args()
        cfg = load_video_backends()
        if pre_args.list_backends:
            for bid in list_backend_ids(cfg):
                b = cfg["backends"][bid]
                print(f"{bid}  status={b.get('status')}  {b.get('engine', '')}")
        if pre_args.list_formats:
            for fid in list_format_ids(cfg):
                f = cfg["formats"][fid]
                print(
                    f"{fid}  aspect={f.get('aspect')}  "
                    f"work={f.get('default_work_preset')}  "
                    f"deliver={f.get('default_deliver_preset')}"
                )
        if pre_args.list_presets:
            for pid in list_preset_ids(cfg):
                p = cfg["presets"][pid]
                print(
                    f"{pid}  {p['width']}x{p['height']}  "
                    f"aspect={p.get('aspect')}  stage={p.get('stage')}"
                )
        sys.exit(0)

    args = parser.parse_args()

    prompt = load_text(args.prompt_file) if args.prompt_file else (args.prompt or "")
    if not prompt:
        parser.error("--prompt or --prompt-file required")
    negative = load_text(args.negative_file) if args.negative_file else args.negative

    if (args.width is None) ^ (args.height is None):
        parser.error("Provide both --width and --height, or neither (use --format/--preset)")

    wf = None
    if args.workflow:
        wf = resolve_workflow(args.workflow)

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
        backend=args.backend,
        format_id=args.format_id,
        preset=args.preset,
        workflow_path=wf,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
    )
    sys.exit(0 if result.get("ok") else 1)
