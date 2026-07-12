#!/usr/bin/env python3
"""
Industry full character sheet process runner.

Order (production):
  B2 wardrobe/props lock (character_set_wardrobe)
  1) profile=full_sheet + master_full (locked wardrobe)
  2) B2.5 design plates (off-body): costume flat front/back, callout, prop hero, prop 3-view
  3) on-model costume → body source of truth
  4) Qwen head/body turns
  5) expression / pose / props.hand_item (on-model scale)
  6) auto-approve + review grids

Usage:
  python scripts/character_set_wardrobe.py --id X --default "..." --props "..." --lock
  python scripts/character_full_sheet.py --id X --run
  python scripts/character_full_sheet.py --id X --run --phases design
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import subprocess
import sys

from lib.character_package import CharacterPackage, load_presets
from lib.contact_sheet import build_contact_sheet
from lib.fullbody_source import ensure_fullbody_source
from lib.profiles import (
    apply_profile_to_bible,
    character_sheet_process_profile,
    ensure_export_dirs,
    get_profile,
)
from lib.comfy_client import utc_now_iso
from lib.wardrobe import wardrobe_status


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 31
EXIT_WARDROBE = 22


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
    qwen_view = str(preset.get("qwen_view") or "").lower()
    prefer_qwen = str(preset.get("engine") or "").lower() in (
        "qwen",
        "qwen_angle",
        "qwen_multiview",
        "multigen",
    ) or sheet in ("head", "turnaround")
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
        # Prefer Qwen multi-angle outputs for head/body turns
        if prefer_qwen and ("qwen" in low or "_qwen" in low):
            score += 12
        if qwen_view and qwen_view in low:
            score += 8
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
        "05_costume_design": [
            "costume_flat_front",
            "costume_flat_back",
            "costume_callout",
        ],
        "06_costume_onmodel": [
            "costume_default",
            "costume_alt1",
            "costume_detail_upper",
            "costume_detail_footwear",
            "costume_detail_accessories",
        ],
        "07_props_design": ["prop_hero", "prop_turn_3view"],
        "08_pose": [
            "pose_stand_idle",
            "pose_walk",
            "pose_sit",
            "pose_hands_hips",
            "pose_wave",
            "pose_look_aside",
        ],
        "09_props_onmodel": ["prop_hand_item"],
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


def _expand_cmd(
    py: str,
    scripts_dir: str,
    *,
    character_id: str,
    profile_id: str,
    sheets: str,
    model: str,
    candidates: int,
    seed_base: int,
    timeout: int,
    engine: str = "auto",
    require_wardrobe: bool = False,
) -> list[str]:
    cmd = [
        py,
        os.path.join(scripts_dir, "character_expand_sheets.py"),
        "--id",
        character_id,
        "--sheets",
        sheets,
        "--profile",
        profile_id,
        "--engine",
        engine,
        "--model",
        model,
        "--candidates",
        str(candidates),
        "--seed-base",
        str(seed_base),
        "--timeout",
        str(timeout),
        "--ensure-fullbody",
    ]
    if require_wardrobe:
        cmd.append("--require-wardrobe")
    return cmd


def _approve_costume_default(pkg: CharacterPackage) -> str | None:
    path = _latest_ref(pkg, "costume", "default")
    if not path:
        path = _latest_ref(pkg, "costume", "default_outfit")
    if path and os.path.isfile(path):
        try:
            pkg.approve(path, "costume_default")
            print(f"  mid-approve costume_default ← {os.path.basename(path)}")
            return path
        except Exception as e:
            print(f"  [warn] costume_default mid-approve: {e}")
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Industry full character sheet process")
    p.add_argument("--id", required=True)
    p.add_argument("--run", action="store_true", help="Phased expand + approve + export")
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
        help="full_pack (phased) or custom sheet groups",
    )
    p.add_argument(
        "--turn-engine",
        choices=["qwen", "auto", "controlnet", "skip"],
        default="qwen",
        help="Head/body turn path (default qwen)",
    )
    p.add_argument(
        "--allow-unlocked-wardrobe",
        action="store_true",
        help="Allow --run without B2 wardrobe lock (not recommended)",
    )
    p.add_argument(
        "--phases",
        choices=["all", "design", "costume", "turns", "rest"],
        default="all",
        help=(
            "Pipeline phase: design=off-body flats/props, costume=on-model wardrobe, "
            "turns=Qwen, rest=expr/pose/props.hand"
        ),
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
        wstat = wardrobe_status(pkg.bible)
        print(
            f"\n=== B2 wardrobe gate ===\n"
            f"  locked={wstat.get('wardrobe_locked')} ok={wstat.get('ok_for_full_sheet')} "
            f"generic={wstat.get('is_generic')}"
        )
        if wstat.get("wardrobe_default"):
            print(f"  default: {wstat['wardrobe_default'][:140]}")
        if wstat.get("props_default"):
            print(f"  props: {wstat['props_default'][:140]}")
        if not wstat.get("ok_for_full_sheet") and not args.allow_unlocked_wardrobe:
            print(
                "[ERROR] wardrobe not production-locked.\n"
                "  python scripts/character_set_wardrobe.py --id "
                f"{args.id} --default \"...\" --alt1 \"...\" --props \"...\" --lock\n"
                "  or pass --allow-unlocked-wardrobe",
                file=sys.stderr,
            )
            return EXIT_WARDROBE

        use_phases = args.sheets in ("full_pack", "all_mvp", "full_sheet")
        seed = args.seed_base

        if use_phases:
            # --- Phase 0: dressed master_full ---
            if args.phases in ("all", "costume", "design"):
                print("\n=== Phase 0: master_full (locked wardrobe) ===")
                fb = ensure_fullbody_source(
                    pkg,
                    model=args.model,
                    profile_id=profile_id,
                    force_generate=False,
                    timeout_sec=args.timeout,
                )
                if fb:
                    try:
                        pkg.approve(fb, "master_full")
                        print(f"  master_full ready: {fb}")
                    except Exception as e:
                        print(f"  [warn] master_full approve: {e}")

            # --- Phase B2.5: off-body design plates (no person) ---
            if args.phases in ("all", "design"):
                print(
                    "\n=== Phase B2.5: design plates "
                    "(costume flat/callout + prop hero/3view) ==="
                )
                code = _run(
                    _expand_cmd(
                        py,
                        scripts_dir,
                        character_id=args.id,
                        profile_id=profile_id,
                        sheets="design_pack",
                        model=args.model,
                        candidates=args.candidates,
                        seed_base=seed,
                        timeout=args.timeout,
                        require_wardrobe=not args.allow_unlocked_wardrobe,
                    )
                )
                if code not in (0, 31):
                    print(f"[ERROR] design expand exit={code}", file=sys.stderr)
                    return code
                seed += 10
                pkg = CharacterPackage.load(args.id)
                # Mid-approve design aliases for review
                design_needles = (
                    ("costume", "costume_flat_front", "flat_front"),
                    ("costume", "costume_flat_back", "flat_back"),
                    ("costume", "costume_callout", "callout"),
                    ("props", "prop_hero", "__hero__"),
                    ("props", "prop_turn_3view", "turn_3view"),
                )
                for sub, alias, needle in design_needles:
                    path = _latest_ref(pkg, sub, needle)
                    if path and os.path.isfile(path):
                        try:
                            pkg.approve(path, alias)
                            print(f"  mid-approve {alias} ← {os.path.basename(path)}")
                        except Exception as e:
                            print(f"  [warn] {alias}: {e}")
                pkg.save_manifest()
                pkg.save_bible()

            # --- Phase 1: on-model costume ---
            if args.phases in ("all", "costume"):
                print("\n=== Phase 1: on-model costume plates ===")
                code = _run(
                    _expand_cmd(
                        py,
                        scripts_dir,
                        character_id=args.id,
                        profile_id=profile_id,
                        sheets="wardrobe_pack",
                        model=args.model,
                        candidates=args.candidates,
                        seed_base=seed,
                        timeout=args.timeout,
                        require_wardrobe=not args.allow_unlocked_wardrobe,
                    )
                )
                if code not in (0, 31):
                    print(f"[ERROR] costume expand exit={code}", file=sys.stderr)
                    return code
                seed += 20
                pkg = CharacterPackage.load(args.id)
                _approve_costume_default(pkg)
                pkg.save_manifest()
                pkg.save_bible()

            # --- Phase 2: head + body turns ---
            if args.phases in ("all", "turns") and args.turn_engine != "skip":
                print("\n=== Phase 2: head + body turns ===")
                if args.turn_engine == "qwen":
                    body_src = pkg.path("approved", "costume_default.png")
                    if not os.path.isfile(body_src):
                        body_src = pkg.path("approved", "master_full.png")
                    head_src = pkg.path("approved", "master_front.png")
                    tcmd = [
                        py,
                        os.path.join(scripts_dir, "character_qwen_turns.py"),
                        "--id",
                        args.id,
                        "--mode",
                        "both",
                        "--seed-base",
                        str(seed),
                        "--timeout",
                        str(args.timeout),
                        "--approve",
                    ]
                    if os.path.isfile(head_src):
                        tcmd.extend(["--source-head", head_src])
                    if os.path.isfile(body_src):
                        tcmd.extend(["--source-body", body_src])
                    tcode = _run(tcmd)
                    if tcode not in (0, 31):
                        print(f"[WARN] qwen turns exit={tcode}", file=sys.stderr)
                    seed += 20
                else:
                    code = _run(
                        _expand_cmd(
                            py,
                            scripts_dir,
                            character_id=args.id,
                            profile_id=profile_id,
                            sheets="head,turnaround",
                            model=args.model,
                            candidates=args.candidates,
                            seed_base=seed,
                            timeout=args.timeout,
                            engine="auto" if args.turn_engine == "auto" else "controlnet",
                        )
                    )
                    if code not in (0, 31):
                        print(f"[ERROR] turn expand exit={code}", file=sys.stderr)
                        return code
                    seed += 20

            # --- Phase 3: expression + pose + on-model props ---
            if args.phases in ("all", "rest"):
                print("\n=== Phase 3: expression + pose + props.hand_item ===")
                code = _run(
                    _expand_cmd(
                        py,
                        scripts_dir,
                        character_id=args.id,
                        profile_id=profile_id,
                        sheets="expression,pose,props.hand_item",
                        model=args.model,
                        candidates=args.candidates,
                        seed_base=seed,
                        timeout=args.timeout,
                    )
                )
                if code not in (0, 31):
                    print(f"[ERROR] rest expand exit={code}", file=sys.stderr)
                    return code
        else:
            # Custom --sheets: single expand pass
            print(f"\n=== Expand custom sheets={args.sheets} ===")
            code = _run(
                _expand_cmd(
                    py,
                    scripts_dir,
                    character_id=args.id,
                    profile_id=profile_id,
                    sheets=args.sheets,
                    model=args.model,
                    candidates=args.candidates,
                    seed_base=seed,
                    timeout=args.timeout,
                    require_wardrobe=not args.allow_unlocked_wardrobe,
                )
            )
            if code not in (0, 31):
                print(f"[ERROR] expand exit={code}", file=sys.stderr)
                return code

        pkg = CharacterPackage.load(args.id)

    if args.run or args.approve_only:
        print("\n=== Auto-approve ===")
        fb = _latest_ref(pkg, "master", "full")
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
    print(
        f"Review: {os.path.join(pkg.root, profile.get('export_subdir') or 'exports/full_sheet')}"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
