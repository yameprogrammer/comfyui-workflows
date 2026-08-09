#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

o = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=30).read())
names = [
    "Krea2StyleReference",
    "Krea2StyleTransfer",
    "Krea2ControlLoRALoader",
    "Krea2ControlImageEncode",
    "Krea2ControlApply",
    "ClownsharKSampler_Beta",
]
for name in names:
    if name not in o:
        print("MISSING", name)
        continue
    print("====", name)
    for kind in ("required", "optional"):
        d = o[name].get("input", {}).get(kind) or {}
        for ik, iv in d.items():
            s = str(iv)
            if len(s) > 160:
                s = s[:160] + "..."
            print(f"  {kind}.{ik}: {s}")

# find control loras
for root in [Path(r"F:/model/loras"), Path(r"F:/ComfyUI_windows_portable/ComfyUI/models/loras")]:
    if not root.is_dir():
        continue
    print("scan", root)
    for p in root.rglob("*.safetensors"):
        n = p.name.lower()
        if "krea" in n or "control" in n:
            try:
                rel = p.relative_to(root)
            except Exception:
                rel = p
            print(" ", rel)
