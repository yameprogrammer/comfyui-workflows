#!/usr/bin/env python3
"""Analyze user-saved ltx23AllInOneWorkflowForRTX_v44_IA2V.json vs base AIO."""
from __future__ import annotations

import json
import re
from pathlib import Path

IA2V = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\ltx23AllInOneWorkflowForRTX_v44_IA2V.json"
)
ORIG = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\ltx23AllInOneWorkflowForRTX_v44.json"
)
OUT = Path(__file__).resolve().parents[1] / "docs" / "_ltx23_aio_IA2V_saved_diff.json"

MODE = {0: "ALWAYS", 1: "ON_EVENT", 2: "NEVER", 3: "ON_TRIGGER", 4: "BYPASS"}


def mode_name(m) -> str:
    try:
        return MODE.get(int(m), f"mode_{m}")
    except Exception:
        return str(m)


def main() -> None:
    data = json.loads(IA2V.read_text(encoding="utf-8"))
    odata = json.loads(ORIG.read_text(encoding="utf-8")) if ORIG.exists() else None

    report: dict = {
        "source": str(IA2V),
        "size": IA2V.stat().st_size,
        "root_nodes": len(data.get("nodes") or []),
        "subgraphs": [],
    }

    print("=== FILE ===")
    print(IA2V)
    print("size", report["size"], "root nodes", report["root_nodes"])

    # Orchestrator
    print("\n=== OrchestratorNodeMuter ===")
    orch = []
    for n in data.get("nodes") or []:
        if n.get("type") != "OrchestratorNodeMuter":
            continue
        entry = {
            "id": n.get("id"),
            "title": n.get("title"),
            "mode": n.get("mode"),
            "widgets_values": n.get("widgets_values"),
            "properties": n.get("properties"),
        }
        orch.append(entry)
        print("id", n.get("id"), "title", n.get("title"))
        print("widgets", n.get("widgets_values"))
        props = n.get("properties") or {}
        print("group_id", props.get("group_id"), "node_mode", props.get("node_mode"))
    report["orchestrator"] = orch

    # Switches
    print("\n=== ComfySwitchNode ===")
    switches = []
    for n in data.get("nodes") or []:
        if n.get("type") != "ComfySwitchNode":
            continue
        switches.append(
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "mode": n.get("mode"),
                "widgets": n.get("widgets_values"),
            }
        )
        print("id", n.get("id"), "widgets", n.get("widgets_values"))
    report["switches"] = switches

    # [[P:]] ports
    print("\n=== Root [[P:]] ports ===")
    ports = []
    for n in sorted(data.get("nodes") or [], key=lambda x: x.get("id") or 0):
        title = n.get("title") or ""
        m = re.search(r"\[\[P:([^\]]+)\]\]", title)
        if not m:
            continue
        ports.append(
            {
                "id": n.get("id"),
                "type": n.get("type"),
                "port": m.group(1).strip(),
                "title": title,
                "mode": n.get("mode"),
                "mode_name": mode_name(n.get("mode")),
                "widgets": n.get("widgets_values"),
            }
        )
        print(
            f"  id={n.get('id')} mode={mode_name(n.get('mode')):7s} "
            f"type={n.get('type')} port={m.group(1).strip()!r}"
        )
    report["ports_P"] = ports

    # LoadAudio / Trim
    print("\n=== Audio loaders / trim ===")
    for n in data.get("nodes") or []:
        t = n.get("type") or ""
        if t in ("LoadAudio", "TrimAudioDuration") or "Audio" in (n.get("title") or ""):
            print(
                f"  id={n.get('id')} mode={mode_name(n.get('mode'))} "
                f"type={t} title={n.get('title')!r} widgets={n.get('widgets_values')}"
            )

    # Clip length / sliders
    print("\n=== Clip length / size sliders ===")
    for n in data.get("nodes") or []:
        title = (n.get("title") or "") + " " + (n.get("type") or "")
        if any(k in title for k in ("Clip Length", "Longer Edge", "Aspect", "fps", "Slider")):
            print(
                f"  id={n.get('id')} type={n.get('type')} title={n.get('title')!r} "
                f"widgets={n.get('widgets_values')}"
            )

    # Diff modes vs original
    if odata:
        print("\n=== Root mode changes vs original ===")
        on = {n["id"]: n for n in odata.get("nodes") or []}
        changed = []
        for n in data.get("nodes") or []:
            o = on.get(n.get("id"))
            if not o:
                continue
            if o.get("mode") != n.get("mode"):
                changed.append(
                    {
                        "id": n.get("id"),
                        "type": n.get("type"),
                        "title": n.get("title"),
                        "from": mode_name(o.get("mode")),
                        "to": mode_name(n.get("mode")),
                    }
                )
                print(
                    f"  id={n.get('id')} {n.get('type')} title={n.get('title')!r} "
                    f"{mode_name(o.get('mode'))} -> {mode_name(n.get('mode'))}"
                )
        report["root_mode_changes"] = changed

        # orchestrator widget diff
        o_orch = next(
            (n for n in odata.get("nodes") or [] if n.get("type") == "OrchestratorNodeMuter"),
            None,
        )
        n_orch = next(
            (n for n in data.get("nodes") or [] if n.get("type") == "OrchestratorNodeMuter"),
            None,
        )
        if o_orch and n_orch:
            print("\n=== Orchestrator widgets diff ===")
            print("  orig", o_orch.get("widgets_values"))
            print("  IA2V", n_orch.get("widgets_values"))
            report["orchestrator_widgets_orig"] = o_orch.get("widgets_values")
            report["orchestrator_widgets_ia2v"] = n_orch.get("widgets_values")

        # subgraph diffs
        if (odata.get("definitions") or {}).get("subgraphs") and (
            data.get("definitions") or {}
        ).get("subgraphs"):
            osg = odata["definitions"]["subgraphs"][0]
            nsg = data["definitions"]["subgraphs"][0]
            on2 = {n["id"]: n for n in osg.get("nodes") or []}
            changed2 = []
            print("\n=== Subgraph mode changes (titled or important) ===")
            for n in nsg.get("nodes") or []:
                o = on2.get(n.get("id"))
                if not o or o.get("mode") == n.get("mode"):
                    continue
                title = n.get("title") or ""
                t = n.get("type") or ""
                entry = {
                    "id": n.get("id"),
                    "type": t,
                    "title": title,
                    "from": mode_name(o.get("mode")),
                    "to": mode_name(n.get("mode")),
                }
                changed2.append(entry)
                if title or any(
                    k in t
                    for k in (
                        "Audio",
                        "Trim",
                        "Mask",
                        "ImgToVideo",
                        "Concat",
                        "Empty",
                        "Guide",
                        "Sampler",
                    )
                ):
                    print(
                        f"  id={n.get('id')} {mode_name(o.get('mode'))}->{mode_name(n.get('mode'))} "
                        f"{t} {title!r}"
                    )
            report["subgraph_mode_changes"] = changed2
            print("  total subgraph mode flips:", len(changed2))

            # Active Audio-related in IA2V subgraph
            print("\n=== IA2V subgraph Audio-related (ALWAYS only) ===")
            for n in nsg.get("nodes") or []:
                if n.get("mode") not in (0, None):
                    continue
                t = n.get("type") or ""
                title = n.get("title") or ""
                if any(
                    k in t or k in title
                    for k in (
                        "Audio",
                        "Trim",
                        "ConcatAV",
                        "EmptyLatentAudio",
                        "AudioVideoMask",
                        "LoadAudio",
                    )
                ):
                    print(
                        f"  ALWAYS id={n.get('id')} {t} title={title!r} "
                        f"widgets={n.get('widgets_values')}"
                    )

            print("\n=== IA2V subgraph [[P:Audio input]] nodes (any mode) ===")
            for n in nsg.get("nodes") or []:
                title = n.get("title") or ""
                if "Audio input" in title:
                    print(
                        f"  id={n.get('id')} mode={mode_name(n.get('mode'))} "
                        f"{n.get('type')} widgets={n.get('widgets_values')}"
                    )

    # Load models on root
    print("\n=== Root model loaders ===")
    for n in data.get("nodes") or []:
        t = n.get("type") or ""
        if any(k in t for k in ("Unet", "DualClip", "GGUF", "VAELoader", "Lora", "CLIP")):
            print(
                f"  id={n.get('id')} mode={mode_name(n.get('mode'))} {t} "
                f"title={n.get('title')!r} widgets={n.get('widgets_values')}"
            )

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
