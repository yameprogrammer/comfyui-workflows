#!/usr/bin/env python3
"""
Qwen-Image multi-angle via validated workflow:

  멀티앵글생성-qwen-image.json
  → presets/qwen_multiangle_image.api.json (subgraph flattened)

Default: workflow_api_runner port patch only.
Legacy homemade mini graph: AGENT_QWEN_ANGLE_BACKEND=legacy_mini / --legacy-mini.

Role:
  - Character head/body turns (`character_qwen_turns`, expand engine=qwen)
  - Soft tone remix → Moody I2I; general instruction edit → generate_qwen_edit
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
from lib.workflow_api_runner import run_workflow_api

DEFAULT_PRESET = "qwen_multiangle_image"

# Sheet presets → camera angles for QwenMultiangleCameraNode
# (node emits <sks> {h_dir} {v_dir} {distance})
VIEW_TO_ANGLES: dict[str, tuple[int, int, float]] = {
    "head_front": (0, 0, 8.0),
    "head_qf": (45, 0, 8.0),
    "head_side": (90, 0, 8.0),
    "head_back": (180, 0, 8.0),
    "body_front": (0, 0, 5.0),
    "body_qf": (45, 0, 5.0),
    "body_side": (90, 0, 5.0),
    "body_back": (180, 0, 5.0),
    # aliases
    "front": (0, 0, 5.0),
    "side": (90, 0, 5.0),
    "back": (180, 0, 5.0),
    "qf": (45, 0, 5.0),
}

# Kept for meta / legacy mini
SHEET_ANGLE_PROMPTS: dict[str, str] = {
    "head_front": "<sks> front view eye-level shot close-up",
    "head_qf": "<sks> front-right quarter view eye-level shot close-up",
    "head_side": "<sks> right side view eye-level shot close-up",
    "head_back": "<sks> back view eye-level shot close-up",
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

DEFAULT_INSTRUCTION = (
    "Describe the key features of the input image (color, shape, size, texture, objects, background), "
    "then explain how the user's text instruction should alter or modify the image. "
    "Generate a new image that meets the user's requirements while maintaining consistency "
    "with the original input where appropriate."
)


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_QWEN_ANGLE_BACKEND")
        or "workflow_api"
    ).strip().lower()
    if raw in ("legacy", "legacy_mini", "mini", "homemade"):
        return "legacy_mini"
    return "workflow_api"


def build_angle_prompt(view_key: str, extra: str = "") -> str:
    base = SHEET_ANGLE_PROMPTS.get(view_key) or view_key
    if not base.startswith("<sks>"):
        base = f"<sks> {base}"
    extra = (extra or "").strip()
    if extra:
        return f"{base}, {extra}"
    return base


def view_to_angles(view_key: str) -> tuple[int, int, float] | None:
    return VIEW_TO_ANGLES.get(view_key)


def _build_api_legacy(
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
    """Emergency mini graph (old agent stack)."""
    return {
        "1": {"class_type": "LoaderGGUF", "inputs": {"gguf_name": GGUF_DEFAULT}},
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
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "7": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": CLIP_NAME,
                "type": "qwen_image",
                "device": "default",
            },
        },
        "8": {"class_type": "LoadImage", "inputs": {"image": image_name}},
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
    angles_strength: float = 1.0,
    max_edge: int = 1024,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    preset: str | None = None,
    backend: str | None = None,
    horizontal_angle: int | None = None,
    vertical_angle: int | None = None,
    zoom: float | None = None,
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

    be = _resolve_backend(backend)
    if be == "legacy_mini":
        return _generate_legacy(
            input_image_path=input_image_path,
            view_key=view_key,
            prompt=prompt,
            output_filename=output_filename,
            seed=seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            lightning_strength=lightning_strength,
            angles_strength=angles_strength,
            max_edge=max_edge,
            server_address=server_address,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
        )

    # Resolve camera angles from view_key unless explicit
    ang = view_to_angles(view_key)
    h = horizontal_angle if horizontal_angle is not None else (ang[0] if ang else 0)
    v = vertical_angle if vertical_angle is not None else (ang[1] if ang else 0)
    z = zoom if zoom is not None else (ang[2] if ang else 5.0)

    ports: dict[str, Any] = {
        "input_image": os.path.abspath(input_image_path),
        "horizontal_angle": int(h),
        "vertical_angle": int(v),
        "zoom": float(z),
        "steps": int(steps),
        "cfg": float(cfg),
        "denoise": float(denoise),
        "lightning_strength": float(lightning_strength),
        "angles_strength": float(angles_strength),
        "filename_prefix": f"Qwen_angle_{view_key}",
    }
    # Raw <sks> view or extra text → set prompt string (overrides multiangle link)
    if not ang or (extra_prompt or "").strip() or view_key.startswith("<sks>"):
        ports["positive"] = prompt

    preset_name = preset or DEFAULT_PRESET
    print(
        f"Qwen angle workflow_api preset={preset_name} view={view_key} "
        f"h={h} v={v} zoom={z} prompt={prompt!r} seed={seed}"
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

    out_abs = r.get("output_path") or os.path.abspath(output_filename)
    base_meta = r.get("meta") or {}
    meta = {
        "mode": "qwen_multiangle_image",
        "engine": "workflow_api",
        "backend": "workflow_api",
        "workflow": preset_name,
        "workflow_api": base_meta.get("workflow_api"),
        "source_workflow": "멀티앵글생성-qwen-image",
        "view_key": view_key,
        "prompt": prompt,
        "horizontal_angle": int(h),
        "vertical_angle": int(v),
        "zoom": float(z),
        "seed": r.get("seed"),
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
        "lightning_strength": lightning_strength,
        "angles_strength": angles_strength,
        "source_image": os.path.abspath(input_image_path),
        "output_path": out_abs,
        "comfy_prompt_id": r.get("prompt_id"),
        "created_at": utc_now_iso(),
        "gguf": GGUF_DEFAULT,
        "lora_lightning": LORA_LIGHTNING,
        "lora_angles": LORA_ANGLES,
        "ports_applied": base_meta.get("ports_applied"),
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")

    print(f"OK {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=r.get("seed"),
        prompt_id=r.get("prompt_id"),
        meta_path=meta_path,
        meta=meta,
        preset=preset_name,
        workflow_api=base_meta.get("workflow_api"),
    )


def _generate_legacy(
    *,
    input_image_path: str,
    view_key: str,
    prompt: str,
    output_filename: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    lightning_strength: float,
    angles_strength: float,
    max_edge: int,
    server_address: str,
    timeout_sec: int,
    meta_out: str | None,
) -> dict:
    print("[WARN] legacy_mini qwen angle graph — prefer qwen_multiangle_image preset")
    temp_name = f"temp_qwen_angle_{os.getpid()}.png"
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_name))
    api = _build_api_legacy(
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
    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=seed)
    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
        image_filename, image_subfolder, image_type = extract_first_image(history_entry)
        download_image(
            server_address, image_filename, image_subfolder, image_type, output_filename
        )
    except Exception as e:
        return fail_result(
            error="EXEC_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )
    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": "qwen_image_edit_2511_multiview",
        "backend": "legacy_mini",
        "view_key": view_key,
        "prompt": prompt,
        "seed": seed,
        "source_image": os.path.abspath(input_image_path),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
    }
    if meta_path:
        write_meta(meta_path, meta)
    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Qwen multi-angle via 멀티앵글생성-qwen-image API preset"
    )
    p.add_argument("--input", "-i", required=True)
    p.add_argument(
        "--view",
        "-v",
        required=True,
        help="head_front|…|body_back or raw <sks> phrase",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--extra", default="", help="Extra prompt after angle phrase")
    p.add_argument("--steps", type=int, default=4)
    p.add_argument("--angles-strength", type=float, default=1.0)
    p.add_argument("--horizontal-angle", type=int, default=None)
    p.add_argument("--vertical-angle", type=int, default=None)
    p.add_argument("--zoom", type=float, default=None)
    p.add_argument("--preset", default=None)
    p.add_argument("--legacy-mini", action="store_true")
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
        preset=args.preset,
        backend="legacy_mini" if args.legacy_mini else "workflow_api",
        horizontal_angle=args.horizontal_angle,
        vertical_angle=args.vertical_angle,
        zoom=args.zoom,
    )
    return 0 if r.get("ok") else 30


if __name__ == "__main__":
    raise SystemExit(main())
