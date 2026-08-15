#!/usr/bin/env python3
"""Extract stills from a master for visual QA.

  python scripts/edit_qa_pack.py -i "%AGENT_WORKSPACE%/edits/s01/master.mp4" -o "%AGENT_WORKSPACE%/edits/s01/qa"
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.edit_qa import edit_qa_pack
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="마스터 QA 프레임 팩")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)
    res = edit_qa_pack(args.input, args.output)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res.get("ok"):
        print(f"[OK] qa pack → {res.get('path')} frames={len(res.get('frames') or [])}")
    else:
        print(f"[FAILED] {res.get('error')}: {res.get('message')}", file=sys.stderr)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
