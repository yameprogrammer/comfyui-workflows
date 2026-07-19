#!/usr/bin/env python3
"""
Qwen instruction image edit via official workflow:

  image_qwen_image_edit_2509.json
  → presets/qwen_edit_2509.api.json (subgraph Image Edit Qwen 2509 flattened)

Default: workflow_api (fp8 UNet + turbo Lightning switch).
Legacy homemade graphs: --backend gguf_2509|gguf_2511|fp8_2509_legacy
  or AGENT_QWEN_EDIT_BACKEND=legacy_*

Role coexistence:
  - Moody I2I → soft denoise
  - generate_qwen_angle → multi-view <sks>
  - This CLI → natural-language instruction edit
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import copy
import json
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
from lib.workflow_api_runner import (
    apply_ports,
    resolve_preset,
    run_workflow_api,
)

DEFAULT_PRESET = "qwen_edit_2511"

# Official template structure + GGUF (agent: avoid ~20GB fp8 UNETLoader)
GGUF_2509_Q5 = r"QwenImage\Qwen-Image-Edit-2509-Q5_K_M.gguf"
GGUF_2511_Q4 = r"QwenImage\qwen-image-edit-2511-Q4_K_M.gguf"
GGUF_2511_Q2 = r"QwenImage\qwen-image-edit-2511-Q2_K.gguf"
LORA_LIGHTNING = (
    r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
)
VAE_NAME = "qwen_image_vae.safetensors"
CLIP_NAME = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
# Deprecated heavy path (not used in default preset)
UNET_FP8_2509 = r"QwenImage\qwen_image_edit_2509_fp8_e4m3fn.safetensors"

DEFAULT_NEGATIVE = ""
IDENTITY_SUFFIX = (
    "Keep the same person identity, face structure, wardrobe, camera framing, "
    "and photoreal look where the instruction does not ask to change them."
)

# workflow_api = official template; others = legacy mini inject
BACKENDS = (
    "workflow_api",
    "gguf_2509",
    "gguf_2511",
    "fp8_2509",
)


def _resolve_backend(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("AGENT_QWEN_EDIT_BACKEND")
        or "workflow_api"
    ).strip().lower()
    # Official template path (default). Old mini names map here with a note.
    if raw in (
        "workflow_api",
        "official",
        "2509",
        "image_qwen_image_edit_2509",
        "gguf_2509",  # callers; still use official API graph (fp8 template)
        "fp8_2509",
    ):
        if raw in ("gguf_2509", "fp8_2509"):
            print(
                f"[note] backend={raw!r} → workflow_api "
                f"(image_qwen_image_edit_2509 preset; no homemade mini graph)"
            )
        return "workflow_api"
    if raw in ("gguf_2511", "legacy", "legacy_mini", "mini"):
        print(
            f"[WARN] backend={raw!r} is legacy; forcing workflow_api "
            f"(official 2509 template). For multi-angle use generate_qwen_angle."
        )
        return "workflow_api"
    return "workflow_api"


def _copy_input(src: str, temp_name: str) -> str:
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, temp_name)
    shutil.copy2(src, dest)
    return temp_name


def _inject_multi_ref(
    api: dict[str, Any],
    *,
    image2_name: str | None,
    image3_name: str | None,
) -> dict[str, Any]:
    """Attach optional image2/image3 LoadImage nodes to TextEncode 111/110."""
    api = copy.deepcopy(api)
    if image2_name:
        api["79"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image2_name},
        }
        api["111"]["inputs"]["image2"] = ["79", 0]
        api["110"]["inputs"]["image2"] = ["79", 0]
    if image3_name:
        api["80"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image3_name},
        }
        api["111"]["inputs"]["image3"] = ["80", 0]
        api["110"]["inputs"]["image3"] = ["80", 0]
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
    backend: str = "workflow_api",
    gguf_name: str | None = None,
    lightning: bool = True,
    lightning_strength: float = 1.0,
    steps: int | None = None,
    cfg: float | None = None,
    denoise: float = 1.0,
    shift: float | None = None,
    cfg_norm: float = 1.0,
    max_edge: int = 1024,
    unet_name: str | None = None,
    lora_name: str = LORA_LIGHTNING,
    raw_prompt: bool = False,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    skip_engine_session: bool = False,
    preset: str | None = None,
) -> dict:
    backend = _resolve_backend(backend)
    gguf_name = gguf_name or GGUF_2511_Q4

    if not os.path.isfile(input_image_path):
        return fail_result(error="SOURCE_MISSING", message=input_image_path)
    for p, label in (
        (input_image2_path, "image2"),
        (input_image3_path, "image3"),
    ):
        if p and not os.path.isfile(p):
            return fail_result(error="SOURCE_MISSING", message=f"{label}: {p}")

    family = FAMILY_QWEN_EDIT
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

    return _generate_workflow_api(
        input_image_path=input_image_path,
        input_image2_path=input_image2_path,
        input_image3_path=input_image3_path,
        prompt=prompt,
        negative_text=negative_text,
        output_filename=output_filename,
        seed=seed,
        lightning=lightning,
        lightning_strength=lightning_strength,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
        gguf_name=gguf_name,
        lora_name=lora_name,
        server_address=server_address,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        preset=preset or DEFAULT_PRESET,
    )


def _generate_workflow_api(
    *,
    input_image_path: str,
    input_image2_path: str | None,
    input_image3_path: str | None,
    prompt: str,
    negative_text: str,
    output_filename: str,
    seed: int,
    lightning: bool,
    lightning_strength: float,
    steps: int,
    cfg: float,
    denoise: float,
    gguf_name: str,
    lora_name: str,
    server_address: str,
    timeout_sec: float,
    meta_out: str | None,
    preset: str,
) -> dict:
    ports: dict[str, Any] = {
        "input_image": os.path.abspath(input_image_path),
        "positive": prompt,
        "enable_turbo": bool(lightning),
        "denoise": float(denoise),
        "lightning_strength": float(lightning_strength),
        "gguf_name": gguf_name,
        "lora_name": lora_name,
        "filename_prefix": f"QwenEdit_2509_{seed}",
    }
    # When turbo off, quality primitives already 20/4; allow override via steps/cfg ports
    if lightning:
        ports["steps_turbo"] = int(steps)
        ports["cfg_turbo"] = float(cfg)
    else:
        ports["steps_quality"] = int(steps)
        ports["cfg_quality"] = float(cfg)

    multi = bool(input_image2_path or input_image3_path)
    print(
        f"Qwen-Edit workflow_api preset={preset} turbo={lightning} "
        f"gguf={gguf_name} steps={steps} cfg={cfg} denoise={denoise} seed={seed}"
    )
    print("  source_wf=image_qwen_image_edit_2509 (LoaderGGUF, not fp8 UNET)")
    print(f"  image1={input_image_path}")
    if input_image2_path:
        print(f"  image2={input_image2_path}")
    if input_image3_path:
        print(f"  image3={input_image3_path}")
    print(f"  prompt={prompt[:200]!r}")

    if not multi:
        r = run_workflow_api(
            preset,
            ports=ports,
            output_path=output_filename,
            meta_out=None,
            server_address=server_address,
            timeout_sec=timeout_sec,
            seed=seed,
        )
        if not r.get("ok"):
            return r
        return _ok_meta(
            r=r,
            prompt=prompt,
            negative_text=negative_text,
            seed=r.get("seed") if r.get("seed") is not None else seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            lightning=lightning,
            lightning_strength=lightning_strength,
            weight_label=gguf_name,
            lora_name=lora_name,
            input_image_path=input_image_path,
            input_image2_path=None,
            input_image3_path=None,
            output_filename=r.get("output_path") or output_filename,
            meta_out=meta_out,
            preset=preset,
            backend="workflow_api",
        )

    # multi-ref: port patch + inject LoadImage for image2/3
    try:
        api_path, ports_path = resolve_preset(preset)
    except FileNotFoundError as e:
        return fail_result(error="PRESET_MISSING", message=str(e))

    with open(api_path, "r", encoding="utf-8") as f:
        api = json.load(f)
    ports_spec = {"ports": {}, "defaults": {}}
    if ports_path and os.path.isfile(ports_path):
        with open(ports_path, "r", encoding="utf-8") as f:
            ports_spec = json.load(f)
    values = dict(ports)
    values["seed"] = int(seed)
    try:
        api = apply_ports(copy.deepcopy(api), ports_spec, values)
        img2 = (
            _copy_input(
                input_image2_path, f"temp_qwen_edit2_{os.getpid()}.png"
            )
            if input_image2_path
            else None
        )
        img3 = (
            _copy_input(
                input_image3_path, f"temp_qwen_edit3_{os.getpid()}.png"
            )
            if input_image3_path
            else None
        )
        api = _inject_multi_ref(api, image2_name=img2, image3_name=img3)
        prompt_id = queue_prompt(server_address, api)
        history = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
        fn, sub, itype = extract_first_image(history)
        download_image(server_address, fn, sub, itype, output_filename)
    except Exception as e:
        return fail_result(error="EXEC_FAILED", message=str(e), seed=seed)

    return _ok_meta(
        r={
            "ok": True,
            "output_path": os.path.abspath(output_filename),
            "seed": seed,
            "prompt_id": prompt_id,
            "meta": {"workflow_api": os.path.abspath(api_path)},
        },
        prompt=prompt,
        negative_text=negative_text,
        seed=seed,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
        lightning=lightning,
        lightning_strength=lightning_strength,
        weight_label=gguf_name,
        lora_name=lora_name,
        input_image_path=input_image_path,
        input_image2_path=input_image2_path,
        input_image3_path=input_image3_path,
        output_filename=output_filename,
        meta_out=meta_out,
        preset=preset,
        backend="workflow_api",
    )


def _ok_meta(
    *,
    r: dict,
    prompt: str,
    negative_text: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    lightning: bool,
    lightning_strength: float,
    weight_label: str,
    lora_name: str,
    input_image_path: str,
    input_image2_path: str | None,
    input_image3_path: str | None,
    output_filename: str,
    meta_out: str | None,
    preset: str,
    backend: str,
) -> dict:
    out_abs = r.get("output_path") or os.path.abspath(output_filename)
    base = r.get("meta") or {}
    meta = {
        "mode": "qwen_edit_2511",
        "engine": "workflow_api",
        "backend": backend,
        "workflow": preset,
        "workflow_api": base.get("workflow_api"),
        "source_workflow": "image_qwen_image_edit_2509",
        "model_loader": "LoaderGGUF",
        "prompt": prompt,
        "negative": negative_text or "",
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
        "lightning": lightning,
        "lightning_strength": lightning_strength if lightning else 0.0,
        "enable_turbo": lightning,
        "weight": weight_label,
        "gguf": weight_label,
        "lora_lightning": lora_name if lightning else None,
        "clip": CLIP_NAME,
        "vae": VAE_NAME,
        "source_image": os.path.abspath(input_image_path),
        "source_image2": (
            os.path.abspath(input_image2_path) if input_image2_path else None
        ),
        "source_image3": (
            os.path.abspath(input_image3_path) if input_image3_path else None
        ),
        "output_path": out_abs,
        "comfy_prompt_id": r.get("prompt_id"),
        "created_at": utc_now_iso(),
        "ports_applied": base.get("ports_applied"),
    }
    meta_path = resolve_meta_out(out_abs, meta_out)
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")
    print(f"OK {out_abs}")
    return ok_result(
        output_path=out_abs,
        seed=seed,
        prompt_id=r.get("prompt_id"),
        meta_path=meta_path,
        meta=meta,
        preset=preset,
        workflow_api=base.get("workflow_api"),
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Qwen instruction edit via image_qwen_image_edit_2509 API preset. "
            "Default: workflow_api (fp8 + turbo switch)."
        )
    )
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--input2", "-i2", default=None)
    p.add_argument("--input3", "-i3", default=None)
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument("--negative", "-n", default=DEFAULT_NEGATIVE)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--backend",
        choices=list(BACKENDS),
        default="workflow_api",
        help="workflow_api=official 2509 (default); gguf_*/fp8_2509=legacy mini",
    )
    p.add_argument("--preset", default=None, help=f"default {DEFAULT_PRESET}")
    p.add_argument("--gguf", default=None)
    p.add_argument(
        "--no-lightning",
        action="store_true",
        help="Quality path: enable_turbo=false (steps 20 / cfg 4)",
    )
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--denoise", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--meta-out", default=None)
    p.add_argument(
        "--raw-prompt",
        action="store_true",
        help="Do not append identity lock suffix",
    )
    args = p.parse_args(argv)

    r = generate_qwen_edit(
        args.input,
        args.prompt,
        input_image2_path=args.input2,
        input_image3_path=args.input3,
        negative_text=args.negative,
        output_filename=args.output,
        seed=args.seed,
        backend=args.backend,
        gguf_name=args.gguf,
        lightning=not args.no_lightning,
        steps=args.steps,
        cfg=args.cfg,
        denoise=args.denoise,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        raw_prompt=args.raw_prompt,
        preset=args.preset,
    )
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
