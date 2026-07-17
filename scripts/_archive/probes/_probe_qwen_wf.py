import json
from pathlib import Path

def summarize(path: Path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    print("=" * 60)
    print(path.name)
    nodes = d.get("nodes") or []
    print("nodes", len(nodes))
    keys = (
        "Load",
        "Lora",
        "UNET",
        "CLIP",
        "VAE",
        "KSampler",
        "TextEncode",
        "Qwen",
        "Image",
        "Save",
        "Camera",
        "Multi",
        "ModelSampling",
        "CFG",
        "Reference",
        "Empty",
        "Conditioning",
    )
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        wv = n.get("widgets_values")
        if any(k in t for k in keys) or any(
            k in title for k in ("angle", "Angle", "카메라", "포즈", "view", "View", "멀티")
        ):
            print(f"  id={n['id']:4} type={t} title={title!r}")
            if wv is not None:
                s = repr(wv)
                if len(s) > 350:
                    s = s[:350] + "..."
                print("       widgets=", s)


base = Path(r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows")
for n in [
    "Qwen_2511_MultiGen_v1.json",
    "캐릭터-멀티포즈-생성-Qwen_image_edit_2511.json",
    "멀티앵글생성-qwen-image.json",
]:
    summarize(base / n)
