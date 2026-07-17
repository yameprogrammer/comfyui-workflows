"""Locate main user prompt entry connected to Set_Positive / Set_postext."""
from __future__ import annotations

import json
from pathlib import Path

WF = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Lonecat's AIO Z-Image ver 17.json"
)


def main() -> None:
    d = json.loads(WF.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in d["nodes"]}
    links = d.get("links") or []

    # Find nodes feeding Set_postext / Set_Positive
    targets = {1265, 1268, 1266, 1269, 1994, 82}  # Set positive/postext/neg/prompt tag/rough draft
    print("=== incoming to key SetNodes ===")
    for link in links:
        # [id, from, from_slot, to, to_slot, type]
        if not isinstance(link, list) or len(link) < 5:
            continue
        if link[3] in targets:
            src = nodes.get(link[1], {})
            print(
                f"link {link[0]}: {link[1]}:{src.get('type')}:{src.get('title')!r} "
                f"-> {link[3]}:{nodes[link[3]].get('title')}"
            )

    # Find Text Multiline / easy positive that look like MAIN prompt
    print("\n=== candidate main prompt widgets ===")
    for n in d["nodes"]:
        t = n.get("type")
        title = n.get("title") or ""
        w = n.get("widgets_values")
        if t in ("Text Multiline", "easy positive", "PrimitiveStringMultiline", "StringConstantMultiline"):
            print(f"id={n['id']} type={t} title={title!r}")
            if isinstance(w, list) and w:
                s = str(w[0]) if w else ""
                print(f"  first_widget_len={len(s)} preview={s[:200]!r}")
            elif isinstance(w, str):
                print(f"  widget_len={len(w)} preview={w[:200]!r}")

    # mode mode: which groups are enabled - look at Fast Groups Bypasser widgets
    print("\n=== group bypasser state ===")
    for n in d["nodes"]:
        if n.get("type") == "Fast Groups Bypasser (rgthree)":
            print(f"id={n['id']} title={n.get('title')!r}")
            print(f"  widgets={n.get('widgets_values')!r}"[:500])
            props = n.get("properties") or {}
            if props:
                keys = list(props.keys())[:20]
                print(f"  prop_keys={keys}")

    # Mode selectors: Any Switch
    print("\n=== Any Switch titles ===")
    for n in d["nodes"]:
        if "Switch" in (n.get("type") or ""):
            print(f"id={n['id']} type={n.get('type')} title={n.get('title')!r} widgets={n.get('widgets_values')}")


if __name__ == "__main__":
    main()
