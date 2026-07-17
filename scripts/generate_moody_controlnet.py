#!/usr/bin/env python3
"""
Z-Image Fun Union ControlNet via validated **API workflow preset**.

Default: ``zimage_fun_union_controlnet``
  (official ``image_z_image_turbo_fun_union_controlnet`` subgraph flattened)
  → port patch only → POST /prompt.

Empty latent sized from control image (GetImageSize). Identity from prompt /
core_prefix — not VAEEncode face I2I.

Legacy mini ``I2I-ControlNet-moody`` (+ runtime empty-latent rewire):
  ``--legacy-mini`` or ``AGENT_CN_BACKEND=legacy_mini``.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401  # repo root + scripts on path

import argparse
import os
import random
import shutil
import sys
import tempfile

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

DEFAULT_CN_PRESET = "zimage_fun_union_controlnet"


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_CN_BACKEND")
        or "workflow_api"
    ).strip().lower()
    if raw in ("legacy", "legacy_mini", "mini", "i2i_controlnet_moody"):
        return "legacy_mini"
    return "workflow_api"


def _looks_like_openpose_map(path: str) -> bool:
    name = os.path.basename(path).lower()
    if "openpose" in name or "dwpose" in name or "pose_map" in name:
        return True
    try:
        from PIL import Image

        im = Image.open(path).convert("RGB")
        im.thumbnail((64, 64))
        pixels = list(im.getdata())
        if not pixels:
            return False
        dark = sum(1 for r, g, b in pixels if r + g + b < 40) / len(pixels)
        colorful = sum(
            1
            for r, g, b in pixels
            if max(r, g, b) > 80 and (max(r, g, b) - min(r, g, b)) > 40
        ) / len(pixels)
        return dark > 0.55 and colorful > 0.02
    except Exception:
        return False


def _prepare_control_image(
    control_image_path: str,
    control_preprocess: str,
) -> tuple[str, str]:
    """
    Return (path_to_feed_as_control, mode_used).

    openpose/raw: copy as-is (Union Pose condition).
    canny: write temp canny RGB (Union Canny condition).
    auto: openpose map detect → raw else canny.
    """
    mode_pp = (control_preprocess or "auto").lower()
    if mode_pp == "auto":
        mode_pp = "openpose" if _looks_like_openpose_map(control_image_path) else "canny"

    if mode_pp in ("openpose", "raw", "none", "dwpose", "pose"):
        return os.path.abspath(control_image_path), "openpose"

    from lib.edge_preprocess import write_canny_rgb

    fd, tmp = tempfile.mkstemp(prefix="cn_canny_", suffix=".png")
    os.close(fd)
    write_canny_rgb(control_image_path, tmp, low=50, high=150)
    return tmp, "canny"


def _rewire_empty_latent(api_prompt: dict, width: int, height: int, batch_size: int = 1) -> str:
    """Legacy only: Replace KSampler latent with EmptySD3LatentImage."""
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
    denoise_val=1.0,
    cfg_val=1.0,
    control_strength=1.0,
    model_type="real",
    output_filename=None,
    seed=None,
    negative_text="",
    core_prefix="",
    core_suffix="",
    meta_out=None,
    server_address=DEFAULT_SERVER,
    timeout_sec=600,
    empty_latent: bool = True,
    latent_width: int | None = None,
    latent_height: int | None = None,
    workflow=None,
    control_preprocess: str = "auto",
    *,
    preset: str | None = None,
    backend: str | None = None,
    unet_name: str | None = None,
    steps: int | None = 8,
):
    """
    ControlNet generation.

    Default (workflow_api): official Fun Union ControlNet empty-latent path.
    ``input_image_path`` is optional (legacy I2I face base); unused on API path
    except recorded in meta. Identity = prompt + core_prefix.

    ``empty_latent`` defaults True to match official WF. False only affects
    legacy mini (VAEEncode I2I).
    """
    eng = ensure_engine(
        FAMILY_MOODY, server_address, caller="generate_moody_controlnet"
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    if not control_image_path or not os.path.exists(control_image_path):
        print(f"Error: Control/pose image not found at {control_image_path}")
        return fail_result(error="CONTROL_MISSING", message=control_image_path)

    be = _resolve_backend(backend)
    if be == "legacy_mini":
        return _generate_cn_legacy_mini(
            input_image_path=input_image_path,
            control_image_path=control_image_path,
            prompt_text=prompt_text,
            denoise_val=denoise_val,
            cfg_val=cfg_val,
            control_strength=control_strength,
            model_type=model_type,
            output_filename=output_filename,
            seed=seed,
            negative_text=negative_text,
            core_prefix=core_prefix,
            core_suffix=core_suffix,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            empty_latent=empty_latent,
            latent_width=latent_width,
            latent_height=latent_height,
            workflow=workflow,
            control_preprocess=control_preprocess,
        )

    return _generate_cn_workflow_api(
        input_image_path=input_image_path,
        control_image_path=control_image_path,
        prompt_text=prompt_text,
        denoise_val=denoise_val,
        cfg_val=cfg_val,
        control_strength=control_strength,
        model_type=model_type,
        output_filename=output_filename,
        seed=seed,
        negative_text=negative_text,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        meta_out=meta_out,
        server_address=server_address,
        timeout_sec=timeout_sec,
        control_preprocess=control_preprocess,
        preset=preset,
        unet_name=unet_name,
        steps=steps,
        largest_size=latent_width,  # optional max dimension if provided
    )


def _generate_cn_workflow_api(
    *,
    input_image_path,
    control_image_path: str,
    prompt_text: str,
    denoise_val: float,
    cfg_val: float,
    control_strength: float,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    core_prefix: str,
    core_suffix: str,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    control_preprocess: str,
    preset: str | None,
    unet_name: str | None,
    steps: int | None,
    largest_size: int | None,
) -> dict:
    final_prompt = assemble_prompt(
        core=core_prefix, instruction=prompt_text, suffix=core_suffix
    )
    selected_model = unet_name or MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )
    preset_name = preset or select_lonecat_preset(
        mode="controlnet", unet_name=selected_model
    )

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_controlnet_{model_type}.png"
        )

    control_feed, mode_pp = _prepare_control_image(
        control_image_path, control_preprocess
    )
    tmp_canny = control_feed if mode_pp == "canny" and control_feed != os.path.abspath(
        control_image_path
    ) else None

    ports: dict = {
        "positive": final_prompt,
        "control_image": control_feed,
        "unet_name": selected_model,
        "control_strength": float(control_strength),
        "denoise": float(denoise_val) if denoise_val is not None else 1.0,
    }
    if steps is not None:
        ports["steps"] = int(steps)
    if cfg_val is not None:
        ports["cfg"] = float(cfg_val)
    if largest_size is not None and largest_size > 0:
        # If caller passed a width-like size, use as max dimension cap
        ports["largest_size"] = int(largest_size)

    print(
        f"ControlNet via workflow_api preset={preset_name} "
        f"preprocess={mode_pp} strength={control_strength} model={selected_model}"
    )
    if input_image_path:
        print(
            "[note] input_image ignored for latent (official Fun Union is empty-latent+control); "
            "identity from prompt/core_prefix only"
        )
    if negative_text:
        print("[note] negative saved to meta only (official graph uses ConditioningZeroOut)")

    try:
        r = run_workflow_api(
            preset_name,
            ports=ports,
            output_path=output_filename,
            meta_out=None,
            server_address=server_address,
            timeout_sec=timeout_sec,
            seed=seed,
        )
    finally:
        if tmp_canny and os.path.isfile(tmp_canny):
            try:
                os.remove(tmp_canny)
            except OSError:
                pass

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
        "model": model_type,
        "unet": selected_model,
        "workflow": preset_name,
        "workflow_api": base_meta.get("workflow_api"),
        "mode": "t2i_controlnet",
        "engine": "workflow_api",
        "backend": "workflow_api",
        "empty_latent": True,
        "prompt": final_prompt,
        "prompt_instruction": prompt_text,
        "core_prefix": core_prefix or "",
        "core_suffix": core_suffix or "",
        "negative": negative_text or "",
        "denoise": ports.get("denoise"),
        "cfg": cfg_val,
        "steps": steps,
        "control_strength": float(control_strength),
        "control_preprocess": mode_pp,
        "source_image": (
            os.path.abspath(input_image_path) if input_image_path else None
        ),
        "control_image": os.path.abspath(control_image_path),
        "created_at": utc_now_iso(),
        "comfy_prompt_id": prompt_id,
        "output_path": out_abs,
        "ports_applied": base_meta.get("ports_applied"),
        "source_workflow": "image_z_image_turbo_fun_union_controlnet",
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved to: {meta_path}")

    print(f"ControlNet image successfully saved to: {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=applied_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        workflow_api=base_meta.get("workflow_api"),
        preset=preset_name,
    )


def _generate_cn_legacy_mini(
    *,
    input_image_path,
    control_image_path: str,
    prompt_text: str,
    denoise_val: float,
    cfg_val: float,
    control_strength: float,
    model_type: str,
    output_filename: str | None,
    seed: int | None,
    negative_text: str,
    core_prefix: str,
    core_suffix: str,
    meta_out: str | None,
    server_address: str,
    timeout_sec: float,
    empty_latent: bool,
    latent_width: int | None,
    latent_height: int | None,
    workflow,
    control_preprocess: str,
) -> dict:
    print(
        "[WARN] legacy_mini I2I-ControlNet-moody — not production SSOT. "
        "Prefer zimage_fun_union_controlnet."
    )
    workflow_path = (
        resolve_workflow(workflow) if workflow else default_workflow("i2i_controlnet_moody")
    )
    selected_model = MODEL_MAPPING.get(
        (model_type or "real").lower(), MODEL_MAPPING["real"]
    )

    if not empty_latent:
        if not input_image_path or not os.path.exists(input_image_path):
            return fail_result(error="SOURCE_MISSING", message=input_image_path)

    temp_input_name = "temp_i2i_input.png"
    temp_control_name = "temp_control_input.png"

    try:
        from lib.edge_preprocess import write_canny_rgb

        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        if not empty_latent:
            shutil.copy2(
                input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_input_name)
            )
        else:
            from PIL import Image

            dummy = Image.new("RGB", (64, 64), (128, 128, 128))
            dummy.save(os.path.join(COMFYUI_INPUT_DIR, temp_input_name))

        dest_ctrl = os.path.join(COMFYUI_INPUT_DIR, temp_control_name)
        mode_pp = (control_preprocess or "auto").lower()
        if mode_pp == "auto":
            mode_pp = (
                "openpose" if _looks_like_openpose_map(control_image_path) else "canny"
            )
        if mode_pp in ("openpose", "raw", "none", "dwpose", "pose"):
            shutil.copy2(control_image_path, dest_ctrl)
            print(f"Control preprocess=openpose/raw ← {os.path.basename(control_image_path)}")
        else:
            write_canny_rgb(control_image_path, dest_ctrl, low=50, high=150)
            print(f"Control preprocess=canny ← {os.path.basename(control_image_path)}")
    except Exception as e:
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"output_controlnet_{model_type}.png"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    final_prompt = assemble_prompt(
        core=core_prefix, instruction=prompt_text, suffix=core_suffix
    )

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
    if unet_node_id:
        api_prompt[unet_node_id]["inputs"]["unet_name"] = selected_model
        api_prompt[unet_node_id]["inputs"]["weight_dtype"] = "default"
    if input_image_node_id:
        api_prompt[input_image_node_id]["inputs"]["image"] = temp_input_name
    if control_image_node_id:
        api_prompt[control_image_node_id]["inputs"]["image"] = temp_control_name
    if zimage_cn_node_id:
        api_prompt[zimage_cn_node_id]["inputs"]["strength"] = control_strength

    applied_w = latent_width or 1024
    applied_h = latent_height or 1536
    if empty_latent:
        _rewire_empty_latent(api_prompt, applied_w, applied_h)
        denoise_val = 1.0

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

    try:
        prompt_id = queue_prompt(server_address, api_prompt)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
    except TimeoutError as e:
        return fail_result(
            error="COMFY_TIMEOUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )
    except Exception as e:
        return fail_result(
            error="HISTORY_FAILED", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
        download_image(
            server_address, image_filename, image_subfolder, image_type, output_filename
        )
    except Exception as e:
        return fail_result(
            error="COMFY_NO_OUTPUT", message=str(e), seed=new_seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "seed": new_seed,
        "model": model_type,
        "workflow": "I2I-ControlNet-moody",
        "mode": "t2i_controlnet" if empty_latent else "i2i_controlnet",
        "empty_latent": empty_latent,
        "backend": "legacy_mini",
        "prompt": final_prompt,
        "denoise": denoise_val,
        "cfg": cfg_val,
        "control_strength": control_strength,
        "control_preprocess": control_preprocess,
        "steps": applied_steps,
        "source_image": (
            os.path.abspath(input_image_path)
            if input_image_path and not empty_latent
            else None
        ),
        "control_image": os.path.abspath(control_image_path),
        "created_at": utc_now_iso(),
        "comfy_prompt_id": prompt_id,
        "output_path": os.path.abspath(output_filename),
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
        description=(
            "Z-Image Fun Union ControlNet via API preset "
            "(image_z_image_turbo_fun_union_controlnet)"
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Optional face ref (meta only on API path; required for legacy I2I)",
    )
    parser.add_argument("--control", type=str, required=True, help="Pose/control image")
    parser.add_argument("--prompt", "-p", type=str, default=None)
    parser.add_argument("--prompt-file", type=str, default=None)
    parser.add_argument("--negative", type=str, default="")
    parser.add_argument("--negative-file", type=str, default=None)
    parser.add_argument("--core-prefix-file", type=str, default=None)
    parser.add_argument("--core-suffix-file", type=str, default=None)
    parser.add_argument(
        "--denoise",
        "-d",
        type=float,
        default=1.0,
        help="Denoise (official empty-latent default 1.0)",
    )
    parser.add_argument("--cfg", "-c", type=float, default=1.0)
    parser.add_argument(
        "--strength",
        "-s",
        type=float,
        default=1.0,
        help="ControlNet strength (official default 1.0)",
    )
    parser.add_argument(
        "--model", "-m", type=str, choices=["real", "pro", "wild"], default="real"
    )
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--meta-out", type=str, default=None)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--empty-latent",
        action="store_true",
        default=True,
        help="API path always empty-latent; flag kept for CLI compat",
    )
    parser.add_argument(
        "--no-empty-latent",
        action="store_true",
        help="Legacy mini only: use VAEEncode I2I base",
    )
    parser.add_argument("--width", type=int, default=None, help="Optional largest_size cap")
    parser.add_argument("--height", type=int, default=None, help="Legacy mini latent height")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument(
        "--control-preprocess",
        choices=["auto", "canny", "openpose", "raw"],
        default="auto",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help=f"API preset (default: {DEFAULT_CN_PRESET})",
    )
    parser.add_argument(
        "--legacy-mini",
        action="store_true",
        help="Old I2I-ControlNet-moody mini graph (emergency)",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Legacy mini workflow (requires --legacy-mini)",
    )

    args = parser.parse_args()

    if args.prompt_file:
        prompt_text = load_text(args.prompt_file)
    elif args.prompt:
        prompt_text = args.prompt
    else:
        parser.error("Either --prompt or --prompt-file is required")

    empty_latent = not args.no_empty_latent
    if args.legacy_mini and not empty_latent and not args.input:
        parser.error("--input is required for legacy mini without empty-latent")

    negative_text = (
        load_text(args.negative_file) if args.negative_file else (args.negative or "")
    )
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
        empty_latent=empty_latent,
        latent_width=args.width,
        latent_height=args.height,
        workflow=args.workflow,
        control_preprocess=args.control_preprocess,
        preset=args.preset,
        backend="legacy_mini" if args.legacy_mini else "workflow_api",
        steps=args.steps,
    )
    sys.exit(0 if result.get("ok") else 1)
