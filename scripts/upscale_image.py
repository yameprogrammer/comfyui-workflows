#!/usr/bin/env python3
"""Upscale a still image via multi-backend agent stack (ESRGAN styles / RTX VSR / SeedVR2)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER, resolve_meta_out, utc_now_iso, write_meta
from lib.upscale_backends import (
    list_upscale_backend_ids,
    list_upscale_preset_ids,
    list_upscale_style_ids,
    load_upscale_backends,
    resolve_upscale_job,
)
from lib.upscale_runners import (
    build_esrgan_image_prompt,
    build_rtx_image_prompt,
    build_seedvr2_image_prompt,
    copy_input_for_image,
    run_comfy_image,
    run_seedvr2_cli,
)


def upscale_image(
    input_path: str,
    output_path: str | None = None,
    *,
    backend: str | None = None,
    preset: str | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    short_edge: int | None = None,
    style: str | None = None,
    esrgan_model: str | None = None,
    server: str = DEFAULT_SERVER,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
) -> dict:
    if not os.path.isfile(input_path):
        from lib.comfy_client import fail_result

        return fail_result(error="SOURCE_MISSING", message=input_path)

    try:
        job = resolve_upscale_job(
            backend=backend,
            preset=preset,
            format_id=format_id,
            aspect=aspect,
            width=width,
            height=height,
            short_edge=short_edge,
            style=style,
            esrgan_model=esrgan_model,
            source_path=input_path,
        )
    except Exception as e:
        from lib.comfy_client import fail_result

        return fail_result(error="UPSCALE_JOB_RESOLVE", message=str(e))

    be = job["backend"]
    backend_id = job["backend_id"]
    w, h = job["width"], job["height"]
    se = job["short_edge"]
    cfg = job["config"]

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        style_tag = (job.get("style") or "na").replace(" ", "_")
        output_path = f"{base}_{job['preset_id']}_{backend_id}_{style_tag}{ext or '.png'}"

    model = job.get("esrgan_model")
    print(
        f"Upscale image backend={backend_id} style={job.get('style')} "
        f"model={model or '-'} preset={job['preset_id']} "
        f"aspect={job['aspect']} target={w}x{h} short_edge={se}"
    )

    runner = be.get("runner")
    if runner == "comfy_api" and backend_id == "esrgan":
        model = model or be.get("model_name") or "4x-UltraSharp.pth"
        img_name = copy_input_for_image(input_path)
        api = build_esrgan_image_prompt(img_name, model, w, h)
        result = run_comfy_image(api, output_path, server=server, timeout_sec=timeout_sec)
    elif runner == "comfy_api" and backend_id == "rtx_vsr":
        img_name = copy_input_for_image(input_path)
        api = build_rtx_image_prompt(
            img_name, w, h, quality=str(be.get("quality_mode") or "ULTRA")
        )
        result = run_comfy_image(api, output_path, server=server, timeout_sec=timeout_sec)
    elif runner == "comfy_api_seedvr2" or backend_id == "seedvr2_comfy":
        img_name = copy_input_for_image(input_path)
        tile = se >= int(be.get("vae_tile_short_edge_threshold") or 1440)
        api = build_seedvr2_image_prompt(
            img_name,
            resolution=int(se),
            dit_model=str(
                be.get("dit_model")
                or "seedvr2_ema_7b_fp8_e4m3fn_mixed_block35_fp16.safetensors"
            ),
            vae_model=str(be.get("vae_model") or "ema_vae_fp16.safetensors"),
            color_correction=str(be.get("color_correction") or "lab"),
            encode_tiled=tile or bool(be.get("force_vae_tiled")),
            decode_tiled=tile or bool(be.get("force_vae_tiled")),
        )
        result = run_comfy_image(api, output_path, server=server, timeout_sec=timeout_sec)
    elif runner == "seedvr2_cli":
        result = run_seedvr2_cli(
            input_path,
            output_path,
            short_edge=se,
            backend_cfg=be,
            root_cfg=cfg,
            media="image",
            timeout_sec=timeout_sec,
        )
    else:
        from lib.comfy_client import fail_result

        return fail_result(error="BACKEND_RUNNER_UNKNOWN", message=str(runner))

    if not result.get("ok"):
        return result

    meta_path = resolve_meta_out(output_path, meta_out)
    meta = {
        "mode": "upscale_image",
        "backend": backend_id,
        "style": job.get("style"),
        "esrgan_model": model,
        "preset": job["preset_id"],
        "format": job.get("format_id"),
        "aspect": job.get("aspect"),
        "width": w,
        "height": h,
        "short_edge": se,
        "source": os.path.abspath(input_path),
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
        "prompt_id": result.get("prompt_id"),
        "pack": "image_upscale_dual",
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta: {meta_path}")
    result["meta"] = meta
    result["meta_path"] = meta_path
    print(f"OK: {output_path}")
    return result


if __name__ == "__main__":
    if any(
        a in ("--list-backends", "--list-presets", "--list-styles") for a in sys.argv[1:]
    ):
        cfg = load_upscale_backends()
        if "--list-backends" in sys.argv:
            for bid in list_upscale_backend_ids(cfg):
                b = cfg["backends"][bid]
                print(
                    f"{bid}  status={b.get('status')}  speed={b.get('speed')}  "
                    f"{(b.get('notes') or '')[:60]}"
                )
        if "--list-presets" in sys.argv:
            for pid in list_upscale_preset_ids(cfg):
                p = cfg["presets"][pid]
                print(f"{pid}  short_edge={p['short_edge']}  {p.get('notes', '')}")
        if "--list-styles" in sys.argv:
            for sid in list_upscale_style_ids(cfg):
                s = cfg["styles"][sid]
                print(
                    f"{sid}  model={s.get('model')}  domain={s.get('domain')}  "
                    f"{(s.get('notes') or '')[:50]}"
                )
        sys.exit(0)

    p = argparse.ArgumentParser(
        description="Agent image upscale — dual pack (ESRGAN styles / SeedVR2), max 4K presets"
    )
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--backend",
        default=None,
        help="esrgan | rtx_vsr | seedvr2 | seedvr2_comfy | seedvr2_max",
    )
    p.add_argument(
        "--style",
        default=None,
        help="photo | photo_sharp | anime | anime_fast | general | remacri | realesrgan",
    )
    p.add_argument("--preset", default=None, help="deliver_1080 | deliver_1440 | deliver_2160 ...")
    p.add_argument("--format", dest="format_id", default=None, help="cinematic_16x9, shorts_9x16, ...")
    p.add_argument("--aspect", default=None, help="override e.g. 16:9 (default: source image aspect)")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--short-edge", type=int, default=None)
    p.add_argument("--esrgan-model", default=None, help="override model filename under upscale_models")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--list-backends", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    p.add_argument("--list-styles", action="store_true")
    args = p.parse_args()

    if (args.width is None) ^ (args.height is None):
        p.error("Provide both --width and --height, or neither")

    r = upscale_image(
        args.input,
        args.output,
        backend=args.backend,
        preset=args.preset,
        format_id=args.format_id,
        aspect=args.aspect,
        width=args.width,
        height=args.height,
        short_edge=args.short_edge,
        style=args.style,
        esrgan_model=args.esrgan_model,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
    )
    sys.exit(0 if r.get("ok") else 1)
