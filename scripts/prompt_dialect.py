#!/usr/bin/env python3
"""Official still-prompt dialects for factory image models (no Comfy, no generate).

  python scripts/prompt_dialect.py list
  python scripts/prompt_dialect.py show krea
  python scripts/prompt_dialect.py show flux
  python scripts/prompt_dialect.py pick "시네 인물 한 장"
  python scripts/prompt_dialect.py pick "flux fill mask"

Workflow: tool_intent (which CLI) → prompt_dialect show (how to write -p) → generate_*.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.prompt_dialect import DIALECTS, format_card, get_dialect, search_dialects


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list", help="All still dialects (one line each)")
    sh = sub.add_parser("show", help="Full official recipe for one family")
    sh.add_argument("name", help="krea|zimage|illustrious|anima|flux1|flux_fill|flux2_klein|sdxl|qwen_edit|ideogram")
    pk = sub.add_parser("pick", help="Rank dialects from a natural-language need")
    pk.add_argument("query", nargs="+")
    pk.add_argument("--limit", type=int, default=3)
    pk.add_argument("--json", action="store_true")

    raw = list(argv) if argv is not None else sys.argv[1:]
    if raw and raw[0] not in ("list", "show", "pick", "-h", "--help"):
        raw = ["pick", *raw]
    args = p.parse_args(raw)

    if args.cmd == "list" or args.cmd is None:
        print("still dialects — pick CLI then write -p in that form")
        print("full recipe: python scripts/prompt_dialect.py show <id>")
        print()
        for d in DIALECTS:
            print(f"  {d['id']:14} {d['cli']:32} {d['form']}")
            print(f"                 {d['when']}")
        return 0

    if args.cmd == "show":
        d = get_dialect(args.name)
        if not d:
            print(f"unknown dialect {args.name!r}. try: list", file=sys.stderr)
            return 2
        print(format_card(d, verbose=True))
        print()
        print("Then: python scripts/" + d["scripts"][0] + " -p \"<that string>\" -o ...")
        return 0

    query = " ".join(args.query).strip()
    hits = search_dialects(query, limit=args.limit)
    if args.json:
        slim = [
            {k: h[k] for k in ("id", "cli", "when", "form", "template", "ref", "score") if k in h}
            for h in hits
        ]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        return 0
    if not hits:
        print("no dialect match — python scripts/prompt_dialect.py list")
        return 1
    print(f"pick {query!r}")
    print()
    print(format_card(hits[0], verbose=True))
    if len(hits) > 1:
        print()
        print("also:")
        for h in hits[1:]:
            print(f"  {h['id']} ({h['cli']}) — {h['when']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
