#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

p = Path("workflows/human/lonecat_krea2_v70/CAPABILITIES.json")
c = json.loads(p.read_text(encoding="utf-8"))
updates = {
    "v70_style_ref_2": {
        "status": "ready",
        "agent_cli": 'python scripts/generate_krea2_style.py -i a.png --style-image-2 b.png -p "..." -o dual.png',
        "agent_preset": "krea2_dual_style_v70",
    },
    "v70_img_prompt": {
        "status": "ready",
        "agent_cli": "python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png",
    },
    "v70_prompt_enhancer": {
        "status": "ready_via_other_tool",
        "agent_cli": "python scripts/generate_krea2_img_prompt.py -i ref.png --caption-only",
        "note": "Florence caption covers enhancer need for agents; Qwen VL GGUF enhancer still optional",
    },
    "v70_detailer_face": {
        "status": "ready",
        "agent_cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png",
        "agent_preset": "krea2_face_detail_v70",
    },
}
for f in c["features"]:
    fid = f.get("feature_id")
    if fid in updates:
        f.update(updates[fid])
        f.pop("interim_cli", None)
c["status_counts"] = dict(Counter(x.get("status") for x in c["features"]))
p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(c["status_counts"])

cat_path = Path("workflows/agent/catalog.json")
cat = json.loads(cat_path.read_text(encoding="utf-8"))
cat["workflows"]["krea2_dual_style_v70"] = {
    "file": "presets/krea2_dual_style_v70.api.json",
    "ports": "presets/krea2_dual_style_v70.ports.json",
    "format": "api",
    "role": "t2i_dual_style_reference",
    "family": "krea2",
    "status": "ready",
    "used_by": ["scripts/generate_krea2_style.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "smoke": "dumps/krea2_dual_style_smoke.png",
}
cat["workflows"]["krea2_face_detail_v70"] = {
    "file": "presets/krea2_face_detail_v70.api.json",
    "ports": "presets/krea2_face_detail_v70.ports.json",
    "format": "api",
    "role": "face_detailer",
    "family": "krea2",
    "status": "ready",
    "used_by": ["scripts/generate_krea2_face_detail.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "smoke": "dumps/krea2_face_detail_smoke.png",
}
cat["workflows"]["krea2_img_prompt"] = {
    "file": None,
    "role": "image_caption_then_t2i",
    "family": "krea2",
    "status": "ready",
    "runner": "lib/krea2_img_prompt.py",
    "used_by": ["scripts/generate_krea2_img_prompt.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "notes": "Florence2 caption then krea2_t2i_v10",
}
cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("catalog ok")
