#!/usr/bin/env python3
"""Start an episode commission from a brief JSON (agent intake)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.commission import apply_commission, load_brief, validate_brief, warn_assets

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAIL = 30


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold stories/<episode> from a commission brief JSON"
    )
    parser.add_argument(
        "--brief",
        "-b",
        required=True,
        help="Path to commission brief JSON (see stories/examples/)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--print-schema-path",
        action="store_true",
        help="Print path to JSON schema and exit",
    )
    args = parser.parse_args(argv)

    if args.print_schema_path:
        from lib.comfy_client import WORKSPACE_ROOT
        import os

        print(os.path.join(WORKSPACE_ROOT, "docs", "commission_brief.schema.json"))
        return EXIT_OK

    try:
        brief = load_brief(args.brief)
    except Exception as e:
        print(f"[ERROR] code=2 cannot load brief: {e}", file=sys.stderr)
        return EXIT_USAGE

    errs = validate_brief(brief)
    if errs:
        print("[ERROR] brief invalid:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return EXIT_USAGE

    for w in warn_assets(brief):
        print(f"[WARN] {w}")

    result = apply_commission(brief, force=args.force, dry_run=args.dry_run)
    if not result.get("ok"):
        for e in result.get("errors") or [result]:
            print(f"[ERROR] {e}", file=sys.stderr)
        return EXIT_FAIL

    if args.dry_run:
        print("[dry-run] would create:")
        print(json.dumps({k: result[k] for k in result if k != "ok"}, ensure_ascii=False, indent=2))
        return EXIT_OK

    print(f"OK commission episode={result['episode_id']}")
    print(f"  path={result['path']}")
    print(f"  format={result['format']} look={result['look_id']} shots={result['shot_count']}")
    for w in result.get("warnings") or []:
        print(f"  warn: {w}")
    print("Next:")
    for line in result.get("next") or []:
        print(f"  {line}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
