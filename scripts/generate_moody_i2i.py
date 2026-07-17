#!/usr/bin/env python3
"""
Image-to-Image via validated Comfy **API workflow presets** (Lonecat AIO).

Default path: load `lonecat_i2i_identity` API JSON → port patch only → POST /prompt.
No mini-graph assembly, no convert_ui_to_api, no runtime node inject.

Legacy mini I2I-moody is opt-in only: --legacy-mini or AGENT_I2I_BACKEND=legacy_mini.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401  # repo root + scripts on path
import argparse
import os
import random
import shutil
import sys

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    MODEL_MAPPING,
    convert_ui_to_api,
    download_image,
    extract_first_image,
    fail_result,
    load_workflow,
    ok_result,
    queue_prompt,
    resolve_meta_out,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import FAMILY_MOODY, ensure_engine
from lib.prompt_assembly import assemble_prompt, load_text
from lib.workflow_api_runner import run_workflow_api, select_lonecat_preset
from lib.workflow_paths import default_workflow, resolve_workflow

DEFAULT_I2I_PRESET = "lonecat_i2i_identity"
DEFAULT_DENOISE = 0.55


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_I2I_BACKEND")
        or "workflow_api"
    ).strip().lower()
    if raw in ("legacy", "legacy_mini", "mini", "i2i_moody"):
        return "legacy_mini"
    return "workflow_api"


def _resolve_preset(
    preset: str | None,
    *,
    family: str | None,
    model_type: str,
) -> str:
    if preset:
        return preset
    unet = MODEL_MAPPING.get((model_type or "real").lower())
    return select_lonecat_preset(mode="i2i", unet_name=unet, family=family)


def generate_i2i_image(
    input_image_path,
    prompt_text,
    denoise_val=DEFAULT_DENOISE,
    cfg_val=1.0,
    model_type="real",
    output_filename=None,
    seed=None,
    negative_text="",
    core_prefix="",
    core_suffix="",
    meta_out=None,
    server_address=DEFAULT_SERVER,
    timeout_sec=600,
    workflow=None,
    *,
    preset: str | None = None,
    family: str | None = None,
    backend: str | None = None,
    width: int | None = None,
    height: int | None = None,
    unet_name: str | None = None,
):
    """
    I2I generation.

    Default: Lonecat ``lonecat_i2i_identity`` (or family i2i default) via workflow_api_runner.
    ``workflow`` + ``backend=legacy_mini`` keeps old I2I-moody mini path for emergency only.
    """
    eng = ensure_engine(
        FAMILY_MOODY, server_address, caller="generate_moody_i2i"
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    if not os.path.exists(input_image_path):
        print(f"Error: Input image not found at {input_image_path}")
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    be = _resolve_backend(backend)
    # Explicit mini workflow path forces legacy only when backend allows
    if workflow and be != "legacy_mini" and not preset:
        print(
            "[WARN] --workflow is for legacy mini only; "
            "default uses Lonecat API preset. Pass --legacy-mini to use mini graph."
        )

    if be == "legacy_mini":
        return _generate_i2i_legacy_mini(
            input_image_path=input_image_path,
            prompt_text=prompt_text,
            denoise_val=denoise_val,
            cfg_val=cfg_val,
            model_type=model_type,
            output_filename=output_filename,
            seed=seed,
            negative_text=negative_text,
            core_prefix=core_prefix,
            core_suffix=core_suffix,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            workflow=workflow,
        )

    return _generate_i2i_workflow_api(
        input_image_path=input_image_path,
        prompt_text=prompt_text,
        denoise_val=denoise_val,
        cfg_val=cfg_val,
        model_type=model_type,
        output_filename=output_filename,
        seed=seed,
        negative_text=negative_text,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        meta_out=meta_out,
        server_address=server_address,
        timeout_sec=timeout_sec,
        preset=preset,
        family=family,
        width=width,
        height=height,
        unet_name=unet_name,
    )


def _generate_i2i_workflow_api(
    *,
    input_image_path: str,
    prompt_text: str,
    denoise_val: float,
    cfg_val: float,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    core_prefix: str,
    core_suffix: str,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    preset: str | None,
    family: str | None,
    width: int | None,
    height: int | None,
    unet_name: str | None,
) -> dict:
    final_prompt = assemble_prompt(
        core=core_prefix, instruction=prompt_text, suffix=core_suffix
    )
    selected_model = unet_name or MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )
    preset_name = _resolve_preset(preset, family=family, model_type=model_type)

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_i2i_{model_type}.png"
        )

    ports: dict = {
        "positive": final_prompt,
        "input_image": os.path.abspath(input_image_path),
        "denoise": float(denoise_val),
        "unet_name": selected_model,
    }
    if negative_text:
        ports["negative"] = negative_text
    if width is not None:
        ports["width"] = int(width)
    if height is not None:
        ports["height"] = int(height)

    print(
        f"I2I via workflow_api preset={preset_name} denoise={denoise_val} "
        f"model={selected_model}"
    )
    if cfg_val is not None:
        print(
            f"[note] cfg={cfg_val} stored in meta only "
            f"(Lonecat I2I preset has no cfg port; graph uses baked sampler)"
        )

    r = run_workflow_api(
        preset_name,
        ports=ports,
        output_path=output_filename,
        meta_out=None,  # we write unified meta below
        server_address=server_address,
        timeout_sec=timeout_sec,
        seed=seed,
    )
    if not r.get("ok"):
        return r

    applied_seed = r.get("seed")
    prompt_id = r.get("prompt_id")
    out_abs = r.get("output_path") or os.path.abspath(output_filename)
    base_meta = r.get("meta") or {}

    meta = {
        "character_id": None,
        "sheet": None,
        "view": None,
        "variant": None,
        "seed": applied_seed,
        "candidate": None,
        "model": model_type,
        "unet": selected_model,
        "workflow": preset_name,
        "workflow_api": base_meta.get("workflow_api"),
        "mode": "i2i",
        "engine": "workflow_api",
        "backend": "workflow_api",
        "prompt": final_prompt,
        "prompt_instruction": prompt_text,
        "core_prefix": core_prefix or "",
        "core_suffix": core_suffix or "",
        "negative": negative_text or "",
        "denoise": float(denoise_val),
        "cfg": cfg_val,
        "cfg_note": "not applied as port on lonecat_i2i_identity (baked sampler)",
        "source_image": os.path.abspath(input_image_path),
        "created_at": utc_now_iso(),
        "comfy_prompt_id": prompt_id,
        "output_path": out_abs,
        "ports_applied": base_meta.get("ports_applied"),
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved to: {meta_path}")

    print(f"Edited image successfully saved to: {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=applied_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        workflow_api=base_meta.get("workflow_api"),
        preset=preset_name,
    )


def _generate_i2i_legacy_mini(
    *,
    input_image_path: str,
    prompt_text: str,
    denoise_val: float,
    cfg_val: float,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    core_prefix: str,
    core_suffix: str,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    workflow,
) -> dict:
    """Emergency-only: old I2I-moody mini + convert_ui_to_api."""
    print(
        "[WARN] legacy_mini I2I-moody path — not production SSOT. "
        "Prefer lonecat_i2i_identity."
    )
    workflow_path = (
        resolve_workflow(workflow) if workflow else default_workflow("i2i_moody")
    )
    selected_model = MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )

    temp_input_name = "temp_i2i_input.png"
    target_input_path = os.path.join(COMFYUI_INPUT_DIR, temp_input_name)
    try:
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        shutil.copy2(input_image_path, target_input_path)
        print(f"Copied source image to ComfyUI input directory: {target_input_path}")
    except Exception as e:
        print(f"Error copying input image to ComfyUI input folder: {e}")
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_i2i_{model_type}.png"
        )

    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    final_prompt = assemble_prompt(
        core=core_prefix, instruction=prompt_text, suffix=core_suffix
    )

    print(f"Loading I2I workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    clip_node_id = None
    lora_prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    load_image_node_id = None

    for node_id, node in api_prompt.items():
        ctype = node["class_type"]
        if ctype == "CLIPTextEncode":
            clip_node_id = node_id
        elif ctype == "Prompt (LoraManager)":
            lora_prompt_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype == "UNETLoader":
            unet_node_id = node_id
        elif ctype == "LoadImage":
            load_image_node_id = node_id

    prompt_node_id = clip_node_id or lora_prompt_node_id

    if prompt_node_id:
        api_prompt[prompt_node_id]["inputs"]["text"] = final_prompt
        print(f"Set Prompt: {final_prompt}")
    else:
        print("[WARN] Prompt/CLIPTextEncode node not found")

    if negative_text:
        print(
            "[WARN] Negative text provided; I2I-moody may lack negative node — "
            "saved to meta only"
        )

    if unet_node_id:
        api_prompt[unet_node_id]["inputs"]["unet_name"] = selected_model
        api_prompt[unet_node_id]["inputs"]["weight_dtype"] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")

    new_seed = seed if seed is not None else random.randint(1, 1125899906842624)
    applied_steps = None
    applied_sampler = "euler"
    applied_scheduler = "normal"

    if sampler_node_id:
        s_in = api_prompt[sampler_node_id]["inputs"]
        s_in["seed"] = new_seed
        s_in["denoise"] = denoise_val
        s_in["cfg"] = cfg_val
        s_in["sampler_name"] = "euler"
        s_in["scheduler"] = "normal"
        applied_steps = s_in.get("steps")
        print(
            f"Set KSampler Seed: {new_seed}, Denoise: {denoise_val}, CFG: {cfg_val}, "
            f"Sampler: euler, Scheduler: normal"
        )

    if load_image_node_id:
        api_prompt[load_image_node_id]["inputs"]["image"] = temp_input_name
        print(f"Set LoadImage source file: {temp_input_name}")

    print("Sending I2I prompt request to ComfyUI...")
    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except ConnectionError as e:
        print(f"[ERROR] code=40 message={e}")
        return fail_result(error="COMFY_UNREACHABLE", message=str(e), seed=new_seed)
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    print("Executing Image-to-Image editing (polling)...")
    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
    except TimeoutError as e:
        print(f"[ERROR] code=41 message={e}")
        return fail_result(
            error="COMFY_TIMEOUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )
    except Exception as e:
        print(f"Error waiting for history: {e}")
        return fail_result(
            error="HISTORY_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
    except FileNotFoundError as e:
        print(f"[ERROR] code=42 message={e}")
        return fail_result(
            error="COMFY_NO_OUTPUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    print(f"Downloading image: {image_filename}")
    try:
        download_image(
            server_address,
            image_filename,
            image_subfolder,
            image_type,
            output_filename,
        )
        print(f"Edited image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading edited image: {e}")
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "character_id": None,
        "sheet": None,
        "view": None,
        "variant": None,
        "seed": new_seed,
        "candidate": None,
        "model": model_type,
        "workflow": "I2I-moody",
        "mode": "i2i",
        "engine": "legacy_mini",
        "backend": "legacy_mini",
        "prompt": final_prompt,
        "prompt_instruction": prompt_text,
        "core_prefix": core_prefix or "",
        "core_suffix": core_suffix or "",
        "negative": negative_text or "",
        "denoise": denoise_val,
        "cfg": cfg_val,
        "steps": applied_steps,
        "sampler": applied_sampler,
        "scheduler": applied_scheduler,
        "source_image": os.path.abspath(input_image_path),
        "created_at": utc_now_iso(),
        "comfy_prompt_id": prompt_id,
        "output_path": os.path.abspath(output_filename),
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved to: {meta_path}")

    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=new_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "I2I via Lonecat AIO API preset (default lonecat_i2i_identity). "
            "No mini-graph / IPAdapter inject."
        )
    )
    parser.add_argument(
        "--input", "-i", type=str, required=True, help="Path to the input source image"
    )
    parser.add_argument(
        "--prompt", "-p", type=str, default=None, help="Text prompt for image editing"
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default=None,
        help="Prompt file (overrides --prompt if set alone)",
    )
    parser.add_argument("--negative", type=str, default="", help="Negative prompt")
    parser.add_argument("--negative-file", type=str, default=None, help="Negative prompt file")
    parser.add_argument(
        "--core-prefix-file", type=str, default=None, help="Locked appearance prefix file"
    )
    parser.add_argument(
        "--core-suffix-file", type=str, default=None, help="Optional suffix file"
    )
    parser.add_argument(
        "--denoise",
        "-d",
        type=float,
        default=DEFAULT_DENOISE,
        help=f"Denoise (default {DEFAULT_DENOISE}; identity ~0.42-0.58)",
    )
    parser.add_argument(
        "--cfg",
        "-c",
        type=float,
        default=1.0,
        help="CFG (meta only on Lonecat preset; baked in graph)",
    )
    parser.add_argument(
        "--model", "-m", type=str, choices=["real", "pro", "wild"], default="real"
    )
    parser.add_argument("--output", "-o", type=str, default=None, help="Output path")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed")
    parser.add_argument("--meta-out", type=str, default=None, help="Meta JSON path")
    parser.add_argument("--timeout", type=int, default=600, help="Comfy wait timeout seconds")
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help=f"API preset name (default: {DEFAULT_I2I_PRESET})",
    )
    parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="zimage|lonecat|krea2 — picks family i2i default if --preset omitted",
    )
    parser.add_argument("--width", type=int, default=None, help="Optional port width")
    parser.add_argument("--height", type=int, default=None, help="Optional port height")
    parser.add_argument(
        "--unet-name",
        type=str,
        default=None,
        help="Override diffusion unet filename (port unet_name)",
    )
    parser.add_argument(
        "--legacy-mini",
        action="store_true",
        help="Use old I2I-moody mini graph (emergency only)",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Legacy mini workflow path/alias (requires --legacy-mini)",
    )

    args = parser.parse_args()

    if args.prompt_file:
        prompt_text = load_text(args.prompt_file)
    elif args.prompt:
        prompt_text = args.prompt
    else:
        parser.error("Either --prompt or --prompt-file is required")

    negative_text = (
        load_text(args.negative_file) if args.negative_file else (args.negative or "")
    )
    core_prefix = load_text(args.core_prefix_file) if args.core_prefix_file else ""
    core_suffix = load_text(args.core_suffix_file) if args.core_suffix_file else ""

    result = generate_i2i_image(
        input_image_path=args.input,
        prompt_text=prompt_text,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        model_type=args.model,
        output_filename=args.output,
        seed=args.seed,
        negative_text=negative_text,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        workflow=args.workflow,
        preset=args.preset,
        family=args.family,
        backend="legacy_mini" if args.legacy_mini else "workflow_api",
        width=args.width,
        height=args.height,
        unet_name=args.unet_name,
    )
    sys.exit(0 if result.get("ok") else 1)
