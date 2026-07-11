"""ControlNet-assisted I2I on Moody / Z-Image (Union 2.1 path)."""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    MODEL_MAPPING,
    WORKSPACE_ROOT,
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
from lib.prompt_assembly import assemble_prompt, load_text


def _rewire_empty_latent(api_prompt: dict, width: int, height: int, batch_size: int = 1) -> str:
    """Replace KSampler latent input with EmptySD3LatentImage (T2I+ControlNet path)."""
    empty_id = "9001"
    api_prompt[empty_id] = {
        "class_type": "EmptySD3LatentImage",
        "inputs": {
            "width": int(width),
            "height": int(height),
            "batch_size": int(batch_size),
        },
    }
    for _nid, node in api_prompt.items():
        if node.get("class_type") == "KSampler":
            node["inputs"]["latent_image"] = [empty_id, 0]
            node["inputs"]["denoise"] = 1.0
    return empty_id


def generate_controlnet_image(
    input_image_path,
    control_image_path,
    prompt_text,
    denoise_val=0.70,
    cfg_val=3.5,
    control_strength=0.75,
    model_type="real",
    output_filename=None,
    seed=None,
    negative_text="",
    core_prefix="",
    core_suffix="",
    meta_out=None,
    server_address=DEFAULT_SERVER,
    timeout_sec=600,
    empty_latent: bool = False,
    latent_width: int | None = None,
    latent_height: int | None = None,
):
    """
    ControlNet I2I (default) or empty-latent T2I+ControlNet.

    empty_latent=True: ignore portrait VAEEncode base; identity from prompt only
    (use strong positive_core / later LoRA). Pose from control image.
    """
    workflow_path = os.path.join(WORKSPACE_ROOT, "I2I-ControlNet-moody.json")
    selected_model = MODEL_MAPPING.get(model_type.lower(), MODEL_MAPPING["real"])

    if not empty_latent:
        if not input_image_path or not os.path.exists(input_image_path):
            print(f"Error: Face/character reference not found at {input_image_path}")
            return fail_result(error="SOURCE_MISSING", message=input_image_path)
    if not os.path.exists(control_image_path):
        print(f"Error: Control/pose image not found at {control_image_path}")
        return fail_result(error="CONTROL_MISSING", message=control_image_path)

    temp_input_name = "temp_i2i_input.png"
    temp_control_name = "temp_control_input.png"

    try:
        from lib.edge_preprocess import write_canny_rgb

        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        if not empty_latent:
            shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_input_name))
        else:
            # Dummy pixels for LoadImage node 54 (unused latent path after rewire)
            from PIL import Image

            dummy = Image.new("RGB", (64, 64), (128, 128, 128))
            dummy.save(os.path.join(COMFYUI_INPUT_DIR, temp_input_name))
        write_canny_rgb(
            control_image_path,
            os.path.join(COMFYUI_INPUT_DIR, temp_control_name),
            low=50,
            high=150,
        )
        mode = "empty_latent" if empty_latent else "i2i_latent"
        print(f"Processed control edges; mode={mode}")
    except Exception as e:
        print(f"Error copying/processing reference images: {e}")
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", f"output_controlnet_{model_type}.png")
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    final_prompt = assemble_prompt(core=core_prefix, instruction=prompt_text, suffix=core_suffix)

    print(f"Loading ControlNet workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    input_image_node_id = None
    control_image_node_id = None
    zimage_cn_node_id = None

    for node_id, node in api_prompt.items():
        ctype = node["class_type"]
        if ctype == "CLIPTextEncode":
            prompt_node_id = node_id
        elif ctype == "KSampler":
            sampler_node_id = node_id
        elif ctype == "UNETLoader":
            unet_node_id = node_id
        elif ctype == "LoadImage":
            if node_id == "54":
                input_image_node_id = node_id
            elif node_id == "60":
                control_image_node_id = node_id
            elif input_image_node_id is None:
                input_image_node_id = node_id
            else:
                control_image_node_id = node_id
        elif ctype == "ZImageFunControlnet":
            zimage_cn_node_id = node_id

    if prompt_node_id:
        api_prompt[prompt_node_id]["inputs"]["text"] = final_prompt
        print(f"Set Prompt: {final_prompt}")

    if negative_text:
        print("[WARN] Negative saved to meta only (no dedicated negative node)")

    if unet_node_id:
        api_prompt[unet_node_id]["inputs"]["unet_name"] = selected_model
        api_prompt[unet_node_id]["inputs"]["weight_dtype"] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")

    if input_image_node_id:
        api_prompt[input_image_node_id]["inputs"]["image"] = temp_input_name
    if control_image_node_id:
        api_prompt[control_image_node_id]["inputs"]["image"] = temp_control_name

    if zimage_cn_node_id:
        api_prompt[zimage_cn_node_id]["inputs"]["strength"] = control_strength
        print(f"Set ZImageFunControlnet Strength: {control_strength}")

    applied_w = latent_width or 1024
    applied_h = latent_height or 1536
    if empty_latent:
        _rewire_empty_latent(api_prompt, applied_w, applied_h)
        denoise_val = 1.0
        print(f"Rewired EmptySD3LatentImage {applied_w}x{applied_h}, denoise forced 1.0")

    new_seed = seed if seed is not None else random.randint(1, 1125899906842624)
    applied_steps = None
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

    print("Sending ControlNet prompt request to ComfyUI...")
    try:
        prompt_id = queue_prompt(server_address, api_prompt)
        print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except ConnectionError as e:
        print(f"[ERROR] code=40 message={e}")
        return fail_result(error="COMFY_UNREACHABLE", message=str(e), seed=new_seed)
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    print("Executing ControlNet image editing (polling)...")
    try:
        history_entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        print(f"[ERROR] code=41 message={e}")
        return fail_result(error="COMFY_TIMEOUT", message=str(e), seed=new_seed, prompt_id=prompt_id)
    except Exception as e:
        return fail_result(error="HISTORY_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id)

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
    except FileNotFoundError as e:
        print(f"[ERROR] code=42 message={e}")
        return fail_result(error="COMFY_NO_OUTPUT", message=str(e), seed=new_seed, prompt_id=prompt_id)

    print(f"Downloading image: {image_filename}")
    try:
        download_image(server_address, image_filename, image_subfolder, image_type, output_filename)
        print(f"ControlNet image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading image: {e}")
        return fail_result(error="DOWNLOAD_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id)

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "character_id": None,
        "sheet": None,
        "view": None,
        "variant": None,
        "seed": new_seed,
        "model": model_type,
        "workflow": "I2I-ControlNet-moody",
        "mode": "t2i_controlnet" if empty_latent else "i2i_controlnet",
        "empty_latent": empty_latent,
        "prompt": final_prompt,
        "prompt_instruction": prompt_text,
        "core_prefix": core_prefix or "",
        "core_suffix": core_suffix or "",
        "negative": negative_text or "",
        "denoise": denoise_val,
        "cfg": cfg_val,
        "control_strength": control_strength,
        "steps": applied_steps,
        "sampler": "euler",
        "scheduler": "normal",
        "latent_size": [applied_w, applied_h],
        "source_image": (
            os.path.abspath(input_image_path) if input_image_path and not empty_latent else None
        ),
        "control_image": os.path.abspath(control_image_path),
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
    parser = argparse.ArgumentParser(description="ControlNet-assisted I2I on Moody models")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Character reference image (required unless --empty-latent)",
    )
    parser.add_argument("--control", type=str, required=True, help="Pose/control reference image")
    parser.add_argument("--prompt", "-p", type=str, default=None)
    parser.add_argument("--prompt-file", type=str, default=None)
    parser.add_argument("--negative", type=str, default="")
    parser.add_argument("--negative-file", type=str, default=None)
    parser.add_argument("--core-prefix-file", type=str, default=None)
    parser.add_argument("--core-suffix-file", type=str, default=None)
    parser.add_argument("--denoise", "-d", type=float, default=0.70)
    parser.add_argument("--cfg", "-c", type=float, default=3.5)
    parser.add_argument("--strength", "-s", type=float, default=0.75, help="ControlNet strength")
    parser.add_argument("--model", "-m", type=str, choices=["real", "pro", "wild"], default="real")
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--meta-out", type=str, default=None)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--empty-latent",
        action="store_true",
        help="T2I+ControlNet: EmptySD3 latent (no portrait VAEEncode base)",
    )
    parser.add_argument("--width", type=int, default=1024, help="Empty latent width")
    parser.add_argument("--height", type=int, default=1536, help="Empty latent height")
    args = parser.parse_args()

    if args.prompt_file:
        prompt_text = load_text(args.prompt_file)
    elif args.prompt:
        prompt_text = args.prompt
    else:
        parser.error("Either --prompt or --prompt-file is required")

    if not args.empty_latent and not args.input:
        parser.error("--input is required unless --empty-latent")

    negative_text = load_text(args.negative_file) if args.negative_file else (args.negative or "")
    core_prefix = load_text(args.core_prefix_file) if args.core_prefix_file else ""
    core_suffix = load_text(args.core_suffix_file) if args.core_suffix_file else ""

    result = generate_controlnet_image(
        input_image_path=args.input,
        control_image_path=args.control,
        prompt_text=prompt_text,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        control_strength=args.strength,
        model_type=args.model,
        output_filename=args.output,
        seed=args.seed,
        negative_text=negative_text,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        empty_latent=args.empty_latent,
        latent_width=args.width,
        latent_height=args.height,
    )
    sys.exit(0 if result.get("ok") else 1)
