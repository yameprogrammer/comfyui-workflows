#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("workflows/agent/catalog.json")
c = json.loads(p.read_text(encoding="utf-8"))
c["workflows"]["lonecat_krea2_v70"] = {
    "file": None,
    "format": "ui_expand",
    "role": "krea2_pro_full_graph",
    "family": "krea2",
    "status": "documented",
    "description": "Lonecat Krea 2 v7.0 full pro UI (~478 nodes). Feature map for agents; core T2I via krea2_t2i_v10.",
    "source_ui": r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\Lonecat's Krea 2 v7.0.json",
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
    "capabilities": "workflows/human/lonecat_krea2_v70/CAPABILITIES.json",
    "discovery_cli": "scripts/krea2_features.py",
    "used_by": ["scripts/krea2_features.py", "scripts/generate_krea.py"],
    "notes": "Not full API expand. ready routes via v10/other tools; planned need graphToPrompt presets.",
}
c["workflows"]["krea2_feature_router"] = {
    "file": None,
    "role": "capability_discovery",
    "status": "ready",
    "description": "List/search Krea2 v7+v10 features and agent CLIs",
    "used_by": ["scripts/krea2_features.py"],
    "guide": "workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md",
}
p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ok")
