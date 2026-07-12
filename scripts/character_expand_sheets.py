#!/usr/bin/env python3
"""Expand character sheets from master ref via I2I presets."""

from __future__ import annotations
import _bootstrap  # noqa: F401  # repo root + scripts on path

import argparse
import os
import random
import sys

from generate_moody_controlnet import generate_controlnet_image
from generate_moody_i2i import generate_i2i_image
from generate_moody_i2i_ipadapter import generate_i2i_ipadapter
from generate_moody_i2i_lock import generate_i2i_lock
from lib.character_package import (
    CharacterPackage,
    asset_filename,
    load_presets,
    validate_character_id,
)
from lib.comfy_client import utc_now_iso, write_meta
from lib.fullbody_source import ensure_fullbody_source, find_fullbody_source
from lib.pose_templates import ensure_pose_template, ensure_view_pose
from lib.profiles import (
    PROFILE_IDS,
    apply_profile_to_bible,
    ensure_export_dirs,
    get_profile,
    profile_all_mvp_preset_ids,
    size_for_sheet,
)
from lib.prompt_assembly import assemble_prompt


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PACKAGE_MISSING = 11
EXIT_SOURCE_MISSING = 20
EXIT_PRESET_MISSING = 21
EXIT_ALL_FAILED = 30
EXIT_PARTIAL = 31
EXIT_COMFY = 40


