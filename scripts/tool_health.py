#!/usr/bin/env python3
"""Comfy backend / tool health checks for agents.

Examples:
  python scripts/tool_health.py --backend infinitetalk
  python scripts/tool_health.py --all-s2v
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.s2v_backend_health import (
    check_backend_nodes,
    fetch_object_info,
    list_checked_backends,
)

EXIT_OK = 0
EXIT_DEGRADED = 3
EXIT_USAGE = 2
EXIT_COMFY = 40


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Tool / S2V backend health (Comfy nodes)")
    p.add_argument(
        "--backend",
        action="append",
        dest="backends",
        default=None,
        help="S2V backend id (repeatable). Default: none unless --all-s2v",
    )
    p.add_argument(
        "--all-s2v",
        action="store_true",
        help="Check all backends registered in REQUIRED_NODES_S2V",
    )
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--timeout", type=float, default=60.0)
    args = p.parse_args(argv)

    backends: list[str] = []
    if args.all_s2v:
        backends.extend(list_checked_backends())
    if args.backends:
        backends.extend(args.backends)
    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for b in backends:
        b = (b or "").strip().lower()
        if b and b not in seen:
            seen.add(b)
            ordered.append(b)

    if not ordered:
        print(
            "[ERROR] pass --backend NAME and/or --all-s2v\n"
            f"  registered: {', '.join(list_checked_backends()) or '(none)'}",
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        object_info = fetch_object_info(args.server, timeout=args.timeout)
    except Exception as e:
        print(f"[ERROR] Comfy unreachable at {args.server}: {e}", file=sys.stderr)
        return EXIT_COMFY

    print(f"server={args.server} object_info_types={len(object_info)}")
    print(f"{'backend':<16} {'ok':<6} {'missing':<8} detail")
    print("-" * 72)

    any_fail = False
    for b in ordered:
        r = check_backend_nodes(b, object_info=object_info, server=args.server)
        ok = bool(r.get("ok"))
        if not ok:
            any_fail = True
        missing = r.get("missing") or []
        detail = "OK"
        if r.get("skipped"):
            detail = r.get("message") or "skipped"
        elif missing:
            detail = ", ".join(missing[:6])
            if len(missing) > 6:
                detail += f" (+{len(missing) - 6})"
        print(f"{b:<16} {str(ok):<6} {len(missing):<8} {detail}")
        if r.get("hint") and not ok:
            print(f"  hint: {r['hint']}")

    if any_fail:
        print("\nRESULT: DEGRADED (exit 3)")
        return EXIT_DEGRADED
    print("\nRESULT: OK")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
