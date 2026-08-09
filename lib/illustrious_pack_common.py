"""Shared Legendaer Illustrious pack helpers (Standard/Advanced/Detailer).

Reuses expand + multi-hop bypass pipeline from Standard_V37 runner.
"""

from __future__ import annotations

import copy
import json
import os
import random
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
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
from lib import illustrious_standard_v37_runner as std

DEFAULT_CKPT = r"Illustrious\fabricatedXL_v70.safetensors"
DEFAULT_NEG = std.DEFAULT_NEG
WILDCARD_PLACEHOLDER = std.WILDCARD_PLACEHOLDER
LORA_PLACEHOLDER = std.LORA_PLACEHOLDER

# bare ckpt names in Advanced/Detailer UI → Comfy path
CKPT_REMAP = {
    "fabricatedXL_v70.safetensors": r"Illustrious\fabricatedXL_v70.safetensors",
    "animij_v10.safetensors": r"Illustrious\animij_v10.safetensors",
    "perfectdeliberate_v90.safetensors": r"Illustrious\perfectdeliberate_v90.safetensors",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_group_modes(
    ui: dict[str, Any],
    groups_meta: dict[str, Any],
    feature_groups: dict[str, list[str]],
    *,
    features_on: set[str],
    features_off: set[str],
    default_on: set[str],
) -> dict[str, Any]:
    """Start from GROUPS default_modes, then apply feature on/off."""
    ui = copy.deepcopy(ui)

    for _title, ginfo in groups_meta.items():
        defaults = ginfo.get("default_modes") or {}
        for nid_s, mode in defaults.items():
            std._set_mode(ui, [int(nid_s)], int(mode))

    def set_group(title: str, on: bool) -> None:
        ginfo = groups_meta.get(title) or {}
        nids = ginfo.get("node_ids") or []
        if nids:
            std._set_mode(ui, nids, 0 if on else 4)

    for fid, titles in feature_groups.items():
        want = fid in default_on
        if fid in features_on:
            want = True
        if fid in features_off:
            want = False
        for t in titles:
            set_group(t, want)
    return ui


def build_api(
    ui: dict[str, Any],
    *,
    server_address: str = DEFAULT_SERVER,
    aggressive_relink: bool = True,
) -> dict[str, Any]:
    """Expand UI → API.

    ``aggressive_relink`` (default True) matches Standard_V37 multi-hop bypass
    recovery. Advanced graphs can mis-type ImpactSwitch sockets with that path —
    callers may set False and rely on expand + light cleanup only.
    """
    oi = std._fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    std._reapply_widgets_from_ui(api, ui, oi)
    std._fix_bad_widget_types(api)
    if aggressive_relink:
        std._restore_links_from_ui(api, ui)
        std._resolve_bypass_hops(api, ui)
    std._fix_frontend_only_helpers(api)
    std._fix_combo_placeholders(api)
    std._fix_bad_widget_types(api)
    std._remap_detectors(api)
    if aggressive_relink:
        std._restore_links_from_ui(api, ui)
        std._resolve_bypass_hops(api, ui)
    std._wire_image_saver_fallback(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in api:
                del ins[k]
    # Drop dangling Reroute nodes' consumers if still pointing at missing ids
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in api:
                del ins[k]
    std._wire_image_saver_fallback(api)
    std._fix_bad_widget_types(api)
    # ckpt bare name remap
    for n in api.values():
        if n.get("class_type") == "CheckpointLoaderSimple":
            ins = n.setdefault("inputs", {})
            name = ins.get("ckpt_name")
            if isinstance(name, str) and name in CKPT_REMAP:
                ins["ckpt_name"] = CKPT_REMAP[name]
    return api


def set_wildcard(api: dict[str, Any], node_id: str, text: str) -> None:
    if node_id not in api:
        return
    ins = api[node_id].setdefault("inputs", {})
    ins["wildcard_text"] = text
    ins["populated_text"] = text
    ins["mode"] = "populate"
    ins["Select to add Wildcard"] = WILDCARD_PLACEHOLDER


def set_seed(api: dict[str, Any], node_id: str, seed: int) -> None:
    if node_id in api:
        api[node_id].setdefault("inputs", {})["seed"] = int(seed)


def set_input_params(
    api: dict[str, Any],
    node_id: str,
    *,
    steps: int | None = None,
    cfg: float | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    denoise: float | None = None,
) -> None:
    if node_id not in api:
        return
    ins = api[node_id].setdefault("inputs", {})
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


def set_ckpt(api: dict[str, Any], node_id: str, ckpt: str | None) -> None:
    if not ckpt or node_id not in api:
        return
    name = CKPT_REMAP.get(ckpt, ckpt)
    api[node_id].setdefault("inputs", {})["ckpt_name"] = name


def set_lora(api: dict[str, Any], node_id: str, lora_text: str | None) -> None:
    if lora_text is None or node_id not in api:
        return
    api[node_id].setdefault("inputs", {})["text"] = lora_text


def set_load_image(api: dict[str, Any], node_id: str, image_name: str | None) -> None:
    if image_name and node_id in api:
        api[node_id].setdefault("inputs", {})["image"] = image_name


def set_empty_latent(
    api: dict[str, Any],
    node_id: str,
    *,
    width: int | None = None,
    height: int | None = None,
    batch: int | None = None,
) -> None:
    if node_id not in api:
        return
    ins = api[node_id].setdefault("inputs", {})
    if width is not None:
        ins["width"] = int(width)
    if height is not None:
        ins["height"] = int(height)
    if batch is not None:
        ins["batch_size"] = int(batch)


def set_saver_meta(
    api: dict[str, Any],
    node_id: str,
    *,
    filename: str,
    positive: str,
    negative: str,
    ckpt_name: str | None,
    sampler: str | None,
    scheduler: str | None,
) -> None:
    if node_id not in api:
        # try any Image Saver
        for nid, n in api.items():
            if n.get("class_type") == "Image Saver":
                node_id = nid
                break
        else:
            return
    ins = api[node_id].setdefault("inputs", {})
    ins["filename"] = filename
    ins["path"] = ""
    ins["extension"] = "png"
    if "download_civitai_data" in ins:
        ins["download_civitai_data"] = False
    if not isinstance(ins.get("sampler_name"), str):
        ins["sampler_name"] = sampler or "euler_ancestral"
    if not isinstance(ins.get("scheduler_name"), str):
        ins["scheduler_name"] = scheduler or "normal"
    if not isinstance(ins.get("modelname"), str):
        ins["modelname"] = Path(str(ckpt_name or DEFAULT_CKPT)).stem
    if not isinstance(ins.get("positive"), str):
        ins["positive"] = positive
    if not isinstance(ins.get("negative"), str):
        ins["negative"] = negative


def run_api(
    api: dict[str, Any],
    *,
    output_path: str,
    seed: int,
    timeout_sec: float,
    server_address: str,
    meta_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    try:
        pid = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e))
    try:
        entry = wait_for_history(server_address, pid, timeout_sec=timeout_sec)
        if isinstance(entry, dict) and pid in entry and "outputs" not in entry:
            entry = entry[pid]
        fn, sub, typ = extract_first_image(entry)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        download_image(server_address, fn, sub, typ, str(out_p))
    except Exception as e:
        return fail_result(error="RUN_FAILED", message=str(e), prompt_id=pid)
    meta = {
        "ok": True,
        "tool": "illustrious_pack",
        "seed": seed,
        "prompt_id": pid,
        "output": str(out_p),
        "elapsed_sec": round(time.time() - t0, 2),
        "created_at": utc_now_iso(),
    }
    if meta_extra:
        meta.update(meta_extra)
    try:
        write_meta(str(out_p), meta)
    except Exception:
        pass
    return ok_result(**meta)


def stage(src: str, prefix: str) -> str:
    return std._stage(src, prefix)


def collapse_impact_switches(api: dict[str, Any]) -> None:
    """Short-circuit static ImpactSwitch (select=int) to the chosen input.

    Avoids ImpactSwitch runtime crashes and wrong multi-consumer wiring.
    Removes collapsed switches from the graph after rewiring.
    """
    remove: list[str] = []
    for nid, n in list(api.items()):
        if n.get("class_type") != "ImpactSwitch":
            continue
        ins = n.get("inputs") or {}
        sel = ins.get("select", 1)
        if isinstance(sel, list):
            continue
        try:
            sel_i = int(sel)
        except Exception:
            sel_i = 1
        src = ins.get(f"input{sel_i}") or ins.get("input1")
        if not (isinstance(src, list) and len(src) == 2):
            continue
        # normalize ids to str
        src = [str(src[0]), int(src[1])]
        for m in api.values():
            mins = m.get("inputs") or {}
            for k, v in list(mins.items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                    mins[k] = [src[0], src[1]]
        remove.append(str(nid))
    for nid in remove:
        api.pop(nid, None)


def collapse_reroutes(api: dict[str, Any]) -> None:
    """Flatten Reroute (rgthree) / core Reroute nodes and remove them.

    Core ``Reroute`` is often stripped from modern Comfy installs — leaving it
    causes missing_node_type. Always short-circuit then delete.
    """
    for _ in range(6):
        remove: list[str] = []
        for nid, n in list(api.items()):
            ct = n.get("class_type") or ""
            if "Reroute" not in ct and ct not in ("Reroute", "ReroutePrimitive"):
                continue
            ins = n.get("inputs") or {}
            src = None
            for v in ins.values():
                if isinstance(v, list) and len(v) == 2:
                    src = [str(v[0]), int(v[1])]
                    break
            if src:
                for m in api.values():
                    mins = m.get("inputs") or {}
                    for k, v in list(mins.items()):
                        if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                            mins[k] = [src[0], src[1]]
            remove.append(str(nid))
        for nid in remove:
            api.pop(nid, None)
        if not remove:
            break


def ensure_clip_on_encoders(api: dict[str, Any]) -> None:
    """CLIPTextEncode / ToDetailerPipe must receive CLIP, not MODEL."""
    clip_src = None
    for nid, n in api.items():
        ct = n.get("class_type") or ""
        if ct == "Lora Loader (LoraManager)":
            clip_src = [nid, 1]
            break
        if ct == "CheckpointLoaderSimple" and clip_src is None:
            clip_src = [nid, 1]
    if not clip_src:
        return
    for n in api.values():
        ct = n.get("class_type") or ""
        if ct not in ("CLIPTextEncode", "ToDetailerPipe", "EditDetailerPipe"):
            continue
        ins = n.setdefault("inputs", {})
        # strip invalid free clip widget if present as bad type
        cur = ins.get("clip")
        if isinstance(cur, list) and len(cur) == 2 and str(cur[0]) in api:
            src_n = api[str(cur[0])]
            sct = src_n.get("class_type") or ""
            if sct in ("Lora Loader (LoraManager)", "CheckpointLoaderSimple") and int(
                cur[1]
            ) == 0:
                ins["clip"] = [str(cur[0]), 1]
        elif "clip" not in ins or not isinstance(cur, list):
            ins["clip"] = clip_src
        # FaceDetailerPipe uses detailer_pipe, not free clip


def ensure_ksampler_io(api: dict[str, Any]) -> None:
    """If KSampler missing model/positive/negative/latent, wire from common producers."""
    model_src = None
    clip_src = None
    pos_src = None
    neg_src = None
    latent_src = None
    vae_src = None
    for nid, n in api.items():
        ct = n.get("class_type") or ""
        if ct in ("Lora Loader (LoraManager)", "CheckpointLoaderSimple", "Power Lora Loader (rgthree)"):
            # model output 0, clip 1 for checkpoint/lora
            if model_src is None:
                model_src = [nid, 0]
            if clip_src is None and ct == "CheckpointLoaderSimple":
                clip_src = [nid, 1]
                vae_src = [nid, 2]
            if ct.startswith("Lora") and model_src is None:
                model_src = [nid, 0]
        if ct == "Lora Loader (LoraManager)":
            model_src = [nid, 0]
            clip_src = [nid, 1]
        if ct == "CLIPTextEncode" and pos_src is None:
            pos_src = [nid, 0]
        if ct == "EmptyLatentImage":
            latent_src = [nid, 0]
        if ct == "ImpactWildcardProcessor":
            # not conditioning
            pass
    # Prefer last CLIPTextEncode as neg if two
    encodes = [nid for nid, n in api.items() if n.get("class_type") == "CLIPTextEncode"]
    if len(encodes) >= 2:
        pos_src = [encodes[0], 0]
        neg_src = [encodes[1], 0]
    elif len(encodes) == 1:
        pos_src = [encodes[0], 0]
        neg_src = pos_src

    for nid, n in api.items():
        if n.get("class_type") != "KSampler":
            continue
        ins = n.setdefault("inputs", {})
        if model_src and not (isinstance(ins.get("model"), list) and str(ins["model"][0]) in api):
            ins["model"] = model_src
        if pos_src and not (isinstance(ins.get("positive"), list) and str(ins["positive"][0]) in api):
            ins["positive"] = pos_src
        if neg_src and not (isinstance(ins.get("negative"), list) and str(ins["negative"][0]) in api):
            ins["negative"] = neg_src
        if latent_src and not (
            isinstance(ins.get("latent_image"), list) and str(ins["latent_image"][0]) in api
        ):
            ins["latent_image"] = latent_src

    for nid, n in api.items():
        if n.get("class_type") != "VAEDecode":
            continue
        ins = n.setdefault("inputs", {})
        # samples from first KSampler
        if not (isinstance(ins.get("samples"), list) and str(ins.get("samples", [None])[0]) in api):
            for kn, knode in api.items():
                if knode.get("class_type") == "KSampler":
                    ins["samples"] = [kn, 0]
                    break
        if vae_src and not (isinstance(ins.get("vae"), list) and str(ins["vae"][0]) in api):
            ins["vae"] = vae_src


def wire_saver_from_decode(api: dict[str, Any]) -> None:
    """Point Image Saver images to FaceDetailerPipe or VAEDecode output."""
    preferred = None
    for nid, n in api.items():
        if n.get("class_type") == "FaceDetailerPipe":
            preferred = [nid, 0]
            break
    if preferred is None:
        for nid, n in api.items():
            if n.get("class_type") == "VAEDecode":
                preferred = [nid, 0]
                break
    if preferred is None:
        return
    for n in api.values():
        if n.get("class_type") == "Image Saver":
            ins = n.setdefault("inputs", {})
            cur = ins.get("images")
            if not (isinstance(cur, list) and len(cur) == 2 and str(cur[0]) in api):
                ins["images"] = preferred
            else:
                # still prefer decode/detailer over broken switch
                src = api.get(str(cur[0]), {})
                if src.get("class_type") in ("ImpactSwitch",) or str(cur[0]) not in api:
                    ins["images"] = preferred
