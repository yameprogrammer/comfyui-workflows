#!/usr/bin/env python3
"""Find port inject targets for Advanced / Detailer Control Center."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"F:/ComfyUI_workflows/_lonecat_v17_extract/v37")


def dump(name: str) -> None:
    ui = json.loads((ROOT / name).read_text(encoding="utf-8"))
    print(f"\n======== {name} ========")
    for n in ui["nodes"]:
        t = n.get("type") or ""
        title = n.get("title") or ""
        nid = n.get("id")
        wv = n.get("widgets_values")
        mode = n.get("mode", 0)
        interesting = any(
            k in t or k in title
            for k in (
                "Wildcard",
                "Checkpoint",
                "KSampler",
                "Seed",
                "EmptyLatent",
                "Image Saver",
                "Lora",
                "LoadImage",
                "ImpactSwitch",
                "TIPO",
                "IPAdapter",
                "Openpose",
                "ControlNet",
                "Inpaint",
                "Outpaint",
                "Input Parameters",
            )
        )
        if interesting:
            wshort = None
            if isinstance(wv, list):
                wshort = [
                    x
                    for x in wv[:8]
                    if not isinstance(x, (dict, list)) or isinstance(x, str)
                ]
            print(f"  #{nid} mode={mode} type={t!r} title={title!r} wv={wshort}")


if __name__ == "__main__":
    dump("Advanced_V37.json")
    dump("Detailer_V37.json")
