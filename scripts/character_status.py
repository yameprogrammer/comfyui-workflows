#!/usr/bin/env python3
"""Status for cast pools and character packages (casting process ops view)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.cast_pool import format_cast_status, list_casts, load_manifest, validate_cast_id
from lib.character_package import CharacterPackage, validate_character_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Character / cast pool status")
    p.add_argument("--cast", default=None, help="cast_id status")
    p.add_argument("--id", default=None, help="character_id package status")
    p.add_argument("--list-casts", action="store_true", help="List all cast pools")
    args = p.parse_args(argv)

    if args.list_casts:
        casts = list_casts()
        if not casts:
            print("no cast pools under characters/casts/")
            return EXIT_OK
        for cid in casts:
            try:
                man = load_manifest(cid)
                n = len(man.get("candidates") or [])
                print(
                    f"{cid:24} status={man.get('status'):12} "
                    f"cands={n} promoted={man.get('promoted_character_id') or '—'}"
                )
            except Exception as e:
                print(f"{cid:24} ERROR {e}")
        return EXIT_OK

    if args.cast:
        if not validate_cast_id(args.cast):
            print("[ERROR] bad cast id", file=sys.stderr)
            return EXIT_USAGE
        try:
            print(format_cast_status(args.cast))
        except FileNotFoundError:
            print(f"[ERROR] cast missing: {args.cast}", file=sys.stderr)
            return EXIT_MISSING
        return EXIT_OK

    if args.id:
        if not validate_character_id(args.id):
            print("[ERROR] bad character id", file=sys.stderr)
            return EXIT_USAGE
        try:
            pkg = CharacterPackage.load(args.id)
        except FileNotFoundError:
            print(f"[ERROR] package missing: {args.id}", file=sys.stderr)
            return EXIT_MISSING
        missing = pkg.recompute_missing_mvp()
        pkg.save_manifest()
        print(f"character={args.id}")
        print(f"  status={pkg.bible.get('status')} level={pkg.manifest.get('level')}")
        print(f"  profile={pkg.active_profile_id()}")
        print(f"  primary_ref={(pkg.bible.get('identity') or {}).get('primary_ref')}")
        print(f"  approved={list((pkg.manifest.get('approved') or {}).keys())}")
        print(f"  missing_mvp={missing}")
        if missing:
            print("  next=character_expand_sheets --sheets all_mvp  then approve exprs")
        else:
            print("  next=shot_compose / video (L2 MVP complete)")
        return EXIT_OK

    print("[ERROR] pass --cast, --id, or --list-casts", file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
