#!/usr/bin/env python3
"""Record pass/fail after opening the edit QA pack.

  python scripts/edit_qa_record.py --pack "%AGENT_WORKSPACE%/edits/s01/qa" --verdict pass --notes "hook reads"
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

import os

from lib.edit_qa import edit_qa_record
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="편집 QA 판정 기록")
    p.add_argument("--pack", required=True)
    p.add_argument("--verdict", required=True, choices=["pass", "fail"])
    p.add_argument("--notes", default="")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    try:
        die_if_toolbox(os.path.join(args.pack, "qa_record.json"))
    except SystemExit as e:
        return int(e.code or 14)
    res = edit_qa_record(args.pack, verdict=args.verdict, notes=args.notes)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res.get("ok"):
        print(f"[OK] {res.get('verdict')} → {res.get('path')}")
    else:
        print(f"[FAILED] {res.get('error')}", file=sys.stderr)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
