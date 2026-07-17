#!/usr/bin/env python3
"""
T2I via validated Comfy **API workflow presets** (Lonecat AIO).

Default: ``lonecat_t2i_turbo`` → port patch only → POST /prompt.
No mini-graph assembly, no convert_ui_to_api, no runtime node inject.

Legacy mini T2I-moody: ``--legacy-mini`` or ``AGENT_T2I_BACKEND=legacy_mini``.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401  # repo root + scripts on path
import argparse
import os
import random
import sys

from lib.comfy_client import (
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
from lib.prompt_assembly import load_text
from lib.workflow_api_runner import run_workflow_api, select_lonecat_preset
from lib.workflow_paths import default_workflow, resolve_workflow

DEFAULT_T2I_PRESET = "lonecat_t2i_turbo"


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_T2I_BACKEND")
        or "workflow_api"
    ).strip().lower()
    if raw in ("legacy", "legacy_mini", "mini", "t2i_moody"):
        return "legacy_mini"
    return "workflow_api"


def _resolve_preset(
    preset: str | None,
    *,
    family: str | None,
    model_type: str,
    unet_name: str | None,
) -> str:
    if preset:
        return preset
    unet = unet_name or MODEL_MAPPING.get((model_type or "real").lower())
    return select_lonecat_preset(mode="t2i", unet_name=unet, family=family)


def generate_image(
    prompt_text,
    model_type="real",
    output_filename=None,
    seed=None,
    negative_text="",
    steps=None,
    cfg=None,
    width=None,
    height=None,
    meta_out=None,
    server_address=DEFAULT_SERVER,
    timeout_sec=600,
    workflow=None,
    *,
    preset: str | None = None,
    family: str | None = None,
    backend: str | None = None,
    unet_name: str | None = None,
):
    eng = ensure_engine(FAMILY_MOODY, server_address, caller="generate_moody")
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    be = _resolve_backend(backend)
    if workflow and be != "legacy_mini" and not preset:
        print(
            "[WARN] --workflow is for legacy mini only; "
            "default uses Lonecat API preset. Pass --legacy-mini to use mini graph."
        )

    if be == "legacy_mini":
        return _generate_t2i_legacy_mini(
            prompt_text=prompt_text,
            model_type=model_type,
            output_filename=output_filename,
            seed=seed,
            negative_text=negative_text,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            workflow=workflow,
        )

    return _generate_t2i_workflow_api(
        prompt_text=prompt_text,
        model_type=model_type,
        output_filename=output_filename,
        seed=seed,
        negative_text=negative_text,
        steps=steps,
        cfg=cfg,
        width=width,
        height=height,
        meta_out=meta_out,
        server_address=server_address,
        timeout_sec=timeout_sec,
        preset=preset,
        family=family,
        unet_name=unet_name,
    )


def _generate_t2i_workflow_api(
    *,
    prompt_text: str,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    steps,
    cfg,
    width: int | None,
    height: int | None,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    preset: str | None,
    family: str | None,
    unet_name: str | None,
) -> dict:
    selected_model = unet_name or MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )
    preset_name = _resolve_preset(
        preset, family=family, model_type=model_type, unet_name=selected_model
    )

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_{model_type}.png"
        )

    ports: dict = {
        "positive": prompt_text,
        "unet_name": selected_model,
        "denoise": 1.0,
    }
    if negative_text:
        ports["negative"] = negative_text
    if width is not None:
        ports["width"] = int(width)
    if height is not None:
        ports["height"] = int(height)

    print(
        f"T2I via workflow_api preset={preset_name} "
        f"model={selected_model} size={width}x{height}"
    )
    if steps is not None or cfg is not None:
        print(
            f"[note] steps={steps} cfg={cfg} stored in meta only "
            f"(Lonecat T2I preset uses baked sampler; no steps/cfg ports)"
        )

    r = run_workflow_api(
        preset_name,
        ports=ports,
        output_path=output_filename,
        meta_out=None,
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
        "mode": "t2i",
        "engine": "workflow_api",
        "backend": "workflow_api",
        "prompt": prompt_text,
        "negative": negative_text or "",
        "negative_injected": bool(negative_text),
        "denoise": 1.0,
        "cfg": cfg,
        "steps": steps,
        "width": width,
        "height": height,
        "source_image": None,
        "created_at": utc_now_iso(),
        "comfy_prompt_id": prompt_id,
        "output_path": out_abs,
        "ports_applied": base_meta.get("ports_applied"),
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved to: {meta_path}")

    print(f"Image successfully saved to: {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=applied_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        workflow_api=base_meta.get("workflow_api"),
        preset=preset_name,
    )


def _generate_t2i_legacy_mini(
    *,
    prompt_text: str,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    steps,
    cfg,
    width: int | None,
    height: int | None,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    workflow,
) -> dict:
    """Emergency-only: old T2I-moody mini + convert_ui_to_api."""
    print(
        "[WARN] legacy_mini T2I-moody path — not production SSOT. "
        "Prefer lonecat_t2i_turbo."
    )
    workflow_path = (
        resolve_workflow(workflow) if workflow else default_workflow("t2i_moody")
    )
    selected_model = MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_{model_type}.png"
        )

    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    print(f"Loading base workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    latent_node_id = None
    negative_injected = False

    for node_id, node in api_prompt.items():
        ctype = node["class_type"]
        if ctype == "Prompt (LoraManager)":
            prompt_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype == "UNETLoader":
            unet_node_id = node_id
        elif ctype == "EmptySD3LatentImage":
            latent_node_id = node_id

    if prompt_node_id:
        api_prompt[prompt_node_id]["inputs"]["text"] = prompt_text
        print(f"Set Prompt: {prompt_text}")
    else:
        print("[WARN] Prompt node not found in T2I workflow")

    if negative_text:
        print(
            "[WARN] Negative text provided but T2I-moody has no dedicated negative input; "
            "saved to meta only"
        )

    if unet_node_id:
        api_prompt[unet_node_id]["inputs"]["unet_name"] = selected_model
        api_prompt[unet_node_id]["inputs"]["weight_dtype"] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")

    new_seed = seed if seed is not None else random.randint(1, 1125899906842624)
    applied_steps = None
    applied_cfg = None
    applied_width = None
    applied_height = None
    applied_sampler = None
    applied_scheduler = None

    if sampler_node_id:
        s_in = api_prompt[sampler_node_id]["inputs"]
        s_in["seed"] = new_seed
        if steps is not None:
            s_in["steps"] = steps
        if cfg is not None:
            s_in["cfg"] = cfg
        applied_steps = s_in.get("steps")
        applied_cfg = s_in.get("cfg")
        applied_sampler = s_in.get("sampler_name")
        applied_scheduler = s_in.get("scheduler")
        print(
            f"Set KSampler Seed: {new_seed}, steps={applied_steps}, cfg={applied_cfg}, "
            f"sampler={applied_sampler}, scheduler={applied_scheduler}"
        )

    if latent_node_id:
        l_in = api_prompt[latent_node_id]["inputs"]
        if width is not None:
            l_in["width"] = width
        if height is not None:
            l_in["height"] = height
        applied_width = l_in.get("width")
        applied_height = l_in.get("height")
        if width is not None or height is not None:
            print(f"Set latent size: {applied_width}x{applied_height}")

    print("Sending prompt request to ComfyUI...")
    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except ConnectionError as e:
        print(f"[ERROR] code=40 message={e}")
        return fail_result(error="COMFY_UNREACHABLE", message=str(e), seed=new_seed)
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    print(f"Generating image with {model_type.upper()} model (polling)...")
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
            server_address, image_filename, image_subfolder, image_type, output_filename
        )
        print(f"Image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading output image: {e}")
        return fail_result(
            error="DOWNLOAD_FAILED",
            message=str(e),
            seed=new_seed,
            prompt_id=prompt_id,
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
        "workflow": "T2I-moody",
        "mode": "t2i",
        "engine": "legacy_mini",
        "backend": "legacy_mini",
        "prompt": prompt_text,
        "negative": negative_text or "",
        "negative_injected": negative_injected,
        "denoise": None,
        "cfg": applied_cfg,
        "steps": applied_steps,
        "sampler": applied_sampler,
        "scheduler": applied_scheduler,
        "width": applied_width,
        "height": applied_height,
        "source_image": None,
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
            "T2I via Lonecat AIO API preset (default lonecat_t2i_turbo). "
            "No mini-graph."
        )
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default=(
            "Cinematic photo of a Korean woman in a cozy coffee shop, soft dramatic window lighting, "
            "realistic skin textures, highly detailed, film grain, 8k resolution"
        ),
        help="Text prompt for image generation",
    )
    parser.add_argument(
        "--prompt-file", type=str, default=None, help="Path to prompt text file"
    )
    parser.add_argument("--negative", type=str, default="", help="Negative prompt")
    parser.add_argument("--negative-file", type=str, default=None)
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        choices=["real", "pro", "wild"],
        default="real",
        help="Moody model alias → unet_name",
    )
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--meta-out", type=str, default=None)
    parser.add_argument(
        "--steps", type=int, default=None, help="Meta only on Lonecat preset"
    )
    parser.add_argument(
        "--cfg", type=float, default=None, help="Meta only on Lonecat preset"
    )
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help=f"API preset (default: {DEFAULT_T2I_PRESET})",
    )
    parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="zimage|lonecat|krea2 — family default if --preset omitted",
    )
    parser.add_argument("--unet-name", type=str, default=None)
    parser.add_argument(
        "--legacy-mini",
        action="store_true",
        help="Use old T2I-moody mini graph (emergency only)",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Legacy mini workflow (requires --legacy-mini)",
    )

    args = parser.parse_args()

    prompt_text = load_text(args.prompt_file) if args.prompt_file else args.prompt
    negative_text = (
        load_text(args.negative_file) if args.negative_file else (args.negative or "")
    )

    result = generate_image(
        prompt_text=prompt_text,
        model_type=args.model,
        output_filename=args.output,
        seed=args.seed,
        negative_text=negative_text,
        steps=args.steps,
        cfg=args.cfg,
        width=args.width,
        height=args.height,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        workflow=args.workflow,
        preset=args.preset,
        family=args.family,
        backend="legacy_mini" if args.legacy_mini else "workflow_api",
        unet_name=args.unet_name,
    )
    sys.exit(0 if result.get("ok") else 1)
