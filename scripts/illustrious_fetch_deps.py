#!/usr/bin/env python3
"""Fetch missing Illustrious Advanced/Detailer models (+ optional custom_nodes).

  python scripts/illustrious_fetch_deps.py              # models only
  python scripts/illustrious_fetch_deps.py --nodes      # + git clone node packs
  python scripts/illustrious_fetch_deps.py --dry-run

After --nodes: restart ComfyUI, then:
  python scripts/illustrious_check.py --pack all
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from lib.illustrious_standard_v37_runner import _find_under_models, _model_roots

MODEL_ROOT = Path(r"F:\model")
CUSTOM_NODES = Path(r"F:\ComfyUI_windows_portable\ComfyUI\custom_nodes")
PORTABLE_CN = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\models\controlnet"
)

# (dest_relative, source_kind, source_spec, note)
# source_kind: hf | copy | skip
MODEL_FETCH = [
    {
        "id": "noob_ipa_mark",
        "dest": "ipadapter/noobIPAMARK1_mark1.safetensors",
        "kind": "hf",
        "repo": "nnnn1111/models-moved",
        "file": "noobIPAMARK1_mark1.safetensors",
        "also_copy": ["ipadapter/sdxl_models/noobIPAMARK1_mark1.safetensors"],
    },
    {
        "id": "openpose_cn",
        "dest": "controlnet/controlnet-openpose-sdxl.safetensors",
        "kind": "copy_or_hf",
        "copy_from": [
            str(PORTABLE_CN / "controlnet-openpose-sdxl.safetensors"),
        ],
        "hf_repo": "thibaud/controlnet-openpose-sdxl-1.0",
        "hf_file": None,  # optional later
        "aliases": [
            "controlnet/noobaiXLControlnet_openposeModel.safetensors",
        ],
    },
    {
        "id": "noobai_inpaint_cn",
        "dest": "controlnet/noobaiInpainting_v10.safetensors",
        "kind": "hf",
        "repo": "Acly/NoobAI-Inpainting",
        "file": "noobaiInpainting_v10.fp16.safetensors",
    },
]

NODE_REPOS = [
    {
        "id": "TIPO",
        "dir": "z-tipo-extension",
        "url": "https://github.com/KohakuBlueleaf/z-tipo-extension.git",
        "provides": ["TIPO"],
        "note": "May need pip install -r requirements + TIPO GGUF model",
    },
    {
        "id": "AttentionCouplePPM+CLIPNegPip",
        "dir": "ComfyUI-ppm",
        "url": "https://github.com/pamparamm/ComfyUI-ppm.git",
        "provides": ["AttentionCouplePPM", "CLIPNegPip"],
    },
    {
        "id": "FBCNN",
        "dir": "ComfyUI-FBCNN",
        "url": "https://github.com/Miosp/ComfyUI-FBCNN.git",
        "provides": ["JPEG artifacts removal FBCNN"],
        "note": "FBCNN weights download on first use or from repo README",
    },
]


def _exists_model(rel: str) -> Path | None:
    return _find_under_models(*rel.replace("\\", "/").split("/"))


def _hf_download(repo: str, filename: str, dest: Path) -> Path:
    from huggingface_hub import hf_hub_download

    dest.parent.mkdir(parents=True, exist_ok=True)
    p = hf_hub_download(repo, filename)
    shutil.copy2(p, dest)
    return dest


def fetch_models(*, dry_run: bool = False) -> list[str]:
    logs: list[str] = []
    for item in MODEL_FETCH:
        rel = item["dest"]
        if _exists_model(rel) or _exists_model(item.get("aliases", [None])[0] or rel):
            logs.append(f"[skip] {item['id']}: already present")
            # still create pack-expected alias if missing
            for alias in item.get("aliases") or []:
                if not _exists_model(alias) and not dry_run:
                    src = _exists_model(rel)
                    if src:
                        adest = MODEL_ROOT / alias.replace("/", "\\")
                        adest.parent.mkdir(parents=True, exist_ok=True)
                        if not adest.exists():
                            shutil.copy2(src, adest)
                            logs.append(f"[alias] {alias} ← {src.name}")
            continue

        dest = MODEL_ROOT / rel.replace("/", "\\")
        kind = item["kind"]
        try:
            if dry_run:
                logs.append(f"[dry] would fetch {item['id']} → {dest}")
                continue
            if kind == "hf":
                _hf_download(item["repo"], item["file"], dest)
                logs.append(f"[ok] {item['id']} → {dest} ({dest.stat().st_size})")
            elif kind == "copy_or_hf":
                done = False
                for src in item.get("copy_from") or []:
                    sp = Path(src)
                    if sp.is_file():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sp, dest)
                        logs.append(f"[ok] {item['id']} copied ← {sp}")
                        done = True
                        break
                if not done and item.get("hf_repo") and item.get("hf_file"):
                    _hf_download(item["hf_repo"], item["hf_file"], dest)
                    logs.append(f"[ok] {item['id']} hf → {dest}")
                elif not done:
                    logs.append(f"[MISS] {item['id']}: no local/hf source")
                    continue
            for alias in item.get("aliases") or []:
                adest = MODEL_ROOT / alias.replace("/", "\\")
                if not adest.exists() and dest.exists():
                    adest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, adest)
                    logs.append(f"[alias] {alias}")
            for also in item.get("also_copy") or []:
                adest = MODEL_ROOT / also.replace("/", "\\")
                if not adest.exists() and dest.exists():
                    adest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, adest)
                    logs.append(f"[also] {also}")
        except Exception as e:
            logs.append(f"[FAIL] {item['id']}: {e}")
    return logs


def fetch_nodes(*, dry_run: bool = False) -> list[str]:
    logs: list[str] = []
    if not CUSTOM_NODES.is_dir():
        logs.append(f"[FAIL] custom_nodes missing: {CUSTOM_NODES}")
        return logs
    for item in NODE_REPOS:
        target = CUSTOM_NODES / item["dir"]
        if target.is_dir():
            logs.append(f"[skip] nodes {item['id']}: {target.name} exists")
            continue
        if dry_run:
            logs.append(f"[dry] git clone {item['url']} → {target}")
            continue
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", item["url"], str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            logs.append(f"[ok] cloned {item['id']} → {target.name}")
            if item.get("note"):
                logs.append(f"     note: {item['note']}")
        except Exception as e:
            logs.append(f"[FAIL] clone {item['id']}: {e}")
    logs.append(
        "[action] Restart ComfyUI to load new custom nodes, then run illustrious_check.py"
    )
    return logs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fetch Illustrious MISS dependencies")
    p.add_argument("--nodes", action="store_true", help="also git clone custom node packs")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--models-only", action="store_true", default=False)
    args = p.parse_args(argv)

    print("model roots:", [str(r) for r in _model_roots()])
    for line in fetch_models(dry_run=args.dry_run):
        print(line)
    if args.nodes:
        for line in fetch_nodes(dry_run=args.dry_run):
            print(line)
    else:
        print("[hint] pass --nodes to clone TIPO / ppm (NegPip+Regional) / FBCNN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
