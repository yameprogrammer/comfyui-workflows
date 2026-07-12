#!/usr/bin/env python3
"""
Phase B — promote a cast pick (or any image) into a locked character package.

Creates package + writes cores + copies image to refs/master and approved/master_front.
Next: character_expand_sheets (Phase C consistency).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import sys

from lib.cast_pool import load_manifest, save_manifest, validate_cast_id
from lib.character_package import (
    CharacterPackage,
    copy_template,
    fill_bible_from_create,
    fill_manifest_from_create,
    load_json,
    package_dir,
    save_json,
    validate_character_id,
)
from lib.comfy_client import utc_now_iso
from lib.profiles import PROFILE_IDS, ensure_export_dirs, get_profile

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EXISTS = 10
EXIT_MISSING = 11
EXIT_SOURCE = 20


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Promote cast candidate image → character package + master_front"
    )
    p.add_argument("--from", dest="from_path", required=True, help="Source image (abs or rel)")
    p.add_argument("--id", required=True, help="New character_id")
    p.add_argument("--name", required=True, help="Display name")
    p.add_argument(
        "--appearance-prompt",
        default=None,
        help="Locked appearance description (default: cast prompt or filename)",
    )
    p.add_argument("--appearance-prompt-file", default=None)
    p.add_argument("--positive-core", default=None)
    p.add_argument("--negative-core", default=None)
    p.add_argument("--cast", default=None, help="Optional cast_id to mark promoted")
    p.add_argument("--profile", choices=list(PROFILE_IDS), default="video_ref")
    p.add_argument(
        "--model",
        choices=["real", "pro", "wild"],
        default="pro",
        help="Moody model key stored in bible (sheet expand default)",
    )
    p.add_argument("--force", action="store_true", help="Overwrite existing package")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--wardrobe-default",
        default=None,
        help="Optional B2 wardrobe_default at promote time",
    )
    p.add_argument("--wardrobe-alt1", default=None, help="Optional wardrobe_alt1")
    p.add_argument("--props-default", default=None, help="Optional props_default")
    args = p.parse_args(argv)

    if not validate_character_id(args.id):
        print("[ERROR] bad character id", file=sys.stderr)
        return EXIT_USAGE

    src = args.from_path
    if not os.path.isabs(src):
        src = os.path.abspath(src)
    if not os.path.isfile(src):
        print(f"[ERROR] source missing: {src}", file=sys.stderr)
        return EXIT_SOURCE

    appearance = args.appearance_prompt
    if args.appearance_prompt_file:
        with open(args.appearance_prompt_file, "r", encoding="utf-8") as f:
            appearance = f.read().strip()
    if not appearance and args.cast:
        try:
            man = load_manifest(args.cast)
            appearance = man.get("prompt") or ""
        except Exception:
            pass
    if not (appearance or "").strip():
        appearance = f"{args.name}, cinematic character reference, highly detailed face"

    positive = (args.positive_core or appearance).strip()
    if args.name and args.name not in positive:
        positive = f"{args.name}, {positive}"
    negative = (
        args.negative_core
        or "blurry, deformed, extra fingers, watermark, text, logo, low quality"
    ).strip()

    dest = package_dir(args.id)
    print(f"promote → character_id={args.id} profile={args.profile}")
    print(f"  from={src}")
    print(f"  dest={dest}")

    if args.dry_run:
        print("  [dry-run] skip package write")
        return EXIT_OK

    if os.path.exists(dest) and not args.force:
        print(f"[ERROR] package exists: {dest} (use --force)", file=sys.stderr)
        return EXIT_EXISTS

    try:
        copy_template(args.id, force=args.force)
    except FileExistsError:
        print(f"[ERROR] package exists {args.id}", file=sys.stderr)
        return EXIT_EXISTS
    except FileNotFoundError as e:
        print(f"[ERROR] template missing: {e}", file=sys.stderr)
        return EXIT_MISSING

    pkg = CharacterPackage.load(args.id)
    profile = get_profile(args.profile)
    ensure_export_dirs(pkg.root, profile)

    pkg.bible = fill_bible_from_create(
        pkg.bible,
        args.id,
        args.name,
        args.model,
        positive,
        negative,
        appearance.strip(),
        profile_id=args.profile,
    )
    # mark provenance
    pkg.bible.setdefault("identity", {})
    pkg.bible["identity"]["mode"] = "refs_only"
    pkg.bible["identity"]["promoted_from"] = {
        "source": src,
        "cast_id": args.cast,
        "promoted_at": utc_now_iso(),
        "phase": "cast_promote",
    }
    pkg.bible["status"] = "in_review"
    pkg.write_core_prompts(positive, negative)
    if args.wardrobe_default or args.wardrobe_alt1 or args.props_default:
        from lib.wardrobe import set_wardrobe

        set_wardrobe(
            pkg.bible,
            wardrobe_default=args.wardrobe_default,
            wardrobe_alt1=args.wardrobe_alt1,
            props_default=args.props_default,
            lock=bool(args.wardrobe_default),
        )
    pkg.save_bible()

    pkg.manifest = fill_manifest_from_create(
        pkg.manifest, args.id, args.model, profile_id=args.profile
    )
    pkg.manifest["status"] = "in_review"
    pkg.manifest["promoted_from_cast"] = args.cast
    pkg.save_manifest()

    # copy into refs/master with stable name + approve as master_front
    os.makedirs(pkg.path("refs", "master"), exist_ok=True)
    ref_name = f"{args.id}__master__promoted__s0__c01.png"
    ref_path = pkg.path("refs", "master", ref_name)
    shutil.copy2(src, ref_path)
    dest_approved = pkg.approve(ref_path, "master_front", set_primary=True)
    pkg.bible["status"] = "in_review"
    pkg.manifest["status"] = "in_review"
    # keep approved master but package not full L2 until expressions etc.
    pkg.manifest["level"] = "L1"
    pkg.recompute_missing_mvp(args.profile)
    pkg.save_bible()
    pkg.save_manifest()
    pkg.append_changelog(f"promoted master_front from cast={args.cast} src={src}")

    if args.cast and validate_cast_id(args.cast):
        try:
            man = load_manifest(args.cast)
            man["status"] = "promoted"
            man["promoted_character_id"] = args.id
            man["promoted_at"] = utc_now_iso()
            base = os.path.basename(src)
            for c in man.get("candidates") or []:
                rel = c.get("file") or ""
                if rel and base in rel.replace("\\", "/"):
                    c["status"] = "promoted"
            save_manifest(args.cast, man)
        except Exception as e:
            print(f"[WARN] cast manifest update: {e}")

    print(f"OK character={args.id}")
    print(f"  approved/master_front.png ← {dest_approved}")
    print(f"  missing_mvp={pkg.manifest.get('missing_mvp')}")
    if not (args.wardrobe_default or "").strip():
        print(
            f"  next B2: python scripts/character_set_wardrobe.py --id {args.id} "
            f"--default \"...\" --alt1 \"...\" --props \"...\" --lock"
        )
    print(
        f"  next C:  python scripts/character_full_sheet.py --id {args.id} --run"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
