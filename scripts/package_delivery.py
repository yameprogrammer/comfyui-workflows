#!/usr/bin/env python3
"""Package an episode into deliveries/ for client handoff (folder + zip)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.delivery_package import DELIVERIES_DIR, package_episode_delivery
from lib.story_package import validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build user delivery package under deliveries/<episode>__<stamp>/"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--stage",
        choices=["auto", "deliver", "work"],
        default="auto",
        help="Which per-shot clips to include (auto prefers deliver)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Package folder name (default: <episode>__UTC_timestamp)",
    )
    parser.add_argument("--zip", dest="make_zip", action="store_true", default=True)
    parser.add_argument("--no-zip", dest="make_zip", action="store_false")
    parser.add_argument("--no-meta", action="store_true", help="Skip META/ copy")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        result = package_episode_delivery(
            args.episode,
            stage=args.stage,
            include_meta=not args.no_meta,
            make_zip=args.make_zip,
            package_name=args.name,
            dry_run=args.dry_run,
        )
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING
    except Exception as e:
        print(f"[ERROR] code=30 {e}", file=sys.stderr)
        return EXIT_FAIL

    if args.dry_run:
        print("[dry-run] would package:")
        print(f"  dir={result.get('package_dir')}")
        print(f"  final={result.get('final')}")
        print(f"  stills={result.get('stills')} clips={result.get('clips')}")
        print(f"  zip={result.get('zip')}")
        print(f"  deliveries_root={DELIVERIES_DIR}")
        return EXIT_OK

    if not result.get("ok"):
        print(f"[ERROR] {result}", file=sys.stderr)
        return EXIT_FAIL

    print("OK delivery package")
    print(f"  folder={result['package_dir']}")
    if result.get("zip_path"):
        print(f"  zip={result['zip_path']}")
    print(f"  final_included={result.get('final_included')}")
    print(f"  stills={result.get('stills')} clips={result.get('clips')}")
    print(f"  manifest={result.get('manifest')}")
    print("Hand this folder or zip to the user.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
