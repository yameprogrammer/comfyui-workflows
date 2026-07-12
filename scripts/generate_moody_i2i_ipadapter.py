#!/usr/bin/env python3
"""
I2I with IP-Adapter face lock on Moody (Z-Image) workflows.

Uses ComfyUI-IPAdapter-plus UnifiedLoader + Advanced applied to the ref image.
Requires models under ComfyUI/models/ipadapter/ and clip_vision name alias.
If IPAdapter fails (missing weights / arch), callers should fall back to i2i_lock.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import shutil

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
from lib.prompt_assembly import assemble_prompt
from lib.workflow_paths import default_workflow, resolve_workflow

# Stronger same-person lock for sheet expansion
IDENTITY_LOCK = (
    "same exact person as reference, identical face identity, same facial structure, "
    "same eyes nose mouth proportions, consistent skin tone and hair"
)


def inject_ipadapter(
    api_prompt: dict,
    *,
    load_image_node: str,
    model_source: list,
    weight: float = 0.72,
    preset: str = "PLUS FACE (portraits)",
) -> tuple[dict, str]:
    """
    Insert IPAdapter after model_source; return (api, new_model_ref_node_id).
    model_source is [node_id, slot] currently fed into KSampler.model.
    """
    # avoid id collisions
    n_loader = "9001"
    n_apply = "9002"
    while n_loader in api_prompt:
        n_loader = str(int(n_loader) + 10)
        n_apply = str(int(n_apply) + 10)

    api_prompt[n_loader] = {
        "class_type": "IPAdapterUnifiedLoader",
        "inputs": {
            "model": model_source,
            "preset": preset,
        },
    }
    api_prompt[n_apply] = {
        "class_type": "IPAdapterAdvanced",
        "inputs": {
            "model": [n_loader, 0],
            "ipadapter": [n_loader, 1],
            "image": [load_image_node, 0],
            "weight": float(weight),
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": 0.9,
            "embeds_scaling": "V only",
        },
    }
    return api_prompt, n_apply


def generate_i2i_ipadapter(
    input_image_path: str,
    prompt_text: str,
    denoise_val: float = 0.55,
    cfg_val: float = 3.5,
    model_type: str = "pro",
    output_filename: str | None = None,
    seed: int | None = None,
    negative_text: str = "",
    core_prefix: str = "",
    core_suffix: str = "",
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    workflow: str | None = None,
    ipa_weight: float = 0.72,
    ipa_preset: str = "PLUS FACE (portraits)",
    identity_lock: bool = True,
) -> dict:
    workflow_path = (
        resolve_workflow(workflow) if workflow else default_workflow("i2i_moody")
    )
    selected_model = MODEL_MAPPING.get(model_type.lower(), MODEL_MAPPING["real"])

    if not os.path.exists(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    temp_input_name = "temp_i2i_ipa_input.png"
    target_input_path = os.path.join(COMFYUI_INPUT_DIR, temp_input_name)
    try:
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        shutil.copy2(input_image_path, target_input_path)
    except Exception as e:
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_i2i_ipa_{model_type}.png"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    instr = prompt_text
    if identity_lock and IDENTITY_LOCK not in (prompt_text or ""):
        instr = f"{IDENTITY_LOCK}, {prompt_text}"
    final_prompt = assemble_prompt(core=core_prefix, instruction=instr, suffix=core_suffix)

    print(f"Loading I2I+IPAdapter workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    clip_node_id = None
    sampler_node_id = None
    unet_node_id = None
    load_image_node_id = None
    for node_id, node in api_prompt.items():
        ctype = node["class_type"]
        if ctype == "CLIPTextEncode":
            clip_node_id = node_id
        elif ctype == "Prompt (LoraManager)":
            if clip_node_id is None:
                clip_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype == "UNETLoader":
            unet_node_id = node_id
        elif ctype == "LoadImage":
            load_image_node_id = node_id

    if not sampler_node_id or not load_image_node_id:
        return fail_result(error="WF_INCOMPLETE", message="need KSampler + LoadImage")

    if clip_node_id:
        api_prompt[clip_node_id]["inputs"]["text"] = final_prompt
        print(f"Set Prompt: {final_prompt[:120]}...")

    if unet_node_id:
        api_prompt[unet_node_id]["inputs"]["unet_name"] = selected_model
        api_prompt[unet_node_id]["inputs"]["weight_dtype"] = "default"
        print(f"Set UNet ({model_type}): {selected_model}")

    model_src = api_prompt[sampler_node_id]["inputs"].get("model")
    if not model_src:
        return fail_result(error="WF_INCOMPLETE", message="KSampler has no model input")

    api_prompt, ipa_node = inject_ipadapter(
        api_prompt,
        load_image_node=load_image_node_id,
        model_source=model_src,
        weight=ipa_weight,
        preset=ipa_preset,
    )
    api_prompt[sampler_node_id]["inputs"]["model"] = [ipa_node, 0]
    api_prompt[load_image_node_id]["inputs"]["image"] = temp_input_name

    new_seed = seed if seed is not None else random.randint(1, 1125899906842624)
    # Cap denoise so identity can hold with IPA
    denoise = min(float(denoise_val), 0.65)
    s_in = api_prompt[sampler_node_id]["inputs"]
    s_in["seed"] = new_seed
    s_in["denoise"] = denoise
    if cfg_val is not None:
        s_in["cfg"] = float(cfg_val)
    print(
        f"IPAdapter preset={ipa_preset} weight={ipa_weight} "
        f"seed={new_seed} denoise={denoise} cfg={s_in.get('cfg')}"
    )

    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Queued IPAdapter I2I: {prompt_id}")
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    try:
        history = wait_for_history(server_address, prompt_id, timeout_sec)
    except TimeoutError as e:
        return fail_result(
            error="COMFY_TIMEOUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    status = history.get("status") or {}
    if status.get("status_str") == "error" or status.get("completed") is False:
        err_msg = "execution error"
        for msg in status.get("messages") or []:
            if msg and msg[0] == "execution_error":
                err_msg = msg[1].get("exception_message") or err_msg
                print(f"[ERROR] {msg[1].get('node_type')}: {str(err_msg)[:400]}")
        return fail_result(
            error="IPADAPTER_FAILED",
            message=str(err_msg)[:800],
            seed=new_seed,
            prompt_id=prompt_id,
        )

    try:
        filename, subfolder, image_type = extract_first_image(history)
        download_image(server_address, filename, subfolder, image_type, output_filename)
    except Exception as e:
        return fail_result(
            error="COMFY_NO_OUTPUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    meta = {
        "mode": "i2i_ipadapter",
        "engine": "ipadapter",
        "ipa_preset": ipa_preset,
        "ipa_weight": ipa_weight,
        "model_type": model_type,
        "unet": selected_model,
        "seed": new_seed,
        "denoise": denoise,
        "cfg": cfg_val,
        "prompt": final_prompt,
        "negative": negative_text,
        "source_image": os.path.abspath(input_image_path),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
    }
    mp = resolve_meta_out(output_filename, meta_out)
    if mp:
        write_meta(mp, meta)
    print(f"OK IPAdapter I2I → {output_filename}")
    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=new_seed,
        prompt_id=prompt_id,
        meta=meta,
        meta_path=mp,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Moody I2I + IPAdapter face lock")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    p.add_argument("--denoise", "-d", type=float, default=0.55)
    p.add_argument("--cfg", type=float, default=3.5)
    p.add_argument("--weight", type=float, default=0.72, help="IPAdapter weight")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args(argv)
    r = generate_i2i_ipadapter(
        args.input,
        args.prompt,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        model_type=args.model,
        output_filename=args.output,
        seed=args.seed,
        ipa_weight=args.weight,
        timeout_sec=args.timeout,
    )
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
