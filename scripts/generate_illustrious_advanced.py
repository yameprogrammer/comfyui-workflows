#!/usr/bin/env python3
"""Illustrious Advanced_V37 — TIPO / IPAdapter / OpenPose / Regional / full kitchen.

  python scripts/generate_illustrious_advanced.py --list-features
  python scripts/generate_illustrious_advanced.py -p "1girl, solo, ..." -o out.png
  python scripts/generate_illustrious_advanced.py -p "..." --tipo -o out.png
  python scripts/generate_illustrious_advanced.py -p "..." --openpose pose.png -o out.png
  python scripts/generate_illustrious_advanced.py -p "..." --ipa face.png -o out.png

Guide: workflows/human/illustrious_advanced_v37/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import FAMILY_OTHER, ensure_engine
from lib.illustrious_advanced_v37_runner import (
    DEFAULT_CKPT,
    DEFAULT_NEG,
    FEATURE_GROUPS,
    generate_illustrious_advanced,
    load_capabilities,
    resolve_features,
)


def _print_features() -> int:
    caps = load_capabilities()
    print("=== Advanced_V37 feature menu ===\n")
    for f in caps.get("features") or []:
        print(f"  {f.get('feature_id')}: {f.get('name')}  default={f.get('default')}")
        if f.get("cli"):
            print(f"    cli: {f.get('cli')}")
        if f.get("when_to_use"):
            print(f"    when: {f.get('when_to_use')}")
    print("\nToggle map:")
    for fid, groups in FEATURE_GROUPS.items():
        print(f"  {fid}: {groups}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Illustrious Advanced_V37 real-UI runner")
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--negative", "-n", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--sampler", default=None)
    p.add_argument("--scheduler", default=None)
    p.add_argument("--denoise", "-d", type=float, default=None)
    p.add_argument("--ckpt", default=None)
    p.add_argument("--lora-text", default=None)
    p.add_argument("--image", "-i", default=None, help="I2I source")
    p.add_argument("--openpose", default=None, help="OpenPose reference image")
    p.add_argument("--controlnet", default=None, help="Any ControlNet reference image")
    p.add_argument("--ipa", default=None, help="IP-Adapter Advanced face/ref image")
    p.add_argument("--style-image", default=None)
    p.add_argument("--composition-image", default=None)
    p.add_argument("--preset", default=None)
    p.add_argument("--feature", action="append", default=[])
    p.add_argument("--no-feature", action="append", default=[])
    # shared detailers
    p.add_argument("--face", dest="face", action="store_true", default=None)
    p.add_argument("--no-face", dest="face", action="store_false")
    p.add_argument("--hand", action="store_true")
    p.add_argument("--eyes", action="store_true")
    p.add_argument("--nsfw-detailer", action="store_true")
    p.add_argument("--i-am-18", action="store_true")
    # advanced
    p.add_argument("--tipo", action="store_true")
    p.add_argument("--regional", action="store_true")
    p.add_argument("--fbcnn", action="store_true")
    p.add_argument("--rmbg", action="store_true")
    p.add_argument("--hires-pre", action="store_true")
    p.add_argument("--hires-post", action="store_true")
    p.add_argument("--ultimate-pre", action="store_true")
    p.add_argument("--ultimate-post", action="store_true")
    p.add_argument("--second-sampler", action="store_true")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-features", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    args = p.parse_args(argv)

    if args.list_features:
        return _print_features()
    if args.list_presets:
        print(json.dumps(load_capabilities().get("agent_presets") or {}, indent=2, ensure_ascii=False))
        return 0
    if args.nsfw_detailer and not args.i_am_18:
        print("[advanced] refuse --nsfw-detailer without --i-am-18", file=sys.stderr)
        return 2

    prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt required (or --list-features)")

    flags = {
        "face_adetailer": args.face,
        "hand_adetailer": True if args.hand else None,
        "eyes_adetailer": True if args.eyes else None,
        "nsfw_adetailer": True if args.nsfw_detailer else None,
        "tipo": True if args.tipo else None,
        "regional": True if args.regional else None,
        "fbcnn": True if args.fbcnn else None,
        "rmbg": True if args.rmbg else None,
        "hires_pre": True if args.hires_pre else None,
        "hires_post": True if args.hires_post else None,
        "ultimate_pre": True if args.ultimate_pre else None,
        "ultimate_post": True if args.ultimate_post else None,
        "second_sampler": True if args.second_sampler else None,
    }
    # strip Nones that mean "don't set" for face only when None
    flags = {k: v for k, v in flags.items() if v is not None}

    on, off = resolve_features(
        preset=args.preset,
        flags=flags,
        features=args.feature,
        no_features=args.no_feature,
    )

    out = args.output or os.path.join("dumps", "illustrious_adv_v37_out.png")
    eng = ensure_engine(FAMILY_OTHER, args.server, caller="generate_illustrious_advanced")
    if not eng.get("ok"):
        print(f"FAIL ENGINE: {eng.get('message')}", file=sys.stderr)
        return 2

    print(f"Advanced_V37 features_on={sorted(on)} out={out}")
    r = generate_illustrious_advanced(
        positive=prompt,
        negative=args.negative if args.negative is not None else DEFAULT_NEG,
        output_path=out,
        seed=args.seed,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg=args.cfg,
        sampler=args.sampler,
        scheduler=args.scheduler,
        denoise=args.denoise,
        ckpt_name=args.ckpt or DEFAULT_CKPT,
        lora_text=args.lora_text,
        image_path=args.image,
        openpose_image=args.openpose,
        controlnet_image=args.controlnet,
        ipa_image=args.ipa,
        style_image=args.style_image,
        composition_image=args.composition_image,
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
