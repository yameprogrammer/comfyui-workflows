#!/usr/bin/env python3
"""Add / search / list shared agent failure notes (failures/)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.failure_notes import (
    create_note,
    format_note_brief,
    list_notes,
    load_tags,
    rebuild_index,
    search_notes,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_ERR = 10


def cmd_add(args: argparse.Namespace) -> int:
    tags = []
    for t in args.tags or []:
        tags.extend([x.strip() for x in t.split(",") if x.strip()])
    try:
        note = create_note(
            stage=args.stage,
            tags=tags,
            symptom=args.symptom,
            root_cause=args.cause,
            fix=args.fix,
            prevention=args.prevention,
            severity=args.severity,
            agent=args.agent,
            episode_id=args.episode,
            shot_id=args.shot,
            related_paths=args.path or [],
            user_visible=not args.internal,
            refs=args.ref or [],
        )
    except ValueError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE
    print(f"OK {note['id']}")
    print(format_note_brief(note))
    print(f"  index=failures/INDEX.md")
    return EXIT_OK


def cmd_search(args: argparse.Namespace) -> int:
    tags = []
    for t in args.tag or []:
        tags.extend([x.strip() for x in t.split(",") if x.strip()])
    notes = search_notes(
        args.query,
        tags=tags or None,
        stage=args.stage,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(notes, ensure_ascii=False, indent=2))
        return EXIT_OK
    if not notes:
        print("No matching failure notes.")
        print("Tip: python scripts/failure_note.py list --limit 20")
        return EXIT_OK
    print(f"matches={len(notes)}")
    for n in notes:
        print(format_note_brief(n))
        print("---")
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    notes = list_notes(limit=args.limit)
    if args.json:
        print(json.dumps(notes, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"count={len(notes)}")
    for n in notes:
        print(format_note_brief(n))
        print("---")
    return EXIT_OK


def cmd_tags(_: argparse.Namespace) -> int:
    for t in load_tags():
        print(t)
    return EXIT_OK


def cmd_reindex(_: argparse.Namespace) -> int:
    rebuild_index()
    print("OK failures/INDEX.md rebuilt")
    return EXIT_OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Shared failure notes for agents (learn from failure)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Record a failure note")
    p_add.add_argument("--stage", required=True)
    p_add.add_argument(
        "--tags",
        action="append",
        required=True,
        help="Tag or comma-list (repeatable)",
    )
    p_add.add_argument("--symptom", required=True)
    p_add.add_argument("--cause", required=True, help="Root cause")
    p_add.add_argument("--fix", required=True)
    p_add.add_argument("--prevention", required=True)
    p_add.add_argument(
        "--severity",
        default="medium",
        choices=["critical", "high", "medium", "low"],
    )
    p_add.add_argument("--agent", default="unknown")
    p_add.add_argument("--episode", "-e", default=None)
    p_add.add_argument("--shot", "-s", default=None)
    p_add.add_argument("--path", action="append", help="Related file path")
    p_add.add_argument("--ref", action="append", help="Related FN-id")
    p_add.add_argument(
        "--internal",
        action="store_true",
        help="Not shown to end user (tooling-only)",
    )
    p_add.set_defaults(func=cmd_add)

    p_se = sub.add_parser("search", help="Search notes by text and/or tags")
    p_se.add_argument("query", nargs="?", default=None, help="Text; supports OR")
    p_se.add_argument("--tag", action="append", help="Require tag (AND)")
    p_se.add_argument("--stage", default=None)
    p_se.add_argument("--limit", type=int, default=20)
    p_se.add_argument("--json", action="store_true")
    p_se.set_defaults(func=cmd_search)

    p_li = sub.add_parser("list", help="List recent notes")
    p_li.add_argument("--limit", type=int, default=20)
    p_li.add_argument("--json", action="store_true")
    p_li.set_defaults(func=cmd_list)

    p_tg = sub.add_parser("tags", help="Print preferred tags")
    p_tg.set_defaults(func=cmd_tags)

    p_ri = sub.add_parser("reindex", help="Rebuild INDEX.md")
    p_ri.set_defaults(func=cmd_reindex)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
