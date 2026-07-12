#!/usr/bin/env python3
"""List / validate Look packages; optional approve flag."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import utc_now_iso
from lib.look_package import (
    list_looks,
    load_json,
    look_dir,
    look_readiness,
    save_json,
    validate_look_id,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Look/style core status")
    p.add_argument("--id", default=None, help="look_id")
    p.add_argument("--list", action="store_true", help="List all looks")
    p.add_argument(
        "--approve",
        action="store_true",
        help="With --id: mark bible.status=approved if cores ok",
    )
    args = p.parse_args(argv)

    if args.list or not args.id:
        looks = list_looks()
        if not looks:
            print("no looks under looks/")
            return EXIT_OK
        for lid in looks:
            r = look_readiness(lid)
            flag = "OK" if r["ok"] else "BAD"
            print(
                f"{lid:28} [{flag}] status={r['status']:10} "
                f"pos_len={r['positive_len']} mood_refs={r['has_mood_refs']}"
            )
        return EXIT_OK

    if not validate_look_id(args.id):
        print("[ERROR] bad look id", file=sys.stderr)
        return EXIT_USAGE
    r = look_readiness(args.id)
    if r["status"] == "missing" and "package_dir" in r["missing"]:
        print(f"[ERROR] look missing: {args.id}", file=sys.stderr)
        return EXIT_MISSING
    print(f"look={r['look_id']} name={r.get('name')}")
    print(f"  status={r['status']} ok={r['ok']}")
    print(f"  positive_len={r['positive_len']} mood_refs={r['has_mood_refs']}")
    if r["missing"]:
        print(f"  missing={r['missing']}")
    else:
        print("  cores=present")

    if args.approve:
        if not r["ok"]:
            print("[ERROR] cannot approve — fix missing cores", file=sys.stderr)
            return EXIT_USAGE
        path = look_dir(args.id)
        bible = load_json(f"{path}/bible.json")
        bible["status"] = "approved"
        bible["updated_at"] = utc_now_iso()
        save_json(f"{path}/bible.json", bible)
        print("  status → approved")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
