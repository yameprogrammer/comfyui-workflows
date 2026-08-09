"""Detailer_V37 — real Legendaer UI for existing-image polish / inpaint / outpaint."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from lib.comfy_client import DEFAULT_SERVER, fail_result
from lib import illustrious_pack_common as common

WORKSPACE = Path(__file__).resolve().parents[1]
HUMAN = WORKSPACE / "workflows" / "human" / "illustrious_detailer_v37"
UI_PATH = HUMAN / "Detailer_V37.json"
GROUPS_PATH = HUMAN / "GROUPS.json"
CAPS_PATH = HUMAN / "CAPABILITIES.json"

DEFAULT_CKPT = common.DEFAULT_CKPT
DEFAULT_NEG = common.DEFAULT_NEG

FEATURE_GROUPS: dict[str, list[str]] = {
    "face_adetailer": ["Face ADetailer"],
    "hand_adetailer": ["Hand ADetailer"],
    "eyes_adetailer": ["Eyes ADetailer"],
    "nsfw_adetailer": ["NSFW ADetailer"],
    "generic_detailer": ["Detailer"],
    "mask_adetailer": ["Mask ADetailer"],
    "use_sam": ["Use SAMLoader"],
    "clip_skip": ["CLIP Skip"],
    "separate_vae": ["Seperate VAE"],
    "vpred": ["VPred Model?"],
    "epsilon_scaling": ["Epsilon Scaling"],
    "cfg_zero_star": ["CFGZeroStar"],
    "hires": ["HiresFix"],
    "color_match": ["Color Match"],
    "ultimate_sd_upscale": ["Ultimate SD Upscale"],
    "apply_signature": ["Apply Signature"],
    "inpaint": ["Inpaint"],
    "outpaint": ["Outpaint"],
    "rmbg": ["Remove Background"],
    "remove_watermark": ["Remove Watermark"],
    "fbcnn": ["Compression Removal"],
    "any_detailer_sam31": ["Any Detailer (SAM 3.1)"],
    "post_morphology": ["ImageMorphology"],
    "post_quantize": ["ImageQuantize"],
    "post_sharpen": ["ImageSharpen"],
    "post_contrast": ["Contrast"],
    "fx_film_grain": ["Film Grain"],
    "fx_chromatic": ["Chromatic Aberration"],
    "fx_edge_blur": ["Edge-Preserving Blur"],
    "fx_glitch": ["Glitch"],
    "fx_pixelation": ["Pixelation"],
    "fx_gameboy": ["Gameboy"],
    "fx_vhs": ["VHS TV"],
    "fx_night_vision": ["Night Vision"],
    "fx_blueprint": ["Blueprint"],
}

# Detailer ships with face/mask/sam often useful
DEFAULT_ON = frozenset({"face_adetailer", "use_sam", "clip_skip", "mask_adetailer"})


def load_capabilities() -> dict[str, Any]:
    if CAPS_PATH.is_file():
        return common.load_json(CAPS_PATH)
    return {}


def load_groups() -> dict[str, Any]:
    if GROUPS_PATH.is_file():
        return common.load_json(GROUPS_PATH)
    return {}


def resolve_features(
    *,
    preset: str | None = None,
    flags: dict[str, bool | None] | None = None,
    features: list[str] | None = None,
    no_features: list[str] | None = None,
) -> tuple[set[str], set[str]]:
    on: set[str] = set(DEFAULT_ON)
    off: set[str] = set()
    caps = load_capabilities()
    if preset and preset in (caps.get("agent_presets") or {}):
        pe = caps["agent_presets"][preset]
        on = {f for f in (pe.get("features_on") or []) if f != "core"}
        off = set(pe.get("features_off") or [])
        for fid in FEATURE_GROUPS:
            if fid not in on:
                off.add(fid)

    def _set(fid: str, enabled: bool) -> None:
        if enabled:
            on.add(fid)
            off.discard(fid)
        else:
            off.add(fid)
            on.discard(fid)

    for fid, val in (flags or {}).items():
        if val is None:
            continue
        _set(fid, bool(val))
    for f in features or []:
        if f.strip():
            _set(f.strip(), True)
    for f in no_features or []:
        if f.strip():
            _set(f.strip(), False)
    return on, off


def generate_illustrious_detailer(
    *,
    image_path: str,
    output_path: str,
    positive: str | None = None,
    negative: str | None = None,
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    denoise: float | None = None,
    ckpt_name: str | None = None,
    lora_text: str | None = None,
    features_on: set[str] | None = None,
    features_off: set[str] | None = None,
    timeout_sec: float = 900,
    server_address: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    if not image_path:
        return fail_result(error="MISSING_IMAGE", message="Detailer requires --image")

    on = set(features_on or DEFAULT_ON)
    off = set(features_off or set())
    pos = (
        positive
        or "masterpiece, best quality, amazing quality, absurdres, detailed"
    )
    neg = negative if negative is not None else DEFAULT_NEG

    try:
        ui = common.load_json(UI_PATH)
        groups = (load_groups().get("groups") or {})
        ui2 = common.apply_group_modes(
            ui,
            groups,
            FEATURE_GROUPS,
            features_on=on,
            features_off=off,
            default_on=set(DEFAULT_ON),
        )
        # main load image always on (node 2)
        from lib.illustrious_standard_v37_runner import _set_mode

        _set_mode(ui2, [2], 0)
        api = common.build_api(
            ui2, server_address=server_address, aggressive_relink=False
        )
        common.collapse_reroutes(api)
        common.collapse_impact_switches(api)
        common.collapse_reroutes(api)
        common.ensure_clip_on_encoders(api)
        common.ensure_ksampler_io(api)
        lora = next(
            (
                nid
                for nid, n in api.items()
                if n.get("class_type") == "Lora Loader (LoraManager)"
            ),
            None,
        )
        ckpt = next(
            (
                nid
                for nid, n in api.items()
                if n.get("class_type") == "CheckpointLoaderSimple"
                and "sam" not in str((n.get("inputs") or {}).get("ckpt_name", "")).lower()
            ),
            None,
        )
        model_src = [lora, 0] if lora else ([ckpt, 0] if ckpt else None)
        if model_src:
            for n in api.values():
                if n.get("class_type") in ("DifferentialDiffusion", "KSampler"):
                    n.setdefault("inputs", {})["model"] = model_src
        # FaceDetailerPipe image from LoadImage
        load = next(
            (nid for nid, n in api.items() if n.get("class_type") == "LoadImage"),
            None,
        )
        if load:
            for n in api.values():
                if n.get("class_type") in ("FaceDetailerPipe", "MaskDetailerPipe"):
                    n.setdefault("inputs", {})["image"] = [load, 0]
        common.wire_saver_from_decode(api)
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    try:
        common.set_wildcard(api, "1", pos)
        common.set_wildcard(api, "76", neg)
        common.set_seed(api, "79", seed_i)
        common.set_ckpt(api, "90", ckpt_name or DEFAULT_CKPT)
        common.set_lora(api, "3", lora_text)
        img_name = common.stage(image_path, "det_v37")
        common.set_load_image(api, "2", img_name)
        # re-assert load image after staging for all LoadImage nodes used
        for nid, n in api.items():
            if n.get("class_type") == "LoadImage" and "signature" not in (
                n.get("inputs") or {}
            ).get("image", ""):
                # only main still if still default placeholder
                cur = (n.get("inputs") or {}).get("image")
                if cur in (None, "load_image.png", "load_signature.png") or nid == "2":
                    if nid == "2" or cur == "load_image.png":
                        n.setdefault("inputs", {})["image"] = img_name
        # sampler free widgets on inpaint/outpaint samplers if live
        for nid, n in api.items():
            if n.get("class_type") != "KSampler":
                continue
            ins = n.setdefault("inputs", {})
            if denoise is not None and not isinstance(ins.get("denoise"), list):
                ins["denoise"] = float(denoise)
            if steps is not None and not isinstance(ins.get("steps"), list):
                ins["steps"] = int(steps)
            if cfg is not None and not isinstance(ins.get("cfg"), list):
                ins["cfg"] = float(cfg)
            if sampler is not None and not isinstance(ins.get("sampler_name"), list):
                ins["sampler_name"] = sampler
            if scheduler is not None and not isinstance(ins.get("scheduler"), list):
                ins["scheduler"] = scheduler
        common.set_saver_meta(
            api,
            "32",
            filename="illustrious_det_v37",
            positive=pos,
            negative=neg,
            ckpt_name=ckpt_name or DEFAULT_CKPT,
            sampler=sampler,
            scheduler=scheduler,
        )
    except Exception as e:
        return fail_result(error="PORT_FAILED", message=str(e))

    return common.run_api(
        api,
        output_path=output_path,
        seed=seed_i,
        timeout_sec=timeout_sec,
        server_address=server_address,
        meta_extra={
            "tool": "generate_illustrious_detailer",
            "features_on": sorted(on),
            "pack": "Detailer_V37",
            "input_image": image_path,
        },
    )
