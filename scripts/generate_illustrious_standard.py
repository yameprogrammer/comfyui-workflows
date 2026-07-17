#!/usr/bin/env python3
"""Illustrious Standard_V37 — real Legendaer UI for XL/Illustrious/NoobAI stills.

Source purpose (Civitai 1386234):
  \"Workflow for XL / Illustrious / NoobAI Models\"
  Standard = more basic version of Advanced (daily driver).
  Not a photoreal Z-Image substitute; not Advanced (TIPO/IPA/OpenPose).

Uses the real UI only: Fast Groups (pale_blue/cyan) → expand + ports.
No mini-graph rebuild.

  python scripts/generate_illustrious_standard.py -p "1girl, solo, ..." -o out.png
  python scripts/generate_illustrious_standard.py --list-features
  python scripts/generate_illustrious_standard.py --preset t2i_clean -p "..." -o out.png
  python scripts/generate_illustrious_standard.py -p "..." --hand --eyes -o out.png
  python scripts/generate_illustrious_standard.py -i ref.png -p "..." -d 0.55 -o out.png

Guide: workflows/human/illustrious_standard_v37/AGENT_GUIDE.md
Civitai: https://civitai.red/models/1386234/comfyui-image-workflows
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import FAMILY_OTHER, ensure_engine
from lib.illustrious_standard_v37_runner import (
    DEFAULT_CKPT,
    DEFAULT_NEG,
    FEATURE_GROUPS,
    generate_illustrious_standard,
    load_capabilities,
    resolve_features_from_args,
)


def _print_features() -> int:
    caps = load_capabilities()
    print("=== Standard_V37 feature menu (real UI groups) ===\n")
    for f in caps.get("features") or []:
        fid = f.get("feature_id")
        print(f"  {fid}")
        print(f"    name:     {f.get('name')}")
        print(f"    default:  {f.get('default')}")
        print(f"    when:     {f.get('when_to_use')}")
        if f.get("cli"):
            print(f"    cli:      {f.get('cli')}")
        if f.get("groups_on"):
            print(f"    groups:   {f.get('groups_on')}")
        print()
    print("=== agent_presets ===")
    for name, pe in (caps.get("agent_presets") or {}).items():
        print(f"  {name}: {pe.get('description')}")
        print(f"    on:  {pe.get('features_on')}")
        print(f"    off: {pe.get('features_off')}")
    print("\nToggle map (feature_id → group titles):")
    for fid, groups in FEATURE_GROUPS.items():
        print(f"  {fid}: {groups}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Standard_V37 Illustrious XL — real UI workflow, feature switches"
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
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
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--ckpt", default=None, help=f"checkpoint (default {DEFAULT_CKPT})")
    p.add_argument(
        "--lora-text",
        default=None,
        help="LoraManager text field (LoRA syntax as in UI)",
    )
    p.add_argument("--image", "-i", default=None, help="I2I source (enables Load Image group)")
    p.add_argument("--signature", default=None, help="signature PNG (Apply Signature group)")
    p.add_argument("--vae-name", default=None)
    p.add_argument("--preset", default=None, help="agent_preset from CAPABILITIES.json")
    p.add_argument(
        "--feature",
        action="append",
        default=[],
        help="feature_id to force ON (repeatable)",
    )
    p.add_argument(
        "--no-feature",
        action="append",
        default=[],
        help="feature_id to force OFF (repeatable)",
    )
    # detailers
    p.add_argument("--face", dest="face", action="store_true", default=None)
    p.add_argument("--no-face", dest="face", action="store_false")
    p.add_argument("--hand", action="store_true")
    p.add_argument("--eyes", action="store_true")
    p.add_argument("--nsfw-detailer", action="store_true")
    p.add_argument("--generic-detailer", action="store_true")
    p.add_argument("--sam", dest="sam", action="store_true", default=None)
    p.add_argument("--no-sam", dest="sam", action="store_false")
    p.add_argument("--clip-skip", dest="clip_skip", action="store_true", default=None)
    p.add_argument("--no-clip-skip", dest="clip_skip", action="store_false")
    # model / sampler mods
    p.add_argument("--separate-vae", action="store_true")
    p.add_argument("--vpred", action="store_true")
    p.add_argument("--epsilon-scaling", action="store_true")
    p.add_argument("--cfg-zero-star", action="store_true")
    # upscale / post
    p.add_argument("--hires-pre", action="store_true")
    p.add_argument("--hires-post", action="store_true")
    p.add_argument("--color-match", action="store_true")
    p.add_argument("--ultimate-upscale", action="store_true")
    p.add_argument("--fx-morphology", action="store_true")
    p.add_argument("--fx-quantize", action="store_true")
    p.add_argument("--fx-sharpen", action="store_true")
    p.add_argument("--fx-contrast", action="store_true")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--list-features", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    args = p.parse_args(argv)

    if args.list_features:
        return _print_features()
    if args.list_presets:
        caps = load_capabilities()
        print(json.dumps(caps.get("agent_presets") or {}, indent=2, ensure_ascii=False))
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt / --prompt-file required (or --list-features)")

    out = args.output or os.path.join(
        r"F:\generated_images",
        "illustrious_std_v37_out.png",
    )

    on, off = resolve_features_from_args(
        preset=args.preset,
        face=args.face,
        hand=args.hand,
        eyes=args.eyes,
        nsfw_detailer=args.nsfw_detailer,
        generic_detailer=args.generic_detailer,
        sam=args.sam,
        clip_skip=args.clip_skip,
        image=args.image,
        separate_vae=args.separate_vae,
        vpred=args.vpred,
        epsilon_scaling=args.epsilon_scaling,
        cfg_zero_star=args.cfg_zero_star,
        hires_pre=args.hires_pre,
        hires_post=args.hires_post,
        color_match=args.color_match,
        ultimate_upscale=args.ultimate_upscale,
        signature=args.signature,
        fx_morphology=args.fx_morphology,
        fx_quantize=args.fx_quantize,
        fx_sharpen=args.fx_sharpen,
        fx_contrast=args.fx_contrast,
        features=args.feature,
        no_features=args.no_feature,
    )

    eng = ensure_engine(FAMILY_OTHER, args.server, caller="generate_illustrious_standard")
    if not eng.get("ok"):
        print(
            f"FAIL ENGINE: {eng.get('error')} {eng.get('message')}",
            file=sys.stderr,
        )
        return 2

    print(
        f"Standard_V37 real-UI  features_on={sorted(on)}  "
        f"size={args.width or 'default'}x{args.height or 'default'}  out={out}"
    )

    result = generate_illustrious_standard(
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
        batch_size=args.batch_size,
        ckpt_name=args.ckpt,
        lora_text=args.lora_text,
        image_path=args.image,
        signature_path=args.signature,
        vae_name=args.vae_name,
        features_on=on,
        features_off=off,
        timeout_sec=args.timeout,
        server_address=args.server,
    )

    if not result.get("ok"):
        print(
            f"FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        if result.get("features_on") is not None:
            print(f"  features_on={result.get('features_on')}", file=sys.stderr)
        return 1

    print(f"OK {result.get('output')}")
    print(f"  seed={result.get('ports', {}).get('seed')}  prompt_id={result.get('prompt_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
