#!/usr/bin/env python3
"""
Run the user-saved ComfyUI workflow:
  F:/ComfyUI_windows_portable/ComfyUI/user/default/workflows/krea2_identity_edit.json

Single-image identity edit via Krea2EditModelPatch + Krea2EditGroundedEncode.
Default: turbo UNET, identity-edit LoRA v1.2, ref_boost=4, 10 steps, cfg=1.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import copy
import json
import os
import random
import shutil
import sys
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    get_comfy_input_dir,
    ok_result,
    fail_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)

DEFAULT_WF = (
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\krea2_identity_edit.json"
)
DEFAULT_UNET = r"Krea2Turbo\krea2_turbo_fp8_scaled.safetensors"
DEFAULT_LORA = r"Krea2\krea2_identity_edit_v1_2.safetensors"
DEFAULT_CLIP = "qwen3vl_4b_fp8_scaled.safetensors"
DEFAULT_VAE = "qwen_image_vae.safetensors"

# UI mode: 0=always, 2=mute, 4=never/bypass
BYPASS_MODE = 4


def _widget_map(class_type: str, widgets: list[Any]) -> dict[str, Any]:
    """Map widgets_values to API input keys for this workflow's node types."""
    w = list(widgets or [])
    out: dict[str, Any] = {}
    if class_type == "UNETLoader" and len(w) >= 2:
        out["unet_name"], out["weight_dtype"] = w[0], w[1]
    elif class_type == "CLIPLoader" and len(w) >= 2:
        out["clip_name"], out["type"] = w[0], w[1]
        if len(w) >= 3:
            out["device"] = w[2]
    elif class_type == "VAELoader" and w:
        out["vae_name"] = w[0]
    elif class_type == "LoraLoaderModelOnly" and len(w) >= 2:
        out["lora_name"], out["strength_model"] = w[0], w[1]
    elif class_type == "LoadImage" and w:
        out["image"] = w[0]
    elif class_type == "KSampler" and len(w) >= 7:
        # seed, control_after_generate, steps, cfg, sampler, scheduler, denoise
        out["seed"] = w[0]
        out["steps"] = w[2]
        out["cfg"] = w[3]
        out["sampler_name"] = w[4]
        out["scheduler"] = w[5]
        out["denoise"] = w[6]
    elif class_type == "EmptySD3LatentImage" and len(w) >= 3:
        out["width"], out["height"], out["batch_size"] = w[0], w[1], w[2]
    elif class_type == "ResolutionSelector" and len(w) >= 3:
        out["aspect_ratio"], out["megapixels"], out["multiple"] = w[0], w[1], w[2]
    elif class_type == "SaveImage" and w:
        out["filename_prefix"] = w[0]
    elif class_type == "Krea2EditGroundedEncode" and w:
        out["prompt"] = w[0] if len(w) > 0 else ""
        if len(w) > 1:
            out["grounding_px"] = w[1]
        if len(w) > 2:
            out["system_prompt"] = w[2]
    elif class_type == "Krea2EditModelPatch" and w:
        # widgets: ref_boost, ref_boost_a, fit_mode
        if len(w) > 0:
            out["ref_boost"] = w[0]
        if len(w) > 1:
            out["ref_boost_a"] = w[1]
        if len(w) > 2:
            out["fit_mode"] = w[2]
    return out


def convert_identity_edit_ui(ui_data: dict, *, drop_bypassed: bool = True) -> dict:
    """UI workflow → API prompt; skip Notes and optionally bypassed nodes."""
    links = {l[0]: l for l in ui_data.get("links", [])}
    bypassed: set[str] = set()
    if drop_bypassed:
        for node in ui_data.get("nodes", []):
            if int(node.get("mode", 0) or 0) == BYPASS_MODE:
                bypassed.add(str(node["id"]))

    api: dict[str, Any] = {}
    for node in ui_data.get("nodes", []):
        nid = str(node["id"])
        ctype = node["type"]
        if ctype == "Note":
            continue
        if nid in bypassed:
            continue

        inputs: dict[str, Any] = {}
        # Widgets first, then links — linked sockets must win.
        # (EmptySD3LatentImage keeps widget 1024x1024; ResolutionSelector wires
        # width/height via links. Overwriting links with widgets forced square.)
        for k, v in _widget_map(ctype, node.get("widgets_values") or []).items():
            inputs[k] = v
        for inp in node.get("inputs", []) or []:
            name = inp["name"]
            link_id = inp.get("link")
            if link_id is None or link_id not in links:
                continue
            link = links[link_id]
            origin = str(link[1])
            if origin in bypassed:
                continue  # optional second-image refs drop cleanly
            inputs[name] = [origin, link[2]]

        api[nid] = {"class_type": ctype, "inputs": inputs}
    return api


