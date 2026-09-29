#!/usr/bin/env python3
"""Soft-reset ComfyUI without killing the process.

Preferred recovery when Comfy feels stuck / VRAM thrash / timed-out job:

  1) interrupt running job
  2) clear pending queue
  3) POST /free (unload models + free memory)
  4) report queue + VRAM

Only escalate to process restart when this reports WEDGED / still hung.

Usage (from F:\\Agent_media_tools):
  python scripts/comfy_soft_reset.py
  python scripts/comfy_soft_reset.py --no-unload   # free tensors only
  python scripts/comfy_soft_reset.py --status-only
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from typing import Any

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.comfy_client import (  # noqa: E402
    DEFAULT_SERVER,
    free_comfy_memory,
    get_queue,
    interrupt_comfy,
)


def _post(server: str, path: str, body: dict[str, Any], timeout: float = 60) -> Any:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def _system_stats(server: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"http://{server}/system_stats", timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _summarize_queue(q: dict[str, Any]) -> dict[str, int]:
    return {
        "running": len(q.get("queue_running") or []),
        "pending": len(q.get("queue_pending") or []),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Interrupt + clear queue + free VRAM (no process kill)")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--status-only", action="store_true")
    p.add_argument("--no-unload", action="store_true", help="free_memory only, keep loaded models")
    p.add_argument("--timeout", type=float, default=120.0)
    args = p.parse_args()

    try:
        before = get_queue(args.server, ensure=False)
    except Exception as e:
        print(f"[ERROR] Comfy not reachable at {args.server}: {e}", file=sys.stderr)
        print("Escalate: restart process only if soft reset cannot connect.", file=sys.stderr)
        return 2

    print("queue_before", _summarize_queue(before))
    try:
        stats = _system_stats(args.server)
        devices = stats.get("devices") or []
        if devices:
            d0 = devices[0]
            print(
                "vram_before_mb",
                {
                    "free": round((d0.get("vram_free") or 0) / (1024 * 1024), 1),
                    "total": round((d0.get("vram_total") or 0) / (1024 * 1024), 1),
                },
            )
    except Exception:
        pass

    if args.status_only:
        return 0

    print("interrupt", interrupt_comfy(args.server))
    print("queue_clear", _post(args.server, "/queue", {"clear": True}))
    print(
        "free",
        free_comfy_memory(
            args.server,
            unload_models=not args.no_unload,
            free_memory=True,
            timeout=args.timeout,
            ensure=False,
        ),
    )

    after = get_queue(args.server, ensure=False)
    print("queue_after", _summarize_queue(after))
    try:
        stats = _system_stats(args.server)
        devices = stats.get("devices") or []
        if devices:
            d0 = devices[0]
            print(
                "vram_after_mb",
                {
                    "free": round((d0.get("vram_free") or 0) / (1024 * 1024), 1),
                    "total": round((d0.get("vram_total") or 0) / (1024 * 1024), 1),
                },
            )
    except Exception:
        pass

    if _summarize_queue(after)["running"] > 0:
        print(
            "[WARN] job still running after interrupt+free — may be WEDGED; "
            "escalate with restart_comfyui only then.",
            file=sys.stderr,
        )
        return 1

    print("OK soft_reset — safe to re-enqueue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
