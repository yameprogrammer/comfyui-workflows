"""Shared ComfyUI API helpers and UI→API conversion."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


DEFAULT_SERVER = "127.0.0.1:8188"
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFYUI_INPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\input"
DEFAULT_TIMEOUT_SEC = 600
POLL_INTERVAL_SEC = 1.0

MODEL_MAPPING = {
    "real": "ZImageTurbo\\moodyRealMix_zitV6DPO.safetensors",
    "pro": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
    "wild": "ZImageTurbo\\moodyWildMixZIBZID_v01.safetensors",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_meta(path: str, data: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_meta_out(output_filename: str | None, meta_out: str | None) -> str | None:
    if meta_out:
        return meta_out
    if output_filename:
        base, _ = os.path.splitext(output_filename)
        return base + ".json"
    return None


def convert_ui_to_api(ui_data: dict) -> dict:
    """Convert ComfyUI UI workflow JSON to API prompt format."""
    api_data = {}
    links = {l[0]: l for l in ui_data.get("links", [])}

    for node in ui_data.get("nodes", []):
        node_id = str(node["id"])
        class_type = node["type"]
        inputs: dict[str, Any] = {}

        for inp in node.get("inputs", []):
            name = inp["name"]
            link_id = inp.get("link")
            if link_id is not None and link_id in links:
                link = links[link_id]
                origin_node_id = str(link[1])
                origin_output_index = link[2]
                inputs[name] = [origin_node_id, origin_output_index]

        widgets_values = node.get("widgets_values", []) or []

        if class_type == "CLIPLoader":
            if len(widgets_values) >= 3:
                inputs["clip_name"] = widgets_values[0]
                inputs["type"] = widgets_values[1]
                inputs["device"] = widgets_values[2]
        elif class_type == "VAELoader":
            if len(widgets_values) >= 1:
                inputs["vae_name"] = widgets_values[0]
        elif class_type == "UNETLoader":
            if len(widgets_values) >= 2:
                inputs["unet_name"] = widgets_values[0]
                inputs["weight_dtype"] = widgets_values[1]
        elif class_type == "ModelSamplingAuraFlow":
            if len(widgets_values) >= 1:
                inputs["shift"] = widgets_values[0]
        elif class_type == "KSampler":
            if len(widgets_values) >= 7:
                inputs["seed"] = widgets_values[0]
                inputs["steps"] = widgets_values[2]
                inputs["cfg"] = widgets_values[3]
                inputs["sampler_name"] = widgets_values[4]
                inputs["scheduler"] = widgets_values[5]
                inputs["denoise"] = widgets_values[6]
        elif class_type == "EmptySD3LatentImage":
            if len(widgets_values) >= 3:
                inputs["width"] = widgets_values[0]
                inputs["height"] = widgets_values[1]
                inputs["batch_size"] = widgets_values[2]
        elif class_type == "Prompt (LoraManager)":
            if len(widgets_values) >= 2:
                inputs["text"] = widgets_values[1]
        elif class_type == "Save Image (LoraManager)":
            if len(widgets_values) >= 2:
                inputs["filename_prefix"] = widgets_values[0]
                inputs["file_format"] = widgets_values[1]
        elif class_type == "Lora Loader (LoraManager)":
            if len(widgets_values) >= 3:
                inputs["text"] = widgets_values[1]
        elif class_type == "TriggerWord Toggle (LoraManager)":
            if len(widgets_values) >= 3:
                inputs["group_mode"] = widgets_values[0]
                inputs["default_active"] = widgets_values[1]
                inputs["allow_strength_adjustment"] = widgets_values[2]
        elif class_type == "CLIPTextEncode":
            if len(widgets_values) >= 1:
                inputs["text"] = widgets_values[0]
        elif class_type == "LoadImage":
            if len(widgets_values) >= 1:
                inputs["image"] = widgets_values[0]
                inputs["upload"] = "image"
        elif class_type == "VAEEncode":
            pass
        elif class_type == "ControlNetLoader":
            if len(widgets_values) >= 1:
                inputs["control_net_name"] = widgets_values[0]
        elif class_type == "FL_ZImageControlNetPatch":
            if len(widgets_values) >= 2:
                inputs["name"] = widgets_values[0]
                inputs["auto_config"] = widgets_values[1]
        elif class_type == "ZImageFunControlnet":
            if len(widgets_values) >= 1:
                inputs["strength"] = widgets_values[0]

        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type,
        }
    return api_data


def load_workflow(workflow_path: str) -> dict:
    with open(workflow_path, "r", encoding="utf-8") as f:
        return json.load(f)


def queue_prompt(server_address: str, api_prompt: dict) -> str:
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server_address}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["prompt_id"]
    except urllib.error.URLError as e:
        raise ConnectionError(f"ComfyUI unreachable at {server_address}: {e}") from e


def wait_for_history(
    server_address: str,
    prompt_id: str,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    poll_interval: float = POLL_INTERVAL_SEC,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server_address}/history/{prompt_id}", timeout=30
            ) as response:
                history = json.loads(response.read().decode("utf-8"))
                if prompt_id in history:
                    return history[prompt_id]
        except Exception:
            pass
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI timed out after {timeout_sec}s (prompt_id={prompt_id})")


def extract_first_image(history_entry: dict) -> tuple[str, str, str]:
    outputs = history_entry.get("outputs", {})
    for _node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                return (
                    img["filename"],
                    img.get("subfolder", ""),
                    img.get("type", "output"),
                )
    raise FileNotFoundError("Output image not found in ComfyUI history")


def download_image(
    server_address: str,
    filename: str,
    subfolder: str,
    image_type: str,
    dest_path: str,
) -> str:
    ensure_parent_dir(dest_path)
    view_url = (
        f"http://{server_address}/view?"
        f"filename={urllib.parse.quote(filename)}"
        f"&subfolder={urllib.parse.quote(subfolder)}"
        f"&type={image_type}"
    )
    urllib.request.urlretrieve(view_url, dest_path)
    return dest_path


def fail_result(**extra) -> dict:
    result = {"ok": False, "output_path": None, "seed": None, "prompt_id": None, "meta_path": None}
    result.update(extra)
    return result


def ok_result(**extra) -> dict:
    result = {"ok": True}
    result.update(extra)
    return result
