"""LTX 2.3 AIO mode selection — [[P:]] mute rules (same as Orchestrator table).

Modes mirror the user workflow note (Select options table).
Applying modes sets Comfy node.mode: 0=ALWAYS, 2=NEVER on tagged nodes.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Iterable

# Official table (docs / Note 923)
# Keys: agent mode ids used in generate_s2v / ltx_s2v
AIO_MODE_PORTS: dict[str, set[str]] = {
    # Text to Video
    "t2v": {"01 Text to Video"},
    "t2v_audio": {"01 Text to Video", "Audio input"},
    # Image to Video
    "i2v": {"02 Image to Video"},
    "i2v_audio": {"02 Image to Video", "Audio input"},
    # First/Last
    "flf": {"02 Image to Video", "Last Frame input"},
    "flf_audio": {"02 Image to Video", "Last Frame input", "Audio input"},
    # First/Mid/Last
    "fml": {"02 Image to Video", "Last Frame input", "Mid Frame input"},
    "fml_audio": {
        "02 Image to Video",
        "Last Frame input",
        "Mid Frame input",
        "Audio input",
    },
    # Video to Video
    "v2v": {"03 Video to Video"},
    "v2v_audio": {"03 Video to Video", "Audio input"},
}

# All known port labels that appear in [[P:...]] titles
ALL_P_PORTS = {
    "01 Text to Video",
    "02 Image to Video",
    "03 Video to Video",
    "Audio input",
    "Last Frame input",
    "Mid Frame input",
}

MODE_ALWAYS = 0
MODE_NEVER = 2

_P_TAG_RE = re.compile(r"\[\[P:([^\]]+)\]\]")


def parse_p_tags(title: str | None) -> list[str]:
    if not title:
        return []
    return [m.group(1).strip() for m in _P_TAG_RE.finditer(title)]


def ports_for_mode(mode: str) -> set[str]:
    m = (mode or "i2v_audio").strip().lower().replace("-", "_")
    aliases = {
        "image": "i2v",
        "image_audio": "i2v_audio",
        "ia2v": "i2v_audio",
        "first_last": "flf",
        "first_last_audio": "flf_audio",
        "first_mid_last": "fml",
        "first_mid_last_audio": "fml_audio",
        "video": "v2v",
        "video_to_video": "v2v",
        "text": "t2v",
        "text_audio": "t2v_audio",
    }
    m = aliases.get(m, m)
    if m not in AIO_MODE_PORTS:
        raise ValueError(f"unknown AIO mode {mode!r}; known={list(AIO_MODE_PORTS)}")
    return set(AIO_MODE_PORTS[m])


def _node_should_be_active(title: str | None, active_ports: set[str]) -> bool | None:
    """Return True/False if node is P-tagged; None if untagged (leave mode alone)."""
    tags = parse_p_tags(title)
    if not tags:
        return None
    # Node active if ANY of its P-tags is in the selected mode set
    # (AIO titles usually have one primary port tag)
    return any(t in active_ports for t in tags)


def apply_mode_to_nodes(nodes: Iterable[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    """Mutate node modes for [[P:]] tags according to mode. Returns change log."""
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


def apply_aio_mode_to_ui_workflow(workflow: dict[str, Any], mode: str) -> dict[str, Any]:
    """Deep-copy UI workflow and apply mode mutes on root + all subgraphs."""
    wf = copy.deepcopy(workflow)
    log: list[dict[str, Any]] = []
    log.extend(apply_mode_to_nodes(wf.get("nodes") or [], mode))
    for sg in (wf.get("definitions") or {}).get("subgraphs") or []:
        log.extend(apply_mode_to_nodes(sg.get("nodes") or [], mode))
    wf["_agent_aio_mode"] = mode
    wf["_agent_aio_active_ports"] = sorted(ports_for_mode(mode))
    wf["_agent_aio_mode_changes"] = log
    return wf


def describe_mode(mode: str) -> dict[str, Any]:
    ports = sorted(ports_for_mode(mode))
    return {
        "mode": mode,
        "active_ports": ports,
        "inactive_ports": sorted(ALL_P_PORTS - set(ports)),
    }
