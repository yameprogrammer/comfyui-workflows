#!/usr/bin/env python3
"""
Location sheet process runner (mirror of character_full_sheet).

1) Expand video_ref / artbook MVP sheets from approved master_wide
2) Auto-approve latest refs into approved/
3) Export review contact sheets under exports/<profile>/

Usage:
  python scripts/location_full_sheet.py --id cafe_seoul_v1 --run
  python scripts/location_full_sheet.py --id cafe_seoul_v1 --approve-only
  python scripts/location_full_sheet.py --id cafe_seoul_v1 --export-only
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import subprocess
import sys

from lib.comfy_client import utc_now_iso
from lib.contact_sheet import build_contact_sheet
from lib.location_package import (
    LocationPackage,
    get_location_profile,
    load_presets,
    mvp_aliases_for,
    validate_location_id,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_PARTIAL = 31


def _run(cmd: list[str]) -> int:
    print("\n>>", " ".join(cmd))
    return subprocess.call(cmd)


def _latest_ref(pkg: LocationPackage, subdir: str, needle: str) -> str | None:
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


def _best_ref_for_preset(pkg: LocationPackage, preset_id: str, preset: dict) -> str | None:
    sub = preset.get("refs_subdir") or preset.get("sheet") or ""
    root = pkg.path("refs", sub) if sub else None
    if not root or not os.path.isdir(root):
        return None
    view = str(preset.get("view") or "").lower()
    variant = str(preset.get("variant") or "").lower()
    tail = preset_id.split(".")[-1].lower()
    scored = []
    for name in os.listdir(root):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        low = name.lower()
        # Strict: if preset declares a variant (prop_a / day / golden…), require it
        if variant and variant not in low:
            continue
        if view and f"__{view}__" not in low and view not in low:
            continue
        score = 0
        if view and f"__{view}__" in low:
            score += 6
        elif view and view in low:
            score += 4
        if variant and variant in low:
            score += 5
        if tail and tail in low:
            score += 3
        if score <= 0:
            continue
        path = os.path.join(root, name)
        scored.append((score, os.path.getmtime(path), path))
    if not scored:
        # Do not fall back to unrelated files in the same folder
        # (e.g. light_night must not steal light_golden)
        return None
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return scored[0][2]


def auto_approve(pkg: LocationPackage, presets: dict) -> list[str]:
    alias_map = presets.get("approve_alias_map") or {}
    approved: list[str] = []
    for preset_id, alias in alias_map.items():
        preset = (presets.get("presets") or {}).get(preset_id) or {}
        path = None
        if alias == "master_wide":
            # Prefer existing approved master if present, else latest establishing
            p = pkg.path("approved", "master_wide.png")
            if os.path.isfile(p):
                path = p
            else:
                path = _latest_ref(pkg, "master", "wide") or _latest_ref(
                    pkg, "master", "establishing"
                )
        else:
            path = _best_ref_for_preset(pkg, preset_id, preset)
        if not path or not os.path.isfile(path):
            print(f"  [skip] {alias} — no matching ref for {preset_id}")
            continue
        try:
            pkg.approve(path, alias)
            approved.append(alias)
            print(f"  approved {alias} ← {os.path.basename(path)}")
        except Exception as e:
            print(f"  [fail] {alias}: {e}")
    missing = pkg.recompute_missing_mvp()
    if not missing:
        pkg.bible["status"] = "approved"
        pkg.manifest["status"] = "approved"
        pkg.manifest["level"] = "L2"
    pkg.save_manifest()
    pkg.save_bible()
    return approved


def export_review_grids(pkg: LocationPackage, profile: dict) -> list[str]:
    export_sub = profile.get("export_subdir") or f"exports/{profile.get('id') or 'video_ref'}"
    export_root = pkg.path(*export_sub.replace("\\", "/").split("/"))
    os.makedirs(export_root, exist_ok=True)
    os.makedirs(os.path.join(export_root, "approved"), exist_ok=True)

    groups = {
        "01_master": ["master_wide"],
        "02_angles": [
            "angle_eye",
            "angle_reverse",
            "angle_high",
            "angle_low",
            "empty_stage",
        ],
        "03_lighting": ["light_day", "light_golden", "light_night"],
        "04_landmarks": ["landmark_a", "landmark_b"],
    }
    approved_dir = pkg.path("approved")
    outs: list[str] = []
    all_paths: list[str] = []
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
        r = build_contact_sheet(all_paths, full, cols=4, thumb_max=280)
        if r.get("ok"):
            outs.append(full)
            print(f"  grid {full} ({len(all_paths)})")

    idx = os.path.join(export_root, "README_REVIEW.md")
    lines = [
        f"# Location sheet review — `{pkg.location_id}`",
        "",
        f"- generated: {utc_now_iso()}",
        f"- profile: {profile.get('id')}",
        f"- package: `{pkg.root}`",
        f"- missing_mvp: {pkg.manifest.get('missing_mvp')}",
        "",
        "## Grids",
        "",
    ]
    for o in outs:
        lines.append(f"- `{os.path.relpath(o, pkg.root)}`")
    lines.append("")
    lines.append("## Approved")
    lines.append("")
    for name in sorted(os.listdir(approved_dir)):
        if name.lower().endswith(".png"):
            lines.append(f"- `approved/{name}`")
    with open(idx, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  index {idx}")
    return outs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Location full sheet process")
    p.add_argument("--id", required=True)
    p.add_argument("--run", action="store_true", help="Expand MVP + approve + export")
    p.add_argument("--export-only", action="store_true")
    p.add_argument("--approve-only", action="store_true")
    p.add_argument("--model", default="pro", choices=["real", "pro", "wild"])
    p.add_argument("--profile", choices=["video_ref", "artbook"], default=None)
    p.add_argument("--candidates", type=int, default=1)
    p.add_argument("--seed-base", type=int, default=43001)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--skip-expand", action="store_true")
    p.add_argument(
        "--sheets",
        default="all_mvp",
        help="Expand sheets (default all_mvp)",
    )
    args = p.parse_args(argv)

    if not (args.run or args.export_only or args.approve_only):
        print("[ERROR] pass --run | --export-only | --approve-only", file=sys.stderr)
        return EXIT_USAGE
    if not validate_location_id(args.id):
        print("[ERROR] bad location id", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = LocationPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] package missing {args.id}", file=sys.stderr)
        return EXIT_MISSING

    profile_id = args.profile or pkg.active_profile_id()
    try:
        profile = get_location_profile(profile_id)
    except KeyError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return EXIT_USAGE
    pkg.bible["active_profile"] = profile_id
    pkg.save_bible()
    presets = load_presets()

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable

    if args.run and not args.skip_expand and not args.export_only and not args.approve_only:
        master = pkg.path("approved", "master_wide.png")
        if not os.path.isfile(master):
            master = pkg.default_source_ref()
        if not master or not os.path.isfile(master):
            print(
                "[ERROR] need approved/master_wide.png first "
                "(location_create + location_approve --as master_wide)",
                file=sys.stderr,
            )
            return EXIT_USAGE

        print(f"\n=== Expand location sheets profile={profile_id} ===")
        code = _run(
            [
                py,
                os.path.join(scripts_dir, "location_expand_sheets.py"),
                "--id",
                args.id,
                "--sheets",
                args.sheets,
                "--profile",
                profile_id,
                "--model",
                args.model,
                "--candidates",
                str(args.candidates),
                "--seed-base",
                str(args.seed_base),
                "--timeout",
                str(args.timeout),
                "--source",
                master,
            ]
        )
        if code not in (0, 31):
            print(f"[ERROR] expand exit={code}", file=sys.stderr)
            return code
        pkg = LocationPackage.load(args.id)

    if args.run or args.approve_only:
        print("\n=== Auto-approve ===")
        auto_approve(pkg, presets)
        missing = pkg.recompute_missing_mvp(profile_id)
        print(f"missing_mvp ({len(missing)}): {missing}")
        print(f"required: {mvp_aliases_for(profile_id)}")

    print("\n=== Export review grids ===")
    grids = export_review_grids(pkg, profile)
    print(
        f"\nDone location={args.id} profile={profile_id} "
        f"level={pkg.manifest.get('level')} grids={len(grids)}"
    )
    print(f"Review: {pkg.path(profile.get('export_subdir') or 'exports/video_ref')}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
