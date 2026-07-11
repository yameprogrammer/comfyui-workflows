#!/usr/bin/env python3
"""Expand location package sheets via I2I from primary master."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import sys

from generate_moody_i2i import generate_i2i_image
from lib.comfy_client import utc_now_iso, write_meta
from lib.location_package import (
    LocationPackage,
    asset_filename,
    get_location_profile,
    load_presets,
    save_json,
    validate_location_id,
)
from lib.prompt_assembly import assemble_prompt

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_SOURCE = 20
EXIT_ALL_FAILED = 30


def resolve_sheet_keys(presets: dict, sheets_arg: str) -> list[str]:
    groups = presets.get("mvp_sheet_groups") or {}
    raw = [s.strip() for s in sheets_arg.split(",") if s.strip()]
    keys: list[str] = []
    for item in raw:
        if item in groups:
            keys.extend(groups[item])
        else:
            keys.append(item)
    # unique preserve order
    seen = set()
    out = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Expand location sheets (I2I from master)")
    parser.add_argument("--id", required=True)
    parser.add_argument(
        "--sheets",
        required=True,
        help="Group or preset keys: all_mvp, angles, lighting, landmarks, or preset ids",
    )
    parser.add_argument("--source", default=None, help="Source image (default: primary master)")
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    parser.add_argument("--profile", choices=["video_ref", "artbook"], default=None)
    parser.add_argument("--candidates", type=int, default=1)
    parser.add_argument("--seed-base", type=int, default=None)
    parser.add_argument("--only", type=str, default=None, help="Comma filter of preset keys")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    if not validate_location_id(args.id):
        print(f"[ERROR] code=2 invalid id", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = LocationPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] code=11 package missing {args.id}", file=sys.stderr)
        return EXIT_MISSING

    if args.profile:
        try:
            profile = get_location_profile(args.profile)
            pkg.bible["active_profile"] = profile["id"]
            pkg.save_bible()
        except KeyError as e:
            print(f"[ERROR] code=2 {e}", file=sys.stderr)
            return EXIT_USAGE

    presets_doc = load_presets()
    preset_map = presets_doc.get("presets") or {}
    keys = resolve_sheet_keys(presets_doc, args.sheets)
    if args.only:
        allow = {x.strip() for x in args.only.split(",") if x.strip()}
        keys = [k for k in keys if k in allow]

    unknown = [k for k in keys if k not in preset_map]
    if unknown:
        print(f"[ERROR] code=2 unknown presets: {unknown}", file=sys.stderr)
        return EXIT_USAGE

    source = args.source or pkg.default_source_ref()
    if args.dry_run:
        print(f"[dry-run] source={source or '(none yet)'}")
        for k in keys:
            p = preset_map[k]
            print(f"  {k} mode={p.get('mode')} denoise={p.get('denoise')} → {p.get('refs_subdir')}")
        return EXIT_OK

    if not source or not os.path.isfile(source):
        print(
            "[ERROR] code=20 no source master; approve master_wide or pass --source",
            file=sys.stderr,
        )
        return EXIT_SOURCE

    positive_core = pkg.read_positive_core()
    negative_core = pkg.read_negative_core()
    quality = (presets_doc.get("global") or {}).get("quality_tags") or ""
    seed_base = args.seed_base if args.seed_base is not None else random.randint(20000, 80000)

    ok = 0
    total = 0
    for ki, key in enumerate(keys):
        p = preset_map[key]
        if p.get("mode") == "t2i":
            print(f"[skip] {key} is t2i (use location_create)")
            continue
        for c in range(args.candidates):
            total += 1
            seed = seed_base + ki * 10 + c
            cand = c + 1
            sheet = p.get("sheet") or "angles"
            view = p.get("view") or "eye"
            variant = p.get("variant") or "v"
            sub = p.get("refs_subdir") or sheet
            fname = asset_filename(args.id, sheet, view, variant, seed, cand)
            out_dir = pkg.path("refs", sub)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, fname)
            meta_path = pkg.path("meta", os.path.splitext(fname)[0] + ".json")

            prompt = assemble_prompt(
                core=positive_core,
                instruction=p.get("instruction") or "",
                style_lock=p.get("style_lock") or "",
                quality_tags=quality,
            )
            negative = assemble_prompt(
                core=negative_core,
                instruction=p.get("negative_extra") or "",
            )
            denoise = float(p.get("denoise") or 0.8)
            cfg = float(p.get("cfg") or 3.5)

            print(f"[{key}] c{cand} denoise={denoise} seed={seed}")
            result = generate_i2i_image(
                input_image_path=source,
                prompt_text=prompt,
                denoise_val=denoise,
                cfg_val=cfg,
                model_type=args.model,
                output_filename=out_path,
                seed=seed,
                negative_text=negative,
                core_prefix=positive_core,
                meta_out=meta_path,
                timeout_sec=args.timeout,
            )
            if result.get("ok"):
                ok += 1
                pkg.append_asset(
                    {
                        "path": f"refs/{sub}/{fname}",
                        "sheet": sheet,
                        "view": view,
                        "preset": key,
                        "seed": seed,
                        "created_at": utc_now_iso(),
                    }
                )
                print(f"  OK {out_path}")
            else:
                print(f"  FAIL {result.get('error')} {result.get('message')}")

    pkg.append_changelog(f"expand sheets={args.sheets} ok={ok}/{total}")
    print(f"Done ok={ok}/{total}")
    if total and ok == 0:
        return EXIT_ALL_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
