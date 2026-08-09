"""Dependency health for Illustrious Standard / Advanced / Detailer packs.

Checks:
  - weight files under shared model roots (F:\\model, portable, COMFYUI_MODELS)
  - required Comfy node class_types via /object_info
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from lib.comfy_client import DEFAULT_SERVER
from lib.illustrious_standard_v37_runner import _find_under_models, _model_roots

# (id, kind=model|node, path_or_class, alts)
STANDARD_CHECKS: list[tuple[str, str, str, list[str]]] = [
    ("ckpt_fabricated", "model", "checkpoints/Illustrious/fabricatedXL_v70.safetensors", []),
    ("face_yolo", "model", "ultralytics/bbox/face_yolov9c.pt", ["ultralytics/bbox/face_yolov8m.pt"]),
    ("hand_yolo", "model", "ultralytics/bbox/hand_yolov9c.pt", ["ultralytics/bbox/hand_yolov8s.pt"]),
    ("eyes_yolo", "model", "ultralytics/bbox/Eyeful_v2-Individual.pt", ["ultralytics/bbox/Eyeful_v2-Paired.pt"]),
    ("nsfw_segm", "model", "ultralytics/segm/ntd11_anime_nsfw_segm_v5-variant1.pt", ["ultralytics/segm/nsfw-anime-medium-x1280.pt"]),
    ("sam_vit_b", "model", "sams/sam_vit_b_01ec64.pth", []),
    ("upscale_remacri", "model", "upscale_models/4x_foolhardy_Remacri.pth", []),
    ("canny_control_lora", "model", "controlnet/SDXL/control-lora-canny-rank256.safetensors", []),
    ("sdxl_vae", "model", "vae/sdxl_vae.safetensors", []),
    ("ImpactSwitch", "node", "ImpactSwitch", []),
    ("FaceDetailerPipe", "node", "FaceDetailerPipe", []),
    ("UltralyticsDetectorProvider", "node", "UltralyticsDetectorProvider", []),
    ("Lora Loader (LoraManager)", "node", "Lora Loader (LoraManager)", []),
]

ADVANCED_EXTRA: list[tuple[str, str, str, list[str]]] = [
    ("ipadapter_sdxl_face", "model", "ipadapter/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors", [
        "ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors",
    ]),
    ("clip_vision_h", "model", "clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors", [
        "clip_vision/clip_vision_h.safetensors",
        "clip_vision/CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors",
    ]),
    ("openpose_cn", "model", "controlnet/noobaiXLControlnet_openposeModel.safetensors", [
        "controlnet/controlnet-openpose-sdxl.safetensors",
        "controlnet/SDXL/openpose.safetensors",
        "controlnet/SDXL/controlnet-openpose-sdxl.safetensors",
    ]),
    ("noob_ipa_mark", "model", "ipadapter/noobIPAMARK1_mark1.safetensors", [
        "ipadapter/sdxl_models/noobIPAMARK1_mark1.safetensors",
    ]),
    ("IPAdapterAdvanced", "node", "IPAdapterAdvanced", []),
    ("IPAdapterStyleComposition", "node", "IPAdapterStyleComposition", []),
    ("OpenposePreprocessor", "node", "OpenposePreprocessor", []),
    ("TIPO", "node", "TIPO", []),
    ("AttentionCouplePPM", "node", "AttentionCouplePPM", []),
    ("JPEG artifacts removal FBCNN", "node", "JPEG artifacts removal FBCNN", []),
    ("CLIPNegPip", "node", "CLIPNegPip", []),
    ("SAM3_Detect", "node", "SAM3_Detect", []),
]

DETAILER_EXTRA: list[tuple[str, str, str, list[str]]] = [
    ("noobai_inpaint_cn", "model", "controlnet/noobaiInpainting_v10.safetensors", [
        "controlnet/SDXL/noobaiInpainting_v10.safetensors",
    ]),
    ("watermark_segm", "model", "ultralytics/segm/unwantedV10x.pt", []),
    ("InpaintPreprocessor", "node", "InpaintPreprocessor", []),
    ("VAEEncodeForInpaint", "node", "VAEEncodeForInpaint", []),
    ("ImagePadForOutpaint", "node", "ImagePadForOutpaint", []),
    ("MaskDetailerPipe", "node", "MaskDetailerPipe", []),
]


def _object_info(server: str = DEFAULT_SERVER) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _check_one(
    item_id: str,
    kind: str,
    primary: str,
    alts: list[str],
    object_info: dict[str, Any],
) -> dict[str, Any]:
    if kind == "node":
        ok = primary in object_info
        return {
            "id": item_id,
            "kind": "node",
            "required": primary,
            "ok": ok,
            "resolved": primary if ok else None,
            "severity": "optional" if item_id in ("CLIPNegPip", "TIPO", "AttentionCouplePPM", "JPEG artifacts removal FBCNN", "SAM3_Detect") else "required_for_feature",
        }
    # model
    path = _find_under_models(*primary.replace("\\", "/").split("/"))
    used = str(path) if path else None
    ok = path is not None
    if not ok:
        for a in alts:
            p2 = _find_under_models(*a.replace("\\", "/").split("/"))
            if p2:
                ok = True
                used = str(p2)
                break
    return {
        "id": item_id,
        "kind": "model",
        "required": primary,
        "ok": ok,
        "resolved": used,
        "severity": "required_for_feature",
    }


def check_pack(pack: str, *, server: str = DEFAULT_SERVER) -> dict[str, Any]:
    pack = (pack or "all").lower()
    oi = _object_info(server)
    rows: list[dict[str, Any]] = []
    checks = list(STANDARD_CHECKS)
    if pack in ("advanced", "all", "adv"):
        checks += ADVANCED_EXTRA
    if pack in ("detailer", "all", "det"):
        checks += DETAILER_EXTRA
    if pack in ("standard", "std"):
        checks = list(STANDARD_CHECKS)

    seen: set[str] = set()
    for item_id, kind, primary, alts in checks:
        if item_id in seen:
            continue
        seen.add(item_id)
        rows.append(_check_one(item_id, kind, primary, alts, oi))

    ok_n = sum(1 for r in rows if r["ok"])
    miss = [r for r in rows if not r["ok"]]
    return {
        "pack": pack,
        "server": server,
        "model_roots": [str(p) for p in _model_roots() if p],
        "ok_count": ok_n,
        "total": len(rows),
        "rows": rows,
        "missing": miss,
        "comfy_reachable": bool(oi),
    }


def format_report(result: dict[str, Any]) -> str:
    lines = [
        f"Illustrious health pack={result.get('pack')}  "
        f"{result.get('ok_count')}/{result.get('total')} OK  "
        f"comfy={'up' if result.get('comfy_reachable') else 'DOWN'}",
        "roots: " + ", ".join(result.get("model_roots") or []),
        "",
    ]
    for r in result.get("rows") or []:
        mark = "OK" if r["ok"] else "MISS"
        lines.append(f"  [{mark}] {r['id']:28s} {r['kind']:5s} {r['required']}")
        if r.get("resolved") and r["resolved"] != r["required"]:
            lines.append(f"         → {r['resolved']}")
    if result.get("missing"):
        lines.append("\nMissing (feature may fail when toggled):")
        for r in result["missing"]:
            lines.append(f"  - {r['id']}: {r['required']}")
    return "\n".join(lines)
