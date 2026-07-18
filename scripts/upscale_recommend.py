#!/usr/bin/env python3
"""
Agent upscaler selector — classify factory upscale tools and print a CLI.

Discovery only (no Comfy). SSOT: upscale_backends.json

  python scripts/upscale_recommend.py --media image --goal delivery --domain photo
  python scripts/upscale_recommend.py --media video --goal hero --source blurry
  python scripts/upscale_recommend.py --media video --goal master_4k
  python scripts/upscale_recommend.py --media video --goal face_fix
  python scripts/upscale_recommend.py matrix
  python scripts/upscale_recommend.py list
  python scripts/upscale_recommend.py scenarios
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.upscale_backends import (
    DOMAIN_IDS,
    GOAL_IDS,
    MEDIA_IDS,
    SOURCE_IDS,
    format_backend_matrix_table,
    format_recommendation,
    list_agent_goals,
    list_agent_matrix,
    list_backend_cards,
    load_upscale_backends,
    recommend_upscale,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Recommend which upscale backend/style/preset fits your media job. "
            "Does not run upscale — prints CLI only."
        )
    )
    sub = p.add_subparsers(dest="cmd")

    pr = sub.add_parser("pick", help="Recommend backend (default if flags given)")
    pr.add_argument("--media", "-m", default="image", help="image | video")
    pr.add_argument(
        "--goal",
        "-g",
        default="delivery",
        help="preview | batch | delivery | hero | master_4k | face_fix",
    )
    pr.add_argument(
        "--domain",
        "-d",
        default="photo",
        help="photo | anime | general",
    )
    pr.add_argument(
        "--source",
        "-s",
        default="normal",
        help="clean | normal | blurry | ai_artifacts",
    )
    pr.add_argument("--batch-count", type=int, default=None, help="shots/clips in batch")
    pr.add_argument("--format", dest="format_id", default=None)
    pr.add_argument("--input", "-i", default=None, help="path placeholder in CLI")
    pr.add_argument("--output", "-o", default=None)
    pr.add_argument(
        "--allow-optional",
        action="store_true",
        help="Allow rtx_vsr optional backend as primary",
    )
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--quiet", action="store_true", help="Print CLI line only")

    sub.add_parser("matrix", help="Performance/feature table of all backends")
    pl = sub.add_parser("list", help="Detailed backend cards")
    pl.add_argument("--json", action="store_true")
    sub.add_parser("scenarios", help="Scenario matrix (media×goal×domain)")
    sub.add_parser("goals", help="List agent goals")

    raw = list(argv) if argv is not None else sys.argv[1:]
    # Bare flags → pick
    if raw and raw[0] not in (
        "pick",
        "matrix",
        "list",
        "scenarios",
        "goals",
        "-h",
        "--help",
    ):
        if raw[0].startswith("-"):
            raw = ["pick", *raw]

    args = p.parse_args(raw)

    if not args.cmd:
        p.print_help()
        print("\nExamples:")
        print("  python scripts/upscale_recommend.py --media image --goal batch --domain anime")
        print("  python scripts/upscale_recommend.py --media video --goal hero --source blurry")
        print("  python scripts/upscale_recommend.py matrix")
        print("  python scripts/upscale_recommend.py scenarios")
        print(
            "\nAxes: media="
            + "|".join(MEDIA_IDS)
            + "  goal="
            + "|".join(GOAL_IDS)
            + "  domain="
            + "|".join(DOMAIN_IDS)
            + "  source="
            + "|".join(SOURCE_IDS)
        )
        print("SSOT: upscale_backends.json · docs/upscale_research_and_design.md")
        return 0

    if args.cmd == "matrix":
        print(format_backend_matrix_table())
        return 0

    if args.cmd == "list":
        cards = list_backend_cards()
        if getattr(args, "json", False):
            print(json.dumps(cards, ensure_ascii=False, indent=2))
            return 0
        for c in cards:
            print(f"=== {c['id']}  [{c.get('lane')}]  status={c.get('status')} ===")
            print(f"  media={','.join(c.get('media') or [])}  kind={c.get('kind')}")
            print(
                f"  ranks speed={c.get('rank_speed')} quality={c.get('rank_quality')} "
                f"restore={c.get('rank_restore')}  latency={c.get('latency_class')}"
            )
            print(f"  when: {c.get('when')}")
            print(f"  when_not: {c.get('when_not')}")
            if c.get("best_for"):
                print(f"  best_for: {', '.join(c['best_for'])}")
            if c.get("avoid_for"):
                print(f"  avoid_for: {', '.join(c['avoid_for'])}")
            print(f"  vram: {c.get('vram_note')}")
            print("")
        print("Pick: python scripts/upscale_recommend.py --media … --goal …")
        return 0

    if args.cmd == "scenarios":
        rows = list_agent_matrix()
        print(
            f"{'id':24s} {'media':6s} {'goal':10s} {'domain':8s} {'src':12s} "
            f"{'backend':18s} style    preset"
        )
        print("-" * 110)
        for r in rows:
            print(
                f"{str(r.get('id') or ''):24s} {str(r.get('media')):6s} "
                f"{str(r.get('goal')):10s} {str(r.get('domain')):8s} "
                f"{str(r.get('source')):12s} {str(r.get('backend')):18s} "
                f"{str(r.get('style') or '-'):8s} {r.get('preset') or '-'}"
            )
            if r.get("why"):
                print(f"  · {r['why']}")
        print("\nSSOT matrix: upscale_backends.json → agent_matrix")
        return 0

    if args.cmd == "goals":
        goals = list_agent_goals()
        for gid, meta in goals.items():
            print(f"{gid:12s}  {meta.get('summary')}  preset={meta.get('default_preset')}")
        return 0

    if args.cmd == "pick":
        try:
            rec = recommend_upscale(
                media=args.media,
                goal=args.goal,
                domain=args.domain,
                source=args.source,
                batch_count=args.batch_count,
                allow_optional=args.allow_optional,
                format_id=args.format_id,
                input_path=args.input,
                output_path=args.output,
            )
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            return 0
        if args.quiet:
            print(rec["cli"])
            return 0
        print(format_recommendation(rec, verbose=True))
        print("")
        print(
            "Tip: fix structure before upscale. "
            "After pick → run cli. Catalog: docs/tool_catalog.md §2.6"
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
