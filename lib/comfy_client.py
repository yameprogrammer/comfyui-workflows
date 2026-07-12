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


def _http_json(
    server_address: str,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 30,
) -> Any:
    """GET/POST JSON helper for Comfy API. path like '/system_stats'."""
    url = f"http://{server_address}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        raise ConnectionError(
            f"ComfyUI HTTP {e.code} at {server_address}{path}: {e.reason}. {err_body}"
        ) from e
    except urllib.error.URLError as e:
        raise ConnectionError(f"ComfyUI unreachable at {server_address}: {e}") from e


def get_system_stats(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    return _http_json(server_address, "/system_stats", timeout=15)


def get_queue(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    return _http_json(server_address, "/queue", timeout=15)


def interrupt_comfy(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    """POST /interrupt — stop current execution if any."""
    try:
        return _http_json(server_address, "/interrupt", method="POST", body={}, timeout=30)
    except ConnectionError:
        # Some builds accept empty POST without JSON body
        req = urllib.request.Request(
            f"http://{server_address}/interrupt", data=b"{}", method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}


def free_comfy_memory(
    server_address: str = DEFAULT_SERVER,
    *,
    unload_models: bool = True,
    free_memory: bool = True,
    timeout: float = 120,
) -> dict[str, Any]:
    """POST /free — unload models and/or free cached tensors.

    Only call when the execution queue is idle; mid-run free is often a no-op.
    """
    return _http_json(
        server_address,
        "/free",
        method="POST",
        body={"unload_models": bool(unload_models), "free_memory": bool(free_memory)},
        timeout=timeout,
    )


def memory_snapshot(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    """Normalize system_stats into GB/MB fields for guards and logs."""
    stats = get_system_stats(server_address)
    system = stats.get("system") or {}
    devices = stats.get("devices") or []
    dev = devices[0] if devices else {}
    ram_total = float(system.get("ram_total") or 0)
    ram_free = float(system.get("ram_free") or 0)
    vram_total = float(dev.get("vram_total") or 0)
    vram_free = float(dev.get("vram_free") or 0)
    torch_free = float(dev.get("torch_vram_free") or 0)
    return {
        "ram_total_gb": ram_total / (1024**3) if ram_total else 0.0,
        "ram_free_gb": ram_free / (1024**3) if ram_free else 0.0,
        "vram_total_mb": vram_total / (1024**2) if vram_total else 0.0,
        "vram_free_mb": vram_free / (1024**2) if vram_free else 0.0,
        "torch_vram_free_mb": torch_free / (1024**2) if torch_free else 0.0,
        "device_name": dev.get("name"),
        "argv": system.get("argv"),
        "raw": stats,
    }


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
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        raise ConnectionError(
            f"ComfyUI HTTP {e.code} at {server_address}: {e.reason}. {body}"
        ) from e
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


def extract_first_audio(history_entry: dict) -> tuple[str, str, str]:
    """Return (filename, subfolder, type) for first audio artifact in history."""
    outputs = history_entry.get("outputs", {})
    for _node_id, node_output in outputs.items():
        for key in ("audio", "audios"):
            if key not in node_output:
                continue
            items = node_output[key]
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
        # Some nodes put a single dict
        if isinstance(node_output.get("gifs"), list):
            pass
    raise FileNotFoundError("Output audio not found in ComfyUI history")


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


def download_audio(
    server_address: str,
    filename: str,
    subfolder: str,
    media_type: str,
    dest_path: str,
) -> str:
    """Same /view endpoint as images; works for SaveAudio outputs."""
    return download_image(server_address, filename, subfolder, media_type, dest_path)


def fail_result(**extra) -> dict:
    result = {"ok": False, "output_path": None, "seed": None, "prompt_id": None, "meta_path": None}
    result.update(extra)
    return result


def ok_result(**extra) -> dict:
    result = {"ok": True}
    result.update(extra)
    return result
