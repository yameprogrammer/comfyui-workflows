#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

p = Path("workflows/human/lonecat_krea2_v70/CAPABILITIES.json")
c = json.loads(p.read_text(encoding="utf-8"))
for f in c["features"]:
    fid = f.get("feature_id")
    if fid == "v70_style_ref_1":
        f["status"] = "ready"
        f["agent_cli"] = (
            'python scripts/generate_krea2_style.py -i style.png -p "..." -o out.png --seed 42'
        )
        f["agent_preset"] = "krea2_style_ref_v70"
        f["gap"] = "Minimal agent graph (not full v7 UI). Dual style still planned."
        f.pop("interim_cli", None)
    if fid == "v70_controlnet":
        f["status"] = "ready"
        f["agent_cli"] = (
            'python scripts/generate_krea2_control.py -i depth.png -p "..." -o out.png --seed 42'
        )
        f["agent_preset"] = "krea2_control_v70"
        f["gap"] = "Default depth-control-lora; pose maps OK if control image is a pose plate."
        f.pop("interim_cli", None)
c["status_counts"] = dict(Counter(f.get("status") for f in c["features"]))
p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(c["status_counts"])
