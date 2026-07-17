#!/usr/bin/env python3
"""Krea2 uncensored T2I — factory tool for adult (NSFW / 빨간맛) stills.

Workflow: krea2SFWNSFWUncensoredImageTo_v10
Preset:   krea2_t2i_v10 (same graph; abliterated CLIP + Krea2 turbo)

  python scripts/generate_krea_nsfw.py -p "adult woman in lingerie, ..." -o out.png
  python scripts/generate_krea_nsfw.py --prompt-file prompt.txt --seed 42

Hard policy (agents):
  - Subjects must be clearly **adult 18+** (or fictional adult).
  - Refuse/decline: anyone 17 or under, ambiguous age, school-uniform sexualization of minors.
  - For SFW photoreal defaults prefer generate_moody / Lonecat, not this CLI.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_krea import generate_krea_image
from lib.comfy_client import ok_result

DEFAULT_PRESET = "krea2_t2i_v10"
# Portrait-friendly default (Krea2 common 2:3-ish)
DEFAULT_W = 832
DEFAULT_H = 1216


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Krea2 uncensored T2I (NSFW / 빨간맛 stills) via workflow_api preset"
    )
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=DEFAULT_W)
    p.add_argument("--height", type=int, default=DEFAULT_H)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        help=f"API preset (default {DEFAULT_PRESET})",
    )
    p.add_argument(
        "--unet-name",
        default=None,
        help="Optional UNET override (default from ports: Krea2Turbo/krea2_turbo_fp8_scaled)",
    )
    args = p.parse_args(argv)

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt or --prompt-file required")

    # Light guardrail language for agents (not a full classifier)
    low = prompt.lower()
    banned = (
        "child",
        "kid",
        "loli",
        "shota",
        "underage",
        "teen boy",
        "teen girl",
        "schoolgirl",
        "schoolboy",
        "12 year",
        "14 year",
        "15 year",
        "16 year",
        "17 year",
    )
    hit = [b for b in banned if b in low]
    if hit:
        print(
            f"FAIL AGE_POLICY: prompt hits {hit!r}. "
            "This tool is adult-only (18+).",
            file=sys.stderr,
        )
        return 11

    out = args.output
    if not out:
        out = os.path.join(
            r"F:\generated_images",
            "krea2_nsfw_out.png",
        )

    print(
        f"Krea2 NSFW T2I preset={args.preset} size={args.width}x{args.height} "
        f"(uncensored / abliterated CLIP path)"
    )
    r = generate_krea_image(
        prompt_text=prompt,
        output_filename=out,
        seed=args.seed,
        width=args.width,
        height=args.height,
        timeout_sec=args.timeout,
        preset=args.preset,
        unet_name=args.unet_name,
        return_dict=True,
    )
    if isinstance(r, dict) and r.get("ok"):
        meta_path = os.path.splitext(out)[0] + ".meta.json"
        if os.path.isfile(meta_path):
            try:
                import json

                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["role"] = "nsfw_still"
                meta["tool"] = "generate_krea_nsfw"
                meta["policy"] = "adult_18_plus_only"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        print("OK", r.get("output_path") or out)
        return 0
    if r is True:
        print("OK", out)
        return 0
    err = r.get("error") if isinstance(r, dict) else "FAIL"
    msg = r.get("message") if isinstance(r, dict) else str(r)
    print(f"FAIL {err}: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
