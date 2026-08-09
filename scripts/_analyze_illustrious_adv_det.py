#!/usr/bin/env python3
"""Analyze Advanced_V37 / Detailer_V37 groups vs Standard_V37."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"F:/ComfyUI_workflows/_lonecat_v17_extract/v37")
OUT = Path(__file__).resolve().parents[1] / "workflows" / "human"


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def group_info(ui: dict) -> dict[str, dict]:
    groups = {}
    for g in ui.get("groups") or []:
        title = g.get("title") or ""
        color = g.get("color") or ""
        bounding = g.get("bounding") or [0, 0, 0, 0]
        bx, by, bw, bh = bounding[:4]
        nids = []
        defaults = {}
        types = set()
        for n in ui.get("nodes") or []:
            pos = n.get("pos") or [0, 0]
            if isinstance(pos, dict):
                x, y = pos.get("x", 0), pos.get("y", 0)
            else:
                x, y = pos[0], pos[1]
            if bx <= x <= bx + bw and by <= y <= by + bh:
                nid = int(n["id"])
                nids.append(nid)
                defaults[str(nid)] = int(n.get("mode", 0) or 0)
                types.add(n.get("type") or "")
        groups[title] = {
            "color": color,
            "bounding": [bx, by, bw, bh],
            "node_ids": sorted(nids),
            "default_modes": defaults,
            "node_types": sorted(types),
            "n_on": sum(1 for m in defaults.values() if m == 0),
            "n_off": sum(1 for m in defaults.values() if m == 4),
        }
    return groups


def key_models(ui: dict) -> list[str]:
    hits = []
    for n in ui.get("nodes") or []:
        wv = n.get("widgets_values")
        if not isinstance(wv, list):
            continue
        for v in wv:
            if isinstance(v, str) and any(
                v.endswith(ext) for ext in (".pt", ".pth", ".safetensors", ".gguf")
            ):
                hits.append(f"{n.get('id')}:{n.get('type')}:{v}")
    return sorted(set(hits))


def main() -> None:
    std = load("Standard_V37.json")
    adv = load("Advanced_V37.json")
    det = load("Detailer_V37.json")
    gs, ga, gd = group_info(std), group_info(adv), group_info(det)
    print("=== COUNTS ===")
    print("Standard nodes", len(std["nodes"]), "groups", len(gs))
    print("Advanced nodes", len(adv["nodes"]), "groups", len(ga))
    print("Detailer nodes", len(det["nodes"]), "groups", len(gd))
    print("\n=== GROUP TITLES only Advanced ===")
    for t in sorted(set(ga) - set(gs)):
        g = ga[t]
        print(f"  + {t!r} color={g['color']} nodes={len(g['node_ids'])} on={g['n_on']} off={g['n_off']}")
        print(f"      types={g['node_types'][:12]}")
    print("\n=== GROUP TITLES only Detailer ===")
    for t in sorted(set(gd) - set(gs)):
        g = gd[t]
        print(f"  + {t!r} color={g['color']} nodes={len(g['node_ids'])} on={g['n_on']} off={g['n_off']}")
        print(f"      types={g['node_types'][:12]}")
    print("\n=== shared group titles ===")
    for t in sorted(set(ga) & set(gs)):
        print(f"  = {t}")
    print("\n=== Advanced model files (sample) ===")
    for h in key_models(adv)[:40]:
        print(" ", h)
    print("\n=== Detailer model files ===")
    for h in key_models(det)[:40]:
        print(" ", h)
    # dump group jsons for pack
    for name, gmap in (
        ("Advanced_V37", ga),
        ("Detailer_V37", gd),
    ):
        clean = {
            t: {
                "color": g["color"],
                "bounding": g["bounding"],
                "node_ids": g["node_ids"],
                "default_modes": g["default_modes"],
            }
            for t, g in gmap.items()
        }
        path = OUT / f"_tmp_{name}_groups.json"
        path.write_text(json.dumps({"groups": clean}, indent=2, ensure_ascii=False), encoding="utf-8")
        print("wrote", path)


if __name__ == "__main__":
    main()
