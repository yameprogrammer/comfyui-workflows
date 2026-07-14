"""Convert ComfyUI UI workflow JSON to API prompt using live /object_info."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from lib.comfy_client import DEFAULT_SERVER, ensure_comfy_running


def fetch_object_info(server_address: str = DEFAULT_SERVER) -> dict:
    ensure_comfy_running(server_address)
    with urllib.request.urlopen(f"http://{server_address}/object_info", timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


_WIDGET_PRIMITIVES = frozenset({"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"})


def _widget_input_names(class_info: dict) -> list[str]:
    """Return ordered widget input names for a node class (required then optional)."""
    names: list[str] = []
    inp = class_info.get("input") or {}
    for section in ("required", "optional"):
        block = inp.get(section) or {}
        if not isinstance(block, dict):
            continue
        for name, spec in block.items():
            if not isinstance(spec, (list, tuple)) or not spec:
                continue
            first = spec[0]
            # COMBO options list
            if isinstance(first, list):
                names.append(name)
                continue
            if not isinstance(first, str):
                continue
            # Primitive widgets
            if first in _WIDGET_PRIMITIVES:
                names.append(name)
                continue
            # Connection-only custom types (MODEL, IMAGE, WANVIDEOMODEL, ...)
            # Skip pure socket types: all-caps / underscore tokens that are not primitives
            if first.isupper() or (
                first.replace("_", "").isalnum()
                and first == first.upper()
            ):
                continue
            # Fallback: treat as widget (rare)
            names.append(name)
    return names


def convert_ui_to_api(ui_data: dict, object_info: dict | None = None, server_address: str = DEFAULT_SERVER) -> dict:
    """
    Convert UI format workflow to API prompt dict.

    Uses /object_info widget order when available; falls back to link-only for unknown nodes.
    """
    if object_info is None:
        try:
            object_info = fetch_object_info(server_address)
        except Exception:
            object_info = {}

    api_data: dict[str, Any] = {}
    links = {l[0]: l for l in ui_data.get("links", [])}

    for node in ui_data.get("nodes", []):
        # Skip muted / bypassed
        if node.get("mode", 0) == 4:  # never / mute
            continue
        node_id = str(node["id"])
        class_type = node["type"]
        if class_type in ("Note", "Reroute", "PrimitiveNode"):
            continue

        inputs: dict[str, Any] = {}

        # Linked inputs
        for inp in node.get("inputs", []) or []:
            name = inp.get("name")
            link_id = inp.get("link")
            if name is None or link_id is None:
                continue
            if link_id in links:
                link = links[link_id]
                inputs[name] = [str(link[1]), link[2]]

        # Widget values
        widgets_values = node.get("widgets_values")
        class_info = object_info.get(class_type) or {}
        widget_names = _widget_input_names(class_info) if class_info else []

        def _set_widget(name: str, val: Any) -> None:
            # Linked inputs take precedence (ComfyUI: connection overrides widget)
            if name in inputs and isinstance(inputs[name], list) and len(inputs[name]) == 2:
                return
            inputs[name] = val

        if isinstance(widgets_values, dict):
            # e.g. VHS_VideoCombine
            for k, v in widgets_values.items():
                if k == "videopreview":
                    continue
                _set_widget(k, v)
        elif isinstance(widgets_values, list) and widget_names:
            # Skip control_after_generate style extras carefully
            wi = 0
            for name in widget_names:
                if wi >= len(widgets_values):
                    break
                val = widgets_values[wi]
                # seed nodes sometimes insert "randomize"/"fixed" after seed
                if name == "seed" and wi + 1 < len(widgets_values) and widgets_values[wi + 1] in (
                    "fixed",
                    "randomize",
                    "increment",
                    "decrement",
                ):
                    _set_widget(name, val)
                    wi += 2
                    continue
                _set_widget(name, val)
                wi += 1
        elif isinstance(widgets_values, list) and widgets_values:
            # Fallback: leave raw list under _widgets if no object_info
            inputs["_widgets_values"] = widgets_values

        api_data[node_id] = {"class_type": class_type, "inputs": inputs}

    return api_data
