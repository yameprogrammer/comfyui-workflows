#!/usr/bin/env python3
"""Illustrious Detailer_V37 — polish / inpaint / outpaint existing images.

  python scripts/generate_illustrious_detailer.py --list-features
  python scripts/generate_illustrious_detailer.py -i still.png -o out.png
  python scripts/generate_illustrious_detailer.py -i still.png -o out.png --hand --eyes
  python scripts/generate_illustrious_detailer.py -i still.png -o out.png --inpaint -p "fix hands"
  python scripts/generate_illustrious_detailer.py -i still.png -o out.png --outpaint

Guide: workflows/human/illustrious_detailer_v37/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import FAMILY_OTHER, ensure_engine
from lib.illustrious_detailer_v37_runner import (
    DEFAULT_CKPT,
    DEFAULT_NEG,
    FEATURE_GROUPS,
    generate_illustrious_detailer,
    load_capabilities,
    resolve_features,
)


def _print_features() -> int:
    caps = load_capabilities()
    print("=== Detailer_V37 feature menu ===\n")
    for f in caps.get("features") or []:
        print(f"  {f.get('feature_id')}: {f.get('name')}  default={f.get('default')}")
        if f.get("cli"):
            print(f"    cli: {f.get('cli')}")
    print("\nToggle map:")
    for fid, groups in FEATURE_GROUPS.items():
        print(f"  {fid}: {groups}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Illustrious Detailer_V37 real-UI runner")
    p.add_argument("--image", "-i", required=False, help="input image (required to run)")
    p.add_argument(
        "--mask",
        "-m",
        default=None,
        help="inpaint mask PNG (white=edit). Applied as alpha; auto-enables --inpaint",
    )
    p.add_argument(
        "--mask-invert",
        action="store_true",
        help="invert mask before apply (if white is keep)",
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--negative", "-n", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--sampler", default=None)
    p.add_argument("--scheduler", default=None)
    p.add_argument("--denoise", "-d", type=float, default=None)
    p.add_argument("--ckpt", default=None)
    p.add_argument("--lora-text", default=None)
    p.add_argument("--preset", default=None)
    p.add_argument("--feature", action="append", default=[])
    p.add_argument("--no-feature", action="append", default=[])
    p.add_argument("--face", dest="face", action="store_true", default=None)
    p.add_argument("--no-face", dest="face", action="store_false")
    p.add_argument("--hand", action="store_true")
    p.add_argument("--eyes", action="store_true")
    p.add_argument("--nsfw-detailer", action="store_true")
    p.add_argument("--i-am-18", action="store_true")
    p.add_argument("--inpaint", action="store_true")
    p.add_argument("--outpaint", action="store_true")
    p.add_argument("--rmbg", action="store_true")
    p.add_argument("--remove-watermark", action="store_true")
    p.add_argument("--fbcnn", action="store_true")
    p.add_argument("--hires", action="store_true")
    p.add_argument("--ultimate-upscale", action="store_true")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-features", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    p.add_argument(
        "--check-models",
        action="store_true",
        help="dependency health (models + Comfy nodes)",
    )
    args = p.parse_args(argv)

    if args.list_features:
        return _print_features()
    if args.list_presets:
        print(json.dumps(load_capabilities().get("agent_presets") or {}, indent=2, ensure_ascii=False))
        return 0
    if args.check_models:
        from lib.illustrious_health import check_pack, format_report

        r = check_pack("detailer", server=args.server)
        print(format_report(r))
        return 0 if r.get("ok_count", 0) else 1
    if not args.image:
        p.error("--image required (or --list-features)")
    if args.nsfw_detailer and not args.i_am_18:
        print("[detailer] refuse --nsfw-detailer without --i-am-18", file=sys.stderr)
        return 2

    flags = {
        "face_adetailer": args.face,
        "hand_adetailer": True if args.hand else None,
        "eyes_adetailer": True if args.eyes else None,
        "nsfw_adetailer": True if args.nsfw_detailer else None,
        "inpaint": True if args.inpaint else None,
        "outpaint": True if args.outpaint else None,
        "rmbg": True if args.rmbg else None,
        "remove_watermark": True if args.remove_watermark else None,
        "fbcnn": True if args.fbcnn else None,
        "hires": True if args.hires else None,
        "ultimate_sd_upscale": True if args.ultimate_upscale else None,
    }
    flags = {k: v for k, v in flags.items() if v is not None}

    on, off = resolve_features(
        preset=args.preset,
        flags=flags,
        features=args.feature,
        no_features=args.no_feature,
    )

    out = args.output or os.path.join("dumps", "illustrious_det_v37_out.png")
    eng = ensure_engine(FAMILY_OTHER, args.server, caller="generate_illustrious_detailer")
    if not eng.get("ok"):
        print(f"FAIL ENGINE: {eng.get('message')}", file=sys.stderr)
        return 2

    print(f"Detailer_V37 features_on={sorted(on)} in={args.image} out={out}")
    r = generate_illustrious_detailer(
        image_path=args.image,
        output_path=out,
        mask_path=args.mask,
        mask_invert=bool(args.mask_invert),
        positive=args.prompt,
        negative=args.negative if args.negative is not None else DEFAULT_NEG,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        sampler=args.sampler,
        scheduler=args.scheduler,
        denoise=args.denoise,
        ckpt_name=args.ckpt or DEFAULT_CKPT,
        lora_text=args.lora_text,
        features_on=on,
        features_off=off,
        timeout_sec=args.timeout,
        server_address=args.server,
    )
    if not r.get("ok"):
        print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 1
    print(f"OK {r.get('output')} seed={r.get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
