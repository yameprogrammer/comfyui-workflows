#!/usr/bin/env python3
"""
T2I via Krea2 validated **API workflow preset**.

Default: ``krea2_t2i_v10`` → port patch only → POST /prompt.
Uses ``lib.comfy_client.queue_prompt`` (via workflow_api_runner) so Comfy autostart stays intact.

Legacy mini T2I-krea: ``--legacy-mini`` or ``AGENT_KREA_BACKEND=legacy_mini``.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401  # repo root + scripts on path
import argparse
import os
import random
import sys

from lib.comfy_client import (
    DEFAULT_SERVER,
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
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api, select_lonecat_preset
from lib.workflow_paths import default_workflow, resolve_workflow

DEFAULT_KREA_PRESET = "krea2_t2i_v10"
FAMILY_KREA2 = "krea2_still"


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_KREA_BACKEND")
        or "workflow_api"
    ).strip().lower()
    if raw in ("legacy", "legacy_mini", "mini", "t2i_krea"):
        return "legacy_mini"
    return "workflow_api"


def generate_krea_image(
    prompt_text,
    steps=8,
    cfg=1.0,
    sampler="euler_ancestral",
    scheduler="simple",
    output_filename=None,
    workflow=None,
    seed=None,
    width=None,
    height=None,
    meta_out=None,
    server_address=DEFAULT_SERVER,
    timeout_sec=600,
    *,
    preset: str | None = None,
    backend: str | None = None,
    unet_name: str | None = None,
    return_dict: bool = False,
):
    """
    Queue Krea2 T2I and download first image.

    Returns:
      - dict result (ok/output_path/...) when return_dict=True
      - True/False when return_dict=False (legacy cast_pool / CLI bool)
    """
    eng = ensure_engine(FAMILY_KREA2, server_address, caller="generate_krea")
    if not eng.get("ok"):
        r = fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )
        return r if return_dict else False

    be = _resolve_backend(backend)
    if be == "legacy_mini":
        r = _generate_krea_legacy_mini(
            prompt_text=prompt_text,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            output_filename=output_filename,
            workflow=workflow,
            seed=seed,
            width=width,
            height=height,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
        )
    else:
        r = _generate_krea_workflow_api(
            prompt_text=prompt_text,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            output_filename=output_filename,
            seed=seed,
            width=width,
            height=height,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            preset=preset,
            unet_name=unet_name,
        )

    if return_dict:
        return r
    return bool(r.get("ok"))


def _generate_krea_workflow_api(
    *,
    prompt_text: str,
    steps,
    cfg,
    sampler,
    scheduler,
    output_filename: str | None,
    seed: int | None,
    width: int | None,
    height: int | None,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    preset: str | None,
    unet_name: str | None,
) -> dict:
    preset_name = preset or select_lonecat_preset(mode="t2i", family="krea2")

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", "output_krea.png")

    ports: dict = {"positive": prompt_text}
    if unet_name:
        ports["unet_name"] = unet_name
    if width is not None:
        ports["width"] = int(width)
    if height is not None:
        ports["height"] = int(height)

    print(
        f"Krea T2I via workflow_api preset={preset_name} "
        f"size={width}x{height}"
    )
    if steps is not None or cfg is not None:
        print(
            f"[note] steps={steps} cfg={cfg} sampler={sampler} scheduler={scheduler} "
            f"meta only (krea2_t2i_v10 uses baked sampler)"
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
        "engine": "krea2_t2i_v10",
        "workflow": preset_name,
        "workflow_api": base_meta.get("workflow_api"),
        "mode": "t2i",
        "backend": "workflow_api",
        "seed": applied_seed,
        "steps": steps,
        "cfg": cfg,
        "sampler": sampler,
        "scheduler": scheduler,
        "width": width,
        "height": height,
        "prompt": prompt_text,
        "comfy_prompt_id": prompt_id,
        "output_path": out_abs,
        "created_at": utc_now_iso(),
        "server": server_address,
        "ports_applied": base_meta.get("ports_applied"),
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)

    print(f"Krea T2I image successfully saved to: {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=applied_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        workflow_api=base_meta.get("workflow_api"),
        preset=preset_name,
    )


def _generate_krea_legacy_mini(
    *,
    prompt_text: str,
    steps,
    cfg,
    sampler,
    scheduler,
    output_filename: str | None,
    workflow,
    seed: int | None,
    width: int | None,
    height: int | None,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
) -> dict:
    print("[WARN] legacy_mini T2I-krea — not production SSOT. Prefer krea2_t2i_v10.")
    workflow_path = (
        resolve_workflow(workflow) if workflow else default_workflow("t2i_krea")
    )

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", "output_krea.png")

    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    print(f"Loading Krea base workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    prompt_node_id = None
    sampler_node_id = None
    latent_node_id = None
    for node_id, node in api_prompt.items():
        ctype = node["class_type"]
        if ctype == "CLIPTextEncode" and prompt_node_id is None:
            prompt_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype in ("EmptyLatentImage", "EmptySD3LatentImage"):
            latent_node_id = node_id

    if "5" in api_prompt and api_prompt["5"]["class_type"] == "CLIPTextEncode":
        prompt_node_id = "5"
    if "7" in api_prompt and api_prompt["7"]["class_type"] == "KSampler":
        sampler_node_id = "7"
    if "4" in api_prompt and api_prompt["4"]["class_type"] in (
        "EmptyLatentImage",
        "EmptySD3LatentImage",
    ):
        latent_node_id = "4"

    if prompt_node_id:
        api_prompt[prompt_node_id]["inputs"]["text"] = prompt_text
        print(f"Set Prompt: {prompt_text}")
    else:
        print("[WARN] Positive CLIPTextEncode node not found")

    new_seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    applied_steps = steps
    applied_cfg = cfg
    applied_sampler = sampler
    applied_scheduler = scheduler
    applied_width = None
    applied_height = None

    if sampler_node_id:
        s_in = api_prompt[sampler_node_id]["inputs"]
        s_in["seed"] = new_seed
        s_in["steps"] = steps
        s_in["cfg"] = cfg
        s_in["sampler_name"] = sampler
        s_in["scheduler"] = scheduler
        s_in["denoise"] = 1.0
        print(
            f"Set KSampler Seed: {new_seed}, Steps: {steps}, CFG: {cfg}, "
            f"Sampler: {sampler}, Scheduler: {scheduler}"
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

    print("Sending Krea prompt request to ComfyUI...")
    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except ConnectionError as e:
        print(f"[ERROR] code=40 message={e}")
        return fail_result(error="COMFY_UNREACHABLE", message=str(e), seed=new_seed)
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    print("Executing Krea T2I generation (polling)...")
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
        print(f"Krea T2I image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading output image: {e}")
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "engine": "krea2_turbo",
        "workflow": os.path.basename(workflow_path),
        "mode": "t2i",
        "backend": "legacy_mini",
        "seed": new_seed,
        "steps": applied_steps,
        "cfg": applied_cfg,
        "sampler": applied_sampler,
        "scheduler": applied_scheduler,
        "width": applied_width,
        "height": applied_height,
        "prompt": prompt_text,
        "comfy_prompt_id": prompt_id,
        "output_path": os.path.abspath(output_filename),
        "created_at": utc_now_iso(),
        "server": server_address,
    }
    if meta_path:
        write_meta(meta_path, meta)

    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=new_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="T2I via krea2_t2i_v10 API preset (workflow_api_runner)"
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default="Cinematic photo of a Korean woman in a cozy coffee shop, smiling, highly detailed, 8k",
        help="Prompt describing the scene to generate",
    )
    parser.add_argument("--steps", "-s", type=int, default=8, help="Meta only on API preset")
    parser.add_argument("--cfg", "-c", type=float, default=1.0, help="Meta only on API preset")
    parser.add_argument("--sampler", "-sm", type=str, default="euler_ancestral")
    parser.add_argument("--scheduler", "-sc", type=str, default="simple")
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--preset", type=str, default=None, help=f"default {DEFAULT_KREA_PRESET}")
    parser.add_argument("--unet-name", type=str, default=None)
    parser.add_argument(
        "--legacy-mini",
        action="store_true",
        help="Old T2I-krea mini graph (emergency only)",
    )
    args = parser.parse_args()

    ok = generate_krea_image(
        prompt_text=args.prompt,
        steps=args.steps,
        cfg=args.cfg,
        sampler=args.sampler,
        scheduler=args.scheduler,
        output_filename=args.output,
        seed=args.seed,
        width=args.width,
        height=args.height,
        timeout_sec=args.timeout,
        preset=args.preset,
        backend="legacy_mini" if args.legacy_mini else "workflow_api",
        unet_name=args.unet_name,
        return_dict=False,
    )
    sys.exit(0 if ok else 1)
