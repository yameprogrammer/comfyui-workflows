#!/usr/bin/env python3
"""Upscale a video clip via multi-backend agent stack (ESRGAN frames / RTX VSR / SeedVR2)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys
import tempfile

from lib.comfy_client import DEFAULT_SERVER, resolve_meta_out, utc_now_iso, write_meta
from lib.upscale_backends import (
    list_upscale_backend_ids,
    list_upscale_preset_ids,
    load_upscale_backends,
    resolve_upscale_job,
)
from lib.upscale_runners import (
    build_esrgan_video_prompt,
    build_rtx_video_prompt,
    run_comfy_video,
    run_seedvr2_cli,
)


def upscale_video(
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
    fps: float = 16.0,
    two_pass: bool | None = None,
    style: str | None = None,
    esrgan_model: str | None = None,
    server: str = DEFAULT_SERVER,
    timeout_sec: int = 14400,
    meta_out: str | None = None,
) -> dict:
    from lib.comfy_client import fail_result, ok_result

    if not os.path.isfile(input_path):
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
        )
    except Exception as e:
        return fail_result(error="UPSCALE_JOB_RESOLVE", message=str(e))
    be = job["backend"]
    backend_id = job["backend_id"]
    w, h = job["width"], job["height"]
    se = job["short_edge"]
    cfg = job["config"]
    resolved_model = job.get("esrgan_model") or esrgan_model

    if output_path is None:
        base, _ext = os.path.splitext(input_path)
        output_path = f"{base}_{job['preset_id']}_{backend_id}.mp4"

    # two-pass for 4K unless disabled
    tp_cfg = cfg.get("two_pass_4k") or {}
    if two_pass is None:
        two_pass = bool(tp_cfg.get("enabled_default")) and se >= 2160 and backend_id.startswith(
            "seedvr2"
        )

    print(
        f"Upscale video backend={backend_id} preset={job['preset_id']} "
        f"aspect={job['aspect']} target={w}x{h} short_edge={se} two_pass={two_pass}"
    )

    def _one_pass(src: str, dst: str, short: int, width_: int, height_: int) -> dict:
        runner = be.get("runner")
        if runner == "comfy_api" and backend_id == "esrgan":
            model = resolved_model or be.get("model_name") or "RealESRGAN_x4plus.pth"
            api = build_esrgan_video_prompt(
                os.path.abspath(src), model, width_, height_, fps
            )
            return run_comfy_video(api, dst, server=server, timeout_sec=timeout_sec)
        if runner == "comfy_api" and backend_id == "rtx_vsr":
            api = build_rtx_video_prompt(
                os.path.abspath(src),
                width_,
                height_,
                fps,
                quality=str(be.get("quality_mode") or "ULTRA"),
            )
            return run_comfy_video(api, dst, server=server, timeout_sec=timeout_sec)
        if runner == "seedvr2_cli":
            return run_seedvr2_cli(
                src,
                dst,
                short_edge=short,
                backend_cfg=be,
                root_cfg=cfg,
                media="video",
                timeout_sec=timeout_sec,
            )
        return fail_result(error="BACKEND_RUNNER_UNKNOWN", message=str(runner))

    passes = []
    if two_pass:
        mid_preset = str(tp_cfg.get("pass1_preset") or "deliver_1080")
        mid_job = resolve_upscale_job(
            backend=backend_id,
            preset=mid_preset,
            format_id=format_id or job.get("format_id"),
            aspect=aspect or job.get("aspect"),
        )
        fd, mid_path = tempfile.mkstemp(suffix=".mp4", prefix="upscale_pass1_")
        os.close(fd)
        try:
            print(f"Pass1 → {mid_job['width']}x{mid_job['height']}")
            r1 = _one_pass(
                input_path, mid_path, mid_job["short_edge"], mid_job["width"], mid_job["height"]
            )
            passes.append({"pass": 1, "result": r1, "size": [mid_job["width"], mid_job["height"]]})
            if not r1.get("ok"):
                return r1
            print(f"Pass2 → {w}x{h}")
            r2 = _one_pass(mid_path, output_path, se, w, h)
            passes.append({"pass": 2, "result": r2, "size": [w, h]})
            if not r2.get("ok"):
                return r2
            result = r2
        finally:
            try:
                os.remove(mid_path)
            except OSError:
                pass
    else:
        result = _one_pass(input_path, output_path, se, w, h)
        passes.append({"pass": 1, "result": result, "size": [w, h]})
        if not result.get("ok"):
            return result

    meta_path = resolve_meta_out(output_path, meta_out)
    meta = {
        "mode": "upscale_video",
        "backend": backend_id,
        "style": job.get("style"),
        "esrgan_model": resolved_model,
        "preset": job["preset_id"],
        "format": job.get("format_id"),
        "aspect": job.get("aspect"),
        "width": w,
        "height": h,
        "short_edge": se,
        "fps": fps,
        "two_pass": two_pass,
        "passes": [{"pass": p["pass"], "size": p["size"], "ok": p["result"].get("ok")} for p in passes],
        "source": os.path.abspath(input_path),
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
        "prompt_id": result.get("prompt_id"),
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta: {meta_path}")
    out = ok_result(
        output_path=os.path.abspath(output_path),
        prompt_id=result.get("prompt_id"),
        meta=meta,
        meta_path=meta_path,
    )
    print(f"OK: {output_path}")
    return out


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

    p = argparse.ArgumentParser(description="Agent video upscale (selectable up to 4K)")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--backend", default=None, help="esrgan | rtx_vsr | seedvr2 | seedvr2_max")
    p.add_argument(
        "--style",
        default=None,
        help="esrgan style: photo | photo_sharp | anime | anime_fast | general | …",
    )
    p.add_argument("--preset", default=None, help="deliver_1080 | deliver_1440 | deliver_2160")
    p.add_argument("--format", dest="format_id", default=None)
    p.add_argument("--aspect", default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--short-edge", type=int, default=None)
    p.add_argument("--fps", type=float, default=16.0)
    p.add_argument("--two-pass", action="store_true", help="Force 1080 then 4K for seedvr2")
    p.add_argument("--no-two-pass", action="store_true", help="Disable automatic two-pass on 4K")
    p.add_argument("--esrgan-model", default=None)
    p.add_argument("--timeout", type=int, default=14400)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--list-backends", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    args = p.parse_args()

    if (args.width is None) ^ (args.height is None):
        p.error("Provide both --width and --height, or neither")

    two = True if args.two_pass else (False if args.no_two_pass else None)

    r = upscale_video(
        args.input,
        args.output,
        backend=args.backend,
        preset=args.preset,
        format_id=args.format_id,
        aspect=args.aspect,
        width=args.width,
        height=args.height,
        short_edge=args.short_edge,
        fps=args.fps,
        two_pass=two,
        style=args.style,
        esrgan_model=args.esrgan_model,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
    )
    sys.exit(0 if r.get("ok") else 1)
