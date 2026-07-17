import json
from pathlib import Path

SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_qwen_image_edit_2509.json"
)
d = json.loads(SRC.read_text(encoding="utf-8"))
for n in d["nodes"]:
    if n.get("id") in (433, 466):
        print("OUTER", n.get("id"), n.get("type"), "mode", n.get("mode"))
        print("  inputs", n.get("inputs"))
        print("  outputs", n.get("outputs"))
        print("  props", {k: (n.get("properties") or {}).get(k) for k in ("proxyWidgets",)})

for sg in (d.get("definitions") or {}).get("subgraphs") or []:
    print("\n==== SUBGRAPH", sg.get("name"), sg.get("id"))
    print("inputs", json.dumps(sg.get("inputs"), ensure_ascii=False)[:1500])
    print("outputs", json.dumps(sg.get("outputs"), ensure_ascii=False)[:800])
    for n in sg.get("nodes") or []:
        print(
            f"  id={n.get('id')} type={n.get('type')} mode={n.get('mode')} "
            f"w={n.get('widgets_values')}"
        )
    print("links:")
    for L in sg.get("links") or []:
        print(" ", L)
