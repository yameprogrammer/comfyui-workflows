#!/usr/bin/env python3
"""
Copy episode artifacts from the tool repo (stories/<ep>/) into an agent workspace.

Consumer agents MUST land outputs in THEIR project directory after generation.
This helper makes that step explicit and fail-loud if dest is missing.

Usage:
  set AGENT_WORKSPACE=D:/projects/my_film
  python scripts/export_episode_to_workspace.py -e my_ep

  python scripts/export_episode_to_workspace.py -e my_ep --dest D:/projects/my_film/inbox/my_ep
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import sys

from lib.agent_result import agent_result, print_agent_summary, write_agent_result
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_DEST = 12

# Relative paths under stories/<ep>/ to copy when present
DEFAULT_GLOBS = [
    "shots.json",
    "keyframes",
    "clips/work",
    "clips/deliver",
    "audio",
    "exports/final",
    "meta",
    "board",
]


def _copy_tree_or_file(src: str, dst: str) -> list[str]:
    copied = []
    if not os.path.exists(src):
        return copied
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copied.append(dst)
    else:
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def export_episode(
    episode_id: str,
    dest: str,
    *,
    parts: list[str] | None = None,
) -> dict:
    story = StoryPackage.load(episode_id)
    src_root = story.root
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    parts = parts or list(DEFAULT_GLOBS)
    copied: list[str] = []
    missing: list[str] = []
    for rel in parts:
        rel = rel.replace("\\", "/").strip("/")
        src = os.path.join(src_root, *rel.split("/"))
        dst = os.path.join(dest, *rel.split("/"))
        if not os.path.exists(src):
            missing.append(rel)
            continue
        copied.extend(_copy_tree_or_file(src, dst))

    # README handoff for the receiving agent
    note = os.path.join(dest, "FROM_AGENT_CUSTOM.txt")
    with open(note, "w", encoding="utf-8") as f:
        f.write(
            "Exported from agent_custom tool repo.\n"
            f"episode_id={episode_id}\n"
            f"source={src_root}\n"
            f"dest={dest}\n"
            "Edit and deliver FROM THIS DIRECTORY (or your project root).\n"
            "Do not leave the only copy under the tool repo stories/ folder.\n"
        )
    copied.append(note)

    ok = len(copied) > 1  # at least note + something
    return agent_result(
        ok=ok or os.path.isdir(dest),
        tool="export_episode_to_workspace",
        episode_id=episode_id,
        error=None if (copied) else "NOTHING_COPIED",
        message=f"exported to {dest}",
        exit_code=EXIT_OK if copied else EXIT_MISSING,
        artifacts=[{"role": "workspace_copy", "path": dest}]
        + [{"role": "file", "path": p} for p in copied[:40]],
        extra={
            "source_root": src_root,
            "dest": dest,
            "missing_optional": missing,
            "agent_notes": [
                "Outputs now live in YOUR workspace. Continue editing here.",
                "Tool repo stories/ is a factory floor — not the final workbench.",
            ],
        },
    )


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

    dest = args.dest
    if not dest:
        ws = os.environ.get("AGENT_WORKSPACE") or os.environ.get("AGENT_PROJECT_DIR")
        if not ws:
            print(
                "[ERROR] code=12 --dest required, or set AGENT_WORKSPACE / AGENT_PROJECT_DIR",
                file=sys.stderr,
            )
            print(
                "  Consumer agents must copy factory outputs into THEIR project directory.",
                file=sys.stderr,
            )
            return EXIT_DEST
        dest = os.path.join(os.path.abspath(ws), "episodes", args.episode)

    parts = None
    if args.parts:
        parts = [x.strip() for x in args.parts.split(",") if x.strip()]

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
    return int(result.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
