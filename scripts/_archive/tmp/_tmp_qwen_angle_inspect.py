"""Inspect 멀티앵글생성-qwen-image UI workflow."""
import json
from collections import Counter
from pathlib import Path

SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\멀티앵글생성-qwen-image.json"
)
# alt MultiGen
ALT = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Qwen_2511_MultiGen_v1.json"
)


def inspect(path: Path) -> None:
    print("=" * 60)
    print(path.name, "exists", path.is_file(), "size", path.stat().st_size if path.is_file() else 0)
    d = json.loads(path.read_text(encoding="utf-8"))
    print("keys", list(d.keys())[:15])
    nodes = d.get("nodes") or []
    # API format?
    if not nodes and isinstance(d, dict):
        api_like = [k for k, v in d.items() if isinstance(v, dict) and "class_type" in v]
        if api_like:
            print("API format n=", len(api_like))
            for k in api_like:
                n = d[k]
                print(f"  {k}: {n.get('class_type')} inputs={list((n.get('inputs') or {}).keys())} vals={ {kk:vv for kk,vv in (n.get('inputs') or {}).items() if not isinstance(vv,list)} }")
            return
    print("n_nodes", len(nodes))
    c = Counter(n.get("type") for n in nodes)
    for t, n in c.most_common(40):
        print(f"  {n:3d} {t}")
    for n in nodes:
        t = n.get("type")
        if t in (
            "LoadImage",
            "SaveImage",
            "KSampler",
            "CLIPTextEncode",
            "UNETLoader",
            "LoaderGGUF",
            "LoraLoaderModelOnly",
            "VAELoader",
            "CLIPLoader",
            "VAEDecode",
            "TextEncodeQwenImageEditPlusCustom_lrzjason",
            "TextEncodeQwenImageEditPlus",
            "QwenEditConfigPreparer",
            "QwenEditAdaptiveLongestEdge",
            "PrimitiveNode",
            "Note",
            "MarkdownNote",
        ) or (t and ("Qwen" in t or "Lora" in t or "GGUF" in t or "Angle" in t or "Text" in t)):
            print(
                f"  id={n.get('id')} type={t} title={n.get('title')!r} "
                f"mode={n.get('mode')} w={n.get('widgets_values')}"
            )
    # subgraphs?
    defs = d.get("definitions") or {}
    if defs:
        print("definitions keys", list(defs.keys()))
        sgs = defs.get("subgraphs") or []
        print("n_subgraphs", len(sgs))
        for sg in sgs[:3]:
            print(" sg", sg.get("name"), "n_nodes", len(sg.get("nodes") or []))


inspect(SRC)
inspect(ALT)
