#!/usr/bin/env python3
"""Clean disposable factory staging after export / smoke sessions.

Default is dry-run. Staging in the tool repo is OK; leaving it forever is not.

  # see what a session cleanup would remove
  python scripts/factory_cleanup.py --scope session

  # actually delete smoke dumps + Comfy temps + archive logs
  python scripts/factory_cleanup.py --scope session --apply

  # after export_episode_to_workspace
  python scripts/factory_cleanup.py --scope episode -e my_ep --apply

Scopes: smoke | comfy | logs | session | episode | all
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.factory_cleanup import build_scope_plan, execute_plan


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Factory floor cleanup (export first, then tidy staging)"
    )
    p.add_argument(
        "--scope",
        default="session",
        choices=["smoke", "comfy", "logs", "session", "episode", "all"],
        help="session=smoke+comfy+logs (default)",
    )
    p.add_argument(
        "--episode",
        "-e",
        default=None,
        help="Episode id for --scope episode|all (requires export marker)",
    )
    p.add_argument(
        "--min-age-hours",
        type=float,
        default=0,
        help="Only delete files older than N hours (0=all matching)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete (default is dry-run)",
    )
    p.add_argument("--json", action="store_true", help="Machine-readable result")
    args = p.parse_args(argv)

    if args.scope in ("episode", "all") and not args.episode and args.scope == "episode":
        print("[ERROR] --episode required for scope=episode", file=sys.stderr)
        return 2

    plan = build_scope_plan(
        args.scope,
        episode_id=args.episode,
        min_age_hours=float(args.min_age_hours or 0),
    )
    result = execute_plan(plan, dry_run=not args.apply)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        mode = "DRY-RUN" if result.get("dry_run") else "APPLY"
        print(f"=== factory_cleanup [{mode}] scope={args.scope} ===")
        pl = result.get("plan") or {}
        print(f"  roots: {', '.join(pl.get('roots_scanned') or [])}")
        if result.get("dry_run"):
            print(
                f"  would delete files={result.get('would_delete_files')} "
                f"dirs={result.get('would_delete_dirs')} "
                f"~{result.get('mb')} MB"
            )
        else:
            print(
                f"  deleted files={result.get('deleted_files')} "
                f"dirs={result.get('deleted_dirs')} "
                f"(planned ~{result.get('mb_planned')} MB)"
            )
        samples = (pl.get("file_samples") or [])[:12]
        if samples:
            print("  samples:")
            for s in samples:
                print(f"    {s}")
        for e in (pl.get("errors") or result.get("errors") or [])[:8]:
            print(f"  ERROR: {e}", file=sys.stderr)
        if result.get("dry_run"):
            print("  (re-run with --apply to delete)")

    if plan.errors and args.scope == "episode":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
