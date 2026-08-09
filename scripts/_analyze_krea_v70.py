#!/usr/bin/env python3
"""One-shot analysis of Lonecat's Krea 2 v7.0 UI workflow."""
from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path

CANDS = [
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\Lonecat's Krea 2 v7.0.json"),
    Path(r"F:\ComfyUI_workflows\Lonecat's Krea 2 v7.0.json"),
]
ZIP = Path(r"F:\ComfyUI_workflows\krea2ProGradeWImageEditStyle_v70Moodboard.zip")


def load_wf() -> tuple[dict, str]:
    for p in CANDS:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")), str(p)
    z = zipfile.ZipFile(ZIP)
    name = next(n for n in z.namelist() if n.endswith(".json") and "v7" in n.lower())
    return json.loads(z.read(name)), f"zip:{name}"


def in_group(n: dict, g: dict) -> bool:
    bb = g.get("bounding") or g.get("boundingRect")
    if not bb or len(bb) < 4:
        return False
    pos = n.get("pos") or [0, 0]
    if isinstance(pos, dict):
        x, y = float(pos.get(0, pos.get("0", 0))), float(pos.get(1, pos.get("1", 0)))
    else:
        x, y = float(pos[0]), float(pos[1])
    gx, gy, gw, gh = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
    return gx <= x <= gx + gw and gy <= y <= gy + gh


def main() -> None:
    data, src = load_wf()
    nodes = data.get("nodes") or []
    groups = data.get("groups") or []
    print(f"source={src}")
    print(f"nodes={len(nodes)} groups={len(groups)}")

    print("\n=== GROUPS ===")
    for g in groups:
        print(f"  - {g.get('title') or '?'}")

    print("\n=== BYPASSERS / MUTES ===")
    for n in nodes:
        t = n.get("type") or ""
        if "Bypass" not in t and "Muter" not in t and "Mute" not in t:
            continue
        props = n.get("properties") or {}
        print(f"id={n.get('id')} type={t}")
        print(f"  title={(n.get('title') or '')!r}")
        print(
            f"  matchTitle={props.get('matchTitle')!r} "
            f"matchColors={props.get('matchColors')!r} "
            f"toggleRestriction={props.get('toggleRestriction')!r}"
        )
        print(f"  widgets={str(n.get('widgets_values'))[:220]}")

    print("\n=== FEATURE-RELATED TYPES ===")
    keys = (
        "Krea",
        "Style",
        "Mood",
        "Control",
        "Lora",
        "LoRA",
        "Sampler",
        "SeedVR",
        "Upscale",
        "IPAdapter",
        "Detail",
        "Enhancer",
        "Switch",
        "Power",
        "Bypass",
        "Muter",
        "LoadImage",
        "CLIP",
        "UNET",
        "VAE",
        "Reference",
    )
    ctr = Counter(n.get("type") for n in nodes)
    for t, c in ctr.most_common():
        if not t:
            continue
        if any(k.lower() in t.lower() for k in keys):
            print(f"  {c:3d}  {t}")

    print("\n=== TITLED NODES (feature entry) ===")
    for n in nodes:
        title = (n.get("title") or "").strip()
        if not title:
            continue
        tl = title.lower()
        if any(
            k in tl
            for k in (
                "prompt",
                "image",
                "style",
                "mood",
                "control",
                "lora",
                "size",
                "pass",
                "upscale",
                "seed",
                "reference",
                "denoise",
                "strength",
                "positive",
                "negative",
                "i2i",
                "edit",
            )
        ):
            print(
                f"  id={n.get('id')} [{n.get('type')}] {title!r} mode={n.get('mode')}"
            )

    print("\n=== GROUP MEMBERS (bbox) ===")
    for g in groups:
        title = g.get("title") or "?"
        members = [n for n in nodes if in_group(n, g)]
        types = Counter(n.get("type") for n in members)
        print(f"\n## {title} (members≈{len(members)})")
        for t, c in types.most_common(15):
            print(f"    {c:2d} {t}")
        for n in members:
            tit = (n.get("title") or "").strip()
            if tit:
                print(f"    · id={n.get('id')} {n.get('type')} title={tit!r}")


if __name__ == "__main__":
    main()
