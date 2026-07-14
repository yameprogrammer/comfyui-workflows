#!/usr/bin/env python3
"""
Generate images with local Ideogram 4 (ComfyUI) — typography / layout specialty.

NOT a replacement for Moody/Krea general T2I. Use for:
  title_card, end_card, menu_board, signage, thumbnail, free JSON caption.

Models (ComfyUI/models/):
  diffusion_models/Ideogram4/ideogram4_fp8_scaled.safetensors
  diffusion_models/Ideogram4/ideogram4_unconditional_fp8_scaled.safetensors
  text_encoders/qwen3vl_8b_fp8_scaled.safetensors
  vae/flux2-vae.safetensors

License: Ideogram Non-Commercial Model Agreement (check before commercial use).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import random
import sys
from typing import Any

from lib.comfy_client import (
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
from lib.ideogram4_prompt import (
    ASPECT_PRESETS,
    QUALITY_PRESETS,
    SLOT_DEFAULTS,
    build_caption,
    caption_to_prompt_string,
    resolve_size,
)

# Paths as exposed by this machine's ComfyUI object_info
UNET_COND = r"Ideogram4\ideogram4_fp8_scaled.safetensors"
UNET_UNCOND = r"Ideogram4\ideogram4_unconditional_fp8_scaled.safetensors"
CLIP_NAME = "qwen3vl_8b_fp8_scaled.safetensors"
VAE_NAME = "flux2-vae.safetensors"

COMFY_MODELS = os.environ.get(
    "COMFYUI_MODELS",
    r"F:\ComfyUI_windows_portable\ComfyUI\models",
)


def _model_paths() -> dict[str, str]:
    return {
        "unet_cond": os.path.join(COMFY_MODELS, "diffusion_models", "Ideogram4", "ideogram4_fp8_scaled.safetensors"),
        "unet_uncond": os.path.join(
            COMFY_MODELS, "diffusion_models", "Ideogram4", "ideogram4_unconditional_fp8_scaled.safetensors"
        ),
        "clip": os.path.join(COMFY_MODELS, "text_encoders", CLIP_NAME),
        "vae": os.path.join(COMFY_MODELS, "vae", VAE_NAME),
    }


def check_models() -> dict[str, Any]:
    paths = _model_paths()
    missing = [k for k, p in paths.items() if not os.path.isfile(p)]
    sizes = {k: os.path.getsize(p) if os.path.isfile(p) else 0 for k, p in paths.items()}
    ok = not missing
    # qwen3vl_8b is ~8GB; reject partial downloads under 1GB
    if ok and sizes.get("clip", 0) < 1_000_000_000:
        ok = False
        missing.append("clip_incomplete")
    return {"ok": ok, "missing": missing, "paths": paths, "sizes": sizes}


def _build_api(
    *,
    prompt_text: str,
    width: int,
    height: int,
    seed: int,
    steps: int,
    mu: float,
    std: float,
    cfg: float,
    filename_prefix: str,
    unet_cond: str = UNET_COND,
    unet_uncond: str = UNET_UNCOND,
    clip_name: str = CLIP_NAME,
    vae_name: str = VAE_NAME,
) -> dict[str, Any]:
    """API graph: DualModelGuider + Ideogram4Scheduler + SamplerCustomAdvanced."""
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet_cond, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet_uncond, "weight_dtype": "default"},
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": clip_name,
                "type": "ideogram4",
                "device": "default",
            },
        },
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["3", 0], "text": prompt_text},
        },
        "6": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["5", 0]},
        },
        "7": {
            "class_type": "EmptyFlux2LatentImage",
            "inputs": {
                "width": int(width),
                "height": int(height),
                "batch_size": 1,
            },
        },
        "8": {
            "class_type": "DualModelGuider",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "model_negative": ["2", 0],
                "negative": ["6", 0],
                "cfg": float(cfg),
            },
        },
        "9": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": int(seed)},
        },
        "10": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler"},
        },
        "11": {
            "class_type": "Ideogram4Scheduler",
            "inputs": {
                "steps": int(steps),
                "width": int(width),
                "height": int(height),
                "mu": float(mu),
                "std": float(std),
            },
        },
        "12": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["9", 0],
                "guider": ["8", 0],
                "sampler": ["10", 0],
                "sigmas": ["11", 0],
                "latent_image": ["7", 0],
            },
        },
        "13": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["12", 0], "vae": ["4", 0]},
        },
        "14": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["13", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


def generate_ideogram4(
    *,
    prompt: str | None = None,
    slot: str = "free",
    text: str = "",
    subtitle: str = "",
    scene: str = "",
    raw_json: str | None = None,
    aspect: str = "9:16",
    width: int | None = None,
    height: int | None = None,
    profile: str = "default",
    steps: int | None = None,
    mu: float | None = None,
    std: float | None = None,
    cfg: float | None = None,
    seed: int | None = None,
    color_palette: list[str] | None = None,
    output_filename: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 900,
    meta_out: str | None = None,
    dry_run: bool = False,
) -> dict:
    chk = check_models()
    if not chk["ok"]:
        return fail_result(
            error="MISSING_MODELS",
            message=(
                f"Ideogram4 models incomplete: missing={chk['missing']}. "
                "Need Ideogram4 unets, flux2-vae, and qwen3vl_8b_fp8_scaled.safetensors "
                "(~8GB). See docs/ideogram4_typography_tool.md"
            ),
            model_check=chk,
        )

    try:
        w, h = resolve_size(aspect, width, height)
    except ValueError as e:
        return fail_result(error="BAD_ASPECT", message=str(e))

    q = QUALITY_PRESETS.get(profile) or QUALITY_PRESETS["default"]
    steps = int(steps if steps is not None else q["steps"])
    mu = float(mu if mu is not None else q["mu"])
    std = float(std if std is not None else q["std"])
    cfg = float(cfg if cfg is not None else q["cfg"])
    seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))

    if prompt and prompt.strip().startswith("{"):
        # treat as raw JSON caption string
        raw_json = prompt
        prompt = None

    if raw_json or text or slot != "free" or scene:
        try:
            caption = build_caption(
                slot=slot,
                text=text,
                subtitle=subtitle,
                scene=scene or (prompt or ""),
                high_level="" if (text or raw_json) else (prompt or ""),
                color_palette=color_palette,
                width=w,
                height=h,
                raw_json=raw_json,
            )
        except (ValueError, json.JSONDecodeError) as e:
            return fail_result(error="BAD_CAPTION", message=str(e))
        prompt_text = caption_to_prompt_string(caption)
    elif prompt:
        # plain natural language (higher safety-filter risk)
        caption = {"plain_prompt": prompt}
        prompt_text = prompt
    else:
        return fail_result(
            error="EMPTY_PROMPT",
            message="provide --text / --prompt / --json for Ideogram4",
        )

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", f"ideogram4_{seed}.png")
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    prefix = "agent_ideogram4"
    api = _build_api(
        prompt_text=prompt_text,
        width=w,
        height=h,
        seed=seed,
        steps=steps,
        mu=mu,
        std=std,
        cfg=cfg,
        filename_prefix=prefix,
    )

    print(
        f"Ideogram4 slot={slot} profile={profile} {w}x{h} steps={steps} "
        f"cfg={cfg} seed={seed} mu={mu} std={std}"
    )
    print(f"  text={text!r} out={output_filename}")
    if dry_run:
        return ok_result(
            dry_run=True,
            prompt_text=prompt_text,
            width=w,
            height=h,
            seed=seed,
            api_nodes=list(api.keys()),
        )

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

    status = (history_entry.get("status") or {})
    if status.get("status_str") == "error" or status.get("completed") is False:
        msgs = status.get("messages") or []
        return fail_result(
            error="EXECUTION_ERROR",
            message=str(msgs)[:800],
            seed=seed,
            prompt_id=prompt_id,
        )

    try:
        filename, subfolder, media_type = extract_first_image(history_entry)
    except Exception as e:
        outs = history_entry.get("outputs") or {}
        keys = {nid: list(v.keys()) for nid, v in outs.items() if isinstance(v, dict)}
        return fail_result(
            error="COMFY_NO_IMAGE",
            message=f"{e}; outputs={keys}",
            seed=seed,
            prompt_id=prompt_id,
        )

    print(f"Downloading {filename}")
    try:
        download_image(
            server_address, filename, subfolder, media_type, output_filename
        )
    except Exception as e:
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": "ideogram4_t2i",
        "slot": slot,
        "profile": profile,
        "text": text or None,
        "subtitle": subtitle or None,
        "width": w,
        "height": h,
        "aspect": aspect,
        "steps": steps,
        "mu": mu,
        "std": std,
        "cfg": cfg,
        "seed": seed,
        "caption": caption,
        "prompt_text_preview": prompt_text[:2000],
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "license_note": "Ideogram Non-Commercial — verify before commercial use",
        "not_default_t2i": True,
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
        width=w,
        height=h,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Ideogram 4 typography / layout T2I (not general Moody/Krea)"
    )
    p.add_argument(
        "--slot",
        choices=sorted(SLOT_DEFAULTS.keys()),
        default="title_card",
        help="Layout recipe (default title_card)",
    )
    p.add_argument(
        "--text",
        "-t",
        default="",
        help="Exact on-image text (spelling-critical)",
    )
    p.add_argument("--subtitle", default="", help="Secondary line for title/thumbnail")
    p.add_argument(
        "--scene",
        default="",
        help="Extra scene/mood description woven into caption",
    )
    p.add_argument(
        "--prompt",
        "-p",
        default="",
        help="Natural language or full JSON caption string (if starts with '{')",
    )
    p.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Path to full Ideogram JSON caption file",
    )
    p.add_argument(
        "--json-inline",
        default=None,
        help="Full Ideogram JSON caption as a string",
    )
    p.add_argument(
        "--aspect",
        default="9:16",
        help=f"Aspect preset: {', '.join(sorted(ASPECT_PRESETS))} (default 9:16)",
    )
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument(
        "--profile",
        choices=sorted(QUALITY_PRESETS.keys()),
        default="default",
        help="turbo|default|quality step schedule",
    )
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--mu", type=float, default=None)
    p.add_argument("--std", type=float, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--palette",
        default="",
        help="Comma-separated hex colors e.g. #1E73BE,#FDFDFD",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--check-models", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--dump-caption", action="store_true", help="Print caption JSON and exit")
    args = p.parse_args(argv)

    if args.check_models:
        chk = check_models()
        print(json.dumps(chk, indent=2))
        return 0 if chk["ok"] else 11

    raw_json = args.json_inline
    if args.json_path:
        with open(args.json_path, "r", encoding="utf-8") as f:
            raw_json = f.read()

    palette = None
    if args.palette.strip():
        palette = [c.strip() for c in args.palette.split(",") if c.strip()]

    if args.dump_caption:
        w, h = resolve_size(args.aspect, args.width, args.height)
        cap = build_caption(
            slot=args.slot,
            text=args.text,
            subtitle=args.subtitle,
            scene=args.scene or args.prompt,
            color_palette=palette,
            width=w,
            height=h,
            raw_json=raw_json,
        )
        print(caption_to_prompt_string(cap))
        return 0

    r = generate_ideogram4(
        prompt=args.prompt or None,
        slot=args.slot,
        text=args.text,
        subtitle=args.subtitle,
        scene=args.scene,
        raw_json=raw_json,
        aspect=args.aspect,
        width=args.width,
        height=args.height,
        profile=args.profile,
        steps=args.steps,
        mu=args.mu,
        std=args.std,
        cfg=args.cfg,
        seed=args.seed,
        color_palette=palette,
        output_filename=args.output,
        timeout_sec=args.timeout,
        dry_run=args.dry_run,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    if args.dry_run:
        print("--- caption preview ---")
        print(r.get("prompt_text", "")[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
