#!/usr/bin/env python3
"""SDXL photoreal T2I — Juggernaut / Dreamshaper Lightning / Pony / NSFW ckpt.

NOT Illustrious (use generate_illustrious_* for Danbooru XL).
NOT cinematic default (use generate_krea).
18+ default remains generate_krea_nsfw; --model nsfw is an SDXL look only.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.sdxl_runner import check_sdxl_models, generate_sdxl
from lib.still_model_profiles import SDXL_MODEL_CHOICES, format_profile_table


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="SDXL photoreal T2I (Juggernaut / Lightning / Pony). Not Illustrious, not Krea."
    )
    p.add_argument(
        "--model",
        "-m",
        choices=list(SDXL_MODEL_CHOICES),
        default="juggernaut",
        help="juggernaut (default) | lightning (scout) | pony | nsfw",
    )
    p.add_argument("--prompt", "-p", default="")
    p.add_argument("--negative", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--sampler", default=None)
    p.add_argument("--scheduler", default=None)
    p.add_argument("--ckpt", default=None, help="Override checkpoint filename")
    p.add_argument(
        "--no-pony-scores",
        action="store_true",
        help="Do not prepend score_9 tags when --model pony",
    )
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--check-models", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        print(format_profile_table("sdxl"))
        return 0
    if args.check_models:
        chk = check_sdxl_models(None)
        print(json.dumps(chk, indent=2))
        return 0 if chk["ok"] else 11

    prompt = (args.prompt or "").strip()
    if not prompt:
        p.error("--prompt required")

    out = args.output
    if not out:
        out = os.path.join(r"F:\generated_images", f"sdxl_{args.model}.png")

    r = generate_sdxl(
        prompt=prompt,
        output_path=out,
        model=args.model,
        negative=args.negative,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        sampler=args.sampler,
        scheduler=args.scheduler,
        ckpt_name=args.ckpt,
        pony_score_tags=not args.no_pony_scores,
        timeout_sec=args.timeout,
        dry_run=args.dry_run,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    print("OK", r.get("output_path") or out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
