#!/usr/bin/env python3
"""T2I via Krea 2 Turbo — uses shared Comfy client (ensure + queue + history).

Do **not** bypass ``lib.comfy_client.queue_prompt``: that path auto-starts Comfy
with the official portable bat via ``ensure_comfy_running`` /
``_launch_comfy_process`` only.
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
from lib.workflow_paths import default_workflow, resolve_workflow


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
):
    """Queue Krea T2I and download the first image. Returns True/False or result dict.

    Backward compatible: returns True on success / False on failure when used as
    a simple bool; structured failures also print error codes like generate_moody.
    """
    workflow_path = resolve_workflow(workflow) if workflow else default_workflow("t2i_krea")

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
            # Node 5 = positive in T2I-krea (first CLIPTextEncode in graph order
            # is not guaranteed — prefer linked-to-sampler positive if needed)
            prompt_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype in ("EmptyLatentImage", "EmptySD3LatentImage"):
            latent_node_id = node_id

    # T2I-krea fixed IDs (keep override for stable workflow)
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

    print("Sending Krea prompt request to ComfyUI (queue_prompt → ensure bat if down)...")
    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except ConnectionError as e:
        print(f"[ERROR] code=40 message={e}")
        fail_result(error="COMFY_UNREACHABLE", message=str(e), seed=new_seed)
        return False
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)
        return False

    print("Executing Krea T2I generation (polling)...")
    try:
        history_entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        print(f"[ERROR] code=41 message={e}")
        return False
    except RuntimeError as e:
        # execution_error from Comfy (e.g. console/tqdm OSError) — fail loud
        print(f"[ERROR] code=43 message={e}")
        return False
    except Exception as e:
        print(f"Error waiting for history: {e}")
        return False

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
    except FileNotFoundError as e:
        print(f"[ERROR] code=42 message={e}")
        return False

    print(f"Downloading image: {image_filename}")
    try:
        download_image(
            server_address, image_filename, image_subfolder, image_type, output_filename
        )
        print(f"Krea T2I image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading output image: {e}")
        return False

    meta_path = resolve_meta_out(output_filename, meta_out)
    if meta_path:
        write_meta(
            meta_path,
            {
                "engine": "krea2_turbo",
                "workflow": os.path.basename(workflow_path),
                "seed": new_seed,
                "steps": applied_steps,
                "cfg": applied_cfg,
                "sampler": applied_sampler,
                "scheduler": applied_scheduler,
                "width": applied_width,
                "height": applied_height,
                "prompt": prompt_text,
                "prompt_id": prompt_id,
                "output_path": output_filename,
                "created_at": utc_now_iso(),
                "server": server_address,
            },
        )

    ok_result(
        output_path=output_filename,
        seed=new_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
    )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T2I Generation using Krea 2 Turbo model")
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default="Cinematic photo of a Korean woman in a cozy coffee shop, smiling, highly detailed, 8k",
        help="Prompt describing the scene to generate",
    )
    parser.add_argument("--steps", "-s", type=int, default=8, help="Inference steps (default 8)")
    parser.add_argument("--cfg", "-c", type=float, default=1.0, help="CFG scale (default 1.0)")
    parser.add_argument(
        "--sampler",
        "-sm",
        type=str,
        default="euler_ancestral",
        help="Sampler name (default euler_ancestral)",
    )
    parser.add_argument(
        "--scheduler",
        "-sc",
        type=str,
        default="simple",
        help="Scheduler name (default simple)",
    )
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output image")
    parser.add_argument("--seed", type=int, default=None, help="Optional fixed seed")
    parser.add_argument("--width", type=int, default=None, help="Optional latent width")
    parser.add_argument("--height", type=int, default=None, help="Optional latent height")
    parser.add_argument("--timeout", type=float, default=600, help="History poll timeout seconds")
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
    )
    sys.exit(0 if ok else 1)
