"""Find inject ports in Lonecat AIO Z-Image ver 17."""
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
    # link format: [link_id, from_node, from_slot, to_node, to_slot, type]

    # Find Set/Get names
    print("=== SetNode / GetNode bus ===")
    for n in d["nodes"]:
        t = n.get("type")
        if t in ("SetNode", "GetNode"):
            w = n.get("widgets_values") or []
            print(f"  {t} id={n['id']} title={n.get('title')!r} widgets={w}")

    # Text Multiline / easy positive / prompt-like
    print("\n=== Prompt-like nodes ===")
    for n in d["nodes"]:
        t = n.get("type") or ""
        title = (n.get("title") or "")
        w = n.get("widgets_values")
        if t in (
            "Text Multiline",
            "easy positive",
            "easy negative",
            "PrimitiveStringMultiline",
            "CR Text",
            "String Literal",
            "CLIPTextEncode",
            "DF_Text",
            "JoinStrings",
            "ShowText|pysssss",
        ) or "prompt" in title.lower() or "positive" in title.lower() or "negative" in title.lower():
            ws = repr(w)
            if len(ws) > 400:
                ws = ws[:400] + "..."
            print(f"id={n['id']} type={t} title={title!r}")
            print(f"  widgets={ws}")

    # LoadImage nodes
    print("\n=== LoadImage ===")
    for n in d["nodes"]:
        if n.get("type") == "LoadImage":
            print(f"id={n['id']} title={n.get('title')!r} widgets={n.get('widgets_values')}")
            # who consumes this?
            for link in links:
                if isinstance(link, list) and len(link) >= 5 and link[1] == n["id"]:
                    tgt = nodes.get(link[3], {})
                    print(
                        f"  -> link to id={link[3]} type={tgt.get('type')} title={tgt.get('title')!r}"
                    )

    # Groups
    print("\n=== Groups ===")
    for g in d.get("groups") or []:
        title = g.get("title") or g.get("name") or g
        if isinstance(g, dict):
            print(f"  {g.get('title')!r} color={g.get('color')} bounding={g.get('bounding')}")
        else:
            print(" ", g)

    # Fast Groups Bypasser titles
    print("\n=== Fast Groups Bypasser / switches ===")
    for n in d["nodes"]:
        t = n.get("type") or ""
        if "Bypass" in t or "Switch" in t or "mxSlider" in t:
            title = n.get("title") or ""
            w = n.get("widgets_values")
            ws = repr(w)
            if len(ws) > 250:
                ws = ws[:250] + "..."
            print(f"id={n['id']} type={t} title={title!r} widgets={ws}")

    # Empty latent / size
    print("\n=== Size / latent ===")
    for n in d["nodes"]:
        t = n.get("type") or ""
        title = (n.get("title") or "")
        if any(
            k in t or k in title.lower()
            for k in (
                "Empty",
                "Width",
                "Height",
                "resolution",
                "Aspect",
                "Resize",
                "denoise",
                "Denoise",
                "latent",
            )
        ):
            print(
                f"id={n['id']} type={t} title={title!r} widgets={n.get('widgets_values')!r}"[:300]
            )


if __name__ == "__main__":
    main()
