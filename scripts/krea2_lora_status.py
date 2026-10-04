#!/usr/bin/env python3
"""Krea2 LoRA catalog for agents.

  python scripts/krea2_lora_status.py
  python scripts/krea2_lora_status.py --json
  python scripts/krea2_lora_status.py show darkbrush
  python scripts/krea2_lora_status.py recommend "붓터치 회화"
  python scripts/krea2_lora_status.py draft SomeLora.safetensors

Drop weights in F:\\model\\loras\\Krea2 and fill the sibling .purpose.json.
SSOT: docs/krea2_loras_agent.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.krea2_lora_catalog import catalog, draft_card, format_table, recommend, status_summary

EXIT_OK = 0
EXIT_MISSING = 3
EXIT_USAGE = 2


def _print_entry(row: dict) -> None:
    for key in (
        "id",
        "status",
        "apply",
        "slot",
        "purpose",
        "when",
        "when_not",
        "strength",
        "trigger",
        "source",
        "notes",
        "comfy_name",
        "path",
        "cli",
        "purpose_card",
        "card_error",
    ):
        if key in row:
            print(f"{key}: {row.get(key)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Krea2 LoRA purpose catalog")
    parser.add_argument(
        "command",
        nargs="?",
        default="list",
        choices=["list", "show", "recommend", "draft"],
    )
    parser.add_argument("arg", nargs="?", default=None, help="id, query, or filename")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "recommend":
        if not args.arg:
            print("FAIL USAGE: recommend needs a look phrase", file=sys.stderr)
            return EXIT_USAGE
        result = recommend(args.arg)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("match"):
            match = result["match"]
            print(f"match: {match['id']}  score={result['score']}  slot={match['slot']}")
            print(f"purpose: {match['purpose']}")
            print(f"when: {match['when'][0] if match.get('when') else ''}")
            print(f"cli: {match['cli']}")
        else:
            print("no matching LoRA. Use generate_krea with no --lora.")
            ready = [row["id"] for row in catalog() if row.get("apply")]
            print("ready:", ", ".join(ready) or "(none)")
        return EXIT_OK if result.get("match") else EXIT_MISSING

    if args.command == "draft":
        if not args.arg:
            print("FAIL USAGE: draft needs a filename in F:\\model\\loras\\Krea2", file=sys.stderr)
            return EXIT_USAGE
        result = draft_card(args.arg)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("ok"):
            print("wrote", result["purpose_card"])
            print("Fill purpose, when, and keywords. Empty cards stay off.")
        else:
            print("FAIL", result.get("error"), result.get("purpose_card") or result.get("filename"), file=sys.stderr)
            return EXIT_USAGE
        return EXIT_OK if result.get("ok") else EXIT_USAGE

    rows = catalog()
    if args.command == "show":
        if not args.arg:
            print("FAIL USAGE: show needs an id", file=sys.stderr)
            return EXIT_USAGE
        hit = next((row for row in rows if row.get("id") == args.arg), None)
        if not hit:
            print(f"FAIL UNKNOWN_ID {args.arg}", file=sys.stderr)
            print("known:", ", ".join(str(row["id"]) for row in rows) or "(none)", file=sys.stderr)
            return EXIT_USAGE
        if args.json:
            print(json.dumps(hit, ensure_ascii=False, indent=2))
        else:
            _print_entry(hit)
        return EXIT_OK if hit.get("apply") else EXIT_MISSING

    summary = status_summary()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_table(rows))
    return EXIT_OK if summary.get("ready_ids") else EXIT_MISSING


if __name__ == "__main__":
    sys.exit(main())
