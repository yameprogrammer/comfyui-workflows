"""Flatten image_z_image_turbo_fun_union_controlnet UI+subgraph → API prompt."""
from __future__ import annotations

import _bootstrap  # noqa: F401
import json
import copy
from pathlib import Path

from lib.comfy_ui_convert import convert_ui_to_api, fetch_object_info

SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_z_image_turbo_fun_union_controlnet.json"
)
OUT_API = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\agent\presets"
    r"\zimage_fun_union_controlnet.api.json"
)
OUT_PORTS = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\agent\presets"
    r"\zimage_fun_union_controlnet.ports.json"
)


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    sg = (d.get("definitions") or {}).get("subgraphs")[0]
    print("subgraph", sg.get("name"), "id", sg.get("id"))

    # Print full subgraph links and inputNode/outputNode
    print("inputNode", json.dumps(sg.get("inputNode"), indent=2)[:800])
    print("outputNode", json.dumps(sg.get("outputNode"), indent=2)[:800])
    print("links:")
    for L in sg.get("links") or []:
        print(" ", L)

    # Try convert of full workflow as-is (may drop subgraph)
    oi = fetch_object_info()
    api_raw = convert_ui_to_api(d, oi)
    print("raw convert n nodes", len(api_raw))
    for nid, n in api_raw.items():
        print(f"  {nid}: {n.get('class_type')} inputs={list((n.get('inputs') or {}).keys())}")

    # Build flat UI: outer non-subgraph nodes + expanded subgraph nodes
    # with remapped IDs
    outer_nodes = [n for n in d["nodes"] if n.get("type") != sg["id"]]
    # remove MarkdownNote
    outer_nodes = [n for n in outer_nodes if n.get("type") not in ("MarkdownNote", "Note", "Reroute")]

    # Subgraph internal: use original IDs if no collision; outer uses 9,56,57,58,62
    # subgraph uses 39-47,60,64,69 — no collision
    sub_nodes = copy.deepcopy(sg.get("nodes") or [])
    sub_links = copy.deepcopy(sg.get("links") or [])

    # Comfy subgraph links can be list or dict-shaped — normalize
    print("sub link types", type(sub_links[0]) if sub_links else None)
    if sub_links and isinstance(sub_links[0], dict):
        # format: {id, origin_id, origin_slot, target_id, target_slot, type}
        flat_links = []
        for L in sub_links:
            flat_links.append(
                [
                    L.get("id"),
                    L.get("origin_id"),
                    L.get("origin_slot"),
                    L.get("target_id"),
                    L.get("target_slot"),
                    L.get("type"),
                ]
            )
        sub_links = flat_links
        print("normalized sub links:")
        for L in sub_links:
            print(" ", L)

    # Outer links excluding those into/out of subgraph node 70
    outer_links = []
    for L in d.get("links") or []:
        # L = [id, from_node, from_slot, to_node, to_slot, type]
        if L[1] == 70 or L[3] == 70:
            print("boundary link", L)
            continue
        outer_links.append(L)

    # Subgraph input: control IMAGE from Canny 57:0 → into subgraph image
    # Need to find which internal node receives the subgraph image input
    # Look at inputNode
    print("\n--- resolve subgraph boundary ---")
    # inputNode often has outputs that fan into internal graph
    inp = sg.get("inputNode") or {}
    outn = sg.get("outputNode") or {}
    print("inputNode full", json.dumps(inp, indent=2)[:2000])
    print("outputNode full", json.dumps(outn, indent=2)[:2000])

    # Also check subgraph.inputs[].linkIds against sub links
    for si in sg.get("inputs") or []:
        print("sg.input", si.get("name"), si.get("label"), "linkIds", si.get("linkIds"))


if __name__ == "__main__":
    main()
