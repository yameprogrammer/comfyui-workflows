#!/usr/bin/env python3
"""
Qwen instruction image edit (semantic replace/remove).

Role coexistence (do not collapse):
  - Moody I2I (`generate_moody_i2i`)           → soft denoise remix
  - Qwen angle (`generate_qwen_angle`)         → multi-view turns + Angles LoRA + <sks>
  - **This CLI** (`generate_qwen_edit`)        → instruction edit

Default backend: **gguf_2509**
  QuantStack Qwen-Image-Edit-2509-Q5_K_M.gguf + native TextEncodeQwenImageEditPlus
  (same encode path as Comfy template image_qwen_image_edit_2509, GGUF instead of 19GB fp8)

Lightning policy (factory default):
  - **ON by default** (4 step / CFG 1) — first pass, speed
  - If result fails local intent (e.g. whole cup gone): re-run with
    ``--no-lightning --steps 20 --cfg 4``

Other backends:
  gguf_2511  — multi-angle GGUF stack (fallback; weaker as pure editor)
  fp8_2509   — heavy official fp8 UNet (VRAM thrash risk on 24GB)

  python scripts/generate_qwen_edit.py -i keyframe.png \\
    -p "remove the black straw from the iced coffee, keep the glass and person"
  # quality escalate:
  python scripts/generate_qwen_edit.py --no-lightning --steps 20 --cfg 4 -i ... -p "..."
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
from lib.comfy_engine_session import (
    FAMILY_QWEN_ANGLE,
    FAMILY_QWEN_EDIT,
    ensure_engine,
)

# --- 2509 instruction-edit GGUF (QuantStack) ---
GGUF_2509_Q5 = r"QwenImage\Qwen-Image-Edit-2509-Q5_K_M.gguf"

# --- 2511 multi-angle stack weights (fallback edit / shared with angle CLI) ---
GGUF_2511_Q4 = r"QwenImage\qwen-image-edit-2511-Q4_K_M.gguf"
GGUF_2511_Q2 = r"QwenImage\qwen-image-edit-2511-Q2_K.gguf"

# Template often pairs 2509 UNet with 2511 Lightning; optional speed LoRA
LORA_LIGHTNING = (
    r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
)
VAE_NAME = "qwen_image_vae.safetensors"
CLIP_NAME = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
UNET_FP8_2509 = r"QwenImage\qwen_image_edit_2509_fp8_e4m3fn.safetensors"

DEFAULT_INSTRUCTION = (
    "Describe the key features of the input image (color, shape, size, texture, objects, background), "
    "then explain how the user's text instruction should alter or modify the image. "
    "Generate a new image that meets the user's requirements while maintaining consistency "
    "with the original input where appropriate."
)

DEFAULT_NEGATIVE = ""
IDENTITY_SUFFIX = (
    "Keep the same person identity, face structure, wardrobe, camera framing, "
    "and photoreal look where the instruction does not ask to change them."
)

BACKENDS = ("gguf_2509", "gguf_2511", "fp8_2509")


def _copy_input(src: str, temp_name: str) -> str:
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, temp_name)
    shutil.copy2(src, dest)
    return temp_name


def build_api_gguf_2509(
    *,
    image_name: str,
    image2_name: str | None,
    image3_name: str | None,
    prompt: str,
    negative: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    shift: float,
    cfg_norm: float,
    lightning: bool,
    lightning_strength: float,
    gguf_name: str,
    lora_name: str,
    filename_prefix: str,
) -> dict[str, Any]:
    """2509 instruction-edit graph with GGUF UNet (template encode path)."""
    api: dict[str, Any] = {
        "1": {
            "class_type": "LoaderGGUF",
            "inputs": {"gguf_name": gguf_name},
        },
        "2": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": float(shift)},
        },
        "3": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["2", 0], "strength": float(cfg_norm)},
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
            "class_type": "FluxKontextImageScale",
            "inputs": {"image": ["8", 0]},
        },
    }

    model_src: list[Any] = ["3", 0]
    if lightning:
        api["4"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": lora_name,
                "strength_model": float(lightning_strength),
            },
        }
        model_src = ["4", 0]

    img1_ref: list[Any] = ["9", 0]
    img2_ref: list[Any] | None = None
    img3_ref: list[Any] | None = None
    if image2_name:
        api["20"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image2_name},
        }
        img2_ref = ["20", 0]
    if image3_name:
        api["21"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image3_name},
        }
        img3_ref = ["21", 0]

    def _encode_inputs(text: str) -> dict[str, Any]:
        enc: dict[str, Any] = {
            "clip": ["7", 0],
            "prompt": text,
            "vae": ["6", 0],
            "image1": img1_ref,
        }
        if img2_ref is not None:
            enc["image2"] = img2_ref
        if img3_ref is not None:
            enc["image3"] = img3_ref
        return enc

    api["10"] = {
        "class_type": "TextEncodeQwenImageEditPlus",
        "inputs": _encode_inputs(prompt),
    }
    api["11"] = {
        "class_type": "TextEncodeQwenImageEditPlus",
        "inputs": _encode_inputs(negative or ""),
    }
    api["12"] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": ["9", 0], "vae": ["6", 0]},
    }
    api["13"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_src,
            "positive": ["10", 0],
            "negative": ["11", 0],
            "latent_image": ["12", 0],
            "seed": int(seed),
            "steps": int(steps),
            "cfg": float(cfg),
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": float(denoise),
        },
    }
    api["14"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["13", 0], "vae": ["6", 0]},
    }
    api["15"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["14", 0],
            "filename_prefix": filename_prefix,
        },
    }
    return api


def build_api_gguf_2511(
    *,
    image_name: str,
    prompt: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    shift: float,
    cfg_norm: float,
    lightning: bool,
    lightning_strength: float,
    gguf_name: str,
    lora_name: str,
    max_edge: int,
    filename_prefix: str,
) -> dict[str, Any]:
    """Fallback: multi-angle encode stack without Angles LoRA."""
    api: dict[str, Any] = {
        "1": {
            "class_type": "LoaderGGUF",
            "inputs": {"gguf_name": gguf_name},
        },
        "2": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": float(shift)},
        },
        "3": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["2", 0], "strength": float(cfg_norm)},
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
    }

    model_src: list[Any] = ["3", 0]
    if lightning:
        api["4"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": lora_name,
                "strength_model": float(lightning_strength),
            },
        }
        model_src = ["4", 0]

    api["13"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_src,
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
    }
    api["14"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["13", 0], "vae": ["6", 0]},
    }
    api["15"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["14", 0],
            "filename_prefix": filename_prefix,
        },
    }
    return api


def build_api_fp8_2509(
    *,
    image_name: str,
    image2_name: str | None,
    image3_name: str | None,
    prompt: str,
    negative: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    shift: float,
    cfg_norm: float,
    lightning: bool,
    lightning_strength: float,
    unet_name: str,
    lora_name: str,
    filename_prefix: str,
) -> dict[str, Any]:
    """Heavy Comfy 2509 template path (fp8 UNet)."""
    api: dict[str, Any] = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet_name, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": float(shift)},
        },
        "3": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["2", 0], "strength": float(cfg_norm)},
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
            "class_type": "FluxKontextImageScale",
            "inputs": {"image": ["8", 0]},
        },
    }

    model_src: list[Any] = ["3", 0]
    if lightning:
        api["4"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": lora_name,
                "strength_model": float(lightning_strength),
            },
        }
        model_src = ["4", 0]

    img1_ref: list[Any] = ["9", 0]
    img2_ref: list[Any] | None = None
    img3_ref: list[Any] | None = None
    if image2_name:
        api["20"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image2_name},
        }
        img2_ref = ["20", 0]
    if image3_name:
        api["21"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image3_name},
        }
        img3_ref = ["21", 0]

    def _encode_inputs(text: str) -> dict[str, Any]:
        enc: dict[str, Any] = {
            "clip": ["7", 0],
            "prompt": text,
            "vae": ["6", 0],
            "image1": img1_ref,
        }
        if img2_ref is not None:
            enc["image2"] = img2_ref
        if img3_ref is not None:
            enc["image3"] = img3_ref
        return enc

    api["10"] = {
        "class_type": "TextEncodeQwenImageEditPlus",
        "inputs": _encode_inputs(prompt),
    }
    api["11"] = {
        "class_type": "TextEncodeQwenImageEditPlus",
        "inputs": _encode_inputs(negative or ""),
    }
    api["12"] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": ["9", 0], "vae": ["6", 0]},
    }
    api["13"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_src,
            "positive": ["10", 0],
            "negative": ["11", 0],
            "latent_image": ["12", 0],
            "seed": int(seed),
            "steps": int(steps),
            "cfg": float(cfg),
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": float(denoise),
        },
    }
    api["14"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["13", 0], "vae": ["6", 0]},
    }
    api["15"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["14", 0],
            "filename_prefix": filename_prefix,
        },
    }
    return api


def generate_qwen_edit(
    input_image_path: str,
    prompt_text: str,
    *,
    input_image2_path: str | None = None,
    input_image3_path: str | None = None,
    negative_text: str = DEFAULT_NEGATIVE,
    output_filename: str | None = None,
    seed: int | None = None,
    backend: str = "gguf_2509",
    gguf_name: str | None = None,
    lightning: bool = True,
    lightning_strength: float = 1.0,
    steps: int | None = None,
    cfg: float | None = None,
    denoise: float = 1.0,
    shift: float | None = None,
    cfg_norm: float = 1.0,
    max_edge: int = 1024,
    unet_name: str = UNET_FP8_2509,
    lora_name: str = LORA_LIGHTNING,
    raw_prompt: bool = False,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    skip_engine_session: bool = False,
) -> dict:
    """Instruction edit. Default: 2509 Q5 GGUF + native edit encode."""
    backend = (backend or "gguf_2509").strip().lower()
    if backend not in BACKENDS:
        return fail_result(
            error="BAD_BACKEND",
            message=f"backend must be one of {BACKENDS}, got {backend!r}",
        )

    if gguf_name is None:
        if backend == "gguf_2509":
            gguf_name = GGUF_2509_Q5
        else:
            gguf_name = GGUF_2511_Q4

    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)
    for p, label in (
        (input_image2_path, "image2"),
        (input_image3_path, "image3"),
    ):
        if p and not os.path.isfile(p):
            return fail_result(error="SOURCE_MISSING", message=f"{label}: {p}")

    if backend == "gguf_2511" and (input_image2_path or input_image3_path):
        print(
            "[WARN] gguf_2511 uses single-image MultiGen encode; "
            "image2/image3 ignored (use gguf_2509 or fp8_2509 for multi-ref)"
        )

    family = FAMILY_QWEN_ANGLE if backend == "gguf_2511" else FAMILY_QWEN_EDIT
    if not skip_engine_session:
        eng = ensure_engine(family, server_address, caller="generate_qwen_edit")
        if not eng.get("ok"):
            return fail_result(
                error=eng.get("error") or "ENGINE_SESSION",
                message=eng.get("message") or "comfy engine free/gate failed",
                engine_session=eng,
            )

    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    if steps is None:
        steps = 4 if lightning else 20
    if cfg is None:
        cfg = 1.0 if lightning else 4.0
    if shift is None:
        shift = 3.1 if backend == "gguf_2511" else 3.0

    prompt = (prompt_text or "").strip()
    if not prompt:
        return fail_result(error="PROMPT_EMPTY", message="edit prompt required")
    if not raw_prompt and IDENTITY_SUFFIX.lower() not in prompt.lower():
        prompt = f"{prompt.rstrip('.')}. {IDENTITY_SUFFIX}"

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_images", f"qwen_edit_{seed}.png"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    pid = os.getpid()
    multi_ref = backend in ("gguf_2509", "fp8_2509")
    img1 = _copy_input(input_image_path, f"temp_qwen_edit_{pid}_1.png")
    img2 = (
        _copy_input(input_image2_path, f"temp_qwen_edit_{pid}_2.png")
        if input_image2_path and multi_ref
        else None
    )
    img3 = (
        _copy_input(input_image3_path, f"temp_qwen_edit_{pid}_3.png")
        if input_image3_path and multi_ref
        else None
    )

    prefix = f"QwenEdit_{backend}_{seed}"
    if backend == "gguf_2509":
        api = build_api_gguf_2509(
            image_name=img1,
            image2_name=img2,
            image3_name=img3,
            prompt=prompt,
            negative=negative_text or "",
            seed=seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            shift=float(shift),
            cfg_norm=cfg_norm,
            lightning=lightning,
            lightning_strength=lightning_strength,
            gguf_name=gguf_name,
            lora_name=lora_name,
            filename_prefix=prefix,
        )
        weight_label = gguf_name
    elif backend == "gguf_2511":
        api = build_api_gguf_2511(
            image_name=img1,
            prompt=prompt,
            seed=seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            shift=float(shift),
            cfg_norm=cfg_norm,
            lightning=lightning,
            lightning_strength=lightning_strength,
            gguf_name=gguf_name,
            lora_name=lora_name,
            max_edge=max_edge,
            filename_prefix=prefix,
        )
        weight_label = gguf_name
    else:
        api = build_api_fp8_2509(
            image_name=img1,
            image2_name=img2,
            image3_name=img3,
            prompt=prompt,
            negative=negative_text or "",
            seed=seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            shift=float(shift),
            cfg_norm=cfg_norm,
            lightning=lightning,
            lightning_strength=lightning_strength,
            unet_name=unet_name,
            lora_name=lora_name,
            filename_prefix=prefix,
        )
        weight_label = unet_name

    print(
        f"Qwen-Edit backend={backend} weight={weight_label} "
        f"lightning={lightning} steps={steps} cfg={cfg} denoise={denoise} seed={seed}"
    )
    print(f"  image1={input_image_path}")
    if img2:
        print(f"  image2={input_image2_path}")
    if img3:
        print(f"  image3={input_image3_path}")
    print(f"  prompt={prompt[:200]!r}")
    if backend == "gguf_2509":
        print("  note: 2509 instruction-edit GGUF + TextEncodeQwenImageEditPlus")
    elif backend == "gguf_2511":
        print("  note: 2511 GGUF (angle stack, no Angles LoRA) — fallback")

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
        image_filename, image_subfolder, image_type = extract_first_image(
            history_entry
        )
    except Exception as e:
        return fail_result(
            error="COMFY_NO_OUTPUT", message=str(e), seed=seed, prompt_id=prompt_id
        )

    print(f"Downloading {image_filename}")
    try:
        download_image(
            server_address,
            image_filename,
            image_subfolder,
            image_type,
            output_filename,
        )
    except Exception as e:
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": f"qwen_image_edit_{backend}",
        "engine": "qwen_edit",
        "backend": backend,
        "prompt": prompt,
        "negative": negative_text or "",
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
        "shift": shift,
        "lightning": lightning,
        "lightning_strength": lightning_strength if lightning else 0.0,
        "angles_lora": False,
        "weight": weight_label,
        "gguf": gguf_name if backend.startswith("gguf") else None,
        "unet": unet_name if backend == "fp8_2509" else None,
        "lora_lightning": lora_name if lightning else None,
        "clip": CLIP_NAME,
        "vae": VAE_NAME,
        "max_edge": max_edge if backend == "gguf_2511" else None,
        "source_image": os.path.abspath(input_image_path),
        "source_image2": (
            os.path.abspath(input_image2_path)
            if input_image2_path and multi_ref
            else None
        ),
        "source_image3": (
            os.path.abspath(input_image3_path)
            if input_image3_path and multi_ref
            else None
        ),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "family": family,
        "shares_weights_with": (
            "generate_qwen_angle" if backend == "gguf_2511" else None
        ),
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
    p = argparse.ArgumentParser(
        description=(
            "Qwen instruction edit — default 2509 Q5 GGUF. "
            "Coexists with Moody I2I & generate_qwen_angle."
        )
    )
    p.add_argument("--input", "-i", required=True, help="Primary image")
    p.add_argument(
        "--input2",
        "-i2",
        default=None,
        help="Optional ref (gguf_2509 / fp8_2509 multi-ref)",
    )
    p.add_argument(
        "--input3",
        "-i3",
        default=None,
        help="Optional ref (gguf_2509 / fp8_2509)",
    )
    p.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="Edit instruction in natural language (not <sks> angle syntax)",
    )
    p.add_argument("--negative", "-n", default=DEFAULT_NEGATIVE)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--backend",
        choices=list(BACKENDS),
        default="gguf_2509",
        help="gguf_2509=default Q5 edit; gguf_2511=angle-stack fallback; fp8_2509=heavy",
    )
    p.add_argument(
        "--gguf",
        default=None,
        help=f"Override GGUF path (default 2509: {GGUF_2509_Q5})",
    )
    p.add_argument(
        "--q2",
        action="store_true",
        help="With gguf_2511: use Q2_K GGUF",
    )
    p.add_argument(
        "--lightning",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Lightning 4-step LoRA (default ON — first pass). "
            "If edit overshoots, re-run with --no-lightning --steps 20 --cfg 4"
        ),
    )
    p.add_argument("--lightning-strength", type=float, default=1.0)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--denoise", type=float, default=1.0)
    p.add_argument("--shift", type=float, default=None)
    p.add_argument("--max-edge", type=int, default=1024, help="gguf_2511 only")
    p.add_argument("--unet", default=UNET_FP8_2509, help="fp8_2509 only")
    p.add_argument("--lora", default=LORA_LIGHTNING, help="Lightning LoRA name")
    p.add_argument(
        "--raw-prompt",
        action="store_true",
        help="Do not append identity/framing keep suffix",
    )
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--server", default=DEFAULT_SERVER)
    args = p.parse_args(argv)

    gguf = args.gguf
    if gguf is None and args.backend == "gguf_2511" and args.q2:
        gguf = GGUF_2511_Q2

    r = generate_qwen_edit(
        args.input,
        args.prompt,
        input_image2_path=args.input2,
        input_image3_path=args.input3,
        negative_text=args.negative,
        output_filename=args.output,
        seed=args.seed,
        backend=args.backend,
        gguf_name=gguf,
        lightning=bool(args.lightning),
        lightning_strength=float(args.lightning_strength),
        steps=args.steps,
        cfg=args.cfg,
        denoise=float(args.denoise),
        shift=args.shift,
        max_edge=int(args.max_edge),
        unet_name=args.unet,
        lora_name=args.lora,
        raw_prompt=bool(args.raw_prompt),
        server_address=args.server,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
    )
    return 0 if r.get("ok") else 30


if __name__ == "__main__":
    raise SystemExit(main())