def resolve_preset_ids(
    presets: dict,
    sheets_arg: str,
    only: str | None,
    profile: dict,
) -> list[str]:
    if only:
        return [x.strip() for x in only.split(",") if x.strip()]

    tokens = [t.strip() for t in sheets_arg.split(",") if t.strip()]
    groups = presets.get("mvp_sheet_groups", {})
    result: list[str] = []

    for token in tokens:
        if token in ("all_mvp", "mvp", "full_pack", "full_sheet"):
            if token in ("full_pack", "full_sheet") and "full_pack" in groups:
                result.extend(groups["full_pack"])
            else:
                result.extend(profile_all_mvp_preset_ids(profile, presets))
            continue
        if token in groups:
            result.extend(groups[token])
        elif token in presets.get("presets", {}):
            result.append(token)
        else:
            raise KeyError(token)

    seen = set()
    ordered = []
    for pid in result:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    return ordered


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Expand character sheets using I2I presets")
    parser.add_argument("--id", required=True)
    parser.add_argument(
        "--sheets",
        default=None,
        help="turnaround,expression,costume | all_mvp (profile-aware) | preset ids (or use --only)",
    )
    parser.add_argument("--source", default=None, help="Source image (default: approved master)")
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default=None)
    parser.add_argument(
        "--profile",
        choices=list(PROFILE_IDS),
        default=None,
        help="Purpose profile (default: package active_profile or video_ref)",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=None,
        help="Per-preset candidates (default: profile candidates_sheet_default)",
    )
    parser.add_argument("--presets-file", default=None)
    parser.add_argument("--only", default=None, help="Comma preset ids filter")
    parser.add_argument("--seed-base", type=int, default=None)
    parser.add_argument(
        "--engine",
        choices=[
            "auto",
            "i2i",
            "i2i_lock",
            "ipadapter",
            "controlnet",
            "controlnet_empty",
        ],
        default="auto",
        help=(
            "auto|i2i: plain I2I; "
            "i2i_lock: strong same-person prompt + denoise cap (always works); "
            "ipadapter: IP-Adapter face lock (needs models; falls back to i2i_lock on fail); "
            "controlnet / controlnet_empty: pose CN"
        ),
    )
    parser.add_argument(
        "--ipa-weight",
        type=float,
        default=0.72,
        help="IPAdapter weight when engine=ipadapter (default 0.72)",
    )
    parser.add_argument(
        "--ipa-fallback",
        action="store_true",
        default=True,
        help="On IPAdapter failure, fall back to i2i_lock (default on)",
    )
    parser.add_argument(
        "--no-ipa-fallback",
        action="store_true",
        help="Do not fall back if IPAdapter fails",
    )
    parser.add_argument(
        "--ensure-fullbody",
        action="store_true",
        default=True,
        help="If turnaround needs CN I2I, generate full-body master when missing (default on)",
    )
    parser.add_argument(
        "--no-ensure-fullbody",
        action="store_true",
        help="Do not auto-generate full-body master",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 31 on partial failure")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    if not validate_character_id(args.id):
        print(f"[ERROR] code=2 message=invalid id {args.id}", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] code=11 message=package missing {args.id}", file=sys.stderr)
        return EXIT_PACKAGE_MISSING

    profile_id = args.profile or pkg.active_profile_id()
    try:
        profile = get_profile(profile_id)
    except KeyError as e:
        print(f"[ERROR] code=2 message={e}", file=sys.stderr)
        return EXIT_USAGE

    # persist active profile on expand
    apply_profile_to_bible(pkg.bible, profile)
    pkg.save_bible()
    ensure_export_dirs(pkg.root, profile)

    candidates = (
        args.candidates
        if args.candidates is not None
        else int(profile.get("candidates_sheet_default") or 2)
    )
    model = args.model or profile.get("default_model") or "pro"

    if not args.sheets and not args.only:
        print("[ERROR] code=2 pass --sheets and/or --only", file=sys.stderr)
        return EXIT_USAGE

    presets = load_presets(args.presets_file)
    try:
        preset_ids = resolve_preset_ids(
            presets, args.sheets or "all_mvp", args.only, profile
        )
    except KeyError as e:
        print(f"[ERROR] code=21 message=unknown sheet/preset {e}", file=sys.stderr)
        return EXIT_PRESET_MISSING

    expand_ids = []
    for pid in preset_ids:
        p = presets["presets"].get(pid)
        if not p:
            print(f"[ERROR] code=21 message=preset missing {pid}", file=sys.stderr)
            return EXIT_PRESET_MISSING
        if p.get("mode") == "t2i":
            print(f"[WARN] skip t2i preset in expand: {pid}")
            continue
        expand_ids.append(pid)

    if not expand_ids:
        print("[ERROR] code=2 message=no expandable presets selected", file=sys.stderr)
        return EXIT_USAGE

    needs_fullbody = any(
        (presets["presets"].get(pid) or {}).get("source_pref") == "fullbody"
        or (presets["presets"].get(pid) or {}).get("sheet")
        in ("turnaround", "pose", "costume", "props")
        for pid in expand_ids
    )
    ensure_fb = args.ensure_fullbody and not args.no_ensure_fullbody

    face_source = pkg.default_source_ref()
    fullbody_source = None
    if args.source:
        source_path = pkg.resolve(args.source)
        face_source = source_path
        fullbody_source = source_path
    else:
        source_path = face_source
        if needs_fullbody and args.engine != "controlnet_empty":
            if ensure_fb:
                fullbody_source = ensure_fullbody_source(
                    pkg,
                    model=model,
                    profile_id=profile_id,
                    force_generate=False,
                    timeout_sec=args.timeout,
                )
            else:
                fullbody_source = find_fullbody_source(pkg)
            source_path = fullbody_source or face_source

    # controlnet_empty does not require character image
    if args.engine != "controlnet_empty":
        if not source_path or not os.path.exists(source_path):
            print(
                "[ERROR] code=20 message=source missing — approve master or pass --source "
                "(turnaround/pose/costume prefer full-body master)",
                file=sys.stderr,
            )
            return EXIT_SOURCE_MISSING

    positive_core = pkg.read_positive_core()
    negative_core = pkg.read_negative_core()
    quality_tags = presets.get("global", {}).get("quality_tags", "")
    global_negative = presets.get("global", {}).get("global_negative", "")

    print(f"Profile: {profile_id}")
    print(f"Face source: {face_source or '—'}")
    print(f"Fullbody source: {fullbody_source or '—'}")
    print(f"Default source: {source_path or '(none — empty latent CN)'}")
    print(f"Presets ({len(expand_ids)}): {', '.join(expand_ids)}")
    print(f"Candidates/preset: {candidates}")

    def resolve_engine(preset: dict) -> str:
        if args.engine != "auto":
            return args.engine
        eng = (preset.get("engine") or "i2i").lower()
        if eng in ("controlnet", "cn"):
            return "controlnet"
        if eng in ("controlnet_empty", "cn_empty", "t2i_controlnet"):
            return "controlnet_empty"
        if eng in ("ipadapter", "ipa", "faceid"):
            return "ipadapter"
        if eng in ("i2i_lock", "identity", "lock"):
            return "i2i_lock"
        return "i2i"

    ipa_fallback = args.ipa_fallback and not args.no_ipa_fallback

    if args.dry_run:
        for pid in expand_ids:
            p = presets["presets"][pid]
            w, h = size_for_sheet(profile, p.get("sheet", ""), p.get("view"))
            eng = resolve_engine(p)
            prompt = assemble_prompt(
                core=positive_core,
                instruction=p.get("instruction", ""),
                style_lock=p.get("style_lock", ""),
                quality_tags=quality_tags,
            )
            print(
                f"\n[{pid}] engine={eng} denoise={p.get('denoise')} cfg={p.get('cfg')} "
                f"size_hint={w}x{h} pose={p.get('pose_template')}"
            )
            print(f"  prompt: {prompt[:160]}...")
        return EXIT_OK

    success = 0
    failures = 0
    job_index = 0

    for pid in expand_ids:
        preset = presets["presets"][pid]
        w, h = size_for_sheet(profile, preset.get("sheet", ""), preset.get("view"))
        engine = resolve_engine(preset)
        for c in range(1, candidates + 1):
            job_index += 1
            if args.seed_base is not None:
                seed = args.seed_base + job_index - 1
            else:
                seed = random.randint(1, 1125899906842624)

            instruction = preset.get("instruction", "")
            if pid == "costume.default":
                wardrobe = (pkg.bible.get("appearance") or {}).get("wardrobe_default")
                if wardrobe:
                    instruction = (
                        f"same exact person, full body, wearing default wardrobe: {wardrobe}"
                    )
            if pid == "costume.alt1":
                wardrobe = (pkg.bible.get("appearance") or {}).get("wardrobe_alt1")
                if wardrobe:
                    instruction = (
                        f"same exact person, full body, alternate outfit: {wardrobe}"
                    )

            # expand instruction is full prompt body; core_prefix applied inside generators
            prompt_instruction = assemble_prompt(
                core="",
                instruction=instruction,
                style_lock=preset.get("style_lock", ""),
                quality_tags=quality_tags,
            )
            negative = assemble_prompt(
                core=negative_core,
                instruction=preset.get("negative_extra", ""),
                style_lock=global_negative,
            )

            eng_suffix = ""
            if engine in ("controlnet", "controlnet_empty", "ipadapter", "i2i_lock"):
                eng_suffix = f"_{engine}"
            fname = asset_filename(
                args.id,
                sheet=preset["sheet"],
                view=preset["view"],
                variant=preset["variant"] + eng_suffix,
                seed=seed,
                candidate=c,
            )
            out_path = pkg.path("refs", preset["refs_subdir"], fname)
            meta_path = pkg.path("meta", os.path.splitext(fname)[0] + ".json")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            denoise = float(preset.get("denoise") if preset.get("denoise") is not None else 0.85)
            cfg = float(preset.get("cfg") if preset.get("cfg") is not None else 3.5)
            strength = float(preset.get("control_strength") if preset.get("control_strength") is not None else 0.75)

            # Per-preset source preference (face close-up vs full body)
            pref = (preset.get("source_pref") or "").lower()
            job_source = source_path
            if pref == "face" and face_source and os.path.isfile(face_source):
                job_source = face_source
            elif pref == "fullbody" and fullbody_source and os.path.isfile(fullbody_source):
                job_source = fullbody_source
            elif pref == "fullbody" and face_source:
                job_source = fullbody_source or face_source

            print(
                f"\n=== [{profile_id}] {pid} engine={engine} c{c} denoise={denoise} "
                f"seed={seed} size_hint={w}x{h} src={os.path.basename(job_source or '')} ==="
            )

            if engine in ("controlnet", "controlnet_empty"):
                pose_id = preset.get("pose_template")
                if pose_id:
                    control_path = ensure_pose_template(pose_id, width=w, height=h)
                else:
                    control_path = ensure_view_pose(preset.get("view") or "front", width=w, height=h)
                print(f"Control pose template: {control_path}")
                use_empty = engine == "controlnet_empty"
                # Full-body I2I+CN: slightly higher denoise helps pose change without total identity wipe
                cn_denoise = 1.0 if use_empty else max(denoise, 0.72)
                ctrl_pp = preset.get("control_preprocess") or "auto"
                result = generate_controlnet_image(
                    input_image_path=job_source,
                    control_image_path=control_path,
                    prompt_text=prompt_instruction,
                    denoise_val=cn_denoise,
                    cfg_val=cfg,
                    control_strength=strength,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=positive_core,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                    empty_latent=use_empty,
                    latent_width=w,
                    latent_height=h,
                    control_preprocess=str(ctrl_pp),
                )
            elif engine == "ipadapter":
                print(f"IPAdapter face lock weight={args.ipa_weight}")
                result = generate_i2i_ipadapter(
                    input_image_path=job_source,
                    prompt_text=prompt_instruction,
                    denoise_val=denoise,
                    cfg_val=cfg,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=positive_core,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                    ipa_weight=args.ipa_weight,
                )
                if (
                    not result.get("ok")
                    and ipa_fallback
                    and result.get("error") in (
                        "IPADAPTER_FAILED",
                        "QUEUE_FAILED",
                        "COMFY_NO_OUTPUT",
                    )
                ):
                    print(
                        f"[WARN] IPAdapter failed ({result.get('error')}: "
                        f"{str(result.get('message') or '')[:120]}); fallback → i2i_lock"
                    )
                    result = generate_i2i_lock(
                        input_image_path=job_source,
                        prompt_text=prompt_instruction,
                        denoise_val=denoise,
                        cfg_val=cfg,
                        model_type=model,
                        output_filename=out_path,
                        seed=seed,
                        negative_text=negative,
                        core_prefix=positive_core,
                        meta_out=meta_path,
                        timeout_sec=args.timeout,
                    )
                    engine = "i2i_lock_fallback"
            elif engine == "i2i_lock":
                result = generate_i2i_lock(
                    input_image_path=job_source,
                    prompt_text=prompt_instruction,
                    denoise_val=denoise,
                    cfg_val=cfg,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=positive_core,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                )
            else:
                result = generate_i2i_image(
                    input_image_path=job_source,
                    prompt_text=prompt_instruction,
                    denoise_val=denoise,
                    cfg_val=cfg,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=positive_core,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                )

            if not result.get("ok"):
                failures += 1
                err = result.get("error", "UNKNOWN")
                print(f"[WARN] failed {pid} c{c}: {err} {result.get('message') or ''}")
                if err == "COMFY_UNREACHABLE":
                    return EXIT_COMFY
                continue

            meta = result.get("meta") or {}
            meta.update(
                {
                    "character_id": args.id,
                    "sheet": preset["sheet"],
                    "view": preset["view"],
                    "variant": preset["variant"],
                    "candidate": c,
                    "preset_id": pid,
                    "profile": profile_id,
                    "engine": engine,
                    "size_hint": [w, h],
                    "seed": result.get("seed", seed),
                }
            )
            write_meta(meta_path, meta)

            rel_out = os.path.relpath(out_path, pkg.root).replace("\\", "/")
            rel_meta = os.path.relpath(meta_path, pkg.root).replace("\\", "/")
            pkg.manifest.setdefault("assets", []).append(
                {
                    "path": rel_out,
                    "meta_path": rel_meta,
                    "sheet": preset["sheet"],
                    "view": preset["view"],
                    "variant": preset["variant"],
                    "seed": result.get("seed", seed),
                    "candidate": c,
                    "preset_id": pid,
                    "profile": profile_id,
                    "created_at": utc_now_iso(),
                }
            )
            success += 1

    pkg.recompute_missing_mvp(profile_id)
    pkg.save_manifest()
    pkg.append_changelog(
        f"expand profile={profile_id} success={success} failures={failures}"
    )

    print(f"\nOK character_id={args.id} profile={profile_id} success={success} failures={failures}")
    print(f"missing_mvp={pkg.manifest.get('missing_mvp')}")
    print("NEXT: character_approve.py 로 좋은 컷을 approved/ 에 승격")

    if success == 0:
        print("[ERROR] code=30 message=all generations failed", file=sys.stderr)
        return EXIT_ALL_FAILED
    if failures and args.strict:
        return EXIT_PARTIAL
    if failures:
        print(f"[WARN] partial={failures}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
