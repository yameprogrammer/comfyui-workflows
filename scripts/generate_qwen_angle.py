#!/usr/bin/env python3
"""
Qwen-Image-Edit-2511 multi-angle camera edit (local MultiGen stack).

Role (coexists — do not replace general instruction edit):
  - Character head/body turns only (`character_qwen_turns`, expand engine=qwen)
  - General object/prop/scene instruction edit → `generate_qwen_edit.py` (2509)
  - Soft tone/expression remix → Moody I2I

Uses:
  - LoaderGGUF: qwen-image-edit-2511-Q4_K_M.gguf
  - Lightning 4step LoRA
  - Multiple-Angles LoRA (<sks> azimuth elevation distance)
  - qweneditutils TextEncode + ConfigPreparer

Prompt format (fal Multiple-Angles LoRA):
  <sks> front view eye-level shot medium shot
  <sks> right side view eye-level shot close-up
  <sks> back view eye-level shot medium shot
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import shutil
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    fail_result,
    ok_result,
    queue_prompt,
    resolve_meta_out,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import FAMILY_QWEN_ANGLE, ensure_engine

DEFAULT_INSTRUCTION = (
    "Describe the key features of the input image (color, shape, size, texture, objects, background), "
    "then explain how the user's text instruction should alter or modify the image. "
    "Generate a new image that meets the user's requirements while maintaining consistency "
    "with the original input where appropriate."
)

# Sheet presets → <sks> prompts (azimuth, elevation, distance)
SHEET_ANGLE_PROMPTS: dict[str, str] = {
    # head (close-up)
    "head_front": "<sks> front view eye-level shot close-up",
    "head_qf": "<sks> front-right quarter view eye-level shot close-up",
    "head_side": "<sks> right side view eye-level shot close-up",
    "head_back": "<sks> back view eye-level shot close-up",
    # body (medium / full-ish)
    "body_front": "<sks> front view eye-level shot medium shot",
    "body_qf": "<sks> front-right quarter view eye-level shot medium shot",
    "body_side": "<sks> right side view eye-level shot medium shot",
    "body_back": "<sks> back view eye-level shot medium shot",
}

GGUF_DEFAULT = r"QwenImage\qwen-image-edit-2511-Q4_K_M.gguf"
LORA_LIGHTNING = r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
LORA_ANGLES = r"QwenImage\qwen-image-edit-2511-multiple-angles-lora.safetensors"
VAE_NAME = "qwen_image_vae.safetensors"
CLIP_NAME = "qwen_2.5_vl_7b_fp8_scaled.safetensors"


def build_angle_prompt(view_key: str, extra: str = "") -> str:
    base = SHEET_ANGLE_PROMPTS.get(view_key) or view_key
    if not base.startswith("<sks>"):
        base = f"<sks> {base}"
    extra = (extra or "").strip()
    if extra:
        return f"{base}, {extra}"
    return base


def _build_api(
    *,
    image_name: str,
    prompt: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    lightning_strength: float,
    angles_strength: float,
    max_edge: int,
    filename_prefix: str,
) -> dict[str, Any]:
    """Minimal single-branch API graph matching local MultiGen stack."""
    return {
        "1": {
            "class_type": "LoaderGGUF",
            "inputs": {"gguf_name": GGUF_DEFAULT},
        },
        "2": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 3.1},
        },
        "3": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["2", 0], "strength": 1.0},
        },
        "4": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": LORA_LIGHTNING,
                "strength_model": float(lightning_strength),
            },
        },
        "5": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["4", 0],
                "lora_name": LORA_ANGLES,
                "strength_model": float(angles_strength),
            },
        },
        "6": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE_NAME},
        },
        "7": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": CLIP_NAME,
                "type": "qwen_image",
                "device": "default",
            },
        },
        "8": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "9": {
            "class_type": "QwenEditAdaptiveLongestEdge",
            "inputs": {"image": ["8", 0], "max_size": int(max_edge)},
        },
        "10": {
            "class_type": "QwenEditConfigPreparer",
            "inputs": {
                "image": ["8", 0],
                "ref_longest_edge": ["9", 0],
                "to_ref": True,
                "ref_main_image": True,
                "ref_crop": "pad",
                "ref_upscale": "lanczos",
                "to_vl": True,
                "vl_resize": True,
                "vl_target_size": 384,
                "vl_crop": "center",
                "vl_upscale": "lanczos",
            },
        },
        "11": {
            "class_type": "TextEncodeQwenImageEditPlusCustom_lrzjason",
            "inputs": {
                "clip": ["7", 0],
                "vae": ["6", 0],
                "configs": ["10", 0],
                "prompt": prompt,
                "return_full_refs_cond": True,
                "instruction": DEFAULT_INSTRUCTION,
            },
        },
        "12": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["11", 0]},
        },
        "13": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["5", 0],
                "positive": ["11", 0],
                "negative": ["12", 0],
                "latent_image": ["11", 1],
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(cfg),
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": float(denoise),
            },
        },
        "14": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["13", 0], "vae": ["6", 0]},
        },
        "15": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["14", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


def generate_qwen_angle(
    input_image_path: str,
    view_key: str,
    *,
    output_filename: str | None = None,
    seed: int | None = None,
    extra_prompt: str = "",
    steps: int = 4,
    cfg: float = 1.0,
    denoise: float = 1.0,
    lightning_strength: float = 1.0,
    angles_strength: float = 0.9,
    max_edge: int = 1024,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
) -> dict:
    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    eng = ensure_engine(
        FAMILY_QWEN_ANGLE, server_address, caller="generate_qwen_angle"
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    prompt = build_angle_prompt(view_key, extra_prompt)
    seed = seed if seed is not None else random.randint(1, 2**31 - 1)

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"qwen_angle_{view_key}_{seed}.png"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    temp_name = f"temp_qwen_angle_{os.getpid()}.png"
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_name))

    api = _build_api(
        image_name=temp_name,
        prompt=prompt,
        seed=seed,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
        lightning_strength=lightning_strength,
        angles_strength=angles_strength,
        max_edge=max_edge,
        filename_prefix=f"Qwen_angle_{view_key}",
    )

    print(f"Qwen angle edit view={view_key} prompt={prompt!r} seed={seed}")
    try:
        prompt_id = queue_prompt(server_address, api)
        print(f"Queued prompt_id={prompt_id}")
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=seed)

    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
    except Exception as e:
        return fail_result(
            error="HISTORY_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    try:
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
    except Exception as e:
        return fail_result(
            error="COMFY_NO_OUTPUT", message=str(e), seed=seed, prompt_id=prompt_id
        )

    print(f"Downloading {image_filename}")
    try:
        download_image(
            server_address, image_filename, image_subfolder, image_type, output_filename
        )
    except Exception as e:
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": "qwen_image_edit_2511_multiview",
        "view_key": view_key,
        "prompt": prompt,
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
        "lightning_strength": lightning_strength,
        "angles_strength": angles_strength,
        "source_image": os.path.abspath(input_image_path),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "gguf": GGUF_DEFAULT,
        "lora_lightning": LORA_LIGHTNING,
        "lora_angles": LORA_ANGLES,
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")

    print(f"OK {output_filename}")
    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Qwen-Image-Edit-2511 multi-angle edit")
    p.add_argument("--input", "-i", required=True)
    p.add_argument(
        "--view",
        "-v",
        required=True,
        help="head_front|head_qf|head_side|head_back|body_front|body_qf|body_side|body_back or raw <sks> phrase",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--extra", default="", help="Extra prompt after <sks> phrase")
    p.add_argument("--steps", type=int, default=4)
    p.add_argument("--angles-strength", type=float, default=0.9)
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args(argv)

    r = generate_qwen_angle(
        args.input,
        args.view,
        output_filename=args.output,
        seed=args.seed,
        extra_prompt=args.extra,
        steps=args.steps,
        angles_strength=args.angles_strength,
        timeout_sec=args.timeout,
    )
    return 0 if r.get("ok") else 30


if __name__ == "__main__":
    raise SystemExit(main())
