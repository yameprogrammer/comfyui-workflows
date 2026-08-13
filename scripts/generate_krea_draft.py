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
    p.add_argument("--output", "-o", default=None, help="Project path (required unless AGENT_WORKSPACE)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=768)
    p.add_argument("--timeout", type=float, default=300)
    args = p.parse_args(argv)

    from lib.output_policy import resolve_media_output

    out = resolve_media_output(args.output, default_name="krea2_draft_out.png")
    print(f"Krea2 DRAFT size={args.width}x{args.height} out={out}")
    ok = generate_krea_image(
        prompt_text=args.prompt,
        output_filename=out,
        seed=args.seed,
        width=args.width,
        height=args.height,
        timeout_sec=float(args.timeout),
        return_dict=False,
    )
    if not ok:
        print("[draft] FAIL", file=sys.stderr)
        return 1
    print(f"[draft] ok → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
