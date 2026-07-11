#!/usr/bin/env python3
"""Upscale a still image via multi-backend agent stack (ESRGAN / RTX VSR / SeedVR2)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import DEFAULT_SERVER, resolve_meta_out, utc_now_iso, write_meta
from lib.upscale_backends import (
    list_upscale_backend_ids,
    list_upscale_preset_ids,
    load_upscale_backends,
    resolve_upscale_job,
)
from lib.upscale_runners import (
    build_esrgan_image_prompt,
    build_rtx_image_prompt,
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
    esrgan_model: str | None = None,
    server: str = DEFAULT_SERVER,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
) -> dict:
    if not os.path.isfile(input_path):
        from lib.comfy_client import fail_result

        return fail_result(error="SOURCE_MISSING", message=input_path)

    job = resolve_upscale_job(
        backend=backend,
        preset=preset,
        format_id=format_id,
        aspect=aspect,
        width=width,
        height=height,
        short_edge=short_edge,
    )
    be = job["backend"]
    backend_id = job["backend_id"]
    w, h = job["width"], job["height"]
    se = job["short_edge"]
    cfg = job["config"]

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_{job['preset_id']}_{backend_id}{ext or '.png'}"

    print(
        f"Upscale image backend={backend_id} preset={job['preset_id']} "
        f"aspect={job['aspect']} target={w}x{h} short_edge={se}"
    )

    runner = be.get("runner")
    if runner == "comfy_api" and backend_id == "esrgan":
        model = esrgan_model or be.get("model_name") or "RealESRGAN_x4plus.pth"
        img_name = copy_input_for_image(input_path)
        api = build_esrgan_image_prompt(img_name, model, w, h)
        result = run_comfy_image(api, output_path, server=server, timeout_sec=timeout_sec)
    elif runner == "comfy_api" and backend_id == "rtx_vsr":
        img_name = copy_input_for_image(input_path)
        api = build_rtx_image_prompt(
            img_name, w, h, quality=str(be.get("quality_mode") or "ULTRA")
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
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta: {meta_path}")
    result["meta"] = meta
    result["meta_path"] = meta_path
    print(f"OK: {output_path}")
    return result


if __name__ == "__main__":
    if any(a in ("--list-backends", "--list-presets") for a in sys.argv[1:]):
        cfg = load_upscale_backends()
        if "--list-backends" in sys.argv:
            for bid in list_upscale_backend_ids(cfg):
                b = cfg["backends"][bid]
                print(f"{bid}  status={b.get('status')}  speed={b.get('speed')}  {b.get('notes','')[:60]}")
        if "--list-presets" in sys.argv:
            for pid in list_upscale_preset_ids(cfg):
                p = cfg["presets"][pid]
                print(f"{pid}  short_edge={p['short_edge']}  {p.get('notes','')}")
        sys.exit(0)

    p = argparse.ArgumentParser(description="Agent image upscale (max 4K via presets)")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--backend", default=None, help="esrgan | rtx_vsr | seedvr2 | seedvr2_max")
    p.add_argument("--preset", default=None, help="deliver_1080 | deliver_1440 | deliver_2160 ...")
    p.add_argument("--format", dest="format_id", default=None, help="cinematic_16x9, shorts_9x16, ...")
    p.add_argument("--aspect", default=None, help="override e.g. 16:9")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--short-edge", type=int, default=None)
    p.add_argument("--esrgan-model", default=None)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--list-backends", action="store_true")
    p.add_argument("--list-presets", action="store_true")
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
        esrgan_model=args.esrgan_model,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
    )
    sys.exit(0 if r.get("ok") else 1)
