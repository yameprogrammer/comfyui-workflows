#!/usr/bin/env python3
"""Fast draft Krea2 T2I (smaller canvas / scout).

Lonecat v7 Draft Mode analogue — not a separate graph, just scout settings.

  python scripts/generate_krea_draft.py -p "cinematic portrait..." -o scout.png --seed 1
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from generate_krea import generate_krea_image


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 draft/scout T2I (768 default)")
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument("--output", "-o", default="dumps/krea2_draft_out.png")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=768)
    p.add_argument("--timeout", type=float, default=300)
    args = p.parse_args(argv)

    print(f"Krea2 DRAFT size={args.width}x{args.height} out={args.output}")
    ok = generate_krea_image(
        prompt_text=args.prompt,
        output_filename=args.output,
        seed=args.seed,
        width=args.width,
        height=args.height,
        timeout_sec=float(args.timeout),
        return_dict=False,
    )
    if not ok:
        print("[draft] FAIL", file=sys.stderr)
        return 1
    print(f"[draft] ok → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
