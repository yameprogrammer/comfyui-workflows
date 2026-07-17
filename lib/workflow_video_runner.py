"""Queue API-format video workflows (VHS_LoadVideo → VHS_VideoCombine).

Companion to workflow_api_runner (image). Port patch + copy media + download first video.
"""

from __future__ import annotations

import copy
import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.workflow_api_runner import apply_ports, resolve_preset

COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"


def _read_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_nodes(api: dict, class_type: str) -> list[str]:
    return [nid for nid, n in api.items() if n.get("class_type") == class_type]


def extract_first_video(history: dict) -> tuple[str, str, str]:
    """Return (filename, subfolder, type) for first video-like output."""
    outputs = history.get("outputs") or {}
    for _nid, o in outputs.items():
        for key in ("gifs", "videos", "images"):
            items = o.get(key) or []
            for it in items:
                fn = it.get("filename") or ""
                if not fn:
                    continue
                lower = fn.lower()
                if key in ("gifs", "videos") or lower.endswith(
                    (".mp4", ".webm", ".gif", ".mkv", ".mov")
                ):
                    return fn, it.get("subfolder") or "", it.get("type") or "output"
    # fallback any image seq entry that is mp4
    for _nid, o in outputs.items():
        for items in o.values():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                fn = str(it.get("filename") or "")
                if fn.lower().endswith((".mp4", ".webm", ".mkv", ".mov")):
                    return fn, it.get("subfolder") or "", it.get("type") or "output"
    raise RuntimeError(f"No video in history outputs: {list(outputs.keys())}")


def _resolve_local_video(filename: str, subfolder: str, ftype: str) -> str:
    base = COMFY_OUTPUT_DIR if ftype != "temp" else COMFY_TEMP_DIR
    if ftype == "input":
        base = COMFYUI_INPUT_DIR
    parts = [base]
    if subfolder:
        parts.append(subfolder)
    parts.append(filename)
    return os.path.join(*parts)


def _normalize_local_model_paths(api: dict[str, Any]) -> list[str]:
    """Fix common bad paths from community packs (subdir prefix on text_encoders, etc.)."""
    notes: list[str] = []
    umt5_ok = "umt5-xxl-enc-bf16.safetensors"
    for nid, node in api.items():
        ct = node.get("class_type") or ""
        inp = node.setdefault("inputs", {})
        if ct == "WanVideoTextEncodeCached" and isinstance(inp.get("model_name"), str):
            raw = inp["model_name"]
            base = raw.replace("\\", "/").split("/")[-1]
            if base != raw or "WAN2.2" in raw or "Wan2.2" in raw:
                # text_encoders list is flat filenames only
                if "umt5" in base.lower() and "fp8" in base.lower():
                    base = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
                elif "umt5" in base.lower():
                    base = umt5_ok
                if base != raw:
                    notes.append(f"{nid}.model_name {raw!r} → {base!r}")
                    inp["model_name"] = base
        if ct == "WanVideoModelLoader":
            # fp16_fast needs torch nightly allow_fp16_accumulation — always ban on this machine
            bp = inp.get("base_precision")
            if bp != "bf16":
                notes.append(f"{nid}.base_precision {bp!r} → bf16")
                inp["base_precision"] = "bf16"
            if inp.get("quantization") not in (None, "disabled"):
                # GGUF requires quantization disabled
                if str(inp.get("model") or "").lower().endswith(".gguf"):
                    notes.append(f"{nid}.quantization → disabled (gguf)")
                    inp["quantization"] = "disabled"
            # torch.compile / fp16_fast traps
            if "compile_args" in inp:
                notes.append(f"{nid}.compile_args cleared")
                inp.pop("compile_args", None)
            # match stable agent I2V defaults
            if inp.get("attention_mode") in (None, "sageattn", "sage"):
                # keep sage only if env asks; default sdpa for reliability
                import os as _os

                if (_os.environ.get("AGENT_WAN_ATTENTION") or "").strip():
                    inp["attention_mode"] = _os.environ.get("AGENT_WAN_ATTENTION").strip()
                else:
                    if inp.get("attention_mode") != "sdpa":
                        notes.append(f"{nid}.attention_mode → sdpa")
                    inp["attention_mode"] = "sdpa"
            inp.setdefault("load_device", "offload_device")
        if ct == "WanVideoVAELoader" and isinstance(inp.get("model_name"), str):
            raw = inp["model_name"]
            base = raw.replace("\\", "/").split("/")[-1]
            if base != raw:
                notes.append(f"{nid}.vae {raw!r} → {base!r}")
                inp["model_name"] = base
        # Drop non-essential output noise nodes if still present
        if ct in ("PlaySound|pysssss", "FancyNoteNode", "FancyTimerNode"):
            notes.append(f"drop noise node {nid} ({ct})")
    # actually drop noise nodes
    for nid, node in list(api.items()):
        ct = node.get("class_type") or ""
        if ct in ("PlaySound|pysssss", "FancyNoteNode", "FancyTimerNode", "Note"):
            api.pop(nid, None)
    return notes


