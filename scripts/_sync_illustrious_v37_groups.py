#!/usr/bin/env python3
"""Sync Standard_V37 GROUPS.json from UI bounding boxes."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUMAN = ROOT / "workflows" / "human" / "illustrious_standard_v37"
COMFY_UI = (
    Path(r"F:/ComfyUI_windows_portable/ComfyUI/user/default/workflows")
    / "[Anime]Standard_V37.json"
)
PACK_UI = HUMAN / "Standard_V37.json"
GROUPS_OUT = HUMAN / "GROUPS.json"


def main() -> None:
    if COMFY_UI.is_file():
        shutil.copy2(COMFY_UI, PACK_UI)
        print("synced UI", COMFY_UI, "->", PACK_UI)
    ui = json.loads(PACK_UI.read_text(encoding="utf-8"))
    groups: dict = {}
    for g in ui.get("groups") or []:
        title = g.get("title") or ""
        color = g.get("color") or ""
        bounding = g.get("bounding") or [0, 0, 0, 0]
        bx, by, bw, bh = bounding[:4]
        nids = []
        defaults = {}
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
        groups[title] = {
            "color": color,
            "bounding": [bx, by, bw, bh],
            "node_ids": sorted(nids),
            "default_modes": defaults,
        }
    out = {
        "workflow": "Standard_V37",
        "source": "[Anime]Standard_V37.json",
        "groups": groups,
    }
    GROUPS_OUT.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("groups", len(groups))
    for t, g in groups.items():
        print(f"  {t}: nodes={len(g['node_ids'])}")


if __name__ == "__main__":
    main()
