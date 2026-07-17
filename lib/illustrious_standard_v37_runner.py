"""Standard_V37 (Legendaer Illustrious XL) — run the **real UI workflow**.

SSOT:
  workflows/human/illustrious_standard_v37/Standard_V37.json
  workflows/human/illustrious_standard_v37/CAPABILITIES.json
  workflows/human/illustrious_standard_v37/GROUPS.json

Policy (user rule):
  - Do **not** rebuild a mini T2I graph.
  - Toggle features the same way the UI Fast Groups Bypasser does:
    set group node ``mode`` to 0 (ON) or 4 (BYPASS).
  - ``expand_ui_workflow_to_api`` + port inject only.
  - Widget realignment for seed ``control_after_generate`` slots (API-safe).
  - Multi-hop bypass resolution so muted post-FX chains still feed Image Saver.
"""

from __future__ import annotations

import copy
import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = WORKSPACE_ROOT / "workflows" / "human" / "illustrious_standard_v37"
HUMAN_UI = HUMAN_DIR / "Standard_V37.json"
CAPABILITIES_PATH = HUMAN_DIR / "CAPABILITIES.json"
GROUPS_PATH = HUMAN_DIR / "GROUPS.json"
API_CACHE = (
    WORKSPACE_ROOT
    / "workflows"
    / "agent"
    / "presets"
    / "illustrious_standard_v37.api.json"
)

DEFAULT_CKPT = r"Illustrious\fabricatedXL_v70.safetensors"
DEFAULT_NEG = (
    "bad quality, worst quality, worst detail, sketch, bad hands, "
    "bad anatomy, extra fingers, deformed, artist name, watermark, "
    "signature, patreon, twitter username"
)
WILDCARD_PLACEHOLDER = "Select the Wildcard to add to the text"
LORA_PLACEHOLDER = "Select the LoRA to add to the text"

# Local detector remaps when pack filenames are missing
DETECTOR_REMAP = {
    r"bbox/hand_yolov9c.pt": (
        r"bbox/hand_yolov9c.pt",
        r"bbox/hand_yolov8s.pt",
    ),
    r"bbox/Eyeful_v2-Individual.pt": (
        r"bbox/Eyeful_v2-Individual.pt",
        r"bbox/Eyeful_v2-Paired.pt",
    ),
}

# Feature id → group titles to turn ON (others stay at UI default unless overridden)
FEATURE_GROUPS: dict[str, list[str]] = {
    "face_adetailer": ["Face ADetailer"],
    "hand_adetailer": ["Hand ADetailer"],
    "eyes_adetailer": ["Eyes ADetailer"],
    "nsfw_adetailer": ["NSFW ADetailer"],
    "generic_detailer": ["Detailer"],
    "use_sam": ["Use SAMLoader"],
    "clip_skip": ["CLIP Skip"],
    "load_image_i2i": ["Load Image"],
    "separate_vae": ["Seperate VAE"],
    "vpred": ["VPred Model?"],
    "epsilon_scaling": ["Epsilon Scaling"],
    "cfg_zero_star": ["CFGZeroStar"],
    "hires_pre": ["HiresFix Pre Detailer"],
    "hires_post": ["HiresFix Post Detailer"],
    "color_match": ["Color Match"],
    "ultimate_sd_upscale": ["Ultimate SD Upscale"],
    "apply_signature": ["Apply Signature"],
    "post_morphology": ["ImageMorphology"],
    "post_quantize": ["ImageQuantize"],
    "post_sharpen": ["ImageSharpen"],
    "post_contrast": ["Contrast"],
}

# Pale_blue optional groups default ON in shipped UI
DEFAULT_ON_FEATURES = frozenset(
    {"face_adetailer", "use_sam", "clip_skip"}
)

# When I2I: also unmute ungrouped latent helpers
I2I_EXTRA_NODES = (50, 70, 73, 72)  # LoadImage, resize, VAEEncode, select=2
SEPARATE_VAE_SELECT = 57  # PrimitiveInt → ImpactSwitch 40
SIGNATURE_SELECT = 95  # PrimitiveInt → ImpactSwitch 75


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ui(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or HUMAN_UI)
    if not p.is_file():
        raise FileNotFoundError(f"Standard_V37 UI not found: {p}")
    return _load_json(p)


