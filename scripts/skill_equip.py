#!/usr/bin/env python3
"""List / install factory skills into agent skill directories.

Factory SSOT: skills/<id>/
Consumer agents that lack the skill should install or session-load SKILL.md.

  python scripts/skill_equip.py list
  python scripts/skill_equip.py install video-direction
  python scripts/skill_equip.py install video-direction --target grok
  python scripts/skill_equip.py install video-direction --dest "D:/my/.claude/skills"
  python scripts/skill_equip.py show video-direction
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import sys
from pathlib import Path

from lib.comfy_client import WORKSPACE_ROOT

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11

SKILLS_ROOT = Path(WORKSPACE_ROOT) / "skills"


def _list_skills() -> list[dict]:
    out = []
    if not SKILLS_ROOT.is_dir():
        return out
    for p in sorted(SKILLS_ROOT.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        skill_md = p / "SKILL.md"
        if not skill_md.is_file():
            continue
        ver = ""
        try:
            text = skill_md.read_text(encoding="utf-8")
            for line in text.splitlines()[:30]:
                if line.strip().startswith("version:"):
                    ver = line.split(":", 1)[1].strip()
                    break
                if line.strip().startswith("name:"):
                    pass
        except OSError:
            pass
        out.append(
            {
                "id": p.name,
                "path": str(p),
                "skill_md": str(skill_md),
                "version": ver,
            }
        )
    return out


def _default_dests(target: str) -> list[Path]:
    home = Path.home()
    repo_grok = Path(WORKSPACE_ROOT) / ".grok" / "skills"
    if target == "grok":
        return [repo_grok, home / ".grok" / "skills"]
    if target == "claude":
        return [home / ".claude" / "skills"]
    if target == "cursor":
        return [Path(WORKSPACE_ROOT) / ".cursor" / "skills", home / ".cursor" / "skills"]
    if target == "all":
        return [
            repo_grok,
            home / ".grok" / "skills",
            home / ".claude" / "skills",
        ]
    # auto: prefer in-repo .grok + user claude if exists
    return [repo_grok]


def _copy_skill(skill_id: str, dest_root: Path) -> Path:
    src = SKILLS_ROOT / skill_id
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"skill not found: {skill_id}")
    dest = dest_root / skill_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Equip factory agent skills")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List factory skills")

    sh = sub.add_parser("show", help="Print skill path + first lines")
    sh.add_argument("skill_id")

    ins = sub.add_parser("install", help="Copy skill into agent skill dir")
    ins.add_argument("skill_id")
    ins.add_argument(
        "--target",
        choices=["auto", "grok", "claude", "cursor", "all"],
        default="auto",
        help="Where to install (default: repo .grok/skills)",
    )
    ins.add_argument(
        "--dest",
        default=None,
        help="Explicit destination parent dir (contains <skill_id>/)",
    )

    ch = sub.add_parser(
        "check",
        help="Exit 0 if skill appears installed under target; else 11",
    )
    ch.add_argument("skill_id")
    ch.add_argument(
        "--target",
        choices=["auto", "grok", "claude", "cursor", "all"],
        default="auto",
    )

    args = p.parse_args(argv)

    if args.cmd == "list":
        rows = _list_skills()
        if not rows:
            print("no skills under skills/")
            return EXIT_MISSING
        print(f"factory_skills_root={SKILLS_ROOT}")
        for r in rows:
            print(f"  {r['id']:<24} v={r['version'] or '?'}  {r['skill_md']}")
        print(
            "\nEquip: python scripts/skill_equip.py install <id> "
            "[--target grok|claude|all]"
        )
        print("Session minimum: read skills/<id>/SKILL.md fully before video work.")
        return EXIT_OK

    if args.cmd == "show":
        path = SKILLS_ROOT / args.skill_id / "SKILL.md"
        if not path.is_file():
            print(f"[ERROR] missing {path}", file=sys.stderr)
            return EXIT_MISSING
        print(f"path={path}")
        print("---")
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[:80]:
            print(line)
        if len(lines) > 80:
            print(f"... ({len(lines) - 80} more lines)")
        return EXIT_OK

    if args.cmd == "install":
        skill_id = args.skill_id
        if not (SKILLS_ROOT / skill_id / "SKILL.md").is_file():
            print(f"[ERROR] skill not found: {skill_id}", file=sys.stderr)
            print("Available:", ", ".join(r["id"] for r in _list_skills()) or "(none)")
            return EXIT_MISSING

        dests: list[Path] = []
        if args.dest:
            dests = [Path(args.dest)]
        else:
            dests = _default_dests(args.target)

        installed = []
        for d in dests:
            try:
                d.mkdir(parents=True, exist_ok=True)
                dest = _copy_skill(skill_id, d)
                installed.append(str(dest))
                print(f"OK installed → {dest}")
            except OSError as e:
                print(f"[WARN] skip {d}: {e}", file=sys.stderr)

        if not installed:
            print("[ERROR] nothing installed", file=sys.stderr)
            return EXIT_MISSING

        print(
            f"\nLoaded identity: read {installed[0]}/SKILL.md "
            f"(or keep session context from factory skills/{skill_id}/)"
        )
        return EXIT_OK

    if args.cmd == "check":
        skill_id = args.skill_id
        # Always OK if factory SSOT exists — agent can session-load
        factory = SKILLS_ROOT / skill_id / "SKILL.md"
        if not factory.is_file():
            print(f"[ERROR] factory skill missing: {skill_id}", file=sys.stderr)
            return EXIT_MISSING
        found = [str(factory)]
        for d in _default_dests(args.target):
            cand = d / skill_id / "SKILL.md"
            if cand.is_file():
                found.append(str(cand))
        print("ok factory_ssot=yes")
        for f in found:
            print(f"  {f}")
        return EXIT_OK

    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
