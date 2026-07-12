#!/usr/bin/env python3
"""Mark cast candidates as shortlist (human pre-promote picks)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.cast_pool import add_shortlist, format_cast_status, validate_cast_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Add cast candidates to shortlist")
    p.add_argument("--cast", required=True)
    p.add_argument(
        "--file",
        "-f",
        action="append",
        required=True,
        help="Candidate filename or candidates/… path (repeatable)",
    )
    args = p.parse_args(argv)

    if not validate_cast_id(args.cast):
        print("[ERROR] bad cast id", file=sys.stderr)
        return EXIT_USAGE
    try:
        add_shortlist(args.cast, args.file)
    except FileNotFoundError:
        print(f"[ERROR] cast missing: {args.cast}", file=sys.stderr)
        return EXIT_MISSING
    print(format_cast_status(args.cast))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