def load_capabilities() -> dict[str, Any]:
    if CAPABILITIES_PATH.is_file():
        return _load_json(CAPABILITIES_PATH)
    return {}


def load_groups() -> dict[str, Any]:
    if GROUPS_PATH.is_file():
        return _load_json(GROUPS_PATH)
    return {}


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _stage(src: str, prefix: str) -> str:
    src_p = Path(src)
    if not src_p.is_file():
        raise FileNotFoundError(f"missing file: {src}")
    dest_dir = Path(COMFYUI_INPUT_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{int(time.time())}_{src_p.name}"
    shutil.copy2(src_p, dest_dir / name)
    return name


def _set_mode(ui: dict[str, Any], node_ids: list[int] | tuple[int, ...], mode: int) -> None:
    want = {int(i) for i in node_ids}
    for n in ui.get("nodes") or []:
        if int(n.get("id", -1)) in want:
            n["mode"] = int(mode)


def _set_widget(ui: dict[str, Any], node_id: int, widgets: list[Any]) -> None:
    for n in ui.get("nodes") or []:
        if int(n.get("id", -1)) == int(node_id):
            n["widgets_values"] = widgets
            return


def apply_feature_modes(
    ui: dict[str, Any],
    *,
    features_on: set[str],
    features_off: set[str],
) -> dict[str, Any]:
    """Mutate a copy of UI: mode 0 for ON groups, mode 4 for OFF groups.

    Starts from **file defaults**, then applies agent overrides.
    """
    ui = copy.deepcopy(ui)
    groups_meta = (load_groups().get("groups") or {})

    # Start: restore file default modes from GROUPS.json when available
    for title, ginfo in groups_meta.items():
        defaults = ginfo.get("default_modes") or {}
        for nid_s, mode in defaults.items():
            _set_mode(ui, [int(nid_s)], int(mode))

    def set_group(title: str, on: bool) -> None:
        ginfo = groups_meta.get(title) or {}
        nids = ginfo.get("node_ids") or []
        if not nids:
            return
        _set_mode(ui, nids, 0 if on else 4)

    # Apply defaults for known optional features, then overrides
    all_toggle = set(FEATURE_GROUPS.keys())
    for fid in all_toggle:
        want_on = fid in DEFAULT_ON_FEATURES
        if fid in features_on:
            want_on = True
        if fid in features_off:
            want_on = False
        for gtitle in FEATURE_GROUPS[fid]:
            set_group(gtitle, want_on)

    # I2I extras (ungrouped VAEEncode chain)
    if "load_image_i2i" in features_on and "load_image_i2i" not in features_off:
        _set_mode(ui, I2I_EXTRA_NODES, 0)
        _set_widget(ui, 72, [2, "fixed"])  # ImpactSwitch 38 → input2
    else:
        # Keep latent on EmptyLatent (switch widget select=1)
        _set_mode(ui, (70, 73, 72), 4)

    if "separate_vae" in features_on and "separate_vae" not in features_off:
        _set_mode(ui, (56, 57), 0)
        _set_widget(ui, 57, [2, "fixed"])
    else:
        _set_mode(ui, (56, 57), 4)

    if "apply_signature" in features_on and "apply_signature" not in features_off:
        _set_mode(ui, (95, 98, 97), 0)
        _set_widget(ui, 95, [2, "fixed"])
    else:
        # Select stays on post-chain input1 via widget default when 95 bypassed
        _set_mode(ui, (95,), 4)

    # Face off: mute Face ADetailer group (already handled via FEATURE_GROUPS)
    return ui


def resolve_features_from_args(
    *,
    preset: str | None = None,
    face: bool | None = None,
    hand: bool = False,
    eyes: bool = False,
    nsfw_detailer: bool = False,
    generic_detailer: bool = False,
    sam: bool | None = None,
    clip_skip: bool | None = None,
    image: str | None = None,
    separate_vae: bool = False,
    vpred: bool = False,
    epsilon_scaling: bool = False,
    cfg_zero_star: bool = False,
    hires_pre: bool = False,
    hires_post: bool = False,
    color_match: bool = False,
    ultimate_upscale: bool = False,
    signature: str | None = None,
    fx_morphology: bool = False,
    fx_quantize: bool = False,
    fx_sharpen: bool = False,
    fx_contrast: bool = False,
    features: list[str] | None = None,
    no_features: list[str] | None = None,
) -> tuple[set[str], set[str]]:
    """Build features_on / features_off sets for apply_feature_modes.

    Order: defaults → optional preset base → explicit CLI flags → --feature/--no-feature.
    ``sam`` / ``clip_skip`` / ``face`` are only applied when not None (preset-safe).
    """
    caps = load_capabilities()
    presets = (caps.get("agent_presets") or {}) if caps else {}

    on: set[str] = set(DEFAULT_ON_FEATURES)
    off: set[str] = set()

    if preset and preset in presets:
        pe = presets[preset]
        on = {f for f in (pe.get("features_on") or []) if f != "core_t2i"}
        off = {f for f in (pe.get("features_off") or []) if f != "core_t2i"}
        # anything not listed stays off for optional pale_blue features
        for fid in FEATURE_GROUPS:
            if fid not in on:
                off.add(fid)

    def _on(fid: str, enabled: bool) -> None:
        if enabled:
            on.add(fid)
            off.discard(fid)
        else:
            off.add(fid)
            on.discard(fid)

    if face is not None:
        _on("face_adetailer", face)
    if hand:
        _on("hand_adetailer", True)
    if eyes:
        _on("eyes_adetailer", True)
    if nsfw_detailer:
        _on("nsfw_adetailer", True)
    if generic_detailer:
        _on("generic_detailer", True)
    if sam is not None:
        _on("use_sam", sam)
    if clip_skip is not None:
        _on("clip_skip", clip_skip)
    if image:
        _on("load_image_i2i", True)
    if separate_vae:
        _on("separate_vae", True)
    if vpred:
        _on("vpred", True)
    if epsilon_scaling:
        _on("epsilon_scaling", True)
    if cfg_zero_star:
        _on("cfg_zero_star", True)
    if hires_pre:
        _on("hires_pre", True)
    if hires_post:
        _on("hires_post", True)
    if color_match:
        _on("color_match", True)
    if ultimate_upscale:
        _on("ultimate_sd_upscale", True)
    if signature:
        _on("apply_signature", True)
    if fx_morphology:
        _on("post_morphology", True)
    if fx_quantize:
        _on("post_quantize", True)
    if fx_sharpen:
        _on("post_sharpen", True)
    if fx_contrast:
        _on("post_contrast", True)

    for f in features or []:
        f = f.strip()
        if f:
            on.add(f)
            off.discard(f)
    for f in no_features or []:
        f = f.strip()
        if f:
            off.add(f)
            on.discard(f)

    return on, off


def _widget_names(object_info: dict[str, Any] | None, class_type: str) -> list[str]:
    if not object_info or class_type not in object_info:
        return []
    names: list[str] = []
    inp = object_info[class_type].get("input") or {}
    for section in ("required", "optional"):
        block = inp.get(section) or {}
        if not isinstance(block, dict):
            continue
        for name, spec in block.items():
            if not isinstance(spec, (list, tuple)) or not spec:
                continue
            first = spec[0]
            if isinstance(first, list):
                names.append(name)
                continue
            if isinstance(first, str) and first in (
                "INT",
                "FLOAT",
                "STRING",
                "BOOLEAN",
                "COMBO",
            ):
                names.append(name)
                continue
            # skip pure socket types (all-caps custom)
            if isinstance(first, str) and (
                first.isupper() or first in ("IMAGE", "MODEL", "CLIP", "VAE", "LATENT", "MASK")
            ):
                continue
            # AUTOCOMPLETE / custom widget strings
            if isinstance(first, str):
                names.append(name)
    return names


def _apply_widgets_with_seed_control(
    inputs: dict[str, Any],
    widgets_values: list[Any],
    widget_names: list[str],
) -> None:
    """Map widgets_values → inputs; skip seed control_after_generate tokens."""
    if not widget_names or not isinstance(widgets_values, list):
        return
    wi = 0
    for name in widget_names:
        if wi >= len(widgets_values):
            break
        # linked sockets already set — still consume widget slot when present in list
        val = widgets_values[wi]
        if name == "seed" and wi + 1 < len(widgets_values) and widgets_values[wi + 1] in (
            "fixed",
            "randomize",
            "increment",
            "decrement",
        ):
            if not (name in inputs and isinstance(inputs[name], list)):
                inputs[name] = val
            wi += 2
            continue
        if name in inputs and isinstance(inputs[name], list):
            # linked: advance one slot only (no control widget for non-seed usually)
            wi += 1
            continue
        # combo placeholders
        if isinstance(val, str) and val.startswith("Select "):
            inputs[name] = val
            wi += 1
            continue
        inputs[name] = val
        wi += 1


def _reapply_widgets_from_ui(
    api: dict[str, Any],
    ui: dict[str, Any],
    object_info: dict[str, Any] | None,
) -> None:
    """Correct expand widget mis-alignment for active API nodes."""
    ui_by_id = {str(n["id"]): n for n in (ui.get("nodes") or []) if "id" in n}
    for nid, node in api.items():
        ui_n = ui_by_id.get(str(nid))
        if not ui_n:
            continue
        if int(ui_n.get("mode", 0) or 0) in (2, 4):
            continue
        ct = node.get("class_type") or ""
        wv = ui_n.get("widgets_values")
        if not isinstance(wv, list):
            continue
        names = _widget_names(object_info, ct)
        if not names:
            continue
        ins = node.setdefault("inputs", {})
        # Keep links; re-fill widgets
        _apply_widgets_with_seed_control(ins, wv, names)


def _link_index(ui: dict[str, Any]) -> dict[int, list]:
    links: dict[int, list] = {}
    for L in ui.get("links") or []:
        if isinstance(L, list) and len(L) >= 5:
            links[int(L[0])] = L
    return links


def _first_live_source(
    api: dict[str, Any],
    nodes: dict[int, dict[str, Any]],
    links: dict[int, list],
    origin_id: int,
    origin_slot: int,
    depth: int = 0,
    prefer_type: str | None = None,
) -> tuple[str, int] | None:
    """Follow mode-4 bypass chain until an API-live producer is found."""
    if depth > 32:
        return None
    if str(origin_id) in api:
        return (str(origin_id), int(origin_slot))
    n = nodes.get(int(origin_id))
    if not n:
        return None
    mode = int(n.get("mode", 0) or 0)
    if mode == 2:
        return None
    if mode != 4:
        # active but not in API (dropped chrome) — try passthrough-like first input
        pass
    # BYPASS or missing: follow typed input if possible
    typed = (prefer_type or "").upper()
    candidates: list[tuple[int, int]] = []
    for inp in n.get("inputs") or []:
        lid = inp.get("link")
        if lid is None or int(lid) not in links:
            continue
        L = links[int(lid)]
        ity = str(inp.get("type") or L[5] if len(L) > 5 else "").upper()
        candidates.append((int(L[1]), int(L[2]), ity))  # type: ignore
    # prefer matching type
    ordered = []
    if typed:
        ordered.extend([(a, b) for a, b, t in candidates if t == typed or typed in t])
    ordered.extend([(a, b) for a, b, _t in candidates if (a, b) not in ordered])
    for oid, oslot in ordered:
        hit = _first_live_source(
            api, nodes, links, oid, oslot, depth + 1, prefer_type=prefer_type
        )
        if hit:
            return hit
    return None


def _restore_links_from_ui(api: dict[str, Any], ui: dict[str, Any]) -> None:
    """Re-bind sockets expand dropped (muted origins) via multi-hop bypass.

    Critical for MODEL (KSampler via Mahiro/Epsilon chain) and IMAGE (saver via post FX).
    """
    nodes = {int(n["id"]): n for n in (ui.get("nodes") or []) if "id" in n}
    links = _link_index(ui)
    # Common type hints by input name
    name_type = {
        "model": "MODEL",
        "clip": "CLIP",
        "vae": "VAE",
        "positive": "CONDITIONING",
        "negative": "CONDITIONING",
        "latent_image": "LATENT",
        "samples": "LATENT",
        "image": "IMAGE",
        "images": "IMAGE",
        "pixels": "IMAGE",
        "detailer_pipe": "DETAILER_PIPE",
        "bbox_detector": "BBOX_DETECTOR",
        "sam_model_opt": "SAM_MODEL",
        "sam_model": "SAM_MODEL",
    }

    for n in ui.get("nodes") or []:
        nid = str(n.get("id"))
        if nid not in api:
            continue
        if int(n.get("mode", 0) or 0) in (2, 4):
            continue
        ins = api[nid].setdefault("inputs", {})
        for inp in n.get("inputs") or []:
            name = inp.get("name")
            lid = inp.get("link")
            if name is None or lid is None or int(lid) not in links:
                continue
            cur = ins.get(name)
            if isinstance(cur, list) and len(cur) == 2 and str(cur[0]) in api:
                continue
            L = links[int(lid)]
            prefer = name_type.get(name) or str(inp.get("type") or "")
            live = _first_live_source(
                api, nodes, links, int(L[1]), int(L[2]), prefer_type=prefer or None
            )
            if live:
                ins[name] = [live[0], live[1]]


def _resolve_bypass_hops(api: dict[str, Any], ui: dict[str, Any]) -> None:
    """Re-point inputs that still reference missing (bypassed) node ids."""
    nodes = {int(n["id"]): n for n in (ui.get("nodes") or []) if "id" in n}
    links = _link_index(ui)

    for node in api.values():
        ins = node.get("inputs") or {}
        for k, v in list(ins.items()):
            if not (isinstance(v, list) and len(v) == 2):
                continue
            src, slot = v[0], v[1]
            if str(src) in api:
                continue
            prefer = {
                "model": "MODEL",
                "images": "IMAGE",
                "image": "IMAGE",
                "clip": "CLIP",
                "vae": "VAE",
            }.get(k)
            try:
                live = _first_live_source(
                    api, nodes, links, int(src), int(slot), prefer_type=prefer
                )
            except Exception:
                live = None
            if live:
                ins[k] = [live[0], live[1]]
            else:
                del ins[k]


def _fix_frontend_only_helpers(api: dict[str, Any]) -> None:
    """Replace WidgetToString / easy showAnything consumers with static values."""
    sampler = "euler_ancestral"
    scheduler = "normal"
    if "18" in api:
        ins18 = api["18"].get("inputs") or {}
        if isinstance(ins18.get("sampler"), str):
            sampler = ins18["sampler"]
        if isinstance(ins18.get("scheduler"), str):
            scheduler = ins18["scheduler"]

    drop_types = {
        "Image Comparer (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "Fast Groups Muter (rgthree)",
        "easy showAnything",
        "WidgetToString",
        "Note",
    }
    dropped = {nid for nid, n in api.items() if n.get("class_type") in drop_types}
    for nid in dropped:
        del api[nid]

    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) in dropped:
                if k in ("sampler_name", "sampler"):
                    ins[k] = sampler
                elif k in ("scheduler", "scheduler_name"):
                    ins[k] = scheduler
                elif k == "modelname":
                    ckpt = (api.get("30") or {}).get("inputs", {}).get("ckpt_name")
                    ins[k] = Path(str(ckpt or DEFAULT_CKPT)).stem
                elif k == "anything":
                    del ins[k]
                else:
                    del ins[k]
        # KSampler free widgets may still hold pack defaults; prefer Control Center
        if n.get("class_type") == "KSampler":
            if not isinstance(ins.get("sampler_name"), list):
                ins["sampler_name"] = sampler
            if not isinstance(ins.get("scheduler"), list):
                ins["scheduler"] = scheduler
            # steps/cfg/denoise/seed should be linked from 18/32 when present
            if "18" in api:
                if not isinstance(ins.get("steps"), list):
                    ins["steps"] = ["18", 1]
                if not isinstance(ins.get("cfg"), list):
                    ins["cfg"] = ["18", 2]
                if not isinstance(ins.get("denoise"), list):
                    ins["denoise"] = ["18", 5]
            if "32" in api and not isinstance(ins.get("seed"), list):
                ins["seed"] = ["32", 0]


