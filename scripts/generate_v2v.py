#!/usr/bin/env python3
"""
Video-to-Video by intent: camera | motion | style.

Uses LTX 2.3 AIO true Video-to-Video port (VHS_LoadVideo) via generate_s2v.

  python scripts/generate_v2v.py --intent camera -v plate.mp4 -i key.png -o out.mp4
  python scripts/generate_v2v.py --intent motion -v dance.mp4 -i hero.png -o out.mp4 --dry-run

See docs/v2v_intent_pipeline_design.md.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_s2v import generate_s2v
from lib.comfy_client import fail_result, resolve_meta_out, write_meta
from lib.ffmpeg_util import probe_duration
from lib.v2v_contract import (
    build_negative,
    build_prompt,
    normalize_intent,
    resolve_clip_duration_sec,
    resolve_strength,
    validate_v2v_inputs,
)

DEFAULT_BACKEND = "ltx23_aio_v2v_true"
DEFAULT_BACKEND_AUDIO = "ltx23_aio_v2v_true_audio"


def generate_v2v(
    video_path: str,
    image_path: str | None = None,
    output_filename: str | None = None,
    *,
    intent: str = "camera",
    prompt: str | None = None,
    negative: str | None = None,
    strength: float | None = None,
    width: int = 544,
    height: int = 960,
    fps: float = 24.0,
    duration_sec: float | None = None,
    trim_start_sec: float = 0.0,
    trim_duration_sec: float | None = None,
    audio_path: str | None = None,
    backend: str | None = None,
    seed: int | None = None,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
    dry_run: bool = False,
) -> dict:
    try:
        intent_n = normalize_intent(intent)
    except ValueError as e:
        return fail_result(error="BAD_INTENT", message=str(e))

    issues = validate_v2v_inputs(
        intent=intent_n,
        video_path=video_path,
        image_path=image_path,
    )
    if issues:
        return fail_result(error=issues[0]["code"], message=issues[0]["message"], issues=issues)

    if not os.path.isfile(video_path):
        return fail_result(error="VIDEO_MISSING", message=video_path)
    if image_path and not os.path.isfile(image_path):
        return fail_result(error="SOURCE_MISSING", message=image_path)

    # Style without still: use a 1x1 placeholder is unsafe — require still for AIO image port
    # when present in graph. Prefer first-frame extract is future work; require -i for now.
    if not image_path:
        return fail_result(
            error="IMAGE_REQUIRED",
            message="P0 requires -i still (identity/scene or style anchor). First-frame extract later.",
        )

    vdur = probe_duration(video_path)
    try:
        clip_dur, dur_meta = resolve_clip_duration_sec(
            video_duration_sec=vdur,
            trim_start_sec=trim_start_sec,
            trim_duration_sec=trim_duration_sec,
            explicit_duration_sec=duration_sec,
        )
    except ValueError as e:
        msg = str(e)
        code = msg.split(":", 1)[0] if ":" in msg else "V2V_DURATION"
        return fail_result(error=code, message=msg)

    strength_v = resolve_strength(intent_n, strength)
    full_prompt = build_prompt(intent_n, prompt)
    full_neg = build_negative(intent_n, negative)

    if backend is None:
        backend = DEFAULT_BACKEND_AUDIO if audio_path else DEFAULT_BACKEND

    frames = max(9, int(round(float(clip_dur) * float(fps))))
    if frames % 2 == 0:
        frames += 1

    if output_filename is None:
        base, _ = os.path.splitext(os.path.abspath(video_path))
        output_filename = base + f"_{intent_n}_v2v.mp4"

    r = generate_s2v(
        image_path,
        audio_path,
        output_filename,
        backend=backend,
        prompt=full_prompt,
        negative=full_neg,
        width=width,
        height=height,
        num_frames=frames,
        fps=fps,
        seed=seed,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        dry_run=dry_run,
        video_path=video_path,
        trim_start_sec=float(trim_start_sec or 0.0),
        ltx_mode="v2v_audio" if audio_path else "v2v",
    )

    # Enrich meta
    if r.get("meta") is None:
        r["meta"] = {}
    if isinstance(r.get("meta"), dict):
        r["meta"].update(
            {
                "v2v_intent": intent_n,
                "v2v_strength": strength_v,
                "v2v_video": os.path.abspath(video_path),
                "v2v_image": os.path.abspath(image_path) if image_path else None,
                "v2v_duration_meta": dur_meta,
                "tool": "generate_v2v",
            }
        )
        mp = r.get("meta_path") or resolve_meta_out(output_filename, meta_out)
        if mp and not dry_run:
            try:
                write_meta(mp, r["meta"])
                r["meta_path"] = mp
            except Exception:
                pass
    return r


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="V2V by intent (camera | motion | style) via LTX AIO true video port"
    )
    p.add_argument("--video", "-v", required=True, help="Driving / reference video")
    p.add_argument(
        "--input",
        "-i",
        required=True,
        help="Identity / scene still (required in P0)",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--intent",
        default="camera",
        choices=["camera", "motion", "style", "v2v_camera", "v2v_motion", "v2v_style"],
        help="camera | motion | style (default camera)",
    )
    p.add_argument("--prompt", "-p", default=None, help="Extra prompt tokens")
    p.add_argument("--negative", default=None)
    p.add_argument(
        "--strength",
        type=float,
        default=None,
        help="0–1 structure adherence guide (stored in meta; P0 prompt-primary)",
    )
    p.add_argument("--width", type=int, default=544)
    p.add_argument("--height", type=int, default=960)
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Output/trim length seconds (default: rest of video after --trim-start)",
    )
    p.add_argument("--trim-start", type=float, default=0.0)
    p.add_argument(
        "--trim-duration",
        type=float,
        default=None,
        help="Alias for limiting driving segment length",
    )
    p.add_argument("--audio", "-a", default=None, help="Optional audio (switches v2v_audio mode)")
    p.add_argument(
        "--backend",
        default=None,
        help=f"default {DEFAULT_BACKEND} or {DEFAULT_BACKEND_AUDIO} with -a",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--meta-out", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    r = generate_v2v(
        args.video,
        args.input,
        args.output,
        intent=args.intent,
        prompt=args.prompt,
        negative=args.negative,
        strength=args.strength,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration_sec=args.duration if args.duration is not None else args.trim_duration,
        trim_start_sec=args.trim_start,
        trim_duration_sec=args.trim_duration,
        audio_path=args.audio,
        backend=args.backend,
        seed=args.seed,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        dry_run=args.dry_run,
    )

    if not r.get("ok"):
        print(
            f"FAIL error={r.get('error')} message={r.get('message')}",
            file=sys.stderr,
        )
        return 1
    if args.dry_run:
        m = r.get("meta") or {}
        print(
            f"OK dry_run intent={m.get('v2v_intent')} strength={m.get('v2v_strength')} "
            f"backend path ready"
        )
        if m.get("v2v_duration_meta"):
            print(f"  duration={m.get('v2v_duration_meta')}")
        return 0
    print(f"OK path={r.get('output_path') or args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
