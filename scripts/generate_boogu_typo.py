#!/usr/bin/env python3
"""Boogu + Ideogram4 + Krea2 — typography / design poster pipeline tool.

Workflow: NEWKrea2BooguIdeogram4_booguKrea2
  Boogu (dense text) → Ideogram4 refine → Krea2 polish [→ optional SeedVR2]

  python scripts/generate_boogu_typo.py -p "poster JSON or prose..." -o out.png
  python scripts/generate_boogu_typo.py --mode boogu -p "..." -o draft.png
  python scripts/generate_boogu_typo.py --mode pipeline --prefer krea2 -p "..." -o final.png

Not a general T2I replacement for Moody/Krea alone — use when you need
**readable dense typography + design layout + photoreal polish**.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.boogu_ideogram_krea_runner import generate_boogu_typo

DEFAULT_OUT = r"F:\generated_images\boogu_typo_out.png"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Boogu+Ideogram4+Krea2 typography pipeline (RedCraft collection WF)"
    )
    p.add_argument("--prompt", "-p", default=None, help="Caption: Ideogram JSON or prose")
    p.add_argument("--prompt-file", default=None)
    p.add_argument(
        "--mode",
        default="pipeline",
        choices=["boogu", "pipeline", "upscale"],
        help="boogu=text draft only; pipeline=Boogu→Ideo→Krea; upscale=+SeedVR2",
    )
    p.add_argument(
        "--prefer",
        default="krea2",
        choices=["boogu", "ideogram", "krea2", "seedvr2", "any"],
        help="Which stage SaveImage to download as -o",
    )
    p.add_argument("--output", "-o", default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=1152)
    p.add_argument("--boogu-steps", type=int, default=None, help="Default pack 8")
    p.add_argument("--krea-denoise", type=float, default=None, help="Default pack 0.5")
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            caption = f.read().strip()
    else:
        caption = (args.prompt or "").strip()
    if not caption:
        p.error("--prompt or --prompt-file required")

    print(
        f"BooguTypo mode={args.mode} prefer={args.prefer} "
        f"size={args.width}x{args.height} caption[:80]={caption[:80]!r}"
    )

    if args.dry_run:
        from lib.boogu_ideogram_krea_runner import build_api

        api, meta = build_api(
            caption=caption,
            mode=args.mode,
            seed=args.seed,
            width=args.width,
            height=args.height,
            boogu_steps=args.boogu_steps,
            krea_denoise=args.krea_denoise,
        )
        print(f"OK dry-run nodes={len(api)} meta={meta}")
        for nid in ("6", "9", "11", "907:186", "915", "927", "922", "926", "912"):
            if nid in api:
                print(f"  {nid} {api[nid].get('class_type')} keys={list((api[nid].get('inputs') or {}).keys())[:8]}")
        return 0

    r = generate_boogu_typo(
        caption=caption,
        output_path=args.output,
        mode=args.mode,
        seed=args.seed,
        width=args.width,
        height=args.height,
        boogu_steps=args.boogu_steps,
        krea_denoise=args.krea_denoise,
        prefer_save=args.prefer,
        timeout_sec=args.timeout,
    )
    if r.get("ok"):
        print("OK", r.get("output_path") or args.output)
        return 0
    print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
