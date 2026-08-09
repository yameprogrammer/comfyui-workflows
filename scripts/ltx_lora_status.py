#!/usr/bin/env python3
"""LTX optional LoRA status for agents (Asian Face, Relight, …).

  python scripts/ltx_lora_status.py
  python scripts/ltx_lora_status.py --json
  python scripts/ltx_lora_status.py download-relight
  python scripts/ltx_lora_status.py show asian_face

SSOT: docs/ltx_loras_agent.md · catalog: lib/ltx_lora_catalog.py
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.ltx_lora_catalog import catalog, status_summary, try_download_relight

EXIT_OK = 0
EXIT_MISSING = 3
EXIT_USAGE = 2
EXIT_DOWNLOAD_FAIL = 11


def _print_human(entries: list[dict]) -> None:
    print("LTX optional LoRAs (agent catalog)")
    print(f"{'id':<14} {'status':<16} path / note")
    print("-" * 78)
    for e in entries:
        st = e.get("status") or "?"
        path = e.get("path") or "(none)"
        auto = "auto-ON" if e.get("auto_inject") else "manual"
        print(f"{e.get('id', '?'):<14} {st:<16} {auto}")
        print(f"{'':14} {path}")
        when0 = (e.get("when") or [""])[0]
        if when0:
            print(f"{'':14} when: {when0}")
    print()
    print("SSOT: docs/ltx_loras_agent.md")
    print("Relight install: python scripts/ltx_lora_status.py download-relight")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="LTX optional LoRA status (Asian Face / Relight)"
    )
    p.add_argument(
        "command",
        nargs="?",
        default="list",
        choices=["list", "download-relight", "show"],
        help="list (default) | download-relight | show <id>",
    )
    p.add_argument("id", nargs="?", default=None, help="LoRA id for show")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON")
    p.add_argument(
        "--token",
        default=None,
        help="HF token for download-relight (else HF_TOKEN / logged-in cache)",
    )
    args = p.parse_args(argv)

    if args.command == "download-relight":
        r = try_download_relight(token=args.token)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        elif r.get("ok"):
            print("OK relight downloaded")
            print("  path:", r.get("path"))
            print("  size:", r.get("size"))
            if r.get("alias"):
                print("  alias:", r.get("alias"))
        else:
            print("FAIL", r.get("error"), file=sys.stderr)
            print(r.get("message", ""), file=sys.stderr)
            print(r.get("hint", ""), file=sys.stderr)
            print(
                "\nManual:\n"
                "  1) Open https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Relight\n"
                "  2) Agree and Access\n"
                "  3) hf auth login --force\n"
                "  4) python scripts/ltx_lora_status.py download-relight",
                file=sys.stderr,
            )
        return EXIT_OK if r.get("ok") else EXIT_DOWNLOAD_FAIL

    entries = catalog()
    if args.command == "show":
        if not args.id:
            print("FAIL USAGE: show needs id (asian_face | relight)", file=sys.stderr)
            return EXIT_USAGE
        hit = next((e for e in entries if e.get("id") == args.id), None)
        if not hit:
            print(f"FAIL UNKNOWN_ID {args.id}", file=sys.stderr)
            print("known:", ", ".join(e["id"] for e in entries), file=sys.stderr)
            return EXIT_USAGE
        if args.json:
            print(json.dumps(hit, ensure_ascii=False, indent=2))
        else:
            for k, v in hit.items():
                print(f"{k}: {v}")
        return EXIT_OK if hit.get("status") == "ready" else EXIT_MISSING

    # list
    summary = status_summary()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_human(entries)
        blocked = summary.get("blocked_ids") or []
        if blocked:
            print(f"blocked: {', '.join(blocked)}")

    # exit 0 if any ready; 3 if all blocked (still useful discovery)
    if summary.get("ready_ids"):
        return EXIT_OK
    return EXIT_MISSING


if __name__ == "__main__":
    raise SystemExit(main())
