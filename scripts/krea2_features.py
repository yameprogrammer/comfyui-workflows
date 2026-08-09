#!/usr/bin/env python3
"""List / search Lonecat Krea2 v7.0 + v10 features for agents (no Comfy).

  python scripts/krea2_features.py list
  python scripts/krea2_features.py list --ready
  python scripts/krea2_features.py list --source v70
  python scripts/krea2_features.py search "style control"
  python scripts/krea2_features.py show v70_moodboard
  python scripts/krea2_features.py routes

Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.krea2_features import (
    READYISH,
    all_features,
    format_feature,
    get_feature,
    ready_routes,
    search_features,
    status_summary,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Krea2 / Lonecat v7 feature inventory")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list features")
    pl.add_argument("--source", choices=("v70", "v10"), default=None)
    pl.add_argument("--ready", action="store_true", help="only callable routes")
    pl.add_argument("--json", action="store_true")

    ps = sub.add_parser("search", help="search by keywords")
    ps.add_argument("query")
    ps.add_argument("--limit", type=int, default=12)
    ps.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="show one feature_id")
    sh.add_argument("feature_id")
    sh.add_argument("--json", action="store_true")

    pr = sub.add_parser("routes", help="agent CLIs usable today")
    pr.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "list":
        feats = all_features(source=args.source)
        if args.ready:
            feats = [
                f
                for f in feats
                if str(f.get("status")) in READYISH
                or f.get("agent_cli")
                or f.get("interim_cli")
            ]
        if args.json:
            print(json.dumps(feats, ensure_ascii=False, indent=2))
            return 0
        print("=== Krea2 feature inventory ===")
        print("status counts:", status_summary())
        print()
        for f in feats:
            print(format_feature(f, verbose=False))
            print()
        print("Tip: python scripts/krea2_features.py routes")
        print("Guide: workflows/human/lonecat_krea2_v70/AGENT_GUIDE.md")
        return 0

    if args.cmd == "search":
        hits = search_features(args.query, limit=args.limit)
        if args.json:
            print(json.dumps(hits, ensure_ascii=False, indent=2))
            return 0
        if not hits:
            print("no matches", file=sys.stderr)
            return 1
        for f in hits:
            print(format_feature(f))
            print()
        return 0

    if args.cmd == "show":
        f = get_feature(args.feature_id)
        if not f:
            print(f"unknown feature_id: {args.feature_id}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(f, ensure_ascii=False, indent=2))
            return 0
        print(format_feature(f, verbose=True))
        return 0

    if args.cmd == "routes":
        rows = ready_routes()
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        print("=== Agent-callable Krea-related routes ===\n")
        for r in rows:
            print(f"[{r['status']}] {r['feature_id']} — {r['name']}")
            print(f"  {r['cli']}\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
