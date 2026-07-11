#!/usr/bin/env python3
"""Compose a production keyframe: look + character + location → format canvas still."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import sys

from generate_moody import generate_image
from generate_moody_i2i import generate_i2i_image
from lib.character_package import CharacterPackage, validate_character_id
from lib.comfy_client import utc_now_iso, write_meta
from lib.location_package import LocationPackage, validate_location_id
from lib.prompt_assembly import assemble_prompt
from lib.story_package import (
    StoryPackage,
    load_look_cores,
    load_shot_types,
    resolve_work_size,
    validate_episode_id,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_SOURCE = 20
EXIT_GEN = 30
EXIT_PARTIAL = 31


def _compose_all(args) -> int:
    """Batch-compose shots missing keyframes (or all with --force)."""
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if not shots:
        print("[ERROR] code=2 no shots in episode", file=sys.stderr)
        return EXIT_USAGE

    todo = []
    for s in shots:
        sid = s.get("shot_id")
        rel = s.get("keyframe") or f"keyframes/{sid}.png"
        path = story.path(*str(rel).replace("\\", "/").split("/"))
        if args.force or not os.path.isfile(path):
            todo.append(sid)

    if not todo:
        print("OK nothing to compose (all keyframes present; use --force to redo)")
        return EXIT_OK

    print(f"episode_compose_all episode={args.episode} count={len(todo)} dry_run={args.dry_run}")
    ok = 0
    fail = 0
    for sid in todo:
        argv = [
            "--episode",
            args.episode,
            "--shot",
            sid,
            "--mode",
            args.mode,
            "--timeout",
            str(args.timeout),
        ]
        if args.dry_run:
            argv.append("--dry-run")
        if args.model:
            argv.extend(["--model", args.model])
        if args.denoise is not None:
            argv.extend(["--denoise", str(args.denoise)])
        if args.cfg is not None:
            argv.extend(["--cfg", str(args.cfg)])
        if args.look:
            argv.extend(["--look", args.look])
        code = main(argv)
        if code == EXIT_OK:
            ok += 1
        else:
            fail += 1
            print(f"[WARN] shot {sid} failed exit={code}")

    print(f"Done compose ok={ok} fail={fail}")
    if fail and ok == 0:
        return EXIT_GEN
    if fail:
        return EXIT_PARTIAL
    return EXIT_OK


def resolve_character_ref(pkg: CharacterPackage, shot: dict, character_id: str) -> str | None:
    refs = shot.get("character_refs") or {}
    rel = refs.get(character_id)
    if rel:
        path = pkg.resolve(rel)
        if os.path.isfile(path):
            return path
    for rel in (
        "approved/master_front.png",
        "approved/expr_neutral.png",
        "approved/master_full.png",
    ):
        p = pkg.resolve(rel)
        if os.path.isfile(p):
            return p
    return pkg.default_source_ref()


def resolve_location_ref(pkg: LocationPackage, shot: dict) -> str | None:
    rel = shot.get("location_ref")
    if rel:
        path = pkg.resolve(rel)
        if os.path.isfile(path):
            return path
    for alias in ("empty_stage", "master_wide", "angle_eye"):
        approved = (pkg.manifest.get("approved") or {}).get(alias)
        if approved:
            p = pkg.resolve(approved["path"])
            if os.path.isfile(p):
                return p
    return pkg.default_source_ref()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose episode keyframe (look + char + loc @ format work size)"
    )
    parser.add_argument("--episode", "-e", required=True, help="episode_id")
    parser.add_argument(
        "--shot",
        "-s",
        default=None,
        help="shot_id e.g. S01 (required unless --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compose all shots missing keyframe file (or all with --force)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --all, recompose even if keyframe file exists",
    )
    parser.add_argument("--action", default=None, help="Override shot action text")
    parser.add_argument(
        "--character",
        action="append",
        default=None,
        help="character_id (repeatable). Default: shot.character_ids",
    )
    parser.add_argument("--location", default=None, help="location_id override")
    parser.add_argument("--look", default=None, help="look_id override")
    parser.add_argument(
        "--shot-type",
        default=None,
        help="establishing|wide|medium|closeup|insert",
    )
    parser.add_argument("--model", "-m", choices=["real", "pro", "wild"], default=None)
    parser.add_argument("--denoise", "-d", type=float, default=None)
    parser.add_argument("--cfg", "-c", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--mode",
        choices=["auto", "i2i", "t2i"],
        default="auto",
        help="auto: i2i if source ref else t2i",
    )
    parser.add_argument("--source", default=None, help="Force I2I source image path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    if args.all:
        if args.shot:
            print("[ERROR] code=2 use either --shot or --all, not both", file=sys.stderr)
            return EXIT_USAGE
        return _compose_all(args)

    if not args.shot:
        print("[ERROR] code=2 --shot is required (or pass --all)", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        # create minimal shot if action provided
        if not args.action:
            print(
                f"[ERROR] code=2 shot {args.shot} not in shots.json; pass --action to create",
                file=sys.stderr,
            )
            return EXIT_USAGE
        shot = story.ensure_shot(
            args.shot,
            action=args.action,
            character_ids=args.character or [],
            location_id=args.location,
            shot_type=args.shot_type or "medium",
        )

    action = (args.action or shot.get("action") or "").strip()
    if not action:
        print("[ERROR] code=2 empty action", file=sys.stderr)
        return EXIT_USAGE

    look_id = args.look or story.look_id()
    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    try:
        width, height, format_id, work_preset_id = resolve_work_size(format_id, work_preset)
    except Exception as e:
        print(f"[ERROR] code=2 size resolve: {e}", file=sys.stderr)
        return EXIT_USAGE

    try:
        look_pos, look_neg = load_look_cores(look_id)
    except FileNotFoundError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    char_ids = args.character or list(shot.get("character_ids") or [])
    location_id = args.location if args.location is not None else shot.get("location_id")
    shot_type = args.shot_type or shot.get("shot_type") or "medium"
    types = load_shot_types()
    type_meta = types.get(shot_type) or {}
    framing = type_meta.get("framing") or ""

    char_cores: list[str] = []
    char_negs: list[str] = []
    char_source: str | None = None
    for cid in char_ids:
        if not validate_character_id(cid):
            print(f"[ERROR] code=2 bad character id {cid}", file=sys.stderr)
            return EXIT_USAGE
        try:
            cpkg = CharacterPackage.load(cid)
        except FileNotFoundError:
            print(f"[ERROR] code=11 character missing {cid}", file=sys.stderr)
            return EXIT_MISSING
        if cpkg.bible.get("status") == "draft" and cpkg.manifest.get("status") == "draft":
            print(f"[WARN] character {cid} status=draft — prefer approved package")
        char_cores.append(cpkg.read_positive_core())
        char_negs.append(cpkg.read_negative_core())
        if char_source is None:
            char_source = resolve_character_ref(cpkg, shot, cid)

    loc_core = ""
    loc_neg = ""
    loc_source: str | None = None
    if location_id:
        if not validate_location_id(str(location_id)):
            print(f"[ERROR] code=2 bad location id {location_id}", file=sys.stderr)
            return EXIT_USAGE
        try:
            lpkg = LocationPackage.load(str(location_id))
            loc_core = lpkg.read_positive_core()
            arch = (lpkg.bible.get("architecture_lock") or "").strip()
            if arch:
                loc_core = assemble_prompt(core=loc_core, instruction=arch)
            loc_neg = lpkg.read_negative_core()
            loc_source = resolve_location_ref(lpkg, shot)
        except FileNotFoundError:
            # Soft: allow compose from action text until location pack exists
            print(
                f"[WARN] location pack missing: {location_id} "
                f"(continuing with action/prompt only; create locations/{location_id} later)",
                file=sys.stderr,
            )
            loc_core = f"location:{location_id}"

    prefer = type_meta.get("prefer_source") or "character"
    source = args.source
    if not source:
        if prefer == "location":
            source = loc_source or char_source
        else:
            source = char_source or loc_source

    mode = args.mode
    if mode == "auto":
        mode = "i2i" if source and os.path.isfile(source) else "t2i"

    camera = shot.get("camera") or {}
    cam_bits = [
        camera.get("angle") or "",
        camera.get("move") or "",
        camera.get("lens_feel") or "",
    ]
    cam_text = ", ".join(b for b in cam_bits if b)

    appearance = assemble_prompt(
        core=look_pos,
        instruction=assemble_prompt(
            core=", ".join(char_cores),
            instruction=loc_core,
            style_lock=framing,
            quality_tags=action,
            suffix=cam_text,
        ),
        quality_tags="cinematic still suitable for later animation, highly detailed, sharp focus",
    )
    negative = assemble_prompt(
        core=look_neg,
        instruction=", ".join(char_negs + ([loc_neg] if loc_neg else [])),
        suffix="watermark, text, logo, morphing face, identity shift",
    )

    model = args.model or story.doc.get("default_model") or "pro"
    denoise = (
        args.denoise
        if args.denoise is not None
        else float(story.doc.get("default_denoise") or 0.78)
    )
    cfg = args.cfg if args.cfg is not None else float(story.doc.get("default_cfg") or 3.5)
    seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)

    out_rel = shot.get("keyframe") or f"keyframes/{args.shot}.png"
    out_path = story.path(*out_rel.replace("\\", "/").split("/"))
    meta_path = story.path("meta", f"{args.shot}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)

    print(
        f"shot_compose episode={args.episode} shot={args.shot} "
        f"format={format_id} {width}x{height} look={look_id} mode={mode}"
    )
    print(f"  chars={char_ids} loc={location_id} type={shot_type}")
    print(f"  source={source or '(none)'}")

    if args.dry_run:
        print(f"[dry-run] out={out_path}")
        print(f"[dry-run] appearance[:200]={appearance[:200]}")
        return EXIT_OK

    if mode == "i2i":
        if not source or not os.path.isfile(source):
            print("[ERROR] code=20 I2I needs source ref", file=sys.stderr)
            return EXIT_SOURCE
        result = generate_i2i_image(
            input_image_path=source,
            prompt_text=action,
            denoise_val=denoise,
            cfg_val=cfg,
            model_type=model,
            output_filename=out_path,
            seed=seed,
            negative_text=negative,
            core_prefix=assemble_prompt(core=look_pos, instruction=", ".join(char_cores + [loc_core])),
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )
    else:
        result = generate_image(
            prompt_text=appearance,
            model_type=model,
            output_filename=out_path,
            seed=seed,
            negative_text=negative,
            width=width,
            height=height,
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )

    if not result.get("ok"):
        print(f"[ERROR] code=30 {result.get('error')} {result.get('message')}", file=sys.stderr)
        return EXIT_GEN

    story.update_shot(
        args.shot,
        action=action,
        character_ids=char_ids,
        location_id=location_id,
        shot_type=shot_type,
        appearance_prompt=appearance,
        keyframe=out_rel.replace("\\", "/"),
        keyframe_status="draft",
        seed=seed,
        work_size={"width": width, "height": height, "preset": work_preset_id},
        look_id=look_id,
        composed_at=utc_now_iso(),
    )

    # enrich meta
    if os.path.isfile(meta_path):
        import json

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    else:
        meta = {}
    meta.update(
        {
            "mode": "shot_compose",
            "episode_id": args.episode,
            "shot_id": args.shot,
            "look_id": look_id,
            "format": format_id,
            "work_preset": work_preset_id,
            "width": width,
            "height": height,
            "character_ids": char_ids,
            "location_id": location_id,
            "compose_mode": mode,
            "source": os.path.abspath(source) if source else None,
            "output_path": os.path.abspath(out_path),
            "created_at": utc_now_iso(),
        }
    )
    write_meta(meta_path, meta)

    print(f"OK keyframe={out_path} status=draft")
    print("  approve: python scripts/shot_approve.py --episode", args.episode, "--shot", args.shot)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
