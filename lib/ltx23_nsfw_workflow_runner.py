"""Kenpechi LTX 2.3 v2.0 NSFW packs — run the **real UI workflow**.

No mini graphs. No node deletion for quality. Only:

  1. Load human UI JSON (SSOT)
  2. Apply Fast Groups Bypasser-equivalent **group switches** (mode ALWAYS/NEVER)
  3. Expand UI → API (``ltx_aio_ui_expand``)
  4. Inject ports only: image / prompt / negative / seed / size / length / fps
  5. Queue + copy first video

Switches: ``lib/ltx23_nsfw_switches.py``
CLIs: ``scripts/generate_ltx_nsfw_i2v.py``, ``scripts/generate_ltx_nsfw_director.py``
"""

from __future__ import annotations

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
from lib.ltx23_nsfw_switches import apply_switch_profile, list_profiles
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api
from lib.workflow_video_runner import extract_first_video, _resolve_local_video

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_NSFW_DIR = WORKSPACE_ROOT / "workflows" / "human" / "ltx23_nsfw"
I2V_UI = HUMAN_NSFW_DIR / "ltx23I2VWorkflow_v20.json"
DIRECTOR_UI = HUMAN_NSFW_DIR / "ltx23DirectorWorkflow_directorV20.json"

DEFAULT_PROFILE = "gguf_10eros"


