"""LTX 2.3 AIO mode selection — mirrors UI **Select options** (OrchestratorNodeMuter).

UI table (Note 923 / black switch node):
  Text to Video              → 01 Text to Video
  Text + Audio               → 01 Text to Video + Audio input
  Image to Video             → 02 Image to Video
  Image + Audio (SI2V)       → 02 Image to Video + Audio input
  First/Last Frame           → 02 + Last Frame input
  First/Last + Audio         → 02 + Last + Audio
  First/Mid/Last             → 02 + Last + Mid Frame input
  First/Mid/Last + Audio     → 02 + Last + Mid + Audio
  Video to Video             → 03 Video to Video
  Video + Audio              → 03 + Audio input

Agent path (API, no frontend Orchestrator JS):
  apply_aio_mode_to_ui_workflow(mode)
    → set node.mode ALWAYS/NEVER for titles containing [[P:<port>]]
    → same effect as Orchestrator multi-select toggles for group_id=P

Do not rename group **P** or [[P:]] tags.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

from lib.comfy_client import WORKSPACE_ROOT

# Official Select options → agent mode ids (generate_s2v / ltx_s2v)
AIO_MODE_PORTS: dict[str, set[str]] = {
    "t2v": {"01 Text to Video"},
    "t2v_audio": {"01 Text to Video", "Audio input"},
    "i2v": {"02 Image to Video"},
    "i2v_audio": {"02 Image to Video", "Audio input"},
    "flf": {"02 Image to Video", "Last Frame input"},
    "flf_audio": {"02 Image to Video", "Last Frame input", "Audio input"},
    "fml": {"02 Image to Video", "Last Frame input", "Mid Frame input"},
    "fml_audio": {
        "02 Image to Video",
        "Last Frame input",
        "Mid Frame input",
        "Audio input",
    },
    "v2v": {"03 Video to Video"},
    "v2v_audio": {"03 Video to Video", "Audio input"},
}

ALL_P_PORTS = {
    "01 Text to Video",
    "02 Image to Video",
    "03 Video to Video",
    "Audio input",
    "Last Frame input",
    "Mid Frame input",
}

# Sorted discovery order used by Orchestrator JS when building toggles
ORCHESTRATOR_TAG_ORDER = sorted(ALL_P_PORTS)

MODE_ALWAYS = 0
MODE_NEVER = 2

_P_TAG_RE = re.compile(r"\[\[P:([^\]]+)\]\]")

# feature_id → mode (agent catalog)
FEATURE_TO_MODE: dict[str, str] = {
    "mode_t2v": "t2v",
    "mode_t2v_audio": "t2v_audio",
    "mode_i2v": "i2v",
    "mode_i2v_audio": "i2v_audio",
    "mode_flf": "flf",
    "mode_flf_audio": "flf_audio",
    "mode_fml": "fml",
    "mode_fml_audio": "fml_audio",
    "mode_v2v": "v2v",
    "mode_v2v_audio": "v2v_audio",
    # short aliases
    "t2v": "t2v",
    "t2v_audio": "t2v_audio",
    "i2v": "i2v",
    "i2v_audio": "i2v_audio",
    "flf": "flf",
    "flf_audio": "flf_audio",
    "fml": "fml",
    "fml_audio": "fml_audio",
    "v2v": "v2v",
    "v2v_audio": "v2v_audio",
    "si2v": "i2v_audio",
    "ia2v": "i2v_audio",
}

MODE_TO_BACKEND: dict[str, str] = {
    "t2v": "ltx23_aio_t2v",
    "t2v_audio": "ltx23_aio_t2v_audio",
    "i2v": "ltx23_aio_i2v",
    "i2v_audio": "ltx23_aio",
    "flf": "ltx23_aio_flf",
    "flf_audio": "ltx23_aio_flf_audio",
    "fml": "ltx23_aio_fml",
    "fml_audio": "ltx23_aio_fml_audio",
    "v2v": "ltx23_aio_v2v",
    "v2v_audio": "ltx23_aio_v2v_audio",
}

MODE_LABELS: dict[str, str] = {
    "t2v": "Text to Video",
    "t2v_audio": "Text + Audio to Video",
    "i2v": "Image to Video",
    "i2v_audio": "Image + Audio to Video",
    "flf": "First/Last Frame to Video",
    "flf_audio": "First/Last Frame + Audio",
    "fml": "First/Mid/Last Frame to Video",
    "fml_audio": "First/Mid/Last + Audio",
    "v2v": "Video to Video",
    "v2v_audio": "Video to Video + Audio",
}

MODE_REQUIRED_INPUTS: dict[str, list[str]] = {
    "t2v": ["prompt"],
    "t2v_audio": ["prompt", "audio"],
    "i2v": ["image", "prompt"],
    "i2v_audio": ["image", "audio", "prompt"],
    "flf": ["image", "last_image", "prompt"],
    "flf_audio": ["image", "last_image", "audio", "prompt"],
    "fml": ["image", "mid_image", "last_image", "prompt"],
    "fml_audio": ["image", "mid_image", "last_image", "audio", "prompt"],
    "v2v": ["video", "prompt"],
    "v2v_audio": ["video", "audio", "prompt"],
}

CAPABILITIES_PATH = os.path.join(
    WORKSPACE_ROOT, "workflows", "human", "LTX23_AIO_v44_CAPABILITIES.json"
)
FEATURE_PRESETS_PATH = os.path.join(
    WORKSPACE_ROOT, "workflows", "agent", "presets", "ltx23_aio_feature_presets.json"
)


def parse_p_tags(title: str | None) -> list[str]:
    if not title:
        return []
    return [m.group(1).strip() for m in _P_TAG_RE.finditer(title)]


def normalize_mode(mode: str | None) -> str:
    m = (mode or "i2v_audio").strip().lower().replace("-", "_").replace("+", "_")
    aliases = {
        "image": "i2v",
        "image_audio": "i2v_audio",
        "image_to_video": "i2v",
        "ia2v": "i2v_audio",
        "si2v": "i2v_audio",
        "first_last": "flf",
        "first_last_audio": "flf_audio",
        "first_mid_last": "fml",
        "first_mid_last_audio": "fml_audio",
        "video": "v2v",
        "video_to_video": "v2v",
        "video_audio": "v2v_audio",
        "text": "t2v",
        "text_audio": "t2v_audio",
        "text_to_video": "t2v",
        "mode_t2v": "t2v",
        "mode_t2v_audio": "t2v_audio",
        "mode_i2v": "i2v",
        "mode_i2v_audio": "i2v_audio",
        "mode_flf": "flf",
        "mode_flf_audio": "flf_audio",
        "mode_fml": "fml",
        "mode_fml_audio": "fml_audio",
        "mode_v2v": "v2v",
        "mode_v2v_audio": "v2v_audio",
    }
    m = aliases.get(m, m)
    if m not in AIO_MODE_PORTS:
        raise ValueError(
            f"unknown AIO mode {mode!r}; known={sorted(AIO_MODE_PORTS)} "
            f"or feature_id in {sorted(FEATURE_TO_MODE)}"
        )
    return m


def ports_for_mode(mode: str) -> set[str]:
    return set(AIO_MODE_PORTS[normalize_mode(mode)])


def resolve_feature(
    feature_or_mode: str | None = None,
    *,
    mode: str | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """
    Resolve agent selection to mode + backend + select_options.

    Accepts feature_id (mode_i2v_audio), mode (i2v_audio), or backend (ltx23_aio_flf).
    """
    from lib.ltx_s2v import BACKEND_TO_AIO_MODE, resolve_aio_mode

    if mode:
        m = normalize_mode(mode)
    elif feature_or_mode:
        raw = str(feature_or_mode).strip()
        if raw in FEATURE_TO_MODE:
            m = FEATURE_TO_MODE[raw]
        elif raw.startswith("ltx23_"):
            m = resolve_aio_mode(raw, None)
        else:
            m = normalize_mode(raw)
    elif backend:
        m = resolve_aio_mode(backend, None)
    else:
        m = "i2v_audio"

    ports = sorted(ports_for_mode(m))
    return {
        "feature_id": f"mode_{m}",
        "mode": m,
        "label": MODE_LABELS.get(m, m),
        "select_options": ports,
        "select_options_on": ports,
        "backend": MODE_TO_BACKEND.get(m, BACKEND_TO_AIO_MODE.get(f"ltx23_aio_{m}", "ltx23_aio")),
        "required_inputs": list(MODE_REQUIRED_INPUTS.get(m, ["prompt"])),
        "needs_audio": "Audio input" in ports,
        "cli": (
            f"python scripts/generate_s2v.py --backend {MODE_TO_BACKEND.get(m, 'ltx23_aio')} "
            f"--ltx-mode {m}"
        ),
    }


def list_features() -> list[dict[str, Any]]:
    """All Select-options modes for agent menus / --list."""
    out = []
    for m in (
        "t2v",
        "t2v_audio",
        "i2v",
        "i2v_audio",
        "flf",
        "flf_audio",
        "fml",
        "fml_audio",
        "v2v",
        "v2v_audio",
    ):
        out.append(resolve_feature(mode=m))
    return out


def load_capabilities() -> dict[str, Any]:
    if os.path.isfile(CAPABILITIES_PATH):
        with open(CAPABILITIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"features": list_features(), "select_options_ports": sorted(ALL_P_PORTS)}


def _node_should_be_active(title: str | None, active_ports: set[str]) -> bool | None:
    """True/False if P-tagged; None if untagged (leave mode alone)."""
    tags = parse_p_tags(title)
    if not tags:
        return None
    # Match Orchestrator JS: group P, tag in selection
    return any(t in active_ports for t in tags)


def apply_mode_to_nodes(
    nodes: Iterable[dict[str, Any]], mode: str
) -> list[dict[str, Any]]:
    """Mutate node modes for [[P:]] tags according to Select options mode."""
    active = ports_for_mode(mode)
    changes: list[dict[str, Any]] = []
    for n in nodes:
        title = n.get("title") or ""
        decision = _node_should_be_active(title, active)
        if decision is None:
            continue
        new_mode = MODE_ALWAYS if decision else MODE_NEVER
        old = n.get("mode", 0)
        if old != new_mode:
            changes.append(
                {
                    "id": n.get("id"),
                    "title": title,
                    "type": n.get("type"),
                    "from": old,
                    "to": new_mode,
                }
            )
        n["mode"] = new_mode
    return changes


def _sync_orchestrator_widgets(nodes: list[dict[str, Any]], mode: str) -> None:
    """
    Best-effort: set OrchestratorNodeMuter widgets_values to reflect multi-select.

    Frontend rebuilds widgets from active tags; for saved JSON we store a flat
    list of bools matching sorted tag order when possible.
    """
    active = ports_for_mode(mode)
    # Pattern observed: [bool, null, bool, null, ...] or pure bool list
    for n in nodes:
        if n.get("type") != "OrchestratorNodeMuter":
            continue
        tags = ORCHESTRATOR_TAG_ORDER
        # Prefer pure bool list aligned to sorted tags
        n["widgets_values"] = [tag in active for tag in tags]
        n.setdefault("properties", {})["group_id"] = "P"
        n["properties"]["node_mode"] = False  # multiple selection
        n["_agent_select_options"] = sorted(active)


def apply_aio_mode_to_ui_workflow(
    workflow: dict[str, Any], mode: str
) -> dict[str, Any]:
    """Deep-copy UI workflow and apply Select-options mutes on root + subgraphs."""
    m = normalize_mode(mode)
    wf = copy.deepcopy(workflow)
    log: list[dict[str, Any]] = []
    root_nodes = wf.get("nodes") or []
    log.extend(apply_mode_to_nodes(root_nodes, m))
    _sync_orchestrator_widgets(root_nodes, m)
    for sg in (wf.get("definitions") or {}).get("subgraphs") or []:
        log.extend(apply_mode_to_nodes(sg.get("nodes") or [], m))
    feat = resolve_feature(mode=m)
    wf["_agent_aio_mode"] = m
    wf["_agent_aio_active_ports"] = feat["select_options"]
    wf["_agent_aio_feature"] = feat
    wf["_agent_aio_mode_changes"] = log
    return wf


def describe_mode(mode: str) -> dict[str, Any]:
    return resolve_feature(mode=mode)
