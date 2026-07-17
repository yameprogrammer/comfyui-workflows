import json
from pathlib import Path

SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\멀티앵글생성-qwen-image.json"
)
d = json.loads(SRC.read_text(encoding="utf-8"))
for n in d["nodes"]:
    print("NODE", n.get("id"), n.get("type"))
    if n.get("type") and len(str(n.get("type"))) > 20:
        print("  inputs", n.get("inputs"))
        print("  outputs", n.get("outputs"))
        print("  widgets", n.get("widgets_values"))
        print("  props keys", list((n.get("properties") or {}).keys())[:20])
        pw = (n.get("properties") or {}).get("proxyWidgets")
        if pw:
            print("  proxyWidgets", pw)
    if n.get("type") == "QwenMultiangleCameraNode":
        print("  multiangle widgets", n.get("widgets_values"))
        print("  multiangle inputs", n.get("inputs"))
        print("  multiangle outputs", n.get("outputs"))

print("\nOUTER LINKS:")
for L in d.get("links") or []:
    print(" ", L)

sg = (d.get("definitions") or {}).get("subgraphs")[0]
print("\nSUBGRAPH name", sg.get("name"), "id", sg.get("id"))
print("inputs", json.dumps(sg.get("inputs"), indent=2, ensure_ascii=False)[:2000])
print("outputs", json.dumps(sg.get("outputs"), indent=2, ensure_ascii=False)[:1000])
print("\nSUB NODES:")
for n in sg.get("nodes") or []:
    print(
        f"  id={n.get('id')} type={n.get('type')} w={n.get('widgets_values')}"
    )
print("\nSUB LINKS:")
for L in sg.get("links") or []:
    print(" ", L)
