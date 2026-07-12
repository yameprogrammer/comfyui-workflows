#!/usr/bin/env python3
"""
Industry full character sheet process runner.

1) Set profile=full_sheet
2) Ensure master_full (T2I if needed)
3) Expand full_pack presets
4) Auto-approve latest generated candidates into approved/
5) Export human review grids under exports/full_sheet/

Usage:
  python scripts/character_full_sheet.py --id sonagi_heroine_v1 --run
  python scripts/character_full_sheet.py --id sonagi_heroine_v1 --export-only
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import re
import subprocess
import sys

from lib.character_package import CharacterPackage, load_presets
from lib.contact_sheet import build_contact_sheet
from lib.profiles import (
    apply_profile_to_bible,
    character_sheet_process_profile,
    ensure_export_dirs,
    get_profile,
)
from lib.comfy_client import utc_now_iso


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 31


def _run(cmd: list[str]) -> int:
    print("\n>>", " ".join(cmd))
    return subprocess.call(cmd)


def _latest_ref(pkg: CharacterPackage, subdir: str, needle: str) -> str | None:
    root = pkg.path("refs", subdir)
    if not os.path.isdir(root):
        return None
    cands = []
    for name in os.listdir(root):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        if needle and needle not in name.lower():
            continue
        path = os.path.join(root, name)
        cands.append((os.path.getmtime(path), path))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][1]


def _best_ref_for_preset(pkg: CharacterPackage, preset_id: str, preset: dict) -> str | None:
    sub = preset.get("refs_subdir") or ""
    root = pkg.path("refs", sub) if sub else None
    if not root or not os.path.isdir(root):
        return None
    view = str(preset.get("view") or "").lower()
    variant = str(preset.get("variant") or "").lower()
    sheet = str(preset.get("sheet") or "").lower()
    tail = preset_id.split(".")[-1].lower()
    scored = []
    for name in os.listdir(root):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        low = name.lower()
        score = 0
        if view and f"__{view}__" in low:
            score += 5
        if variant and variant in low:
            score += 5
        if tail and tail in low:
            score += 3
        if sheet and f"__{sheet}__" in low:
            score += 1
        if score <= 0:
            continue
        path = os.path.join(root, name)
        scored.append((score, os.path.getmtime(path), path))
    if not scored:
        return _latest_ref(pkg, sub, "")
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return scored[0][2]


def auto_approve(pkg: CharacterPackage, presets: dict) -> list[str]:
    """Map approve_alias_map -> best matching ref; approve each."""
    alias_map = presets.get("approve_alias_map") or {}
    approved = []
    for preset_id, alias in alias_map.items():
        preset = (presets.get("presets") or {}).get(preset_id) or {}
        path = None
        if alias == "master_full":
            path = _latest_ref(pkg, "master", "full")
            if not path:
                p = pkg.path("approved", "master_full.png")
                path = p if os.path.isfile(p) else None
        elif alias == "master_front":
            path = pkg.path("approved", "master_front.png")
            if not os.path.isfile(path):
                path = pkg.default_source_ref()
        else:
            path = _best_ref_for_preset(pkg, preset_id, preset)

        if not path or not os.path.isfile(path):
            print(f"  [skip approve] {alias} — no ref for {preset_id}")
            continue
        try:
            pkg.approve(path, alias)
            approved.append(alias)
            print(f"  approved {alias} ← {os.path.basename(path)}")
        except Exception as e:
            print(f"  [fail approve] {alias}: {e}")
    pkg.save_manifest()
    pkg.save_bible()
    return approved


def export_review_grids(pkg: CharacterPackage, profile: dict) -> list[str]:
    export_root = ensure_export_dirs(pkg.root, profile)
    approved_dir = pkg.path("approved")
    groups = {
        "01_master": ["master_front", "master_full"],
        "02_head_turn": ["head_front", "head_qf", "head_side", "head_back"],
        "03_body_turn": ["turn_front", "turn_qf", "turn_side", "turn_back"],
        "04_expression": [
            "expr_neutral",
            "expr_joy",
            "expr_sad",
            "expr_angry",
            "expr_surprise",
            "expr_think",
        ],
        "05_costume": [
            "costume_default",
            "costume_alt1",
            "costume_detail_upper",
            "costume_detail_footwear",
            "costume_detail_accessories",
        ],
        "06_pose": [
            "pose_stand_idle",
            "pose_walk",
            "pose_sit",
            "pose_hands_hips",
            "pose_wave",
            "pose_look_aside",
        ],
        "07_props": ["prop_hand_item"],
    }
    outs = []
    all_paths = []
    for gname, aliases in groups.items():
        paths = []
        for a in aliases:
            p = os.path.join(approved_dir, f"{a}.png")
            if os.path.isfile(p):
                paths.append(p)
                all_paths.append(p)
        if not paths:
            continue
        out = os.path.join(export_root, f"review_{gname}.png")
        r = build_contact_sheet(paths, out, cols=min(4, len(paths)), thumb_max=360)
        if r.get("ok"):
            outs.append(out)
            print(f"  grid {out} ({len(paths)})")
    if all_paths:
        full = os.path.join(export_root, "review_FULL_PACKAGE.png")
        r = build_contact_sheet(all_paths, full, cols=5, thumb_max=280)
        if r.get("ok"):
            outs.append(full)
            print(f"  grid {full} ({len(all_paths)})")
    # index markdown
    idx = os.path.join(export_root, "README_REVIEW.md")
    lines = [
        f"# Full sheet review — `{pkg.character_id}`",
        "",
        f"- generated: {utc_now_iso()}",
        f"- profile: {profile.get('id')}",
        f"- package: `{pkg.root}`",
        "",
        "## Grids",
        "",
    ]
    for o in outs:
        lines.append(f"- `{os.path.relpath(o, pkg.root)}`")
    lines.append("")
    lines.append("## Approved files")
    lines.append("")
    for name in sorted(os.listdir(approved_dir)):
        if name.lower().endswith(".png"):
            lines.append(f"- `approved/{name}`")
    with open(idx, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  index {idx}")
    return outs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Industry full character sheet process")
    p.add_argument("--id", required=True)
    p.add_argument("--run", action="store_true", help="Expand full pack + approve + export")
    p.add_argument("--export-only", action="store_true", help="Only build review grids")
    p.add_argument("--approve-only", action="store_true", help="Only auto-approve + export")
    p.add_argument("--model", default="pro", choices=["real", "pro", "wild"])
    p.add_argument("--candidates", type=int, default=1)
    p.add_argument("--seed-base", type=int, default=94001)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--skip-expand", action="store_true")
    p.add_argument(
        "--sheets",
        default="full_pack",
        help="Expand sheets arg (default full_pack)",
    )
    args = p.parse_args(argv)

    if not (args.run or args.export_only or args.approve_only):
        print("[ERROR] pass --run | --export-only | --approve-only", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] package missing {args.id}", file=sys.stderr)
        return EXIT_USAGE

    profile_id = character_sheet_process_profile()
    profile = get_profile(profile_id)
    apply_profile_to_bible(pkg.bible, profile)
    pkg.save_bible()
    presets = load_presets()

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable

    if args.run and not args.skip_expand and not args.export_only and not args.approve_only:
        # Expand full pack (includes expressions/head/turn/costume/pose/props)
        code = _run(
            [
                py,
                os.path.join(scripts_dir, "character_expand_sheets.py"),
                "--id",
                args.id,
                "--sheets",
                args.sheets,
                "--profile",
                profile_id,
                "--engine",
                "auto",
                "--model",
                args.model,
                "--candidates",
                str(args.candidates),
                "--seed-base",
                str(args.seed_base),
                "--timeout",
                str(args.timeout),
                "--ensure-fullbody",
            ]
        )
        if code not in (0, 31):
            print(f"[ERROR] expand exit={code}", file=sys.stderr)
            return code

    if args.run or args.approve_only:
        print("\n=== Auto-approve ===")
        # ensure master_full approved if present
        fb = None
        master_dir = pkg.path("refs", "master")
        if os.path.isdir(master_dir):
            for name in sorted(os.listdir(master_dir), reverse=True):
                if "full" in name.lower() and name.lower().endswith(".png"):
                    fb = os.path.join(master_dir, name)
                    break
        if fb:
            try:
                pkg.approve(fb, "master_full")
                print(f"  approved master_full ← {os.path.basename(fb)}")
            except Exception as e:
                print(f"  master_full: {e}")
        auto_approve(pkg, presets)
        missing = pkg.recompute_missing_mvp(profile_id)
        pkg.save_manifest()
        print(f"missing_mvp ({len(missing)}): {missing}")

    print("\n=== Export review grids ===")
    grids = export_review_grids(pkg, profile)
    print(f"\nDone character={args.id} profile={profile_id} grids={len(grids)}")
    print(f"Review: {os.path.join(pkg.root, profile.get('export_subdir') or 'exports/full_sheet')}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