def run_workflow_video(
    preset: str,
    *,
    ports: dict[str, Any] | None = None,
    output_path: str | None = None,
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 1800,
    seed: int | None = None,
) -> dict[str, Any]:
    try:
        api_path, ports_path = resolve_preset(preset)
    except FileNotFoundError as e:
        return fail_result(error="PRESET_MISSING", message=str(e))

    api = _read_json(api_path)
    if not isinstance(api, dict) or "nodes" in api:
        return fail_result(
            error="UI_FORMAT_NOT_API",
            message=f"{api_path} must be API format",
        )

    ports_spec: dict[str, Any] = {"ports": {}, "defaults": {}}
    if ports_path and os.path.isfile(ports_path):
        ports_spec = _read_json(ports_path)

    values = dict(ports or {})
    if seed is not None:
        values.setdefault("seed", int(seed))
    elif "seed" in (ports_spec.get("ports") or {}) and "seed" not in values:
        values["seed"] = random.randint(1, 2**31 - 1)

    # unique VHS prefix when not provided
    if "filename_prefix" not in values:
        values["filename_prefix"] = f"{Path(api_path).stem}_{int(time.time())}"

    try:
        api = copy.deepcopy(api)
        norm_notes = _normalize_local_model_paths(api)
        if norm_notes:
            print("[workflow_video] normalize:", "; ".join(norm_notes[:8]))
        apply_ports(api, ports_spec, values)
    except Exception as e:
        return fail_result(error="PORT_PATCH_FAILED", message=str(e))

    # seed patch on samplers if present
    if "seed" in values:
        for nid in _find_nodes(api, "WanVideoSampler"):
            inp = api[nid].setdefault("inputs", {})
            if not isinstance(inp.get("seed"), list):
                inp["seed"] = int(values["seed"])

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e))

    try:
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        return fail_result(error="COMFY_TIMEOUT", message=str(e), prompt_id=prompt_id)
    except Exception as e:
        return fail_result(error="EXEC_FAILED", message=str(e), prompt_id=prompt_id)

    try:
        filename, subfolder, ftype = extract_first_video(history)
    except Exception as e:
        return fail_result(error="NO_VIDEO_OUTPUT", message=str(e), prompt_id=prompt_id)

    src = _resolve_local_video(filename, subfolder, ftype)
    if not output_path:
        output_path = os.path.join(r"F:\generated_videos", filename)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    if not os.path.isfile(src):
        return fail_result(
            error="VIDEO_FILE_MISSING",
            message=f"Comfy reported {filename} but not found at {src}",
            prompt_id=prompt_id,
        )
    shutil.copy2(src, output_path)

    meta = {
        "mode": "workflow_video",
        "workflow_api": os.path.abspath(api_path),
        "ports_file": os.path.abspath(ports_path) if ports_path else None,
        "preset": preset,
        "seed": values.get("seed"),
        "ports_applied": {
            k: (v if k not in ("input_video", "positive") else str(v)[:200])
            for k, v in values.items()
        },
        "comfy_prompt_id": prompt_id,
        "comfy_video": {"filename": filename, "subfolder": subfolder, "type": ftype},
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
    }
    meta_path = meta_out
    if meta_path is None and output_path:
        meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    if meta_path:
        write_meta(meta_path, meta)

    return ok_result(
        output_path=os.path.abspath(output_path),
        seed=values.get("seed"),
        prompt_id=prompt_id,
        meta=meta,
        meta_path=meta_path,
        workflow_api=os.path.abspath(api_path),
    )