def _fix_bad_widget_types(api: dict[str, Any]) -> None:
    """Coerce empty lists / wrong types left by widget packing."""
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if v == [] or v == {}:
                if k in (
                    "allow_strength_adjustment",
                    "group_mode",
                    "default_active",
                    "optimize_png",
                    "lossless_webp",
                    "download_civitai_data",
                    "easy_remix",
                    "show_preview",
                    "embed_workflow",
                    "save_workflow_as_json",
                ):
                    ins[k] = False
                elif k in ("trigger_words",):
                    pass
                else:
                    del ins[k]
            if k == "allow_strength_adjustment" and not isinstance(v, bool):
                ins[k] = bool(v) if v not in ([], None, "") else False
            if k in ("group_mode", "default_active") and not isinstance(v, bool):
                if isinstance(v, list):
                    ins[k] = False
        # TriggerWord Toggle: ensure booleans
        if n.get("class_type") == "TriggerWord Toggle (LoraManager)":
            ins.setdefault("group_mode", True)
            ins.setdefault("default_active", False)
            ins["allow_strength_adjustment"] = bool(
                ins.get("allow_strength_adjustment") or False
            )
            if not isinstance(ins.get("allow_strength_adjustment"), bool):
                ins["allow_strength_adjustment"] = False


def _fix_combo_placeholders(api: dict[str, Any]) -> None:
    for n in api.values():
        ct = n.get("class_type") or ""
        ins = n.get("inputs") or {}
        if ct == "ImpactWildcardProcessor":
            ins["Select to add Wildcard"] = WILDCARD_PLACEHOLDER
            if ins.get("mode") not in ("populate", "fixed", "fixed seed"):
                ins["mode"] = "populate"
        if ct in ("ToDetailerPipe", "EditDetailerPipe"):
            if "Select to add LoRA" in ins or True:
                ins["Select to add LoRA"] = LORA_PLACEHOLDER
            ins["Select to add Wildcard"] = WILDCARD_PLACEHOLDER
            if not isinstance(ins.get("wildcard"), str):
                ins["wildcard"] = ins.get("wildcard") or ""
        if ct == "Lora Loader (LoraManager)":
            if not isinstance(ins.get("text"), str):
                ins["text"] = ""


