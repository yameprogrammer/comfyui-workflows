#!/usr/bin/env python3
"""Print / JSON-dump episode readiness for the next pipeline step."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.episode_status import episode_status_report, format_status_text
from lib.story_package import validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Episode readiness status")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument(
        "--json-out",
        default=None,
        help="Write JSON report path (default: stories/<ep>/meta/status.json if set)",
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        report = episode_status_report(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_status_text(report))

    if args.json_out:
        from lib.comfy_client import write_meta

        write_meta(args.json_out, report)
        print(f"wrote {args.json_out}", file=sys.stderr)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
