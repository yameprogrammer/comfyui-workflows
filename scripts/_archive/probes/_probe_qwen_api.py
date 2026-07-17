import json
import os
from lib.comfy_client import convert_ui_to_api, load_workflow

p = r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\Qwen_2511_MultiGen_v1.json"
ui = load_workflow(p)
api = convert_ui_to_api(ui)
for nid in ["1", "2", "3", "4", "5", "6", "8", "9", "10", "11", "13", "15", "16"]:
    n = api[nid]
    print("---", nid, n["class_type"])
    print(json.dumps(n["inputs"], ensure_ascii=False, indent=2)[:800])

for root, ds, fs in os.walk(r"F:\ComfyUI_windows_portable\ComfyUI\custom_nodes"):
    for f in fs:
        if "QwenEdit" in f or "TextEncodeQwen" in f or "qwenedit" in f.lower():
            print("NODEFILE", os.path.join(root, f))
