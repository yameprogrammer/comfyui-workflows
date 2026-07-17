import json
from pathlib import Path

p = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_z_image_turbo_fun_union_controlnet.json"
)
d = json.loads(p.read_text(encoding="utf-8"))
subs = (d.get("definitions") or {}).get("subgraphs") or []
print("n subgraphs", len(subs) if isinstance(subs, list) else type(subs))
if isinstance(subs, list):
    for i, sg in enumerate(subs):
        print("--- subgraph", i, "keys", list(sg.keys())[:20] if isinstance(sg, dict) else type(sg))
        if not isinstance(sg, dict):
            continue
        print("  id", sg.get("id"), "name", sg.get("name"))
        nodes = sg.get("nodes") or []
        print("  n_nodes", len(nodes))
        for n in nodes:
            print(
                f"    id={n.get('id')} type={n.get('type')} "
                f"title={n.get('title')!r} w={n.get('widgets_values')}"
            )
        print("  n_links", len(sg.get("links") or []))
        # inputs/outputs of subgraph interface
        for key in ("inputs", "outputs", "widgets", "input_nodes", "output_nodes"):
            if key in sg:
                print(f"  {key}:", sg[key])

# node 70 inputs/outputs linking outer graph
for n in d["nodes"]:
    if n.get("id") == 70:
        print("OUTER subgraph node inputs:")
        for inp in n.get("inputs") or []:
            print(" ", inp)
        print("OUTER subgraph node outputs:")
        for out in n.get("outputs") or []:
            print(" ", out)
        print("widgets", n.get("widgets_values"))
        print("properties", n.get("properties"))

print("OUTER links sample:")
for L in (d.get("links") or [])[:30]:
    print(" ", L)
