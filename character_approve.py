#!/usr/bin/env python3
"""Promote a generated ref image into approved/ with a stable alias."""

from __future__ import annotations

import argparse
import sys

from lib.character_package import (
    APPROVE_ALIASES,
    CharacterPackage,
    validate_character_id,
)


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PACKAGE_MISSING = 11
EXIT_SOURCE_MISSING = 20
EXIT_ALIAS_INVALID = 22


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Approve character sheet asset into approved/")
    parser.add_argument("--id", required=True)
    parser.add_argument("--from", dest="from_path", required=True, help="Source image path (package-relative or abs)")
    parser.add_argument(
        "--as",
        dest="alias",
        required=True,
        help=f"Approve alias, one of: {', '.join(sorted(APPROVE_ALIASES))}",
    )
    parser.add_argument("--set-primary", action="store_true", help="Set as identity.primary_ref")
    parser.add_argument(
        "--status",
        choices=["draft", "in_review", "approved", "deprecated"],
        default=None,
        help="Force bible/manifest status",
    )
    args = parser.parse_args(argv)

    if not validate_character_id(args.id):
        print(f"[ERROR] code=2 message=invalid id {args.id}", file=sys.stderr)
        return EXIT_USAGE

    if args.alias not in APPROVE_ALIASES:
        print(f"[ERROR] code=22 message=invalid alias {args.alias}", file=sys.stderr)
        print(f"Allowed: {', '.join(sorted(APPROVE_ALIASES))}", file=sys.stderr)
        return EXIT_ALIAS_INVALID

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] code=11 message=package missing {args.id}", file=sys.stderr)
        return EXIT_PACKAGE_MISSING

    source = pkg.resolve(args.from_path)
    try:
        dest = pkg.approve(source, args.alias, set_primary=args.set_primary)
    except FileNotFoundError:
        print(f"[ERROR] code=20 message=source missing {source}", file=sys.stderr)
        return EXIT_SOURCE_MISSING
    except ValueError as e:
        print(f"[ERROR] code=22 message={e}", file=sys.stderr)
        return EXIT_ALIAS_INVALID

    if args.status:
        pkg.bible["status"] = args.status
        pkg.manifest["status"] = args.status
        pkg.save_bible()
        pkg.save_manifest()

    missing = pkg.manifest.get("missing_mvp", [])
    print(f"OK approved={args.alias}")
    print(f"  path=characters/{args.id}/approved/{args.alias}.png")
    print(f"  dest={dest}")
    if missing:
        print(f"missing_mvp ({len(missing)}): {', '.join(missing)}")
    else:
        print("L2 MVP approve set complete (required aliases present)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
