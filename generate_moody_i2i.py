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


def generate_i2i_image(
    input_image_path,
    prompt_text,
    denoise_val=0.45,
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
):
    workflow_path = os.path.join(WORKSPACE_ROOT, "I2I-moody.json")
    selected_model = MODEL_MAPPING.get(model_type.lower(), MODEL_MAPPING["real"])

    if not os.path.exists(input_image_path):
        print(f"Error: Input image not found at {input_image_path}")
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

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
        output_filename = os.path.join(r"F:\generated_images", f"output_i2i_{model_type}.png")

    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    final_prompt = assemble_prompt(core=core_prefix, instruction=prompt_text, suffix=core_suffix)

    print(f"Loading I2I workflow: {workflow_path}")
    ui_data = load_workflow(workflow_path)
    api_prompt = convert_ui_to_api(ui_data)

    prompt_node_id = None
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

    # Prefer standard CLIPTextEncode (I2I-moody wiring)
    prompt_node_id = clip_node_id or lora_prompt_node_id

    if prompt_node_id:
        api_prompt[prompt_node_id]["inputs"]["text"] = final_prompt
        print(f"Set Prompt: {final_prompt}")
    else:
        print("[WARN] Prompt/CLIPTextEncode node not found")

    if negative_text:
        print(
            "[WARN] Negative text provided; I2I-moody may lack negative node — saved to meta only"
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
        history_entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        print(f"[ERROR] code=41 message={e}")
        return fail_result(error="COMFY_TIMEOUT", message=str(e), seed=new_seed, prompt_id=prompt_id)
    except Exception as e:
        print(f"Error waiting for history: {e}")
        return fail_result(error="HISTORY_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id)

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
    except FileNotFoundError as e:
        print(f"[ERROR] code=42 message={e}")
        return fail_result(error="COMFY_NO_OUTPUT", message=str(e), seed=new_seed, prompt_id=prompt_id)

    print(f"Downloading image: {image_filename}")
    try:
        download_image(server_address, image_filename, image_subfolder, image_type, output_filename)
        print(f"Edited image successfully saved to: {output_filename}")
    except Exception as e:
        print(f"Error downloading edited image: {e}")
        return fail_result(error="DOWNLOAD_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id)

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
    parser = argparse.ArgumentParser(description="Image-to-Image editing using customized Moody models on ComfyUI")
    parser.add_argument("--input", "-i", type=str, required=True, help="Path to the input source image")
    parser.add_argument("--prompt", "-p", type=str, default=None, help="Text prompt for image editing instruction")
    parser.add_argument("--prompt-file", type=str, default=None, help="Prompt file (overrides --prompt if set alone)")
    parser.add_argument("--negative", type=str, default="", help="Negative prompt (meta)")
    parser.add_argument("--negative-file", type=str, default=None, help="Negative prompt file")
    parser.add_argument("--core-prefix-file", type=str, default=None, help="Locked appearance prefix file")
    parser.add_argument("--core-suffix-file", type=str, default=None, help="Optional suffix file")
    parser.add_argument("--denoise", "-d", type=float, default=0.45, help="Denoise value (0.0 to 1.0)")
    parser.add_argument("--cfg", "-c", type=float, default=1.0, help="CFG scale")
    parser.add_argument("--model", "-m", type=str, choices=["real", "pro", "wild"], default="real")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output path")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed")
    parser.add_argument("--meta-out", type=str, default=None, help="Meta JSON path")
    parser.add_argument("--timeout", type=int, default=600, help="Comfy wait timeout seconds")

    args = parser.parse_args()

    if args.prompt_file:
        prompt_text = load_text(args.prompt_file)
    elif args.prompt:
        prompt_text = args.prompt
    else:
        parser.error("Either --prompt or --prompt-file is required")

    negative_text = load_text(args.negative_file) if args.negative_file else (args.negative or "")
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
    )
    sys.exit(0 if result.get("ok") else 1)
