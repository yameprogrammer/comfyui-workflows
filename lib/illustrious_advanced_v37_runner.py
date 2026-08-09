"""Advanced_V37 — real Legendaer UI (TIPO / IPA / OpenPose / Regional / …)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from lib.comfy_client import DEFAULT_SERVER, fail_result
from lib import illustrious_pack_common as common

WORKSPACE = Path(__file__).resolve().parents[1]
HUMAN = WORKSPACE / "workflows" / "human" / "illustrious_advanced_v37"
UI_PATH = HUMAN / "Advanced_V37.json"
GROUPS_PATH = HUMAN / "GROUPS.json"
CAPS_PATH = HUMAN / "CAPABILITIES.json"

DEFAULT_CKPT = common.DEFAULT_CKPT
DEFAULT_NEG = common.DEFAULT_NEG

# Advanced-unique + shared pale_blue/cyan groups
FEATURE_GROUPS: dict[str, list[str]] = {
    # shared with Standard (titles may differ for hires/ultimate)
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
    "clip_negpip": ["CLIP NegPip"],
    "color_match": ["Color Match"],
    "apply_signature": ["Apply Signature"],
    "hires_pre": ["Hires PreDetailer", "HiresFix Pre Detailer"],
    "hires_post": ["Hires PostDetailer", "HiresFix Post Detailer"],
    "ultimate_pre": ["Ultimate SD Upscale Pre Detailer"],
    "ultimate_post": ["Ultimate SD Upscale Post Detailer"],
    "post_morphology": ["ImageMorphology"],
    "post_quantize": ["ImageQuantize"],
    "post_sharpen": ["ImageSharpen"],
    "post_contrast": ["Contrast"],
    # Advanced-only
    "tipo": ["Z-TIPO"],
    "ipadapter": ["IP-Adapter Advanced"],
    "ipadapter_style": ["IP-Adapter Style & Composition"],
    "openpose": ["OpenPose"],
    "any_controlnet": ["Any ControlNet"],
    "regional": ["Regional Prompting"],
    "clip_vision": ["Clip Vision"],
    "second_sampler": ["2ndSampler"],
    "mask_detailer": ["Mask Detailer"],
    "any_detailer_sam31": ["Any Detailer (SAM 3.1)"],
    "rmbg": ["Remove Background"],
    "fbcnn": ["Compression Removal"],
    # cyan FX extras
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

# clip_negpip needs extra custom node (CLIPNegPip) — OFF unless user asks
DEFAULT_ON = frozenset({"face_adetailer", "use_sam", "clip_skip"})

# LoadImage node ids for advanced refs
LOAD_NODES = {
    "i2i": "0",
    "openpose": "118",
    "controlnet": "120",
    "ipa_adv": "170",
    "style": "113",
    "composition": "114",
    "clipvision": "116",
    "signature": "130",
    "regional_red": "1",
    "regional_green": "2",
    "regional_blue": "3",
}


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
    flags: dict[str, bool] | None = None,
    features: list[str] | None = None,
    no_features: list[str] | None = None,
) -> tuple[set[str], set[str]]:
    on: set[str] = set(DEFAULT_ON)
    off: set[str] = set()
    caps = load_capabilities()
    if preset and preset in (caps.get("agent_presets") or {}):
        pe = caps["agent_presets"][preset]
        on = {f for f in (pe.get("features_on") or []) if f != "core_t2i"}
        off = {f for f in (pe.get("features_off") or []) if f != "core_t2i"}
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


def generate_illustrious_advanced(
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
    ckpt_name: str | None = None,
    lora_text: str | None = None,
    image_path: str | None = None,
    openpose_image: str | None = None,
    controlnet_image: str | None = None,
    ipa_image: str | None = None,
    style_image: str | None = None,
    composition_image: str | None = None,
    features_on: set[str] | None = None,
    features_off: set[str] | None = None,
    timeout_sec: float = 900,
    server_address: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    on = set(features_on or DEFAULT_ON)
    off = set(features_off or set())

    # auto-enable groups when refs provided
    if image_path:
        on.add("load_image_i2i")
        off.discard("load_image_i2i")
    if openpose_image:
        on.add("openpose")
        off.discard("openpose")
    if controlnet_image:
        on.add("any_controlnet")
        off.discard("any_controlnet")
    if ipa_image:
        on.add("ipadapter")
        off.discard("ipadapter")
    if style_image or composition_image:
        on.add("ipadapter_style")
        off.discard("ipadapter_style")

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
        # I2I: unmute load image group is enough if switch wiring follows modes
        # Light expand + structural fixes (aggressive multi-hop mis-types Advanced switches)
        api = common.build_api(
            ui2, server_address=server_address, aggressive_relink=False
        )
        common.collapse_reroutes(api)
        common.collapse_impact_switches(api)
        common.collapse_reroutes(api)
        common.ensure_clip_on_encoders(api)
        common.ensure_ksampler_io(api)
        # DifferentialDiffusion (always-on) must get a real MODEL
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
            ),
            None,
        )
        model_src = [lora, 0] if lora else ([ckpt, 0] if ckpt else None)
        for n in api.values():
            if n.get("class_type") == "DifferentialDiffusion" and model_src:
                n.setdefault("inputs", {})["model"] = model_src
        # KSampler should also use same model
        if model_src:
            for n in api.values():
                if n.get("class_type") == "KSampler":
                    n.setdefault("inputs", {})["model"] = model_src
        common.wire_saver_from_decode(api)
        # face detailer needs image from VAEDecode when present
        dec = next(
            (nid for nid, n in api.items() if n.get("class_type") == "VAEDecode"),
            None,
        )
        for n in api.values():
            if n.get("class_type") == "FaceDetailerPipe" and dec:
                ins = n.setdefault("inputs", {})
                if not (
                    isinstance(ins.get("image"), list)
                    and str(ins.get("image", [None])[0]) in api
                ):
                    ins["image"] = [dec, 0]
        common.wire_saver_from_decode(api)
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    neg = negative if negative is not None else DEFAULT_NEG

    try:
        common.set_wildcard(api, "57", positive)
        common.set_wildcard(api, "59", neg)
        common.set_seed(api, "108", seed_i)
        common.set_input_params(
            api,
            "60",
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            denoise=denoise,
        )
        common.set_empty_latent(api, "97", width=width, height=height)
        common.set_ckpt(api, "103", ckpt_name or DEFAULT_CKPT)
        common.set_lora(api, "58", lora_text)
        common.set_saver_meta(
            api,
            "124",
            filename="illustrious_adv_v37",
            positive=positive,
            negative=neg,
            ckpt_name=ckpt_name or DEFAULT_CKPT,
            sampler=sampler,
            scheduler=scheduler,
        )

        def _img(path: str | None, key: str) -> None:
            if not path:
                return
            name = common.stage(path, f"adv_{key}")
            common.set_load_image(api, LOAD_NODES[key], name)

        _img(image_path, "i2i")
        _img(openpose_image, "openpose")
        _img(controlnet_image, "controlnet")
        _img(ipa_image, "ipa_adv")
        _img(style_image, "style")
        _img(composition_image, "composition")

        # TIPO prompt field when enabled
        if "tipo" in on and "8" in api:
            api["8"].setdefault("inputs", {})
            # TIPO widgets vary — set common text keys if present
            for k in ("prompt", "text", "tags"):
                if k in (api["8"].get("inputs") or {}):
                    api["8"]["inputs"][k] = positive
                    break
            # widgets may only be in freeform — leave expand defaults

    except Exception as e:
        return fail_result(error="PORT_FAILED", message=str(e))

    return common.run_api(
        api,
        output_path=output_path,
        seed=seed_i,
        timeout_sec=timeout_sec,
        server_address=server_address,
        meta_extra={
            "tool": "generate_illustrious_advanced",
            "features_on": sorted(on),
            "features_off": sorted(off),
            "pack": "Advanced_V37",
        },
    )
