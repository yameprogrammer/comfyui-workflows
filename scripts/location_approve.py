#!/usr/bin/env python3
"""Promote a location ref into approved/ with a stable alias."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.location_package import (
    APPROVE_ALIASES,
    LocationPackage,
    get_location_profile,
    validate_location_id,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_SOURCE = 20
EXIT_ALIAS = 22


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Approve location asset into approved/")
    parser.add_argument("--id", required=True)
    parser.add_argument("--from", dest="from_path", required=True)
    parser.add_argument(
        "--as",
        dest="alias",
        required=True,
        help=f"One of: {', '.join(sorted(APPROVE_ALIASES))}",
    )
    parser.add_argument("--set-primary", action="store_true")
    parser.add_argument(
        "--status",
        choices=["draft", "in_review", "approved", "deprecated"],
        default=None,
    )
    parser.add_argument("--profile", choices=["video_ref", "artbook"], default=None)
    args = parser.parse_args(argv)

    if not validate_location_id(args.id):
        print(f"[ERROR] code=2 invalid id", file=sys.stderr)
        return EXIT_USAGE
    if args.alias not in APPROVE_ALIASES:
        print(f"[ERROR] code=22 invalid alias {args.alias}", file=sys.stderr)
        print(f"Allowed: {', '.join(sorted(APPROVE_ALIASES))}", file=sys.stderr)
        return EXIT_ALIAS

    try:
        pkg = LocationPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] code=11 package missing", file=sys.stderr)
        return EXIT_MISSING

    if args.profile:
        try:
            profile = get_location_profile(args.profile)
            pkg.bible["active_profile"] = profile["id"]
            pkg.save_bible()
        except KeyError as e:
            print(f"[ERROR] code=2 {e}", file=sys.stderr)
            return EXIT_USAGE

    source = pkg.resolve(args.from_path)
    try:
        dest = pkg.approve(source, args.alias, set_primary=args.set_primary)
    except FileNotFoundError:
        print(f"[ERROR] code=20 source missing {source}", file=sys.stderr)
        return EXIT_SOURCE
    except ValueError as e:
        print(f"[ERROR] code=22 {e}", file=sys.stderr)
        return EXIT_ALIAS

    if args.status:
        pkg.bible["status"] = args.status
        pkg.manifest["status"] = args.status
        pkg.save_bible()
        pkg.save_manifest()

    missing = pkg.manifest.get("missing_mvp", [])
    print(f"OK approved={args.alias}")
    print(f"  path=locations/{args.id}/approved/{args.alias}.png")
    print(f"  dest={dest}")
    if missing:
        print(f"missing_mvp ({len(missing)}): {', '.join(missing)}")
    else:
        print("L2 MVP approve set complete")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
