#!/usr/bin/env python3
"""List workspace packs and check episode asset readiness."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import WORKSPACE_ROOT
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def _list_dirs(root: str) -> list[str]:
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        if name.startswith("_") or name in ("schemas", "examples", "pilots"):
            continue
        path = os.path.join(root, name)
        if os.path.isdir(path) and not name.startswith("."):
            # skip non-pack dirs with only json at locations root level handled
            if name in ("schemas",):
                continue
            out.append(name)
    return out


def list_characters() -> list[dict]:
    root = os.path.join(WORKSPACE_ROOT, "characters")
    rows = []
    for cid in _list_dirs(root):
        if cid in ("pose_templates",):
            continue
        bible = os.path.join(root, cid, "bible.json")
        approved = os.path.join(root, cid, "approved")
        n_app = 0
        if os.path.isdir(approved):
            n_app = len([f for f in os.listdir(approved) if f.lower().endswith(".png")])
        status = "?"
        if os.path.isfile(bible):
            try:
                with open(bible, "r", encoding="utf-8") as f:
                    status = json.load(f).get("status") or status
            except Exception:
                pass
        rows.append({"id": cid, "status": status, "approved_pngs": n_app})
    return rows


def list_locations() -> list[dict]:
    root = os.path.join(WORKSPACE_ROOT, "locations")
    rows = []
    for lid in _list_dirs(root):
        if lid in ("schemas",):
            continue
        # skip if only presets files live at root - package has bible.json
        bible = os.path.join(root, lid, "bible.json")
        if not os.path.isfile(bible):
            continue
        approved = os.path.join(root, lid, "approved")
        n_app = 0
        if os.path.isdir(approved):
            n_app = len([f for f in os.listdir(approved) if f.lower().endswith(".png")])
        status = "?"
        try:
            with open(bible, "r", encoding="utf-8") as f:
                status = json.load(f).get("status") or status
        except Exception:
            pass
        rows.append({"id": lid, "status": status, "approved_pngs": n_app})
    return rows


def list_looks() -> list[dict]:
    root = os.path.join(WORKSPACE_ROOT, "looks")
    rows = []
    for lid in _list_dirs(root):
        pos = os.path.join(root, lid, "prompts", "positive_core.txt")
        rows.append({"id": lid, "has_core": os.path.isfile(pos)})
    return rows


def check_episode(episode_id: str) -> dict:
    story = StoryPackage.load(episode_id)
    chars_needed: set[str] = set()
    locs_needed: set[str] = set()
    for s in story.shots():
        for c in s.get("character_ids") or []:
            chars_needed.add(str(c))
        if s.get("location_id"):
            locs_needed.add(str(s["location_id"]))
    look_id = story.look_id()

    def pack_ok(kind: str, pid: str) -> dict:
        if kind == "character":
            root = os.path.join(WORKSPACE_ROOT, "characters", pid)
            approved = os.path.join(root, "approved")
            n = (
                len([f for f in os.listdir(approved) if f.lower().endswith(".png")])
                if os.path.isdir(approved)
                else 0
            )
            return {
                "id": pid,
                "exists": os.path.isdir(root),
                "approved_pngs": n,
                "ready": os.path.isdir(root) and n > 0,
            }
        if kind == "location":
            root = os.path.join(WORKSPACE_ROOT, "locations", pid)
            approved = os.path.join(root, "approved")
            n = (
                len([f for f in os.listdir(approved) if f.lower().endswith(".png")])
                if os.path.isdir(approved)
                else 0
            )
            return {
                "id": pid,
                "exists": os.path.isdir(root) and os.path.isfile(os.path.join(root, "bible.json")),
                "approved_pngs": n,
                "ready": os.path.isdir(root) and n > 0,
            }
        root = os.path.join(WORKSPACE_ROOT, "looks", pid)
        return {
            "id": pid,
            "exists": os.path.isdir(root),
            "ready": os.path.isfile(os.path.join(root, "prompts", "positive_core.txt")),
        }

    characters = [pack_ok("character", c) for c in sorted(chars_needed)]
    locations = [pack_ok("location", c) for c in sorted(locs_needed)]
    look = pack_ok("look", look_id)
    blockers = []
    for c in characters:
        if not c["ready"]:
            blockers.append(f"character not ready: {c['id']}")
    for loc in locations:
        if not loc["exists"]:
            blockers.append(f"location missing: {loc['id']}")
        elif not loc["ready"]:
            blockers.append(f"location has no approved refs: {loc['id']}")
    if not look.get("ready"):
        blockers.append(f"look not ready: {look_id}")

    return {
        "episode_id": episode_id,
        "format": story.format_id(),
        "look": look,
        "characters": characters,
        "locations": locations,
        "blockers": blockers,
        "ready_to_compose": len(blockers) == 0
        or all(
            # allow compose with missing location if establishing uses t2i only — still warn
            "character not ready" not in b and "look not ready" not in b
            for b in blockers
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="List packs / check episode assets")
    parser.add_argument(
        "--type",
        choices=["all", "characters", "locations", "looks"],
        default="all",
    )
    parser.add_argument(
        "--episode",
        "-e",
        default=None,
        help="If set, check assets required by this episode",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.episode:
        if not validate_episode_id(args.episode):
            print("[ERROR] code=2 invalid episode id", file=sys.stderr)
            return EXIT_USAGE
        try:
            report = check_episode(args.episode)
        except FileNotFoundError:
            print(f"[ERROR] code=11 episode missing", file=sys.stderr)
            return EXIT_MISSING
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"episode={report['episode_id']} format={report['format']}")
            print(f"look={report['look']}")
            print("characters:")
            for c in report["characters"]:
                print(f"  {c}")
            print("locations:")
            for loc in report["locations"]:
                print(f"  {loc}")
            if report["blockers"]:
                print("blockers:")
                for b in report["blockers"]:
                    print(f"  - {b}")
            else:
                print("blockers: (none)")
        return EXIT_OK

    data = {}
    if args.type in ("all", "characters"):
        data["characters"] = list_characters()
    if args.type in ("all", "locations"):
        data["locations"] = list_locations()
    if args.type in ("all", "looks"):
        data["looks"] = list_looks()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if "characters" in data:
            print("=== characters ===")
            for r in data["characters"]:
                print(f"  {r['id']:<24} status={r['status']:<10} approved={r['approved_pngs']}")
        if "locations" in data:
            print("=== locations ===")
            for r in data["locations"]:
                print(f"  {r['id']:<24} status={r['status']:<10} approved={r['approved_pngs']}")
            if not data["locations"]:
                print("  (none)")
        if "looks" in data:
            print("=== looks ===")
            for r in data["looks"]:
                print(f"  {r['id']:<24} core={'Y' if r['has_core'] else 'N'}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
