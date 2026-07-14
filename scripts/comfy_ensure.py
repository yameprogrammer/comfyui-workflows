#!/usr/bin/env python3
"""Ensure local ComfyUI is running (probe + auto-start if down).

Usage:
  python scripts/comfy_ensure.py
  python scripts/comfy_ensure.py --status
  python scripts/comfy_ensure.py --no-start
  python scripts/comfy_ensure.py --server 127.0.0.1:8188 --timeout 180

Env:
  AGENT_COMFY_AUTOSTART=0
  AGENT_COMFY_LAUNCH_BAT=F:\\...\\run_....bat
  AGENT_COMFY_READY_TIMEOUT_SEC=180
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_comfy_running,
    is_comfy_reachable,
    resolve_launch_bat,
    resolve_ready_timeout_sec,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure ComfyUI API is up (auto-start if needed)")
    ap.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"host:port (default {DEFAULT_SERVER})",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="seconds to wait for ready (default AGENT_COMFY_READY_TIMEOUT_SEC or 180)",
    )
    ap.add_argument(
        "--status",
        action="store_true",
        help="probe only; do not start; exit 0 if up else 1",
    )
    ap.add_argument(
        "--no-start",
        action="store_true",
        help="same as --status (explicit name)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="ignore recent-launch cooldown and allow re-spawn if still down",
    )
    ap.add_argument("--json", action="store_true", help="print result JSON")
    ap.add_argument("-q", "--quiet", action="store_true", help="less stderr progress")
    args = ap.parse_args()

    server = args.server
    if args.status or args.no_start:
        up = is_comfy_reachable(server)
        payload = {
            "ok": up,
            "server": server,
            "action": "probe",
            "reachable": up,
            "launch_bat": resolve_launch_bat(),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ComfyUI {server}: {'UP' if up else 'DOWN'}")
            if not up:
                print(f"launcher: {resolve_launch_bat()}")
        return 0 if up else 1

    try:
        result = ensure_comfy_running(
            server,
            timeout_sec=args.timeout,
            force=bool(args.force),
            log=not args.quiet,
        )
    except (ConnectionError, FileNotFoundError, TimeoutError) as e:
        err = {
            "ok": False,
            "server": server,
            "error": str(e),
            "launch_bat": resolve_launch_bat(),
            "ready_timeout_sec": resolve_ready_timeout_sec(args.timeout),
        }
        if args.json:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print(f"FAIL: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"OK server={result.get('server')} action={result.get('action')} "
            f"waited_sec={result.get('waited_sec'):.1f}"
        )
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
