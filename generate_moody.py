import argparse
import os
import random
import sys

from lib.comfy_client import (
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
from lib.prompt_assembly import load_text


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
):
    workflow_path = os.path.join(WORKSPACE_ROOT, "T2I-moody.json")
    selected_model = MODEL_MAPPING.get(model_type.lower(), MODEL_MAPPING["real"])

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", f"output_{model_type}.png")

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
        # T2I-moody may not expose a dedicated negative node; store in meta always.
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
    parser = argparse.ArgumentParser(description="Generate image using customized Moody models on ComfyUI")
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
    parser.add_argument("--prompt-file", type=str, default=None, help="Path to prompt text file (overrides --prompt)")
    parser.add_argument("--negative", type=str, default="", help="Negative prompt (meta; inject if node exists)")
    parser.add_argument("--negative-file", type=str, default=None, help="Path to negative prompt file")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        choices=["real", "pro", "wild"],
        default="real",
        help="Choose moody model type",
    )
    parser.add_argument("--output", "-o", type=str, default=None, help="Output image path")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed (default: random)")
    parser.add_argument("--meta-out", type=str, default=None, help="Meta JSON path (default: output stem + .json)")
    parser.add_argument("--steps", type=int, default=None, help="Override KSampler steps")
    parser.add_argument("--cfg", type=float, default=None, help="Override KSampler CFG")
    parser.add_argument("--width", type=int, default=None, help="Override latent width")
    parser.add_argument("--height", type=int, default=None, help="Override latent height")
    parser.add_argument("--timeout", type=int, default=600, help="Comfy wait timeout seconds")

    args = parser.parse_args()

    prompt_text = load_text(args.prompt_file) if args.prompt_file else args.prompt
    negative_text = load_text(args.negative_file) if args.negative_file else (args.negative or "")

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
    )
    sys.exit(0 if result.get("ok") else 1)
