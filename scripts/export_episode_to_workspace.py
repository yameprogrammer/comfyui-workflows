#!/usr/bin/env python3
"""
Copy episode artifacts from the tool repo (stories/<ep>/) into an agent workspace.

Consumer agents MUST land outputs in THEIR project directory after generation.
This helper makes that step explicit and fail-loud if dest is missing.

Usage:
  set AGENT_WORKSPACE=D:/projects/my_film
  python scripts/export_episode_to_workspace.py -e my_ep

  python scripts/export_episode_to_workspace.py -e my_ep --dest D:/projects/my_film/inbox/my_ep

Also auto-invoked by episode_i2v / episode_s2v / episode_tts when
AGENT_WORKSPACE is set or --export-workspace is passed (P0-3).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.agent_result import print_agent_summary, write_agent_result
from lib.story_package import validate_episode_id
from lib.workspace_export import (
    DEFAULT_PARTS,
    export_episode,
    resolve_export_dest,
    resolve_workspace_root,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_DEST = 12


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Copy stories/<ep> artifacts into agent workspace (required handoff step)"
    )
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--dest",
        "-d",
        default=None,
        help="Destination directory (default: $AGENT_WORKSPACE/episodes/<ep>)",
    )
    p.add_argument(
        "--parts",
        default=None,
        help="Comma-separated relative parts (default: keyframes,clips,audio,exports,meta,shots.json)",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE

    dest = resolve_export_dest(args.episode, args.dest)
    if not dest:
        print(
            "[ERROR] code=12 --dest required, or set AGENT_WORKSPACE / AGENT_PROJECT_DIR",
            file=sys.stderr,
        )
        print(
            "  Consumer agents must copy factory outputs into THEIR project directory.",
            file=sys.stderr,
        )
        return EXIT_DEST

    parts = None
    if args.parts:
        parts = [x.strip() for x in args.parts.split(",") if x.strip()]
    else:
        parts = list(DEFAULT_PARTS)

    try:
        result = export_episode(args.episode, dest, parts=parts)
    except FileNotFoundError:
        print(f"[ERROR] episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    meta = os.path.join(dest, "export_result.json")
    write_agent_result(meta, result)
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_agent_summary(result)
        print(f"dest={dest}")
        if resolve_workspace_root():
            print(f"AGENT_WORKSPACE={resolve_workspace_root()}")
    return int(result.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
