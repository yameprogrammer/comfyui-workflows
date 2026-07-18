#!/usr/bin/env python3
"""Wan 2.2 NSFW / 빨간맛 image-to-video (adult 18+).

**Default:** dedicated Remix NSFW High/Low UNets + lightx2v (speed).
Optional: style LoRA pair (general / dr34ml4y) on top.

  python scripts/generate_wan22_nsfw_i2v.py -i adult_key.png -p "adult woman..." -o out.mp4
  python scripts/generate_wan22_nsfw_i2v.py --list-loras
  python scripts/generate_wan22_nsfw_i2v.py ... --unet-profile base --lora-preset general
  python scripts/generate_wan22_nsfw_i2v.py ... --lora-preset dr34ml4y

Adult 18+ only. SFW motion → generate_i2v (LTX) / --backend wan22.
LTX 10Eros → generate_ltx_nsfw_i2v.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_i2v import generate_i2v
from lib.adult_policy import check_adult_prompt
from lib.wan22_nsfw import (
    DEFAULT_NEGATIVE_NSFW,
    discover_nsfw_lora_pair,
    list_lora_presets,
    nsfw_default_profile,
    resolve_nsfw_loras,
    resolve_nsfw_unets,
)

DEFAULT_OUT = r"F:\generated_videos\wan22_nsfw_i2v_out.mp4"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Wan 2.2 NSFW I2V (18+) — default Remix NSFW UNets + lightx2v; "
            "optional style LoRA pair"
        )
    )
    p.add_argument("--input", "-i", default=None, help="Adult keyframe image")
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", default=None)
    p.add_argument("--output", "-o", default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--frames", type=int, default=49)
    p.add_argument("--fps", type=int, default=16)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument(
        "--profile",
        default=None,
        help=f"Wan speed profile (default {nsfw_default_profile()} from backends)",
    )
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--meta-out", default=None)
    p.add_argument(
        "--unet-profile",
        default=None,
        choices=["remix", "base", "q4", "q5"],
        help=(
            "Diffusion weights: remix=dedicated NSFW High/Low fp8 (default when on disk); "
            "base/q4/q5=official GGUF (+ LoRA recommended)"
        ),
    )
    p.add_argument(
        "--lora-preset",
        default=None,
        help=(
            "Optional style LoRA pair: general|dr34ml4y. "
            "Default with remix: none (model already NSFW). "
            "Default with base: general if present."
        ),
    )
    p.add_argument(
        "--with-lora",
        action="store_true",
        help="Force attach default/general NSFW LoRA even on remix UNet",
    )
    p.add_argument(
        "--no-lora",
        action="store_true",
        help="Do not attach any style LoRA (UNet only)",
    )
    p.add_argument(
        "--lora-high",
        default=None,
        help="NSFW HIGH-noise LoRA path relative to models/loras/",
    )
    p.add_argument(
        "--lora-low",
        default=None,
        help="NSFW LOW-noise LoRA path relative to models/loras/",
    )
    p.add_argument("--lora-strength-high", type=float, default=None)
    p.add_argument("--lora-strength-low", type=float, default=None)
    p.add_argument(
        "--no-auto-lora",
        action="store_true",
        help="Do not auto-discover LoRAs under models/loras/Wan2.2/nsfw/",
    )
    p.add_argument(
        "--require-lora",
        action="store_true",
        help="Fail if no NSFW LoRA pair resolved",
    )
    p.add_argument(
        "--require-remix",
        action="store_true",
        help="Fail if Remix NSFW UNets are not on disk",
    )
    p.add_argument("--wan-scheduler", default=None)
    p.add_argument("--wan-shift", type=float, default=None)
    p.add_argument("--wan-quant", default="q4", choices=["q4", "q5"])
    p.add_argument("--block-swap", type=int, default=None)
    p.add_argument("--attention", default=None)
    p.add_argument("--list-loras", action="store_true")
    args = p.parse_args(argv)

    if args.list_loras:
        disc = discover_nsfw_lora_pair()
        res = resolve_nsfw_loras(auto_discover=True)
        unets = resolve_nsfw_unets(unet_profile=args.unet_profile)
        print("unet_default:", unets)
        print("presets:", list_lora_presets())
        print("discover:", disc)
        print("resolved_loras:", {k: res[k] for k in (
            "lora_high", "lora_low", "strength_high", "strength_low",
            "has_pair", "source", "missing_files", "hint",
        )})
        remix_dir = r"F:\model\diffusion_models\Wan2.2\nsfw_remix"
        if os.path.isdir(remix_dir):
            print("remix_unet_dir:", remix_dir)
            for fn in sorted(os.listdir(remix_dir)):
                if fn.endswith(".safetensors"):
                    fp = os.path.join(remix_dir, fn)
                    print(f"  {fn}  {os.path.getsize(fp)} bytes")
        return 0

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt or --prompt-file required")
    if not args.input:
        p.error("--input/-i required")

    ok, hits = check_adult_prompt(prompt)
    if not ok:
        print(
            f"FAIL AGE_POLICY: prompt hits {hits!r}. "
            "This tool is adult-only (18+).",
            file=sys.stderr,
        )
        return 11

    unets = resolve_nsfw_unets(unet_profile=args.unet_profile)
    if args.require_remix and not unets.get("uses_dedicated_nsfw_unet"):
        print(
            "FAIL REMIX_UNET_REQUIRED: dedicated NSFW UNets not available. "
            f"hint={unets.get('hint')}",
            file=sys.stderr,
        )
        return 13
    if unets.get("hint"):
        print(f"[WARN] {unets['hint']}", file=sys.stderr)

    # LoRA policy: remix UNet already NSFW → LoRA opt-in; base GGUF → LoRA default on
    use_dedicated = bool(unets.get("uses_dedicated_nsfw_unet"))
    want_lora = False
    if args.no_lora:
        want_lora = False
    elif args.lora_high or args.lora_low or args.lora_preset or args.with_lora:
        want_lora = True
    elif args.require_lora:
        want_lora = True
    elif not use_dedicated:
        # base GGUF path needs LoRA for adult quality
        want_lora = True

    loras: dict = {
        "lora_high": None,
        "lora_low": None,
        "strength_high": 0.85,
        "strength_low": 0.9,
        "has_pair": False,
        "has_any": False,
        "source": "none",
    }
    if want_lora:
        preset = args.lora_preset
        if preset is None and args.with_lora:
            preset = "general"
        if preset is None and not use_dedicated:
            preset = "general"
        loras = resolve_nsfw_loras(
            lora_high=args.lora_high,
            lora_low=args.lora_low,
            lora_preset=preset,
            auto_discover=not args.no_auto_lora,
        )
        if args.lora_strength_high is not None:
            loras["strength_high"] = float(args.lora_strength_high)
        if args.lora_strength_low is not None:
            loras["strength_low"] = float(args.lora_strength_low)

        if args.require_lora and not loras.get("has_pair"):
            print(
                "FAIL NSFW_LORA_REQUIRED: no HIGH+LOW NSFW LoRA pair. "
                f"hint={loras.get('hint')}",
                file=sys.stderr,
            )
            return 12

        if loras.get("has_any"):
            print(
                f"NSFW LoRAs source={loras.get('source')} "
                f"high={loras.get('lora_high')}@{loras.get('strength_high')} "
                f"low={loras.get('lora_low')}@{loras.get('strength_low')}"
            )
        else:
            print(
                f"[WARN] LoRA requested but not found: {loras.get('hint')}",
                file=sys.stderr,
            )
    else:
        print("NSFW LoRAs: off (dedicated Remix UNet path; use --with-lora / --lora-preset to add)")

    negative = args.negative if args.negative is not None else DEFAULT_NEGATIVE_NSFW
    profile = args.profile or nsfw_default_profile()
    out = args.output or DEFAULT_OUT
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)

    unet_label = unets.get("unet_profile")
    print(
        f"Wan22 NSFW I2V unet={unet_label} dedicated={use_dedicated} "
        f"speed_profile={profile} policy=adult_18_plus_only"
    )
    if unets.get("model_high"):
        print(f"  UNet HIGH: {unets['model_high']}")
        print(f"  UNet LOW : {unets['model_low']}")

    # quant only used when not overriding with remix paths
    quant = args.wan_quant
    unet_profile = unets.get("unet_profile")
    if unet_profile in ("base",):
        unet_profile = quant

    result = generate_i2v(
        input_image_path=args.input,
        prompt_text=prompt,
        negative_text=negative,
        output_filename=out,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        frame_rate=args.fps,
        backend="wan22",
        timeout_sec=args.timeout,
        attention_mode=args.attention,
        dry_run=bool(args.dry_run),
        profile=profile,
        block_swap=args.block_swap,
        wan_quant=quant,
        wan_scheduler=args.wan_scheduler,
        wan_shift=args.wan_shift,
        meta_out=args.meta_out,
        wan_model_high=unets.get("model_high"),
        wan_model_low=unets.get("model_low"),
        wan_unet_profile=unet_profile if not unets.get("model_high") else "remix",
        extra_lora_high=loras.get("lora_high") if want_lora else None,
        extra_lora_low=loras.get("lora_low") if want_lora else None,
        extra_lora_strength_high=float(loras.get("strength_high") or 0.85),
        extra_lora_strength_low=float(loras.get("strength_low") or 0.9),
        tool_policy="adult_18_plus_only",
        tool_name="wan22_nsfw_i2v",
    )

    if result.get("ok") and result.get("meta"):
        m = result["meta"]
        m["policy"] = "adult_18_plus_only"
        m["tool"] = "wan22_nsfw_i2v"
        m["nsfw_unet"] = unets
        m["nsfw_loras"] = {
            "high": loras.get("lora_high"),
            "low": loras.get("lora_low"),
            "strength_high": loras.get("strength_high"),
            "strength_low": loras.get("strength_low"),
            "has_pair": loras.get("has_pair"),
            "source": loras.get("source"),
            "enabled": want_lora,
        }

    if not result.get("ok"):
        print("FAIL", result.get("error"), result.get("message"), file=sys.stderr)
        return 1
    print("OK", result.get("output_path") or out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
