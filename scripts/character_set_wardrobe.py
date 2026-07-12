#!/usr/bin/env python3
"""
Stage B2 — lock wardrobe + props on a character package before full-body sheets.

Usage:
  python scripts/character_set_wardrobe.py --id sonagi_heroine_v1 --show
  python scripts/character_set_wardrobe.py --id X \\
    --default "cream cardigan over white blouse, light wash jeans, white sneakers" \\
    --alt1 "beige trench over white blouse, dark trousers, sneakers" \\
    --props "closed black compact umbrella held in right hand" \\
    --lock
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.character_package import CharacterPackage, validate_character_id
from lib.wardrobe import set_wardrobe, wardrobe_status


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PACKAGE = 11


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="B2: set/lock character wardrobe + props (bible SSOT)"
    )
    ap.add_argument("--id", required=True)
    ap.add_argument("--show", action="store_true", help="Print current wardrobe status only")
    ap.add_argument("--default", default=None, help="wardrobe_default text")
    ap.add_argument("--alt1", default=None, help="wardrobe_alt1 text")
    ap.add_argument("--props", default=None, help="props_default text")
    ap.add_argument("--props-notes", default=None, help="optional props notes")
    ap.add_argument(
        "--lock",
        action="store_true",
        default=True,
        help="Mark wardrobe_locked=true (default on when writing)",
    )
    ap.add_argument(
        "--no-lock",
        action="store_true",
        help="Write fields without setting wardrobe_locked",
    )
    ap.add_argument(
        "--unlock",
        action="store_true",
        help="Clear wardrobe_locked flag (does not erase text)",
    )
    args = ap.parse_args(argv)

    if not validate_character_id(args.id):
        print(f"[ERROR] invalid id {args.id}", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] package missing {args.id}", file=sys.stderr)
        return EXIT_PACKAGE

    if args.show and not any(
        [args.default, args.alt1, args.props, args.props_notes, args.unlock]
    ):
        st = wardrobe_status(pkg.bible)
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return EXIT_OK

    if args.unlock:
        app = pkg.bible.setdefault("appearance", {})
        app["wardrobe_locked"] = False
        app.pop("wardrobe_locked_at", None)
        pkg.save_bible()
        pkg.append_changelog("wardrobe unlocked")
        print("OK wardrobe unlocked")
        print(json.dumps(wardrobe_status(pkg.bible), ensure_ascii=False, indent=2))
        return EXIT_OK

    if not any([args.default, args.alt1, args.props, args.props_notes]):
        print(
            "[ERROR] pass --default / --alt1 / --props or --show / --unlock",
            file=sys.stderr,
        )
        return EXIT_USAGE

    lock = args.lock and not args.no_lock
    st = set_wardrobe(
        pkg.bible,
        wardrobe_default=args.default,
        wardrobe_alt1=args.alt1,
        props_default=args.props,
        props_notes=args.props_notes,
        lock=lock,
    )
    pkg.save_bible()
    pkg.append_changelog(
        f"wardrobe set lock={lock} default={bool(args.default)} "
        f"alt1={bool(args.alt1)} props={bool(args.props)}"
    )
    print(f"OK character={args.id} wardrobe_locked={st.get('wardrobe_locked')}")
    print(json.dumps(st, ensure_ascii=False, indent=2))
    print(
        f"next: python scripts/character_full_sheet.py --id {args.id} --run"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