def _load_ui(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"UI workflow not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _stage_image(image_path: str) -> str:
    src = Path(image_path)
    if not src.is_file():
        raise FileNotFoundError(f"image not found: {image_path}")
    dest_dir = Path(COMFYUI_INPUT_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"ltx_nsfw_{int(time.time())}_{src.name}"
    shutil.copy2(src, dest_dir / name)
    return name


def _patch_mx_slider(ui: dict[str, Any], title: str, value: float | int) -> bool:
    for n in ui.get("nodes") or []:
        if n.get("type") != "mxSlider":
            continue
        if (n.get("title") or "") != title:
            continue
        old = n.get("widgets_values") or [value, value, 0]
        is_float = old[2] if len(old) >= 3 else 0
        n["widgets_values"] = [value, float(value) if is_float else value, is_float]
        return True
    return False


def _inject_machine_safe_ports(ui: dict[str, Any]) -> None:
    """Minimal machine fixes — keep nodes, only change widgets that crash this host.

    RTX 4090 + torch 2.6: ModelPatchTorchSettings fp16_accumulation needs 2.7.1+.
    """
    for n in ui.get("nodes") or []:
        if n.get("type") == "ModelPatchTorchSettings":
            w = list(n.get("widgets_values") or [True])
            if w:
                w[0] = False  # enable_fp16_accumulation
            n["widgets_values"] = w


def _inject_i2v_ports(
    ui: dict[str, Any],
    *,
    image_name: str,
    prompt: str,
    negative: str | None,
    seed: int,
    width: int | None,
    height: int | None,
    length_sec: float | None,
    fps: int | None,
    filename_prefix: str,
) -> None:
    """Port patch only — does not rewire graph."""
    _inject_machine_safe_ports(ui)
    for n in ui.get("nodes") or []:
        if n.get("type") == "LoadImage":
            w = n.get("widgets_values") or ["", "image"]
            n["widgets_values"] = [image_name, w[1] if len(w) > 1 else "image"]

    for n in ui.get("nodes") or []:
        if n.get("type") != "CLIPTextEncode":
            continue
        w = n.get("widgets_values") or [""]
        text = str(w[0]) if w else ""
        low = text.lower()
        is_neg = (
            "censor" in low
            or "watermark" in low
            or "background music" in low
            or "still image" in low
        )
        if is_neg:
            if negative is not None:
                n["widgets_values"] = [negative]
        else:
            n["widgets_values"] = [prompt]

    if width is not None:
        _patch_mx_slider(ui, "Base Width", int(width))
    if height is not None:
        _patch_mx_slider(ui, "Base Height", int(height))
    if length_sec is not None:
        _patch_mx_slider(ui, "Length (Seconds)", float(length_sec))
    if fps is not None:
        _patch_mx_slider(ui, "Base Frame Rate (24 Default)", int(fps))
        _patch_mx_slider(ui, "Target Frame Rate", int(fps))

    # Seed on SamplerCustom inside First/Upscale pass subgraphs (pack default)
    for sg in (ui.get("definitions") or {}).get("subgraphs") or []:
        for inode in sg.get("nodes") or []:
            if inode.get("type") == "SamplerCustom":
                w = list(inode.get("widgets_values") or [True, seed, "fixed", 1])
                if len(w) >= 2:
                    w[1] = int(seed)
                if len(w) >= 3:
                    w[2] = "fixed"
                inode["widgets_values"] = w
            if inode.get("type") == "VHS_VideoCombine":
                wv = inode.get("widgets_values")
                if isinstance(wv, dict):
                    wv = dict(wv)
                    pref = str(wv.get("filename_prefix") or "")
                    if "first" in pref.lower():
                        wv["filename_prefix"] = f"{filename_prefix}_first"
                    else:
                        wv["filename_prefix"] = filename_prefix
                    if fps is not None:
                        wv["frame_rate"] = int(fps)
                    inode["widgets_values"] = wv


def _inject_director_ports(
    ui: dict[str, Any],
    *,
    prompt: str,
    motion_prompt: str | None,
    negative: str | None,
    seed: int,
    width: int | None,
    height: int | None,
    fps: int | None,
    filename_prefix: str,
) -> None:
    _inject_machine_safe_ports(ui)
    for n in ui.get("nodes") or []:
        if n.get("type") != "CLIPTextEncode":
            continue
        w = n.get("widgets_values") or [""]
        text = str(w[0]) if w else ""
        low = text.lower()
        if negative is not None and (
            "censor" in low or "watermark" in low or "background music" in low
        ):
            n["widgets_values"] = [negative]

    for n in ui.get("nodes") or []:
        if n.get("type") != "LTXDirector":
            continue
        w = list(n.get("widgets_values") or [])
        if len(w) > 6:
            blob = w[6]
            if isinstance(blob, str) and blob.strip().startswith("{"):
                try:
                    data = json.loads(blob)
                    data["global_prompt"] = prompt
                    w[6] = json.dumps(data, ensure_ascii=False)
                except Exception:
                    pass
            elif isinstance(blob, dict):
                blob = dict(blob)
                blob["global_prompt"] = prompt
                w[6] = blob
        if motion_prompt is not None and len(w) > 7:
            w[7] = motion_prompt
        if fps is not None and len(w) > 14:
            w[14] = int(fps)
        if width is not None and len(w) > 16:
            w[16] = int(width)
        if height is not None and len(w) > 17:
            w[17] = int(height)
        n["widgets_values"] = w

    for sg in (ui.get("definitions") or {}).get("subgraphs") or []:
        for inode in sg.get("nodes") or []:
            if inode.get("type") == "SamplerCustom":
                wv = list(inode.get("widgets_values") or [True, seed, "fixed", 1])
                if len(wv) >= 2:
                    wv[1] = int(seed)
                if len(wv) >= 3:
                    wv[2] = "fixed"
                inode["widgets_values"] = wv
            if inode.get("type") == "VHS_VideoCombine":
                wv = inode.get("widgets_values")
                if isinstance(wv, dict):
                    wv = dict(wv)
                    wv["filename_prefix"] = filename_prefix
                    if fps is not None:
                        wv["frame_rate"] = int(fps)
                    inode["widgets_values"] = wv


def build_i2v_api(
    *,
    image_path: str,
    prompt: str,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    length_sec: float | None = None,
    fps: int | None = None,
    filename_prefix: str = "ltx23_nsfw_i2v",
    profile: str = DEFAULT_PROFILE,
    rife: bool | None = None,
    ui_path: str | Path | None = None,
    server_address: str = DEFAULT_SERVER,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _load_ui(ui_path or I2V_UI)
    ui = apply_switch_profile(raw, profile, rife=rife)
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    image_name = _stage_image(image_path)
    _inject_i2v_ports(
        ui,
        image_name=image_name,
        prompt=prompt,
        negative=negative,
        seed=seed_i,
        width=width,
        height=height,
        length_sec=length_sec,
        fps=fps,
        filename_prefix=filename_prefix,
    )
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    api = _repair_final_upscale_passthrough(api)
    meta = {
        "tool": "ltx23_nsfw_i2v",
        "workflow": str(ui_path or I2V_UI),
        "profile": profile,
        "rife": ui.get("_agent_nsfw_rife"),
        "switch_changes": len(ui.get("_agent_nsfw_switch_log") or []),
        "seed": seed_i,
        "image_name": image_name,
        "width": width,
        "height": height,
        "length_sec": length_sec,
        "fps": fps,
        "api_nodes": len(api),
        "policy": "adult_18_plus_only",
        "runner": "real_ui + group_switches + expand + ports",
    }
    return api, meta


def _repair_final_upscale_passthrough(api: dict[str, Any]) -> dict[str, Any]:
    """When Final Upscale group is OFF, UI bypasses ImageScale/RTX (pass-through).

    Pack wires RIFE / Don't Use RIFE images from ImageScale. After expand those
    nodes are omitted — reattach images from Upscale Pass decode (IMAGE).
    Does not delete pack nodes; only repairs broken links.
    """
    # Prefer tiled VAE decode from upscale pass, else any VAEDecode IMAGE
    image_src = None
    for nid, node in api.items():
        ct = node.get("class_type") or ""
        if ct in (
            "LTXVTiledVAEDecode",
            "LTXVSpatioTemporalTiledVAEDecode",
            "VAEDecode",
        ):
            # upscale pass instance ids start with upscale subgraph instance
            if ":" in str(nid):
                image_src = [str(nid), 0]
                if "LTXV" in ct or "Tiled" in ct:
                    break
    if image_src is None:
        return api

    for nid, node in api.items():
        if node.get("class_type") != "VHS_VideoCombine":
            continue
        ins = node.setdefault("inputs", {})
        if "images" not in ins or not isinstance(ins.get("images"), list):
            ins["images"] = list(image_src)
    return api


def build_director_api(
    *,
    prompt: str,
    motion_prompt: str | None = None,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: int | None = None,
    filename_prefix: str = "ltx23_nsfw_director",
    profile: str = DEFAULT_PROFILE,
    rife: bool | None = None,
    ui_path: str | Path | None = None,
    server_address: str = DEFAULT_SERVER,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _load_ui(ui_path or DIRECTOR_UI)
    ui = apply_switch_profile(raw, profile, rife=rife)
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    _inject_director_ports(
        ui,
        prompt=prompt,
        motion_prompt=motion_prompt,
        negative=negative,
        seed=seed_i,
        width=width,
        height=height,
        fps=fps,
        filename_prefix=filename_prefix,
    )
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    meta = {
        "tool": "ltx23_nsfw_director",
        "workflow": str(ui_path or DIRECTOR_UI),
        "profile": profile,
        "rife": ui.get("_agent_nsfw_rife"),
        "switch_changes": len(ui.get("_agent_nsfw_switch_log") or []),
        "seed": seed_i,
        "width": width,
        "height": height,
        "fps": fps,
        "api_nodes": len(api),
        "policy": "adult_18_plus_only",
        "runner": "real_ui + group_switches + expand + ports",
        "note": "LTXDirector timeline/media from pack; prefer I2V for single-image clips.",
    }
    return api, meta


def run_api_video(
    api: dict[str, Any],
    meta: dict[str, Any],
    *,
    output_path: str,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 2400,
) -> dict[str, Any]:
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
        return fail_result(
            error="NO_VIDEO_OUTPUT",
            message=str(e),
            prompt_id=prompt_id,
            history_keys=list((history.get("outputs") or {}).keys()),
        )

    src = _resolve_local_video(filename, subfolder, ftype)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    if not os.path.isfile(src):
        return fail_result(
            error="VIDEO_FILE_MISSING",
            message=f"Comfy reported {filename} but missing at {src}",
            prompt_id=prompt_id,
        )
    shutil.copy2(src, output_path)
    out_meta = {
        **meta,
        "comfy_prompt_id": prompt_id,
        "comfy_video": {"filename": filename, "subfolder": subfolder, "type": ftype},
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
        "role": "nsfw_video",
    }
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    write_meta(meta_path, out_meta)
    return ok_result(meta_path=meta_path, **out_meta)


def generate_ltx_nsfw_i2v(
    *,
    image_path: str,
    prompt: str,
    output_path: str,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    length_sec: float | None = None,
    fps: int | None = None,
    profile: str = DEFAULT_PROFILE,
    rife: bool | None = None,
    timeout_sec: float = 2400,
    server_address: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    api, meta = build_i2v_api(
        image_path=image_path,
        prompt=prompt,
        negative=negative,
        seed=seed,
        width=width,
        height=height,
        length_sec=length_sec,
        fps=fps,
        profile=profile,
        rife=rife,
        server_address=server_address,
    )
    return run_api_video(
        api, meta, output_path=output_path, server_address=server_address, timeout_sec=timeout_sec
    )


def generate_ltx_nsfw_director(
    *,
    prompt: str,
    output_path: str,
    motion_prompt: str | None = None,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: int | None = None,
    profile: str = DEFAULT_PROFILE,
    rife: bool | None = None,
    timeout_sec: float = 3600,
    server_address: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    api, meta = build_director_api(
        prompt=prompt,
        motion_prompt=motion_prompt,
        negative=negative,
        seed=seed,
        width=width,
        height=height,
        fps=fps,
        profile=profile,
        rife=rife,
        server_address=server_address,
    )
    return run_api_video(
        api, meta, output_path=output_path, server_address=server_address, timeout_sec=timeout_sec
    )


def describe_profiles() -> list[dict[str, Any]]:
    return list_profiles()
