"""LatentHeart LTX2.3 AIO (Director) — Fast Groups Bypasser switches.

SSOT UI:
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector2.json
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector13.json

Civitai: https://civitai.red/models/2553704/...
Author notes: model groups are self-contained (STANDARD / GGUF / 10EROS);
enable one via QUICK MODEL SELECTOR (matchTitle ``LTX2.3 MODEL``, max one).

Agent never deletes nodes — only sets mode ALWAYS(0) / NEVER(2) / keep BYPASS(4).
"""

from __future__ import annotations

import copy
from typing import Any

MODE_ALWAYS = 0
MODE_NEVER = 2
MODE_BYPASS = 4

# Exact group titles from UI (case-sensitive match on strip)
GROUP_STANDARD = "LTX2.3 MODEL [STANDARD]"
GROUP_GGUF = "LTX2.3 MODEL [GGUF]"
GROUP_10EROS = "LTX2.3 MODEL [10EROS]"

FEATURE_GROUPS: dict[str, str] = {
    "half_resolution": "Half resolution",
    "controlnet": "Controlnet conditioning",
    "id_lora": "ID LoRA conditioning (voice cloning)",
    "ltx_2x_upscaler": "LTX 2x Upscaler",
    "ltx_detailer": "LTX Detailer",
    "nvidia_vsr": "Nvidia VSR upscaler",
    "interpolation": "Interpolation",
    "image_reference": "Image reference",
    "lipsync_enhancer": "Lipsync enhancer",
    # prompt enhancer appears twice (cyan optional + main); title match both
    "prompt_enhancer": "Prompt enhancer",
}

# Profiles: exclusive model group + optional feature on/off
PROFILES: dict[str, dict[str, Any]] = {
    "gguf_distilled": {
        "description": (
            "Memory-safe: LTX2.3 distilled GGUF only (Q4_K_M local). "
            "STANDARD + 10EROS groups OFF. Heavy post (detailer/upscaler/VFI) OFF."
        ),
        "model": "gguf",
        "features_on": [],
        "features_off": [
            "half_resolution",
            "controlnet",
            "id_lora",
            "ltx_2x_upscaler",
            "ltx_detailer",
            "nvidia_vsr",
            "interpolation",
            "image_reference",
            "lipsync_enhancer",
            "prompt_enhancer",
        ],
        "gguf_name": r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf",
    },
    "gguf_10eros": {
        "description": (
            "GGUF group + 10Eros Q4_K_M weight (NSFW-leaning). "
            "Pack's 10EROS safetensors group stays OFF; diffusion via UnetLoaderGGUF."
        ),
        "model": "gguf",
        "features_on": [],
        "features_off": [
            "half_resolution",
            "controlnet",
            "id_lora",
            "ltx_2x_upscaler",
            "ltx_detailer",
            "nvidia_vsr",
            "interpolation",
            "image_reference",
            "lipsync_enhancer",
            "prompt_enhancer",
        ],
        "gguf_name": r"LTX2.3\10Eros_v1-Q4_K_M.gguf",
    },
    "gguf_half_upscale": {
        "description": (
            "Author-recommended quality path: half-res + LTX 2x upscaler + GGUF distilled. "
            "Heavier VRAM/time than gguf_distilled."
        ),
        "model": "gguf",
        "features_on": ["half_resolution", "ltx_2x_upscaler"],
        "features_off": [
            "controlnet",
            "id_lora",
            "ltx_detailer",
            "nvidia_vsr",
            "interpolation",
            "image_reference",
            "lipsync_enhancer",
            "prompt_enhancer",
        ],
        "gguf_name": r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf",
    },
    "as_saved": {
        "description": "Keep UI export modes; remap GGUF loader if active.",
        "model": None,
        "features_on": None,
        "features_off": None,
        "gguf_name": r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf",
    },
}


def list_profiles() -> dict[str, str]:
    return {k: str(v.get("description") or "") for k, v in PROFILES.items()}


def _node_center(n: dict[str, Any]) -> tuple[float, float]:
    pos = n.get("pos") or [0, 0]
    size = n.get("size") or [0, 0]
    if isinstance(pos, dict):
        x, y = float(pos.get("0", 0)), float(pos.get("1", 0))
    else:
        x, y = float(pos[0]), float(pos[1] if len(pos) > 1 else 0)
    if isinstance(size, dict):
        w, h = float(size.get("0", 0)), float(size.get("1", 0))
    else:
        w = float(size[0]) if size else 0.0
        h = float(size[1]) if size and len(size) > 1 else 0.0
    return x + w / 2.0, y + h / 2.0


def _in_group(n: dict[str, Any], g: dict[str, Any]) -> bool:
    b = g.get("bounding") or g.get("bounding_rect")
    if not b or len(b) < 4:
        return False
    gx, gy, gw, gh = float(b[0]), float(b[1]), float(b[2]), float(b[3])
    cx, cy = _node_center(n)
    return gx <= cx <= gx + gw and gy <= cy <= gy + gh


