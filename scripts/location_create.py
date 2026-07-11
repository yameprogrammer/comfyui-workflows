#!/usr/bin/env python3
"""Create a location package and generate establishing master T2I candidates."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import sys

from generate_moody import generate_image
from lib.comfy_client import utc_now_iso, write_meta
from lib.location_package import (
    LOCATIONS_DIR,
    asset_filename,
    copy_template,
    fill_bible_from_create,
    fill_manifest_from_create,
    get_location_profile,
    load_json,
    load_presets,
    package_dir,
    save_json,
    validate_location_id,
)
from lib.prompt_assembly import assemble_prompt, load_text

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EXISTS = 10
EXIT_TEMPLATE = 12
EXIT_ALL_FAILED = 30


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create location package + master_wide candidates")
    parser.add_argument("--id", required=True, help="location_id (snake_case)")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default=None)
    parser.add_argument("--profile", choices=["video_ref", "artbook"], default=None)
    parser.add_argument("--candidates", type=int, default=None)
    parser.add_argument("--seed-base", type=int, default=None)
    parser.add_argument(
        "--architecture",
        type=str,
        default=None,
        help="Architecture lock text (materials, layout, landmarks)",
    )
    parser.add_argument("--architecture-file", type=str, default=None)
    parser.add_argument("--positive-core", type=str, default=None)
    parser.add_argument("--positive-core-file", type=str, default=None)
    parser.add_argument("--negative-core", type=str, default=None)
    parser.add_argument("--negative-core-file", type=str, default=None)
    parser.add_argument("--type", dest="loc_type", type=str, default="")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    location_id = args.id.strip()
    if not validate_location_id(location_id):
        print(f"[ERROR] code=2 invalid location id: {location_id}", file=sys.stderr)
        return EXIT_USAGE

    try:
        profile = get_location_profile(args.profile)
    except KeyError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    profile_id = profile["id"]
    model = args.model or profile.get("default_model") or "pro"
    candidates = (
        args.candidates
        if args.candidates is not None
        else int(profile.get("candidates_master_default") or 3)
    )
    if candidates < 0:
        print("[ERROR] code=2 candidates must be >= 0", file=sys.stderr)
        return EXIT_USAGE
    size = profile.get("size_default") or {"width": 1280, "height": 720}
    width = args.width or int(size.get("width") or 1280)
    height = args.height or int(size.get("height") or 720)

    architecture = (
        load_text(args.architecture_file)
        if args.architecture_file
        else (args.architecture or "")
    ).strip()
    if not architecture:
        print("[ERROR] code=2 --architecture or --architecture-file required", file=sys.stderr)
        return EXIT_USAGE

    positive_core = (
        load_text(args.positive_core_file)
        if args.positive_core_file
        else (args.positive_core or "")
    ).strip()
    if not positive_core:
        positive_core = (
            f"{args.name}, {architecture}, empty of people, location plate, "
            "fixed architecture and materials, cinematic still"
        )

    negative_core = (
        load_text(args.negative_core_file)
        if args.negative_core_file
        else (args.negative_core or "")
    ).strip()
    if not negative_core:
        presets = load_presets()
        negative_core = (presets.get("global") or {}).get("global_negative") or (
            "different building, people crowd, hero character, watermark"
        )

    dest = package_dir(location_id)
    if os.path.exists(dest) and not args.force:
        print(f"[ERROR] code=10 package exists: {dest}", file=sys.stderr)
        return EXIT_EXISTS

    if args.dry_run:
        print(f"[dry-run] would create {dest}")
        print(f"  profile={profile_id} model={model} candidates={candidates} size={width}x{height}")
        print(f"  architecture={architecture[:120]}...")
        return EXIT_OK

    try:
        copy_template(location_id, force=args.force)
    except FileNotFoundError:
        print("[ERROR] code=12 template missing", file=sys.stderr)
        return EXIT_TEMPLATE

    bible = load_json(os.path.join(dest, "bible.json"))
    manifest = load_json(os.path.join(dest, "manifest.json"))
    fill_bible_from_create(
        bible,
        location_id=location_id,
        name=args.name,
        architecture=architecture,
        positive_core=positive_core,
        negative_core=negative_core,
        profile_id=profile_id,
        location_type=args.loc_type,
    )
    fill_manifest_from_create(
        manifest, location_id=location_id, profile_id=profile_id, model=model
    )
    save_json(os.path.join(dest, "bible.json"), bible)
    save_json(os.path.join(dest, "manifest.json"), manifest)

    with open(os.path.join(dest, "prompts", "positive_core.txt"), "w", encoding="utf-8") as f:
        f.write(positive_core + "\n")
    with open(os.path.join(dest, "prompts", "negative_core.txt"), "w", encoding="utf-8") as f:
        f.write(negative_core + "\n")

    presets = load_presets()
    master_preset = (presets.get("presets") or {}).get("master.wide") or {}
    instruction = master_preset.get("instruction") or "wide establishing shot"
    style_lock = master_preset.get("style_lock") or ""
    quality = (presets.get("global") or {}).get("quality_tags") or ""
    neg_extra = master_preset.get("negative_extra") or ""

    prompt = assemble_prompt(
        core=positive_core,
        instruction=instruction,
        style_lock=style_lock,
        quality_tags=quality,
    )
    negative = assemble_prompt(core=negative_core, instruction=neg_extra)

    seed_base = args.seed_base if args.seed_base is not None else random.randint(10000, 90000)
    ok_count = 0
    master_dir = os.path.join(dest, "refs", "master")
    meta_dir = os.path.join(dest, "meta")
    os.makedirs(master_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)

    for i in range(candidates):
        seed = seed_base + i
        cand = i + 1
        fname = asset_filename(location_id, "master", "wide", "establishing", seed, cand)
        out_path = os.path.join(master_dir, fname)
        meta_path = os.path.join(meta_dir, os.path.splitext(fname)[0] + ".json")
        print(f"[{cand}/{candidates}] T2I master_wide seed={seed}")
        result = generate_image(
            prompt_text=prompt,
            model_type=model,
            output_filename=out_path,
            seed=seed,
            negative_text=negative,
            width=width,
            height=height,
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )
        if result.get("ok"):
            ok_count += 1
            # append asset to manifest
            man = load_json(os.path.join(dest, "manifest.json"))
            man.setdefault("assets", []).append(
                {
                    "path": f"refs/master/{fname}",
                    "sheet": "master",
                    "view": "wide",
                    "seed": seed,
                    "created_at": utc_now_iso(),
                }
            )
            save_json(os.path.join(dest, "manifest.json"), man)
            print(f"  OK {out_path}")
        else:
            print(f"  FAIL {result.get('error')} {result.get('message')}")

    changelog = os.path.join(dest, "versions", "CHANGELOG.md")
    with open(changelog, "a", encoding="utf-8") as f:
        f.write(f"- {utc_now_iso()}: create masters ok={ok_count}/{candidates}\n")

    print(f"Package: locations/{location_id}/")
    print(f"Masters ok={ok_count}/{candidates}")
    if ok_count == 0:
        return EXIT_ALL_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
