"""Inspect image_qwen_image_edit_2509 UI workflow."""
import json
from collections import Counter
from pathlib import Path

SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_qwen_image_edit_2509.json"
)
d = json.loads(SRC.read_text(encoding="utf-8"))
print("keys", list(d.keys())[:15])
nodes = d.get("nodes") or []
print("n_nodes", len(nodes))
print("types:")
for t, n in Counter(n.get("type") for n in nodes).most_common():
    print(f"  {n:3d} {t}")
print("\nnodes:")
for n in nodes:
    print(
        f"  id={n.get('id')} type={n.get('type')} title={n.get('title')!r} "
        f"mode={n.get('mode')} w={n.get('widgets_values')}"
    )
print("\nlinks sample:")
for L in (d.get("links") or [])[:40]:
    print(" ", L)
defs = d.get("definitions") or {}
sgs = defs.get("subgraphs") or []
print("subgraphs", len(sgs))
for sg in sgs:
    print(" sg", sg.get("name"), "n", len(sg.get("nodes") or []))
