"""Inspect Lonecat AIO Z-Image ver 17 for smoke usability."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

WF = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Lonecat's AIO Z-Image ver 17.json"
)
OUT = Path(r"F:\ComfyUI_workflows\agent_custom\workflows\human")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("path:", WF)
    print("exists:", WF.exists(), "size_kb:", WF.stat().st_size // 1024 if WF.exists() else 0)
    d = json.loads(WF.read_text(encoding="utf-8"))
    print("top_keys:", sorted(d.keys())[:30])
    nodes = d.get("nodes") or []
    print("nodes:", len(nodes), "links:", len(d.get("links") or []))
    types = Counter(n.get("type") for n in nodes)
    print("unique_types:", len(types))
    print("\n=== type histogram (top 50) ===")
    for t, c in types.most_common(50):
        print(f"  {c:4}  {t}")

    # titles / interesting widgets
    interesting_kw = (
        "prompt",
        "seed",
        "user",
        "setting",
        "i2i",
        "img2img",
        "load",
        "denoise",
        "ratio",
        "size",
        "width",
        "height",
        "model",
        "turbo",
        "base",
        "detailer",
        "upscale",
        "control",
        "lora",
        "positive",
        "negative",
        "t2i",
        "image",
        "bypass",
        "mode",
        "sampler",
    )
    print("\n=== nodes with useful titles/widgets ===")
    for n in nodes:
        title = (n.get("title") or "").strip()
        t = n.get("type") or ""
        blob = f"{title} {t}".lower()
        if not any(k in blob for k in interesting_kw):
            # still show Primitive / easy controls
            if t not in (
                "PrimitiveStringMultiline",
                "PrimitiveString",
                "CR Text",
                "StringConstant",
                "ImpactStringSelector",
                "easy something",
                "JWString",
                "Text Multiline",
                "Text Box",
                "ShowText|pysssss",
                "easy promptList",
                "Power Lora Loader (rgthree)",
                "LoadImage",
                "EmptyLatentImage",
                "EmptySD3LatentImage",
                "KSampler",
                "KSamplerAdvanced",
                "UNETLoader",
                "CheckpointLoaderSimple",
                "CLIPTextEncode",
            ):
                continue
        w = n.get("widgets_values")
        if isinstance(w, list) and len(w) > 10:
            wshow = w[:10] + ["..."]
        else:
            wshow = w
        print(f"id={n.get('id')} type={t}")
        if title:
            print(f"  title={title!r}")
        if wshow is not None:
            s = repr(wshow)
            if len(s) > 300:
                s = s[:300] + "..."
            print(f"  widgets={s}")

    # model / file references in widgets
    print("\n=== file-like widget strings (models etc) ===")
    files = []
    for n in nodes:
        w = n.get("widgets_values")
        if not isinstance(w, (list, dict, str)):
            continue

        def walk(x, path=""):
            if isinstance(x, str):
                if any(
                    x.endswith(ext)
                    for ext in (
                        ".safetensors",
                        ".ckpt",
                        ".pt",
                        ".pth",
                        ".gguf",
                        ".bin",
                        ".onnx",
                    )
                ) or "\\" in x or "/" in x and len(x) < 200:
                    if any(
                        k in x.lower()
                        for k in (
                            "safetensor",
                            "ckpt",
                            "gguf",
                            "yolo",
                            "upscale",
                            "lora",
                            "vae",
                            "clip",
                            "unet",
                            "z-image",
                            "zimage",
                            "moody",
                            "zit",
                            "zib",
                        )
                    ) or x.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".gguf")):
                        files.append((n.get("id"), n.get("type"), n.get("title"), x))
            elif isinstance(x, list):
                for i, y in enumerate(x):
                    walk(y, f"{path}[{i}]")
            elif isinstance(x, dict):
                for k, y in x.items():
                    walk(y, f"{path}.{k}")

        walk(w)
    seen = set()
    for item in files:
        key = item[3]
        if key in seen:
            continue
        seen.add(key)
        print(f"  node {item[0]} ({item[1]}) {item[2]!r}: {item[3]}")

    # copy to human workflows for SSOT
    dest = OUT / "Lonecat_AIO_Z-Image_ver17.json"
    dest.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\ncopied to:", dest)


if __name__ == "__main__":
    main()