def stage_input_image(src: str, name: str = "krea2_id_edit_input.png") -> str:
    """Copy source into Comfy input dir; return basename for LoadImage."""
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    inp = get_comfy_input_dir()
    os.makedirs(inp, exist_ok=True)
    dest = os.path.join(inp, name)
    shutil.copy2(src, dest)
    return name


def run_identity_edit(
    *,
    input_image: str,
    prompt: str,
    output_path: str,
    workflow_path: str = DEFAULT_WF,
    seed: int | None = None,
    steps: int = 10,
    cfg: float = 1.0,
    denoise: float = 1.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    ref_boost: float = 4.0,
    ref_boost_a: float = 1.0,
    unet_name: str = DEFAULT_UNET,
    lora_name: str = DEFAULT_LORA,
    lora_strength: float = 1.0,
    aspect_ratio: str = "1:1 (Square)",
    megapixels: float = 1.0,
    filename_prefix: str = "krea2_identity_edit",
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 600,
    meta_out: str | None = None,
    ref_image: str | None = None,
    fit_mode: str = "fit",
) -> dict:
    """Krea2 identity edit.

    ``input_image`` is the primary edit subject (structure / scene).
    Optional ``ref_image`` enables the dual-ref branch (LoadImage #90 + VAEEncode #92)
    for a second identity/person reference — e.g. full-body OpenPose base + master_front face.
    """
    if not os.path.isfile(workflow_path):
        return fail_result(error="WORKFLOW_MISSING", message=workflow_path)
    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)
    if ref_image and not os.path.isfile(ref_image):
        return fail_result(error="REF_MISSING", message=ref_image)

    with open(workflow_path, "r", encoding="utf-8") as f:
        ui = json.load(f)
    api = convert_identity_edit_ui(ui)

    seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    img_name = stage_input_image(input_image, "krea2_id_edit_input.png")

    # Node IDs from saved workflow
    api["72"]["inputs"]["image"] = img_name
    api["84"]["inputs"]["prompt"] = prompt
    api["85"]["inputs"]["prompt"] = ""
    api["53"]["inputs"]["seed"] = seed
    api["53"]["inputs"]["steps"] = int(steps)
    api["53"]["inputs"]["cfg"] = float(cfg)
    api["53"]["inputs"]["sampler_name"] = sampler
    api["53"]["inputs"]["scheduler"] = scheduler
    api["53"]["inputs"]["denoise"] = float(denoise)
    api["79"]["inputs"]["ref_boost"] = float(ref_boost)
    api["79"]["inputs"]["ref_boost_a"] = float(ref_boost_a)
    api["79"]["inputs"]["fit_mode"] = str(fit_mode or "fit")
    api["55"]["inputs"]["unet_name"] = unet_name
    api["55"]["inputs"]["weight_dtype"] = "default"
    api["71"]["inputs"]["lora_name"] = lora_name
    api["71"]["inputs"]["strength_model"] = float(lora_strength)
    api["56"]["inputs"]["clip_name"] = DEFAULT_CLIP
    api["56"]["inputs"]["type"] = "krea2"
    api["57"]["inputs"]["vae_name"] = DEFAULT_VAE
    api["83"]["inputs"]["aspect_ratio"] = aspect_ratio
    api["83"]["inputs"]["megapixels"] = float(megapixels)
    api["83"]["inputs"]["multiple"] = 8
    api["29"]["inputs"]["filename_prefix"] = filename_prefix

    # Dual-ref: enable bypassed LoadImage #90 + VAEEncode #92 (identity / face plate)
    dual = False
    if ref_image:
        dual = True
        ref_name = stage_input_image(ref_image, "krea2_id_edit_ref.png")
        api["90"] = {
            "class_type": "LoadImage",
            "inputs": {"image": ref_name},
        }
        api["92"] = {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["90", 0],
                "vae": ["57", 0],
            },
        }
        # Grounded encode secondary image + model patch secondary latent/image
        api["84"]["inputs"]["image_b"] = ["90", 0]
        api["85"]["inputs"]["image_b"] = ["90", 0]
        api["79"]["inputs"]["source_image_b"] = ["90", 0]
        api["79"]["inputs"]["source_latent_b"] = ["92", 0]
        # Second ref strength: higher = pull identity toward ref_image
        if float(ref_boost_a) <= 1.0:
            api["79"]["inputs"]["ref_boost_a"] = max(float(ref_boost_a), 3.0)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    print(
        f"krea2_identity_edit seed={seed} steps={steps} cfg={cfg} "
        f"ref_boost={ref_boost} ref_boost_a={api['79']['inputs'].get('ref_boost_a')} "
        f"dual_ref={dual} aspect={aspect_ratio} mp={megapixels} unet={unet_name}"
    )
    print(f"  input={input_image}")
    if dual:
        print(f"  ref={ref_image}")
    print(f"  prompt={prompt[:120]}...")

    try:
        prompt_id = queue_prompt(server_address, api)
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
        download_image(
            server_address,
            image_filename,
            image_subfolder,
            image_type,
            output_path,
        )
        out = output_path
    except Exception as e:
        return fail_result(error="COMFY_FAIL", message=str(e))

    if not out or not os.path.isfile(out):
        return fail_result(error="NO_IMAGE", message=str(out))

    meta = {
        "engine": "krea2_identity_edit",
        "workflow": workflow_path,
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
        "ref_boost": ref_boost,
        "ref_boost_a": api["79"]["inputs"].get("ref_boost_a"),
        "dual_ref": dual,
        "aspect_ratio": aspect_ratio,
        "megapixels": megapixels,
        "unet": unet_name,
        "lora": lora_name,
        "prompt": prompt,
        "input_image": os.path.abspath(input_image),
        "ref_image": os.path.abspath(ref_image) if dual else None,
        "output_path": os.path.abspath(out),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
    }
    if meta_out:
        write_meta(meta_out, meta)
    else:
        write_meta(out + ".meta.json", meta)

    print(f"OK → {out}")
    return ok_result(output_path=out, seed=seed, prompt_id=prompt_id, meta=meta)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Krea2 Identity Edit (user workflow)")
    p.add_argument("--input", "-i", required=True, help="Primary source image to edit")
    p.add_argument(
        "--ref",
        default=None,
        help="Optional second image (identity/face ref) — enables dual-ref branch",
    )
    p.add_argument("--prompt", "-p", required=True, help="Plain-English edit instruction")
    p.add_argument("--output", "-o", required=True, help="Output PNG path")
    p.add_argument("--workflow", default=DEFAULT_WF)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--denoise", type=float, default=1.0)
    p.add_argument("--ref-boost", type=float, default=4.0)
    p.add_argument(
        "--ref-boost-a",
        type=float,
        default=1.0,
        help="Second-ref boost (dual mode); auto min 3.0 when --ref set and value<=1",
    )
    p.add_argument("--unet-name", default=DEFAULT_UNET)
    p.add_argument("--lora-name", default=DEFAULT_LORA)
    p.add_argument("--lora-strength", type=float, default=1.0)
    p.add_argument(
        "--aspect-ratio",
        default="1:1 (Square)",
        help='e.g. "2:3 (Portrait Photo)", "9:16 (Portrait)" if listed in ResolutionSelector',
    )
    p.add_argument("--megapixels", type=float, default=1.0)
    p.add_argument("--filename-prefix", default="krea2_identity_edit")
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args(argv)

    r = run_identity_edit(
        input_image=args.input,
        prompt=args.prompt,
        output_path=args.output,
        workflow_path=args.workflow,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        denoise=args.denoise,
        ref_boost=args.ref_boost,
        ref_boost_a=args.ref_boost_a,
        unet_name=args.unet_name,
        lora_name=args.lora_name,
        lora_strength=args.lora_strength,
        aspect_ratio=args.aspect_ratio,
        megapixels=args.megapixels,
        filename_prefix=args.filename_prefix,
        timeout_sec=args.timeout,
        ref_image=args.ref,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
