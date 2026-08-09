#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

# CAPABILITIES
p = Path("workflows/human/lonecat_krea2_v70/CAPABILITIES.json")
c = json.loads(p.read_text(encoding="utf-8"))
updates = {
    "v70_detailer_hands": {
        "status": "ready",
        "agent_cli": "python scripts/generate_krea2_hand_detail.py -i still.png -o hands.png",
        "agent_preset": "krea2_hand_detail_v70",
    },
    "v70_moodboard": {
        "status": "ready",
        "agent_cli": 'python scripts/generate_krea2_moodboard.py --query "golden hour" --prompt "portrait" -o out.png',
    },
    "v70_rmbg": {
        "status": "ready",
        "feature_id": "v70_rmbg",
        "name": "Remove background",
        "category": "post",
        "agent_cli": "python scripts/generate_rmbg.py -i person.png -o cutout.png",
        "when_to_use": "Cut out subject (u2net_human_seg)",
    },
}
# ensure rmbg feature exists
ids = {f.get("feature_id") for f in c["features"]}
if "v70_rmbg" not in ids:
    c["features"].append(
        {
            "feature_id": "v70_rmbg",
            "name": "Remove background",
            "category": "post",
            "ui_groups": ["#      Remove Background!"],
            "status": "ready",
            "agent_cli": "python scripts/generate_rmbg.py -i person.png -o cutout.png",
            "when_to_use": "Subject cutout for composites",
        }
    )
for f in c["features"]:
    fid = f.get("feature_id")
    if fid in updates:
        f.update(updates[fid])
c["status_counts"] = dict(Counter(x.get("status") for x in c["features"]))
p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("caps", c["status_counts"])

cat_path = Path("workflows/agent/catalog.json")
cat = json.loads(cat_path.read_text(encoding="utf-8"))
cat["workflows"]["krea2_hand_detail_v70"] = {
    "file": "presets/krea2_hand_detail_v70.api.json",
    "ports": "presets/krea2_hand_detail_v70.ports.json",
    "format": "api",
    "role": "hand_detailer",
    "family": "krea2",
    "status": "ready",
    "used_by": ["scripts/generate_krea2_hand_detail.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "smoke": "dumps/krea2_qa_hands.png",
}
cat["workflows"]["krea2_moodboard"] = {
    "file": None,
    "role": "moodboard_prompt_t2i",
    "family": "krea2",
    "status": "ready",
    "runner": "lib/krea2_moodboard.py",
    "used_by": ["scripts/generate_krea2_moodboard.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "smoke": "dumps/krea2_qa_moodboard.png",
}
cat["workflows"]["rmbg_u2net"] = {
    "file": "presets/rmbg_u2net.api.json",
    "ports": "presets/rmbg_u2net.ports.json",
    "format": "api",
    "role": "remove_background",
    "status": "ready",
    "used_by": ["scripts/generate_rmbg.py"],
    "smoke": "dumps/krea2_qa_rmbg.png",
}
cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("catalog ok")
