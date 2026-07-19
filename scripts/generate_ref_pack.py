#!/usr/bin/env python3
"""
Lightweight identity ref pack (no characters/ package).

TRANSFORM / ASSETS-lite shelf:
  master face + clean + angles + soft expressions + contact sheet.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.ref_pack import REF_PACK_PROFILES, run_ref_pack


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Build a small identity ref pack from one face image "
            "(master, angles, soft expr). Does not create characters/<id>."
        )
    )
    p.add_argument("--input", "-i", default=None, help="Source face / portrait")
    p.add_argument(
        "--pack-dir",
        "-o",
        default=None,
        help="Output directory for pack files",
    )
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument(
        "--profile",
        default="default",
        choices=list(REF_PACK_PROFILES.keys()),
        help="copy|quick|default|full (default: default = soft + one angle)",
    )
    p.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print ref_pack profiles and exit",
    )
    p.add_argument(
        "--no-angles",
        action="store_true",
        help="Skip Qwen multi-angle views (overrides profile)",
    )
    p.add_argument(
        "--no-soft",
        action="store_true",
        help="Skip clean master + expression variants (overrides profile)",
    )
    p.add_argument(
        "--views",
        default=None,
        help="Comma view keys for angles (overrides profile angle list)",
    )
    p.add_argument("--no-contact-sheet", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        for pid, spec in REF_PACK_PROFILES.items():
            print(f"{pid:10s} {spec.get('note')}")
        return 0

    if not args.input or not args.pack_dir:
        p.error("--input/-i and --pack-dir/-o required")

    views = (
        [x.strip() for x in args.views.split(",") if x.strip()] if args.views else None
    )
    # None = follow profile; True/False only when flag forces off
    do_angles = False if args.no_angles else None
    do_soft = False if args.no_soft else None
    r = run_ref_pack(
        input_image=args.input,
        pack_dir=args.pack_dir,
        model_type=args.model,
        seed=args.seed,
        do_angles=do_angles,
        do_soft_variants=do_soft,
        angle_views=views,
        timeout_sec=args.timeout,
        contact_sheet=not args.no_contact_sheet,
        profile=args.profile,
    )

    if r.get("ok"):
        print(f"[ref_pack] ok → {r.get('pack_dir')}")
        if r.get("primary_ref"):
            print(f"[ref_pack] primary_ref (use as -i) → {r.get('primary_ref')}")
        if r.get("manifest_path"):
            print(f"[ref_pack] manifest → {r.get('manifest_path')}")
        if r.get("partial"):
            print("[ref_pack] partial (some stages failed)")
        for a in (r.get("artifacts") or [])[:16]:
            print(f"  - {a.get('role')}: {a.get('path')}")
        print(
            "[ref_pack] next: character_consistent / i2v / style_transfer "
            "with primary_ref; promote to characters/ only if long-term SSOT needed"
        )
        return 0
    print(
        f"[ref_pack] FAIL {r.get('error')} {r.get('message')}",
        file=sys.stderr,
    )
    print(json.dumps({"ok": False, "error": r.get("error")}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
