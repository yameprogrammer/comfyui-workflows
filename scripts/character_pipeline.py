#!/usr/bin/env python3
"""
Production character pipeline orchestrator (A → B → C).

Stages:
  status | cast | promote | expand | approve_master (noop if already) | all

Default without --run: print plan only.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.character_package import validate_character_id
from lib.cast_pool import validate_cast_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_STAGE = 31

STAGES = ["status", "cast", "promote", "expand"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Character production pipeline: cast → promote → expand"
    )
    p.add_argument(
        "--from",
        dest="from_stage",
        default="status",
        choices=STAGES,
        help="First stage (default status)",
    )
    p.add_argument(
        "--to",
        dest="to_stage",
        default="expand",
        choices=STAGES,
        help="Last stage (default expand)",
    )
    p.add_argument("--run", action="store_true", help="Execute (else plan only)")
    p.add_argument("--dry-run", action="store_true", help="Forward dry-run to children")

    # cast
    p.add_argument("--cast", default=None, help="cast_id for cast stage")
    p.add_argument("--prompt", "-p", default=None)
    p.add_argument("--engines", default="moody_pro,krea")
    p.add_argument("--per-engine", type=int, default=2)

    # promote
    p.add_argument("--from-image", default=None, help="Candidate image for promote")
    p.add_argument("--id", default=None, help="character_id for promote/expand")
    p.add_argument("--name", default=None, help="Display name for promote")
    p.add_argument("--profile", default="video_ref")

    # expand
    p.add_argument("--sheets", default="all_mvp")
    p.add_argument("--expand-engine", default="i2i", help="expand --engine (default i2i)")
    args = p.parse_args(argv)

    i0, i1 = STAGES.index(args.from_stage), STAGES.index(args.to_stage)
    if i1 < i0:
        print("[ERROR] --to before --from", file=sys.stderr)
        return EXIT_USAGE
    stages = STAGES[i0 : i1 + 1]

    print("=== CHARACTER PIPELINE PLAN ===")
    print(f"stages={stages} run={args.run} dry_run={args.dry_run}")
    print(f"cast={args.cast} character_id={args.id} from_image={args.from_image}")
    print()
    print("SOP (production v1):")
    print("  1) cast     — multi-engine T2I candidates + contact sheet")
    print("  2) promote  — human-picked image → package + master_front")
    print("  3) expand   — I2I expression/turn MVP sheets from master")
    print("  4) approve  — character_approve remaining aliases (manual gate)")
    print()

    if not args.run:
        print("(pass --run to execute; human must pick --from-image before promote)")
        return EXIT_OK

    failed = []
    for stage in stages:
        print(f"\n>>> STAGE {stage}")
        code = 0
        if stage == "status":
            from character_status import main as st

            if args.cast:
                code = st(["--cast", args.cast])
            elif args.id:
                code = st(["--id", args.id])
            else:
                code = st(["--list-casts"])
        elif stage == "cast":
            if not args.cast or not validate_cast_id(args.cast):
                print("[ERROR] cast stage needs valid --cast", file=sys.stderr)
                return EXIT_USAGE
            if not args.prompt and not args.dry_run:
                # allow resume if cast exists
                pass
            from character_cast_pool import main as cast_main

            argv2 = [
                "--cast",
                args.cast,
                "--engines",
                args.engines,
                "--per-engine",
                str(args.per_engine),
            ]
            if args.prompt:
                argv2.extend(["--prompt", args.prompt])
            if args.dry_run:
                argv2.append("--dry-run")
            code = cast_main(argv2)
        elif stage == "promote":
            if not args.id or not validate_character_id(args.id):
                print("[ERROR] promote needs --id", file=sys.stderr)
                return EXIT_USAGE
            if not args.from_image:
                print("[ERROR] promote needs --from-image (human pick)", file=sys.stderr)
                return EXIT_USAGE
            if not args.name:
                print("[ERROR] promote needs --name", file=sys.stderr)
                return EXIT_USAGE
            from character_promote import main as promo

            argv2 = [
                "--from",
                args.from_image,
                "--id",
                args.id,
                "--name",
                args.name,
                "--profile",
                args.profile,
            ]
            if args.cast:
                argv2.extend(["--cast", args.cast])
            if args.prompt:
                argv2.extend(["--appearance-prompt", args.prompt])
            if args.dry_run:
                argv2.append("--dry-run")
            code = promo(argv2)
        elif stage == "expand":
            if not args.id or not validate_character_id(args.id):
                print("[ERROR] expand needs --id", file=sys.stderr)
                return EXIT_USAGE
            from character_expand_sheets import main as exp

            argv2 = [
                "--id",
                args.id,
                "--sheets",
                args.sheets,
                "--engine",
                args.expand_engine,
                "--profile",
                args.profile,
            ]
            if args.dry_run:
                argv2.append("--dry-run")
            code = exp(argv2)
        print(f"<<< STAGE {stage} exit={code}")
        if code != 0:
            failed.append((stage, code))
            # soft: dry-run expand may fail without package
            if args.dry_run and code in (11, 20, 21):
                print(f"[WARN] soft-fail {stage} under dry-run")
                continue
            return EXIT_STAGE

    if failed:
        print(f"\nCompleted with issues: {failed}")
        return EXIT_STAGE
    print("\nPipeline slice finished OK")
    print("Manual gate: character_approve for any non-auto-approved sheet refs")
    if args.id:
        from character_status import main as st

        st(["--id", args.id])
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
