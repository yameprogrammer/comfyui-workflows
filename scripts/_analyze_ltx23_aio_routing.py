#!/usr/bin/env python3
"""Deep-analyze LTX2.3 AIO v44 routing: switches, muters, Set/Get bus, subgraphs.

Writes a machine-readable JSON summary next to the human workflow and prints
a human-readable report. Does NOT execute Comfy.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "human" / "ltx23AllInOneWorkflowForRTX_v44.json"
OUT_JSON = ROOT / "docs" / "_ltx23_aio_v44_routing_map.json"

# ComfyUI node modes
MODE_NAMES = {
    0: "ALWAYS",  # active
    1: "ON_EVENT",  # rarely used
    2: "NEVER",  # muted / bypassed for execution
    3: "ON_TRIGGER",
    4: "BYPASS",
}


def mode_name(m) -> str:
    try:
        return MODE_NAMES.get(int(m), f"mode_{m}")
    except Exception:
        return str(m)


def load() -> dict:
    return json.loads(WF.read_text(encoding="utf-8"))


def index_links(links) -> dict:
    # Root: list of [id, from_id, from_slot, to_id, to_slot, type]
    # Some subgraphs may store links as dict id -> list
    if links is None:
        return {}
    if isinstance(links, dict):
        out = {}
        for k, l in links.items():
            if isinstance(l, (list, tuple)) and len(l) >= 6:
                out[l[0] if not isinstance(l[0], dict) else k] = l
            else:
                out[k] = l
        return out
    out = {}
    for l in links:
        if isinstance(l, (list, tuple)) and len(l) >= 6:
            out[l[0]] = l
        elif isinstance(l, dict) and "id" in l:
            out[l["id"]] = l
    return out


def collect_nodes(container: dict) -> list[dict]:
    return list(container.get("nodes") or [])


def summarize_container(name: str, container: dict) -> dict:
    nodes = collect_nodes(container)
    links = container.get("links") or []
    types = Counter(n.get("type") for n in nodes)
    modes = Counter(mode_name(n.get("mode", 0)) for n in nodes)

    by_type: dict[str, list] = defaultdict(list)
    for n in nodes:
        by_type[n.get("type") or "?"].append(
            {
                "id": n.get("id"),
                "title": n.get("title") or "",
                "mode": n.get("mode", 0),
                "mode_name": mode_name(n.get("mode", 0)),
                "widgets": n.get("widgets_values"),
            }
        )

    # Routing-critical types
    routing_types = (
        "ComfySwitchNode",
        "OrchestratorNodeMuter",
        "SetNode",
        "GetNode",
        "Anything Everywhere",
        "Combo Clone",
        "Power Lora Loader (rgthree)",
    )
    routing = {t: by_type.get(t, []) for t in routing_types if t in by_type}

    # Ports labeled [[P:...]]
    ports = []
    for n in nodes:
        title = n.get("title") or ""
        m = re.search(r"\[\[P:([^\]]+)\]\]", title)
        if m:
            ports.append(
                {
                    "id": n.get("id"),
                    "type": n.get("type"),
                    "title": title,
                    "port_label": m.group(1).strip(),
                    "mode": n.get("mode", 0),
                    "mode_name": mode_name(n.get("mode", 0)),
                    "widgets": n.get("widgets_values"),
                }
            )

    # LTX / audio core
    ltx_keys = (
        "LTXV",
        "Audio",
        "EmptyLTXV",
        "ImgToVideo",
        "CreateVideo",
        "SaveVideo",
        "Unet",
        "DualClip",
        "GGUF",
        "Sampler",
        "CFG",
        "Guide",
        "VAE",
        "Concat",
        "Separate",
        "Mask",
    )
    ltx_nodes = []
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        if any(k.lower() in t.lower() or k.lower() in title.lower() for k in ltx_keys):
            ltx_nodes.append(
                {
                    "id": n.get("id"),
                    "type": t,
                    "title": title,
                    "mode": n.get("mode", 0),
                    "mode_name": mode_name(n.get("mode", 0)),
                }
            )

    return {
        "name": name,
        "node_count": len(nodes),
        "link_count": len(links),
        "type_counts": dict(types.most_common()),
        "mode_counts": dict(modes),
        "routing": routing,
        "ports_P": ports,
        "ltx_related": ltx_nodes,
    }


def detail_switches_and_muter(data: dict) -> dict:
    nodes = collect_nodes(data)
    by_id = {n["id"]: n for n in nodes if "id" in n}
    links = index_links(data.get("links") or [])

    def link_src(link_id):
        if link_id is None:
            return None
        l = links.get(link_id)
        if not l:
            return {"missing": link_id}
        return {
            "from_id": l[1],
            "from_slot": l[2],
            "to_id": l[3],
            "to_slot": l[4],
            "type": l[5],
            "from_title": (by_id.get(l[1]) or {}).get("title")
            or (by_id.get(l[1]) or {}).get("type"),
        }

    switches = []
    for n in nodes:
        if n.get("type") != "ComfySwitchNode":
            continue
        entry = {
            "id": n.get("id"),
            "title": n.get("title") or "",
            "mode": n.get("mode", 0),
            "mode_name": mode_name(n.get("mode", 0)),
            "widgets": n.get("widgets_values"),
            "properties": n.get("properties"),
            "inputs": [],
            "outputs": [],
        }
        for inp in n.get("inputs") or []:
            entry["inputs"].append(
                {
                    "name": inp.get("name"),
                    "type": inp.get("type"),
                    "from": link_src(inp.get("link")),
                }
            )
        for i, out in enumerate(n.get("outputs") or []):
            entry["outputs"].append(
                {
                    "slot": i,
                    "name": out.get("name"),
                    "type": out.get("type"),
                    "links": out.get("links"),
                }
            )
        switches.append(entry)

    muters = []
    for n in nodes:
        if n.get("type") != "OrchestratorNodeMuter":
            continue
        muters.append(
            {
                "id": n.get("id"),
                "title": n.get("title") or "",
                "mode": n.get("mode", 0),
                "widgets": n.get("widgets_values"),
                "properties": n.get("properties"),
                "inputs": [
                    {
                        "name": inp.get("name"),
                        "type": inp.get("type"),
                        "from": link_src(inp.get("link")),
                    }
                    for inp in (n.get("inputs") or [])
                ],
            }
        )

    # Set/Get bus variable names
    sets = []
    gets = []
    for n in nodes:
        if n.get("type") == "SetNode":
            wv = n.get("widgets_values") or []
            sets.append(
                {
                    "id": n.get("id"),
                    "var": wv[0] if wv else None,
                    "title": n.get("title") or "",
                }
            )
        if n.get("type") == "GetNode":
            wv = n.get("widgets_values") or []
            gets.append(
                {
                    "id": n.get("id"),
                    "var": wv[0] if wv else None,
                    "title": n.get("title") or "",
                }
            )

    bus = sorted({*(s["var"] for s in sets if s["var"]), *(g["var"] for g in gets if g["var"])})

    return {
        "ComfySwitchNode": switches,
        "OrchestratorNodeMuter": muters,
        "set_get_bus_vars": bus,
        "SetNode": sets,
        "GetNode": gets,
    }


def subgraph_audio_paths(sg: dict) -> dict:
    """Map audio-related chain inside main LTX subgraph."""
    nodes = collect_nodes(sg)
    links = index_links(sg.get("links") or [])
    by_id = {n["id"]: n for n in nodes if "id" in n}

    def consumers(node_id: int) -> list:
        out = []
        for l in links.values():
            if not isinstance(l, (list, tuple)) or len(l) < 6:
                continue
            if l[1] == node_id:
                tgt = by_id.get(l[3]) or {}
                out.append(
                    {
                        "to_id": l[3],
                        "to_type": tgt.get("type"),
                        "to_title": tgt.get("title") or "",
                        "to_mode": tgt.get("mode", 0),
                        "to_mode_name": mode_name(tgt.get("mode", 0)),
                        "link_type": l[5],
                        "to_slot": l[4],
                    }
                )
        return out

    interesting = []
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        if any(
            k in t or k in title
            for k in (
                "Audio",
                "ConcatAV",
                "SeparateAV",
                "EmptyLatentAudio",
                "AudioVideoMask",
                "ImgToVideo",
                "EmptyLTXV",
                "AddGuide",
                "CreateVideo",
                "SaveVideo",
            )
        ):
            interesting.append(
                {
                    "id": n.get("id"),
                    "type": t,
                    "title": title,
                    "mode": n.get("mode", 0),
                    "mode_name": mode_name(n.get("mode", 0)),
                    "widgets": n.get("widgets_values"),
                    "feeds": consumers(n.get("id")),
                }
            )
    return {"audio_ltx_chain_nodes": interesting}


def main() -> int:
    data = load()
    report = {
        "source": str(WF),
        "comfy_mode_legend": MODE_NAMES,
        "root": summarize_container("root", data),
        "routing_detail": detail_switches_and_muter(data),
        "subgraphs": [],
        "analysis_notes": [],
    }

    for sg in data.get("definitions", {}).get("subgraphs") or []:
        name = sg.get("name") or sg.get("id")
        sc = summarize_container(f"subgraph:{name}", sg)
        if "LTXV" in str(sc.get("type_counts")) or any(
            "LTXV" in t for t in (sc.get("type_counts") or {})
        ):
            sc["audio_path_detail"] = subgraph_audio_paths(sg)
        report["subgraphs"].append(sc)

    # High-level notes
    root_ports = report["root"]["ports_P"]
    report["analysis_notes"] = [
        "Root graph is primarily an ORCHESTRATION shell (Set/Get bus, switches, muter, loaders).",
        "Heavy LTX compute lives in subgraph(s), not only root nodes.",
        "Comfy node mode: 0=ALWAYS active, 2=NEVER muted, 4=BYPASS — Orchestrator/switches flip these.",
        "[[P:...]] titles are the public ports the user (and any API driver) must feed per mode.",
        "Agent mini-graphs that only do LoadAudio->Encode->Concat are NOT equivalent to AIO Audio input routing.",
        f"Root [[P:]] ports found: {len(root_ports)}",
        f"ComfySwitchNode count: {len(report['routing_detail']['ComfySwitchNode'])}",
        f"OrchestratorNodeMuter count: {len(report['routing_detail']['OrchestratorNodeMuter'])}",
        f"Set/Get bus vars: {report['routing_detail']['set_get_bus_vars']}",
    ]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")

    # Print concise human report
    print("\n========== LTX2.3 AIO v44 ROUTING ANALYSIS ==========")
    print("Source:", WF)
    print("\n[Root] nodes=", report["root"]["node_count"], "modes=", report["root"]["mode_counts"])
    print("Top types:", list(report["root"]["type_counts"].items())[:15])
    print("\n[[P:]] ports (user-facing inputs):")
    for p in root_ports:
        print(
            f"  - id={p['id']} mode={p['mode_name']} type={p['type']} "
            f"port={p['port_label']!r} title={p['title']!r}"
        )
    print("\nComfySwitchNode:")
    for s in report["routing_detail"]["ComfySwitchNode"]:
        print(f"  id={s['id']} title={s['title']!r} widgets={s['widgets']}")
        for inp in s["inputs"]:
            print(f"    in {inp['name']} from {inp['from']}")
    print("\nOrchestratorNodeMuter:")
    for m in report["routing_detail"]["OrchestratorNodeMuter"]:
        print(f"  id={m['id']} title={m['title']!r}")
        print(f"  widgets={json.dumps(m['widgets'], ensure_ascii=False)[:500]}")
        print(f"  properties keys={list((m.get('properties') or {}).keys())}")
    print("\nSet/Get bus vars:", report["routing_detail"]["set_get_bus_vars"])
    print("\nSubgraphs:")
    for sg in report["subgraphs"]:
        print(f"  {sg['name']}: nodes={sg['node_count']} modes={sg['mode_counts']}")
        if sg.get("audio_path_detail"):
            print("  Audio/LTX chain nodes in subgraph:")
            for n in sg["audio_path_detail"]["audio_ltx_chain_nodes"]:
                print(
                    f"    id={n['id']} {n['mode_name']:7s} {n['type']} "
                    f"title={n['title']!r}"
                )
    print("\nNotes:")
    for n in report["analysis_notes"]:
        print(" -", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