def _remap_detectors(api: dict[str, Any], models_root: Path | None = None) -> None:
    root = models_root or Path(
        os.environ.get(
            "COMFYUI_MODELS",
            r"F:\ComfyUI_windows_portable\ComfyUI\models",
        )
    )
    ultra = root / "ultralytics"
    for n in api.values():
        if n.get("class_type") != "UltralyticsDetectorProvider":
            continue
        ins = n.get("inputs") or {}
        name = ins.get("model_name")
        if not isinstance(name, str):
            continue
        candidates = DETECTOR_REMAP.get(name, (name,))
        for c in candidates:
            if (ultra / c.replace("/", os.sep)).is_file() or (ultra / c).is_file():
                ins["model_name"] = c
                break


def _wire_image_saver_fallback(api: dict[str, Any]) -> None:
    """If Image Saver lost images input, wire FaceDetailer or VAEDecode."""
    saver_id = None
    for nid, n in api.items():
        if n.get("class_type") == "Image Saver":
            saver_id = nid
            break
    if not saver_id:
        return
    ins = api[saver_id].setdefault("inputs", {})
    img = ins.get("images")
    if isinstance(img, list) and len(img) == 2 and str(img[0]) in api:
        return
    # Prefer FaceDetailerPipe if live
    for nid, n in api.items():
        if n.get("class_type") == "FaceDetailerPipe":
            ins["images"] = [nid, 0]
            return
    for nid, n in api.items():
        if n.get("class_type") == "VAEDecode":
            ins["images"] = [nid, 0]
            return