def set_group_mode(ui: dict[str, Any], title: str, mode: int, *, substr: bool = False) -> int:
    """Set mode for all nodes whose center lies in matching group(s). Returns count."""
    nset = 0
    title_l = title.strip().lower()
    for g in ui.get("groups") or []:
        gt = (g.get("title") or "").strip()
        ok = gt.lower() == title_l if not substr else title_l in gt.lower()
        if not ok:
            continue
        for n in ui.get("nodes") or []:
            if _in_group(n, g):
                # Never force muter/bypasser chrome itself off in a way that breaks UI logic
                t = n.get("type") or ""
                if "Bypasser" in t or "Muter" in t:
                    continue
                n["mode"] = int(mode)
                nset += 1
    return nset


def apply_model_exclusive(ui: dict[str, Any], model: str) -> None:
    """max-one model family: standard | gguf | 10eros."""
    m = (model or "gguf").strip().lower()
    if m in ("gguf", "gguf_distilled", "distilled_gguf"):
        set_group_mode(ui, GROUP_GGUF, MODE_ALWAYS)
        set_group_mode(ui, GROUP_STANDARD, MODE_NEVER)
        set_group_mode(ui, GROUP_10EROS, MODE_NEVER)
        # Ensure GGUF loader not left at NEVER/BYPASS
        for n in ui.get("nodes") or []:
            if n.get("type") == "GGUFLoaderKJ":
                n["mode"] = MODE_ALWAYS
    elif m in ("10eros", "eros", "nsfw"):
        set_group_mode(ui, GROUP_10EROS, MODE_ALWAYS)
        set_group_mode(ui, GROUP_STANDARD, MODE_NEVER)
        set_group_mode(ui, GROUP_GGUF, MODE_NEVER)
        for n in ui.get("nodes") or []:
            if n.get("type") == "UNETLoader":
                wv = n.get("widgets_values") or []
                if wv and "eros" in str(wv[0]).lower():
                    n["mode"] = MODE_ALWAYS
    elif m in ("standard", "fp8", "distilled"):
        set_group_mode(ui, GROUP_STANDARD, MODE_ALWAYS)
        set_group_mode(ui, GROUP_GGUF, MODE_NEVER)
        set_group_mode(ui, GROUP_10EROS, MODE_NEVER)
    # else: leave as-is


def apply_feature_toggles(
    ui: dict[str, Any],
    *,
    features_on: list[str] | None,
    features_off: list[str] | None,
) -> None:
    for fid in features_off or []:
        title = FEATURE_GROUPS.get(fid)
        if title:
            set_group_mode(ui, title, MODE_NEVER, substr=True)
    for fid in features_on or []:
        title = FEATURE_GROUPS.get(fid)
        if title:
            # half res / brown groups may use BYPASS in pack — use ALWAYS
            set_group_mode(ui, title, MODE_ALWAYS, substr=True)


def remap_gguf_loader(ui: dict[str, Any], gguf_name: str) -> int:
    """Point GGUFLoaderKJ model_name to a local file; disable fp16_accumulation."""
    nfix = 0
    for n in ui.get("nodes") or []:
        if n.get("type") != "GGUFLoaderKJ":
            continue
        wv = list(n.get("widgets_values") or [])
        # [model_name, extra, dequant, patch, patch_on_device, enable_fp16_acc, attention]
        while len(wv) < 7:
            wv.append(None)
        wv[0] = gguf_name
        if wv[1] in (None, ""):
            wv[1] = "none"
        for i, default in ((2, "default"), (3, "default"), (4, False), (6, "none")):
            if wv[i] is None:
                wv[i] = default
        wv[5] = False  # enable_fp16_accumulation — torch 2.6 host safety
        n["widgets_values"] = wv
        if int(n.get("mode", 0) or 0) != MODE_ALWAYS:
            n["mode"] = MODE_ALWAYS
        nfix += 1
    return nfix


def apply_switch_profile(
    ui: dict[str, Any],
    profile: str = "gguf_distilled",
    *,
    features_on: list[str] | None = None,
    features_off: list[str] | None = None,
    model: str | None = None,
    gguf_name: str | None = None,
) -> dict[str, Any]:
    """Return deep-copied UI with profile applied."""
    ui = copy.deepcopy(ui)
    pe = PROFILES.get(profile) or PROFILES["gguf_distilled"]

    if pe.get("model") is not None or model:
        apply_model_exclusive(ui, model or pe.get("model") or "gguf")

    fo = features_off if features_off is not None else pe.get("features_off")
    fon = features_on if features_on is not None else pe.get("features_on")
    if fon is not None or fo is not None:
        apply_feature_toggles(ui, features_on=fon or [], features_off=fo or [])

    gname = gguf_name or pe.get("gguf_name")
    model_key = (model or pe.get("model") or "").strip().lower()
    if gname and model_key in ("gguf", "gguf_distilled", "distilled_gguf", ""):
        # empty model_key only when as_saved still wants filename fix if loader present
        if model_key.startswith("gguf") or profile != "as_saved":
            if model_key.startswith("gguf") or pe.get("model") == "gguf":
                remap_gguf_loader(ui, gname)
        elif profile == "as_saved":
            # only rename if GGUF loader already active
            for n in ui.get("nodes") or []:
                if n.get("type") == "GGUFLoaderKJ" and int(n.get("mode", 0) or 0) == MODE_ALWAYS:
                    remap_gguf_loader(ui, gname)
                    break

    return ui
