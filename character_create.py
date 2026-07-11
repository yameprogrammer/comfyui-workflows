#!/usr/bin/env python3
"""Create a character package and generate master T2I candidates."""

from __future__ import annotations

import argparse
import os
import sys

from generate_moody import generate_image
from lib.character_package import (
    CHARACTERS_DIR,
    asset_filename,
    copy_template,
    fill_bible_from_create,
    fill_manifest_from_create,
    load_json,
    load_presets,
    package_dir,
    save_json,
    validate_character_id,
)
from lib.comfy_client import utc_now_iso, write_meta
from lib.prompt_assembly import assemble_prompt, load_text


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PACKAGE_EXISTS = 10
EXIT_TEMPLATE_MISSING = 12
EXIT_ALL_FAILED = 30
EXIT_COMFY = 40


def build_positive_core(display_name: str, appearance_prompt: str, explicit_core: str | None) -> str:
    if explicit_core:
        return explicit_core.strip()
    # Derive a shorter core from appearance/master prompt (first ~400 chars heuristic)
    text = appearance_prompt.strip()
    if display_name and display_name not in text:
        text = f"{display_name}, {text}"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create character package + master candidates (T2I)")
    parser.add_argument("--id", required=True, help="character_id (snake_case)")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    parser.add_argument("--candidates", type=int, default=4)
    parser.add_argument("--seed-base", type=int, default=None)
    parser.add_argument("--appearance-prompt", type=str, default=None)
    parser.add_argument("--appearance-prompt-file", type=str, default=None)
    parser.add_argument("--positive-core", type=str, default=None)
    parser.add_argument("--positive-core-file", type=str, default=None)
    parser.add_argument("--negative-core", type=str, default=None)
    parser.add_argument("--negative-core-file", type=str, default=None)
    parser.add_argument(
        "--from-brief-samples",
        action="store_true",
        help="Use characters/pilots/samples/mina_* files (quick pilot path)",
    )
    parser.add_argument("--include-full-body", action="store_true", help="Also generate full-body masters")
    parser.add_argument("--force", action="store_true", help="Overwrite existing package")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    character_id = args.id.strip()
    if not validate_character_id(character_id):
        print(f"[ERROR] code=2 message=invalid character id: {character_id}", file=sys.stderr)
        return EXIT_USAGE

    # Resolve prompts
    pilots = os.path.join(CHARACTERS_DIR, "pilots", "samples")
    if args.from_brief_samples:
        appearance_prompt = load_text(os.path.join(pilots, "mina_positive_master.txt"))
        positive_core = load_text(os.path.join(pilots, "mina_positive_core.txt"))
        negative_core = load_text(os.path.join(pilots, "mina_negative_core.txt"))
    else:
        if args.appearance_prompt_file:
            appearance_prompt = load_text(args.appearance_prompt_file)
        elif args.appearance_prompt:
            appearance_prompt = args.appearance_prompt
        else:
            print(
                "[ERROR] code=2 message=need --appearance-prompt, --appearance-prompt-file, "
                "or --from-brief-samples",
                file=sys.stderr,
            )
            return EXIT_USAGE

        if args.positive_core_file:
            positive_core = load_text(args.positive_core_file)
        elif args.positive_core:
            positive_core = args.positive_core
        else:
            positive_core = build_positive_core(args.name, appearance_prompt, None)

        if args.negative_core_file:
            negative_core = load_text(args.negative_core_file)
        elif args.negative_core:
            negative_core = args.negative_core
        else:
            negative_core = (
                "identity shift, different person, face morph, extra fingers, deformed hands, "
                "mutated face, bad anatomy, blurry face, watermark, text, logo, duplicate face"
            )

    dest = package_dir(character_id)
    if os.path.exists(dest) and not args.force:
        print(f"[ERROR] code=10 message=package exists: {dest}", file=sys.stderr)
        return EXIT_PACKAGE_EXISTS

    try:
        if not args.dry_run:
            copy_template(character_id, force=args.force)
    except FileNotFoundError:
        print("[ERROR] code=12 message=template missing characters/_template", file=sys.stderr)
        return EXIT_TEMPLATE_MISSING
    except FileExistsError:
        print(f"[ERROR] code=10 message=package exists: {dest}", file=sys.stderr)
        return EXIT_PACKAGE_EXISTS

    presets = load_presets()
    global_cfg = presets.get("global", {})
    quality_tags = global_cfg.get("quality_tags", "")
    master_preset = presets["presets"]["master.front_upper"]
    full_preset = presets["presets"].get("master.full_body")

    bible_path = os.path.join(dest, "bible.json")
    manifest_path = os.path.join(dest, "manifest.json")

    if args.dry_run:
        print("[DRY-RUN] would create package", dest)
        print("[DRY-RUN] positive_core:", positive_core[:120], "...")
        print("[DRY-RUN] appearance:", appearance_prompt[:120], "...")
        return EXIT_OK

    bible = load_json(bible_path)
    manifest = load_json(manifest_path)
    bible = fill_bible_from_create(
        bible,
        character_id=character_id,
        display_name=args.name,
        model=args.model,
        positive_core=positive_core,
        negative_core=negative_core,
        appearance_prompt=appearance_prompt,
    )
    manifest = fill_manifest_from_create(manifest, character_id, args.model)

    # write cores
    with open(os.path.join(dest, "prompts", "positive_core.txt"), "w", encoding="utf-8") as f:
        f.write(positive_core.strip() + "\n")
    with open(os.path.join(dest, "prompts", "negative_core.txt"), "w", encoding="utf-8") as f:
        f.write(negative_core.strip() + "\n")

    save_json(bible_path, bible)
    save_json(manifest_path, manifest)

    jobs = [("master.front_upper", master_preset)]
    if args.include_full_body and full_preset:
        jobs.append(("master.full_body", full_preset))

    success_paths = []
    failures = 0

    for preset_id, preset in jobs:
        instruction = preset.get("instruction", "")
        style_lock = preset.get("style_lock", "")
        # Master T2I uses full appearance prompt as base + preset locks
        prompt = assemble_prompt(
            core=appearance_prompt,
            instruction=instruction,
            style_lock=style_lock,
            quality_tags=quality_tags,
        )
        for c in range(1, args.candidates + 1):
            if args.seed_base is not None:
                seed = args.seed_base + (len(success_paths) + failures)
            else:
                seed = None

            # provisional seed for filename when random — generate_image returns actual seed
            # Use placeholder then rename? Simpler: if seed None, pick random here for naming consistency
            if seed is None:
                import random

                seed = random.randint(1, 1125899906842624)

            fname = asset_filename(
                character_id,
                sheet=preset["sheet"],
                view=preset["view"],
                variant=preset["variant"],
                seed=seed,
                candidate=c,
            )
            out_path = os.path.join(dest, "refs", preset["refs_subdir"], fname)
            meta_path = os.path.join(dest, "meta", os.path.splitext(fname)[0] + ".json")

            print(f"\n=== master {preset_id} candidate {c}/{args.candidates} seed={seed} ===")
            result = generate_image(
                prompt_text=prompt,
                model_type=args.model,
                output_filename=out_path,
                seed=seed,
                negative_text=negative_core,
                meta_out=meta_path,
                timeout_sec=args.timeout,
            )

            if not result.get("ok"):
                failures += 1
                err = result.get("error", "UNKNOWN")
                print(f"[WARN] generation failed: {err}")
                if err == "COMFY_UNREACHABLE":
                    return EXIT_COMFY
                continue

            # enrich meta
            meta = result.get("meta") or {}
            meta.update(
                {
                    "character_id": character_id,
                    "sheet": preset["sheet"],
                    "view": preset["view"],
                    "variant": preset["variant"],
                    "candidate": c,
                    "preset_id": preset_id,
                    "seed": result.get("seed", seed),
                }
            )
            write_meta(meta_path, meta)

            rel_out = os.path.relpath(out_path, dest).replace("\\", "/")
            rel_meta = os.path.relpath(meta_path, dest).replace("\\", "/")
            manifest["assets"].append(
                {
                    "path": rel_out,
                    "meta_path": rel_meta,
                    "sheet": preset["sheet"],
                    "view": preset["view"],
                    "variant": preset["variant"],
                    "seed": result.get("seed", seed),
                    "candidate": c,
                    "preset_id": preset_id,
                    "created_at": utc_now_iso(),
                }
            )
            success_paths.append(rel_out)

    save_json(manifest_path, manifest)
    changelog = os.path.join(dest, "versions", "CHANGELOG.md")
    with open(changelog, "a", encoding="utf-8") as f:
        f.write(f"- {utc_now_iso()}: created package with {len(success_paths)} master candidates\n")

    if not success_paths:
        print("[ERROR] code=30 message=all master generations failed", file=sys.stderr)
        return EXIT_ALL_FAILED

    print(f"\nOK character_id={character_id}")
    print(f"masters={len(success_paths)}")
    for p in success_paths:
        print(f"  characters/{character_id}/{p}")
    print("NEXT: 후보를 고른 뒤 character_approve.py 로 master_front 승격")
    if failures:
        print(f"[WARN] partial failures={failures}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