def build_api_from_ui(
    *,
    ui: dict[str, Any] | None = None,
    ui_path: str | Path | None = None,
    features_on: set[str] | None = None,
    features_off: set[str] | None = None,
    server_address: str = DEFAULT_SERVER,
    cache: bool = False,
) -> dict[str, Any]:
    base = ui if ui is not None else load_ui(ui_path)
    ui_switched = apply_feature_modes(
        base,
        features_on=features_on or set(DEFAULT_ON_FEATURES),
        features_off=features_off or set(),
    )
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui_switched, object_info=oi)
    _reapply_widgets_from_ui(api, ui_switched, oi)
    _fix_bad_widget_types(api)
    # Restore sockets expand deleted when origin was mode-4 (MODEL/IMAGE chains)
    _restore_links_from_ui(api, ui_switched)
    _resolve_bypass_hops(api, ui_switched)
    _fix_frontend_only_helpers(api)
    _fix_combo_placeholders(api)
    _fix_bad_widget_types(api)
    _remap_detectors(api)
    # After dropping chrome, restore again (showAnything sampler → static already)
    _restore_links_from_ui(api, ui_switched)
    _resolve_bypass_hops(api, ui_switched)
    _wire_image_saver_fallback(api)

    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in api:
                del ins[k]
    _wire_image_saver_fallback(api)
    _fix_bad_widget_types(api)

    if cache:
        try:
            API_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(API_CACHE, "w", encoding="utf-8") as f:
                json.dump(api, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return api


def apply_ports(
    api: dict[str, Any],
    *,
    positive: str,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    denoise: float | None = None,
    batch_size: int | None = None,
    ckpt_name: str | None = None,
    lora_text: str | None = None,
    image_name: str | None = None,
    signature_name: str | None = None,
    vae_name: str | None = None,
    filename: str = "illustrious_std_v37",
) -> dict[str, Any]:
    """Port inject only — node ids from Standard_V37 UI."""
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    neg = negative if negative is not None else DEFAULT_NEG

    # ImpactWildcardProcessor 3=pos, 4=neg
    if "3" in api:
        api["3"].setdefault("inputs", {})
        api["3"]["inputs"]["wildcard_text"] = positive
        api["3"]["inputs"]["populated_text"] = positive
        api["3"]["inputs"]["mode"] = "populate"
        api["3"]["inputs"]["Select to add Wildcard"] = WILDCARD_PLACEHOLDER
    if "4" in api:
        api["4"].setdefault("inputs", {})
        api["4"]["inputs"]["wildcard_text"] = neg
        api["4"]["inputs"]["populated_text"] = neg
        api["4"]["inputs"]["mode"] = "populate"
        api["4"]["inputs"]["Select to add Wildcard"] = WILDCARD_PLACEHOLDER

    if "32" in api:
        api["32"].setdefault("inputs", {})["seed"] = seed_i

    if "1" in api and width is not None:
        api["1"].setdefault("inputs", {})["value"] = int(width)
    if "12" in api and height is not None:
        api["12"].setdefault("inputs", {})["value"] = int(height)
    if "29" in api and batch_size is not None:
        api["29"].setdefault("inputs", {})["value"] = int(batch_size)

    if "18" in api:
        ins = api["18"].setdefault("inputs", {})
        # seed linked from 32 usually
        if steps is not None:
            ins["steps"] = int(steps)
        if cfg is not None:
            ins["cfg"] = float(cfg)
        if sampler is not None:
            ins["sampler"] = sampler
        if scheduler is not None:
            ins["scheduler"] = scheduler
        if denoise is not None:
            ins["denoise"] = float(denoise)

    # KSampler may still hold free widgets if not linked
    if "46" in api:
        k = api["46"].setdefault("inputs", {})
        if denoise is not None and not isinstance(k.get("denoise"), list):
            k["denoise"] = float(denoise)
        if steps is not None and not isinstance(k.get("steps"), list):
            k["steps"] = int(steps)
        if cfg is not None and not isinstance(k.get("cfg"), list):
            k["cfg"] = float(cfg)

    if "30" in api and ckpt_name:
        api["30"].setdefault("inputs", {})["ckpt_name"] = ckpt_name

    if "5" in api and lora_text is not None:
        api["5"].setdefault("inputs", {})["text"] = lora_text

    if image_name and "50" in api:
        api["50"].setdefault("inputs", {})["image"] = image_name

    if signature_name and "77" in api:
        api["77"].setdefault("inputs", {})["image"] = signature_name

    if vae_name and "56" in api:
        api["56"].setdefault("inputs", {})["vae_name"] = vae_name

    if "54" in api:
        ins = api["54"].setdefault("inputs", {})
        ins["filename"] = filename
        ins["path"] = ""
        ins["extension"] = "png"
        # avoid civitai network during agent runs
        if "download_civitai_data" in ins:
            ins["download_civitai_data"] = False
        if not isinstance(ins.get("sampler_name"), str):
            ins["sampler_name"] = sampler or "euler_ancestral"
        if not isinstance(ins.get("scheduler_name"), str):
            ins["scheduler_name"] = scheduler or "normal"
        if not isinstance(ins.get("modelname"), str):
            ck = ckpt_name or (api.get("30") or {}).get("inputs", {}).get("ckpt_name")
            ins["modelname"] = Path(str(ck or DEFAULT_CKPT)).stem
        if not isinstance(ins.get("positive"), str):
            ins["positive"] = positive
        if not isinstance(ins.get("negative"), str):
            ins["negative"] = neg

    return {"seed": seed_i, "positive": positive[:200], "negative": neg[:120]}


def generate_illustrious_standard(
    *,
    positive: str,
    output_path: str,
    negative: str | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    denoise: float | None = None,
    batch_size: int | None = None,
    ckpt_name: str | None = None,
    lora_text: str | None = None,
    image_path: str | None = None,
    signature_path: str | None = None,
    vae_name: str | None = None,
    features_on: set[str] | None = None,
    features_off: set[str] | None = None,
    timeout_sec: float = 600,
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
    filename_prefix: str = "illustrious_std_v37",
) -> dict[str, Any]:
    """Run real Standard_V37 with feature modes + ports."""
    on = set(features_on or DEFAULT_ON_FEATURES)
    off = set(features_off or set())
    if image_path:
        on.add("load_image_i2i")
        off.discard("load_image_i2i")
    if signature_path:
        on.add("apply_signature")
        off.discard("apply_signature")

    try:
        api = build_api_from_ui(
            ui_path=ui_path,
            features_on=on,
            features_off=off,
            server_address=server_address,
            cache=True,
        )
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    image_name = None
    signature_name = None
    try:
        if image_path:
            image_name = _stage(image_path, "stdv37_i2i")
        if signature_path:
            signature_name = _stage(signature_path, "stdv37_sig")
    except Exception as e:
        return fail_result(error="INPUT_MISSING", message=str(e))

    port_meta = apply_ports(
        api,
        positive=positive,
        negative=negative,
        seed=seed,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        sampler=sampler,
        scheduler=scheduler,
        denoise=denoise,
        batch_size=batch_size,
        ckpt_name=ckpt_name,
        lora_text=lora_text,
        image_name=image_name,
        signature_name=signature_name,
        vae_name=vae_name,
        filename=filename_prefix,
    )

    # Final validation: Image Saver must have images
    has_saver = any(n.get("class_type") == "Image Saver" for n in api.values())
    if not has_saver:
        return fail_result(
            error="NO_SAVER",
            message="Image Saver missing after expand — check group modes",
        )

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(
            error="QUEUE_FAILED",
            message=str(e),
            features_on=sorted(on),
            features_off=sorted(off),
            api_node_count=len(api),
        )

    try:
        # wait_for_history returns the entry dict (has "outputs"), not {prompt_id: entry}
        entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
        if isinstance(entry, dict) and prompt_id in entry and "outputs" not in entry:
            entry = entry[prompt_id]
        fn, sub, typ = extract_first_image(entry)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        download_image(server_address, fn, sub, typ, str(out_p))
    except Exception as e:
        return fail_result(
            error="RUN_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            features_on=sorted(on),
            features_off=sorted(off),
        )

    meta = {
        "tool": "illustrious_standard_v37",
        "workflow": str(HUMAN_UI),
        "features_on": sorted(on),
        "features_off": sorted(off),
        "ports": port_meta,
        "output": str(out_p),
        "prompt_id": prompt_id,
        "comfy_image": {"filename": fn, "subfolder": sub, "type": typ},
        "created_at": utc_now_iso(),
    }
    meta_path = str(out_p) + ".meta.json"
    write_meta(meta_path, meta)
    return ok_result(
        output_path=str(out_p),
        output=str(out_p),
        meta_path=meta_path,
        prompt_id=prompt_id,
        seed=port_meta.get("seed"),
        features_on=sorted(on),
        features_off=sorted(off),
        ports=port_meta,
        tool="illustrious_standard_v37",
    )
