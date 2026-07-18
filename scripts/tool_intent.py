#!/usr/bin/env python3
"""
Intent → tool search for the agent toolbox (no Comfy).

  python scripts/tool_intent.py "얼굴 유지하면서 장면 바꿔"
  python scripts/tool_intent.py search "camera push in" --limit 5
  python scripts/tool_intent.py list --shelf MOTION
  python scripts/tool_intent.py shelves
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.tool_intent import (
    format_match,
    list_by_shelf,
    list_shelves,
    search_intents,
)


def _print_failure_preflight(query: str, *, limit: int = 3) -> None:
    """Surface prior failures so agents do not repeat known mistakes."""
    try:
        from lib.failure_notes import before_gen_checklist, format_note_prevention
    except Exception:
        return
    notes = before_gen_checklist(query, limit=limit)
    if not notes:
        return
    print("=== Related failure notes (mistake prevention) ===")
    for n in notes:
        print(format_note_prevention(n))
        print("---")
    print(
        f'Tip: full preflight → python scripts/failure_note.py before "{query}"'
    )
    print("")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Search which factory CLI matches your intent. "
            "Discovery only — does not run generation."
        )
    )
    sub = p.add_subparsers(dest="cmd")

    # Default: bare query as first arg also works via dual parse below
    ps = sub.add_parser("search", help="Search tools by natural language / keywords")
    ps.add_argument("query", nargs="+", help="What you want to do")
    ps.add_argument("--shelf", default=None, help="Filter shelf e.g. MOTION")
    ps.add_argument("--limit", type=int, default=5)
    ps.add_argument("--json", action="store_true", help="Machine-readable JSON")
    ps.add_argument(
        "--no-failures",
        action="store_true",
        help="Do not attach related failure_note preflight tips",
    )

    pl = sub.add_parser("list", help="List tools (optional shelf filter)")
    pl.add_argument("--shelf", default=None)
    pl.add_argument("--json", action="store_true")

    sub.add_parser("shelves", help="List intent shelves")

    # Support: tool_intent.py "query words" without subcommand
    raw = list(argv) if argv is not None else sys.argv[1:]
    if raw and raw[0] not in (
        "search",
        "list",
        "shelves",
        "-h",
        "--help",
    ):
        # treat all as search query unless flag-like
        if not raw[0].startswith("-"):
            raw = ["search", *raw]

    args = p.parse_args(raw)

    if not args.cmd:
        p.print_help()
        print("\nExamples:")
        print('  python scripts/tool_intent.py "같은 사람 유지"')
        print('  python scripts/tool_intent.py search "dance reference" --json')
        print("  python scripts/tool_intent.py list --shelf MOTION")
        return 0

    if args.cmd == "shelves":
        for s in list_shelves():
            n = len(list_by_shelf(s))
            print(f"{s:12s}  tools={n}")
        print("\nHuman SSOT: docs/tool_catalog.md · TOOLS.md")
        return 0

    if args.cmd == "list":
        tools = list_by_shelf(args.shelf)
        if args.json:
            print(json.dumps(tools, ensure_ascii=False, indent=2))
            return 0
        if not tools:
            print("No tools for shelf", args.shelf)
            return 1
        for t in tools:
            print(f"[{t['shelf']}] {t['id']:20s}  {t['summary']}")
            print(f"         {t['cli']}")
        return 0

    if args.cmd == "search":
        query = " ".join(args.query)
        hits = search_intents(query, shelf=args.shelf, limit=args.limit)
        if args.json:
            payload: dict = {"query": query, "count": len(hits), "matches": hits}
            if not args.no_failures:
                try:
                    from lib.failure_notes import before_gen_checklist

                    payload["failure_preflight"] = before_gen_checklist(query, limit=3)
                except Exception:
                    payload["failure_preflight"] = []
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if hits else 1
        if not hits:
            print(f'No match for: "{query}"')
            print("Try: python scripts/tool_intent.py list")
            print("Or read: docs/tool_catalog.md")
            if not args.no_failures:
                _print_failure_preflight(query, limit=3)
            return 1
        print(f'Query: "{query}"  →  {len(hits)} match(es)\n')
        for i, h in enumerate(hits, 1):
            print(f"--- #{i} ---")
            print(format_match(h, verbose=True))
            print("")
        if not args.no_failures:
            _print_failure_preflight(query, limit=3)
        print(
            "Tip: run eg: first; if wrong/fail, use alternatives CLI. "
            "Before heavy gen: failure_note.py before \"…\". "
            "Card standard: docs/toolbox_card_standard.md · "
            "Catalog: docs/tool_catalog.md · discovery only (no Comfy)."
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
