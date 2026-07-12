#!/usr/bin/env python3
"""Create a Look / Style Core package under looks/<look_id>/."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.look_package import create_look, validate_look_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EXISTS = 10
EXIT_MISSING = 11


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Create look/style core package")
    p.add_argument("--id", required=True, help="look_id e.g. noir_rain_v1")
    p.add_argument("--name", required=True, help="Display name")
    p.add_argument(
        "--positive",
        "-p",
        default=None,
        help="positive_core text (global tone block)",
    )
    p.add_argument("--positive-file", default=None)
    p.add_argument("--negative", default=None)
    p.add_argument("--negative-file", default=None)
    p.add_argument("--description", default="")
    p.add_argument("--keywords", default="", help="Comma-separated keywords")
    p.add_argument("--medium", default="cinematic_photoreal")
    p.add_argument(
        "--status",
        choices=["draft", "in_review", "approved"],
        default="draft",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--from-default",
        action="store_true",
        help="Seed positive from cinematic_moody_v1 then allow override",
    )
    args = p.parse_args(argv)

    if not validate_look_id(args.id):
        print("[ERROR] bad look_id", file=sys.stderr)
        return EXIT_USAGE

    positive = args.positive
    if args.positive_file:
        with open(args.positive_file, "r", encoding="utf-8") as f:
            positive = f.read().strip()
    if args.from_default and not positive:
        from lib.look_package import load_look_cores

        try:
            positive, _ = load_look_cores("cinematic_moody_v1")
        except Exception:
            positive = (
                "cinematic photoreal film still, coherent grade, soft dramatic light, "
                "gentle film grain, sharp focus, high detail, restrained contrast"
            )
    if not (positive or "").strip():
        print("[ERROR] --positive / --positive-file / --from-default required", file=sys.stderr)
        return EXIT_USAGE

    negative = args.negative
    if args.negative_file:
        with open(args.negative_file, "r", encoding="utf-8") as f:
            negative = f.read().strip()

    kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
    print(f"look_create id={args.id} name={args.name} status={args.status}")
    print(f"  positive={positive[:100]}...")
    if args.dry_run:
        print("  [dry-run] skip write")
        return EXIT_OK

    try:
        dest = create_look(
            args.id,
            name=args.name,
            positive=positive.strip(),
            negative=negative,
            description=args.description,
            keywords=kws,
            medium=args.medium,
            force=args.force,
            status=args.status,
        )
    except FileExistsError:
        print(f"[ERROR] exists: {args.id} (use --force)", file=sys.stderr)
        return EXIT_EXISTS
    except FileNotFoundError as e:
        print(f"[ERROR] template: {e}", file=sys.stderr)
        return EXIT_MISSING
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return EXIT_USAGE

    print(f"OK look={args.id} path={dest}")
    print("  next: edit prompts if needed; set episode look_id; shot_compose uses it")
    print(f"  approve: set bible status approved via look_status --approve")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
