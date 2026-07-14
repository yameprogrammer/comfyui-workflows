"""Run LTX 2.3 AIO by loading the real UI workflow + mode mute switches.

This replaces ad-hoc mini graphs. Mode selection follows Orchestrator [[P:]] table.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT
from lib.ltx_aio_mode_select import apply_aio_mode_to_ui_workflow, describe_mode
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api

DEFAULT_UI_WF = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "ltx23AllInOneWorkflowForRTX_v44_IA2V.json",
)
# Base (unswitched) file also kept; IA2V snapshot is fine as start — we re-apply modes
DEFAULT_UI_WF_BASE = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "ltx23AllInOneWorkflowForRTX_v44.json",
)


def _load_ui(path: str | None = None) -> dict[str, Any]:
    p = path or os.environ.get("AGENT_LTX_AIO_UI_WORKFLOW") or DEFAULT_UI_WF
    if not os.path.isfile(p) and os.path.isfile(DEFAULT_UI_WF_BASE):
        p = DEFAULT_UI_WF_BASE
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _set(api: dict[str, Any], nid: str, key: str, value: Any) -> None:
    if nid not in api:
        return
    api[nid].setdefault("inputs", {})[key] = value


def build_aio_switched_api(
    *,
    mode: str,
    image_name: str | None = None,
    audio_name: str | None = None,
    last_image_name: str | None = None,
    mid_image_name: str | None = None,
    video_name: str | None = None,
    prompt: str = "",
    negative: str = "animation, cartoon, text",
    seed: int | None = None,
    audio_duration_sec: float | None = None,
    clip_length_sec: float | None = None,
    trim_start_sec: float = 0.0,
    longer_edge: int | None = None,
    aspect: str | None = None,
    fps: int = 24,
    filename_prefix: str = "agent_ltx_aio",
    ui_workflow_path: str | None = None,
    object_info: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply mode switches on real AIO UI WF, expand to API, inject run params."""
    ui = _load_ui(ui_workflow_path)
    ui = apply_aio_mode_to_ui_workflow(ui, mode)
    # Fetch object_info once if not provided (widget field names)
    if object_info is None:
        try:
            import json
            import urllib.request

            object_info = json.loads(
                urllib.request.urlopen(
                    "http://127.0.0.1:8188/object_info", timeout=60
                ).read()
            )
        except Exception:
            object_info = None
    api = expand_ui_workflow_to_api(ui, object_info=object_info)

    # lengths
    if audio_duration_sec is not None and audio_duration_sec > 0:
        trim_dur = float(audio_duration_sec)
    else:
        trim_dur = 3.0
    if clip_length_sec is None or clip_length_sec <= 0:
        # AIO Clip Length is whole seconds. Production default: audio + 1.5s then ceil.
        # S02 bench (2026-07-13): +1.5 (→6s on 3.72s VO) beat tight ceil(audio) for
        # lip + prop stability. Tight mode: AGENT_LTX_CLIP_TIGHT=1 or PAD_SEC=0.
        # AGENT_LTX_CLIP_PAD_SEC = fractional pad before ceil (default 1.5)
        # AGENT_LTX_CLIP_EXTRA_SEC = whole seconds after ceil (default 0)
        import os

        tight = os.environ.get("AGENT_LTX_CLIP_TIGHT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        default_pad = "0" if tight else "1.5"
        try:
            pad = float(os.environ.get("AGENT_LTX_CLIP_PAD_SEC", default_pad) or default_pad)
        except ValueError:
            pad = 0.0 if tight else 1.5
        try:
            extra = int(float(os.environ.get("AGENT_LTX_CLIP_EXTRA_SEC", "0") or 0))
        except ValueError:
            extra = 0
        if mode.endswith("_audio") or mode == "i2v_audio":
            clip_length_sec = float(
                int(math.ceil(trim_dur + pad - 1e-9)) + max(0, extra)
            )
        else:
            clip_length_sec = trim_dur
    clip_i = max(1, min(20, int(math.ceil(float(clip_length_sec) - 1e-9))))
    edge = int(longer_edge or 1024)
    edge = max(512, min(2048, int(round(edge / 64.0) * 64)))
    if aspect is None:
        aspect = "9:16"
    fps_i = int(fps if fps and fps > 0 else 24)

    # inject standard ports
    if image_name:
        _set(api, "149", "image", image_name)
    if audio_name:
        _set(api, "412", "audio", audio_name)
        if "412" in api:
            api["412"].get("inputs", {}).pop("audioUI", None)
    if last_image_name:
        _set(api, "786", "image", last_image_name)
    if mid_image_name:
        _set(api, "1705", "image", mid_image_name)
    # V2V video if present as VHS_LoadVideo
    if video_name and "787" in api:
        # widgets vary; set common field names
        _set(api, "787", "video", video_name)

    _set(api, "1792", "start_index", float(trim_start_sec))
    _set(api, "1792", "duration", float(trim_dur))
    _set(api, "196", "Xi", clip_i)
    _set(api, "196", "Xf", float(clip_i))
    _set(api, "196", "isfloatX", 0)
    _set(api, "1688", "Xi", edge)
    _set(api, "1688", "Xf", float(edge))
    _set(api, "1688", "isfloatX", 0)
    _set(api, "1774", "combo", aspect)
    _set(api, "869", "value", fps_i)
    if seed is not None:
        _set(api, "115", "noise_seed", int(seed))
    if prompt:
        _set(api, "1797", "text", prompt)
    _set(api, "1798", "switch", False)  # use Text Multiline, not LLM rewriter
    if negative:
        _set(api, "593", "text", negative)
    _set(api, "188", "filename_prefix", filename_prefix)
    _set(api, "188", "save_output", True)

    # Drop NEVER-mode nodes from API (safer than relying on Comfy mode field)
    # BUT keep nodes that are linked from ALWAYS path even if... no, NEVER should be skipped.
    # Removing NEVER nodes can break links; Comfy handles mode=2 by not executing.
    # Keep mode field on nodes.

    meta = {
        "runner": "ltx_aio_workflow_runner",
        "mode": mode,
        "mode_info": describe_mode(mode),
        "ui_workflow": ui_workflow_path or DEFAULT_UI_WF,
        "api_nodes": len(api),
        "trim_start_sec": float(trim_start_sec),
        "trim_duration_sec": float(trim_dur),
        "clip_length_sec": clip_i,
        "longer_edge": edge,
        "aspect": aspect,
        "fps": fps_i,
        "seed": seed,
        "mode_changes": len(ui.get("_agent_aio_mode_changes") or []),
        "active_ports": ui.get("_agent_aio_active_ports"),
    }
    return api, meta
