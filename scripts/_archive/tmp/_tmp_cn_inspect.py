"""Inspect controlnet workflows for API export."""
import json
from collections import Counter
from pathlib import Path

OFFICIAL = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_z_image_turbo_fun_union_controlnet.json"
)
AGENT = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\agent\I2I-ControlNet-moody.json"
)


def dump_ui(path: Path) -> None:
    print("=" * 60)
    print(path)
    d = json.loads(path.read_text(encoding="utf-8"))
    print("top keys:", list(d.keys())[:20])
    nodes = d.get("nodes") or []
    print("n_nodes:", len(nodes))
    if nodes and "class_type" not in (nodes[0] if isinstance(nodes[0], dict) else {}):
        c = Counter(n.get("type") for n in nodes)
        for t, n in c.most_common(40):
            print(f"  {n:3d} {t}")
        for n in nodes:
            t = n.get("type")
            interesting = {
                "LoadImage",
                "UNETLoader",
                "KSampler",
                "CLIPTextEncode",
                "ZImageFunControlnet",
                "FL_ZImageControlNetPatch",
                "SaveImage",
                "VAEEncode",
                "EmptySD3LatentImage",
                "EmptyLatentImage",
                "Canny",
                "ImageScaleToMaxDimension",
                "CLIPLoader",
                "VAELoader",
                "ModelSamplingAuraFlow",
            }
            if t in interesting or "Control" in (t or "") or "ZImage" in (t or ""):
                print(
                    f"  id={n.get('id')} type={t} title={n.get('title')!r} "
                    f"w={n.get('widgets_values')}"
                )
            # subgraph-ish
            if n.get("type") and len(str(n.get("type"))) > 30:
                print(f"  SUBGRAPH? id={n.get('id')} type={n.get('type')}")
                print("    keys", list(n.keys()))
    defs = d.get("definitions")
    print("definitions type", type(defs), "keys", list(defs.keys())[:20] if isinstance(defs, dict) else None)
    if isinstance(defs, dict):
        for k, v in defs.items():
            if not isinstance(v, dict):
                continue
            print(f"  def[{k}] keys={list(v.keys())[:15]}")
            sn = v.get("nodes") or []
            print(f"    n_nodes={len(sn)}")
            for n in sn:
                print(
                    f"      id={n.get('id')} type={n.get('type')} "
                    f"w={n.get('widgets_values')}"
                )
    # API-like?
    if all(isinstance(v, dict) and "class_type" in v for v in d.values() if isinstance(v, dict)):
        print("looks like API format already")


def main() -> None:
    dump_ui(OFFICIAL)
    dump_ui(AGENT)


if __name__ == "__main__":
    main()
