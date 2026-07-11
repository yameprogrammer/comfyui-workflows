#!/usr/bin/env python3
"""Generate a story keyframe using an approved character package (video_ref path)."""

from __future__ import annotations
import _bootstrap  # noqa: F401  # repo root + scripts on path

import argparse
import json
import os
import random
import sys

from generate_moody_i2i import generate_i2i_image
from lib.character_package import CharacterPackage, asset_filename, validate_character_id
from lib.comfy_client import utc_now_iso, write_meta
from lib.profiles import PROFILE_IDS, get_profile
from lib.prompt_assembly import assemble_prompt, load_text


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PACKAGE_MISSING = 11
EXIT_SOURCE_MISSING = 20
EXIT_COMFY = 40
EXIT_GEN_FAILED = 30


def load_shot_templates(pkg: CharacterPackage) -> dict:
    path = pkg.path("prompts", "shot_templates.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("templates") or {}


def resolve_ref(pkg: CharacterPackage, ref: str | None, expression: str | None) -> str:
    if ref:
        path = pkg.resolve(ref)
        if os.path.exists(path):
            return path
        raise FileNotFoundError(ref)

    if expression:
        # expr_joy / joy / approved/expr_joy.png
        key = expression if expression.startswith("expr_") else f"expr_{expression}"
        cand = pkg.path("approved", f"{key}.png")
        if os.path.exists(cand):
            return cand
        raise FileNotFoundError(f"expression ref not found: {key}")

    # Prefer face/master for dialogue shots; fall back full body
    for rel in (
        "approved/master_front.png",
        "approved/expr_neutral.png",
        "approved/master_full.png",
    ):
        p = pkg.resolve(rel)
        if os.path.exists(p):
            return p

    primary = pkg.default_source_ref()
    if primary:
        return primary
    raise FileNotFoundError("no approved master/expression ref")


def build_shot_instruction(
    shot: str,
    template_id: str | None,
    templates: dict,
    video_defaults: dict,
) -> str:
    parts = [shot.strip()]
    if template_id:
        t = templates.get(template_id)
        if not t:
            raise KeyError(template_id)
        parts.extend(
            [
                t.get("framing", ""),
                t.get("camera", ""),
                t.get("instruction_suffix", ""),
            ]
        )
    motion = (video_defaults or {}).get("i2v_motion_style")
    # still keyframe: optional cinematic lock, not motion
    if motion:
        parts.append("cinematic still suitable for later animation")
    return assemble_prompt(core="", instruction=", ".join(p for p in parts if p))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Story keyframe from character package (I2I + positive_core)"
    )
    parser.add_argument("--id", required=True, help="character_id")
    parser.add_argument("--shot", "-s", required=True, help="Shot / scene instruction")
    parser.add_argument(
        "--ref",
        default=None,
        help="Source ref (package-relative or abs). Default: approved master/expression",
    )
    parser.add_argument(
        "--expression",
        default=None,
        help="Use approved expr_* as source (e.g. joy, expr_sad)",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Shot template id from prompts/shot_templates.json",
    )
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default=None)
    parser.add_argument("--profile", choices=list(PROFILE_IDS), default=None)
    parser.add_argument(
        "--denoise",
        "-d",
        type=float,
        default=None,
        help="I2I denoise (default: min(0.78, bible.video_defaults.max_identity_risk_denoise))",
    )
    parser.add_argument("--cfg", "-c", type=float, default=3.5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="Output path (default: characters/<id>/refs/shots/...)",
    )
    parser.add_argument("--allow-draft", action="store_true", help="Allow draft package")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not validate_character_id(args.id):
        print(f"[ERROR] code=2 message=invalid id {args.id}", file=sys.stderr)
        return EXIT_USAGE

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] code=11 message=package missing {args.id}", file=sys.stderr)
        return EXIT_PACKAGE_MISSING

    status = (pkg.bible.get("status") or "draft").lower()
    if status != "approved" and not args.allow_draft:
        print(
            f"[WARN] package status={status}; prefer approved. "
            "Pass --allow-draft to silence and continue."
        )

    profile_id = args.profile or pkg.active_profile_id() or "video_ref"
    try:
        profile = get_profile(profile_id)
    except KeyError:
        profile = {"id": profile_id, "default_model": "pro"}

    model = args.model or profile.get("default_model") or "pro"
    video_defaults = pkg.bible.get("video_defaults") or {}
    max_d = float(video_defaults.get("max_identity_risk_denoise") or 0.78)
    denoise = args.denoise if args.denoise is not None else min(0.78, max_d)

    try:
        ref_path = resolve_ref(pkg, args.ref, args.expression)
    except FileNotFoundError as e:
        print(f"[ERROR] code=20 message=source missing {e}", file=sys.stderr)
        return EXIT_SOURCE_MISSING

    templates = load_shot_templates(pkg)
    try:
        instruction = build_shot_instruction(
            args.shot, args.template, templates, video_defaults
        )
    except KeyError:
        print(
            f"[ERROR] code=2 message=unknown shot template {args.template}",
            file=sys.stderr,
        )
        return EXIT_USAGE

    positive_core = pkg.read_positive_core()
    negative_core = pkg.read_negative_core()
    # Light identity protection for shots
    negative = assemble_prompt(
        core=negative_core,
        instruction="identity shift, different person, face morph, extra fingers",
    )

    seed = args.seed if args.seed is not None else random.randint(1, 1125899906842624)
    if args.out:
        out_path = args.out if os.path.isabs(args.out) else os.path.join(os.getcwd(), args.out)
    else:
        os.makedirs(pkg.path("refs", "shots"), exist_ok=True)
        fname = asset_filename(
            args.id,
            sheet="shot",
            view="na",
            variant=(args.template or "custom").replace(" ", "_")[:40],
            seed=seed,
            candidate=1,
        )
        out_path = pkg.path("refs", "shots", fname)

    meta_path = os.path.splitext(out_path)[0] + ".json"
    # prefer package meta folder when under package
    try:
        rel = os.path.relpath(out_path, pkg.root)
        if not rel.startswith(".."):
            meta_path = pkg.path("meta", os.path.basename(os.path.splitext(out_path)[0]) + ".json")
    except ValueError:
        pass

    print(f"character_id={args.id} profile={profile_id} status={status}")
    print(f"ref={ref_path}")
    print(f"denoise={denoise} cfg={args.cfg} seed={seed} model={model}")
    print(f"instruction={instruction[:200]}...")
    print(f"out={out_path}")

    if args.dry_run:
        print("[DRY-RUN] skip generation")
        return EXIT_OK

    result = generate_i2i_image(
        input_image_path=ref_path,
        prompt_text=instruction,
        denoise_val=denoise,
        cfg_val=args.cfg,
        model_type=model,
        output_filename=out_path,
        seed=seed,
        negative_text=negative,
        core_prefix=positive_core,
        meta_out=meta_path,
        timeout_sec=args.timeout,
    )

    if not result.get("ok"):
        err = result.get("error", "UNKNOWN")
        print(f"[ERROR] generation failed: {err}", file=sys.stderr)
        if err == "COMFY_UNREACHABLE":
            return EXIT_COMFY
        return EXIT_GEN_FAILED

    meta = result.get("meta") or {}
    meta.update(
        {
            "character_id": args.id,
            "sheet": "shot",
            "view": "na",
            "variant": args.template or "custom",
            "profile": profile_id,
            "shot": args.shot,
            "template": args.template,
            "expression": args.expression,
            "ref": os.path.relpath(ref_path, pkg.root).replace("\\", "/")
            if ref_path.startswith(pkg.root)
            else ref_path,
            "seed": result.get("seed", seed),
            "created_at": utc_now_iso(),
        }
    )
    write_meta(meta_path, meta)

    try:
        rel_out = os.path.relpath(out_path, pkg.root).replace("\\", "/")
        if not rel_out.startswith(".."):
            pkg.manifest.setdefault("assets", []).append(
                {
                    "path": rel_out,
                    "meta_path": os.path.relpath(meta_path, pkg.root).replace("\\", "/"),
                    "sheet": "shot",
                    "view": "na",
                    "variant": args.template or "custom",
                    "seed": result.get("seed", seed),
                    "candidate": 1,
                    "preset_id": "shot_with_character",
                    "created_at": utc_now_iso(),
                }
            )
            pkg.save_manifest()
            pkg.append_changelog(f"shot keyframe {rel_out}")
    except ValueError:
        pass

    print(f"\nOK shot character_id={args.id}")
    print(f"  output={out_path}")
    print(f"  meta={meta_path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
