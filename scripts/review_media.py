#!/usr/bin/env python3
"""One-off review pack + record for toolbox generate_* outputs.

exit 0 from generate_* means the file exists. This tool is the judge.

  python scripts/review_media.py pack -i hero.png --intent "medium, yellow parasol" \\
    -o "%AGENT_WORKSPACE%/reviews/hero"
  python scripts/review_media.py record --pack "%AGENT_WORKSPACE%/reviews/hero" \\
    --verdict pass --opened --notes "medium OK; hands OK"
  python scripts/review_media.py show still
  python scripts/review_media.py lever S4_anatomy

Episode shots: shot_qa_pack / shot_qa_record. Edit masters: edit_qa_*.
Skill: skills/output-review/SKILL.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.output_review import (
    REVIEW_KIND_AUDIO,
    REVIEW_KIND_CLIP,
    REVIEW_KIND_STILL,
    build_pack,
    format_checks,
    lever_for,
    write_record,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_QA = 23


def _print_result(res: dict, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res.get("ok"):
            print(f"[OK] {res.get('tool')}: {res.get('message')}")
            if res.get("pack_dir"):
                print(f"pack: {res['pack_dir']}")
            if res.get("review_md"):
                print(f"open: {res['review_md']}")
            for p in res.get("open") or []:
                print(f"  OPEN {p}")
            if res.get("next_cli"):
                print(f"next: {res['next_cli']}")
            if res.get("path"):
                print(f"record: {res['path']}")
        else:
            print(
                f"[FAIL] {res.get('error')}: {res.get('message')}",
                file=sys.stderr,
            )
    if not res.get("ok"):
        if res.get("error") in {"NOT_OPENED", "PASS_WITH_FAILS", "FAIL_NEEDS_ID"}:
            return EXIT_QA
        if res.get("error") in {"NO_MEDIA", "NO_PACK"}:
            return EXIT_MISSING
        return 1
    return EXIT_OK


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pk = sub.add_parser("pack", help="Build a review pack next to (or -o) the media")
    pk.add_argument("--json", action="store_true", help="Machine-readable JSON")
    pk.add_argument("--input", "-i", required=True, help="Generated still / clip / audio")
    pk.add_argument("--intent", default="", help="What this file must satisfy (brief)")
    pk.add_argument("--anti", default="", help="Forbidden (anti-list)")
    pk.add_argument(
        "--kind",
        choices=[REVIEW_KIND_STILL, REVIEW_KIND_CLIP, REVIEW_KIND_AUDIO],
        default=None,
        help="Override kind detection",
    )
    pk.add_argument("--output", "-o", default=None, help="Pack directory (project path)")

    rec = sub.add_parser("record", help="Write pass/fail after opening the pack")
    rec.add_argument("--json", action="store_true", help="Machine-readable JSON")
    rec.add_argument("--pack", required=True, help="Pack directory from pack")
    rec.add_argument("--verdict", required=True, choices=["pass", "fail", "pending"])
    rec.add_argument("--notes", default="", help="What you actually saw")
    rec.add_argument(
        "--opened",
        action="store_true",
        help="Required for pass — you opened the files",
    )
    rec.add_argument(
        "--fail",
        action="append",
        default=[],
        help="Failed check id (repeatable). Required when verdict=fail",
    )
    rec.add_argument("--next", dest="next_id", default=None, help="Check id whose lever to print")
    rec.add_argument("--agent", default="", help="Agent name (default AGENT_NAME)")

    sh = sub.add_parser("show", help="Print check ids for a kind")
    sh.add_argument("kind", choices=[REVIEW_KIND_STILL, REVIEW_KIND_CLIP, REVIEW_KIND_AUDIO])

    lv = sub.add_parser("lever", help="Print the next CLI for a failed check id")
    lv.add_argument("check_id")
    lv.add_argument("--json", action="store_true", help="Machine-readable JSON")

    args = p.parse_args(argv)

    if args.cmd == "show":
        print(format_checks(args.kind), end="")
        return EXIT_OK

    if args.cmd == "lever":
        row = lever_for(args.check_id)
        if getattr(args, "json", False):
            print(json.dumps({"id": args.check_id, **row}, ensure_ascii=False, indent=2))
        else:
            print(f"{args.check_id}: {row.get('use')}")
            if row.get("cli"):
                print(row["cli"])
        return EXIT_OK

    if args.cmd == "pack":
        res = build_pack(
            args.input,
            intent=args.intent,
            pack_dir=args.output,
            kind=args.kind,
            anti=args.anti,
        )
        return _print_result(res, as_json=getattr(args, "json", False))

    res = write_record(
        args.pack,
        verdict=args.verdict,
        notes=args.notes,
        opened=bool(args.opened),
        fails=list(args.fail or []),
        next_id=args.next_id,
        agent=args.agent,
    )
    return _print_result(res, as_json=getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
