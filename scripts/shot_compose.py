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


def _fit_image_to_canvas(
    src_path: str,
    dest_path: str,
    width: int,
    height: int,
    *,
    mode: str = "cover",
) -> str:
    """Resize source to exact format canvas so I2I latents match episode aspect.

    Moody I2I inherits latent size from the input image — without this step,
    keyframes stay at source aspect (e.g. 1:1 face ref or 16:9 location)
    even when meta claims work_9x16_540.

    mode=cover: scale to fill, center-crop (default, good for portrait stills)
    mode=contain: letterbox on neutral gray (keeps full source)
    """
    from PIL import Image

    im = Image.open(src_path).convert("RGB")
    tw, th = int(width), int(height)
    if im.size == (tw, th):
        if os.path.abspath(src_path) != os.path.abspath(dest_path):
            im.save(dest_path)
        return dest_path

    sw, sh = im.size
    if mode == "contain":
        scale = min(tw / sw, th / sh)
        nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
        resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (tw, th), (32, 32, 36))
        canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
        canvas.save(dest_path)
    else:
        scale = max(tw / sw, th / sh)
        nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
        resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        cropped = resized.crop((left, top, left + tw, top + th))
        if cropped.size != (tw, th):
            cropped = cropped.resize((tw, th), Image.Resampling.LANCZOS)
        cropped.save(dest_path)
    return dest_path


def _ensure_output_size(path: str, width: int, height: int) -> bool:
    """Force final keyframe to format size; return True if resize was applied."""
    from PIL import Image

    im = Image.open(path)
    if im.size == (int(width), int(height)):
        return False
    fitted = Image.new("RGB", (int(width), int(height)), (32, 32, 36))
    # cover-fit whatever came back
    sw, sh = im.size
    tw, th = int(width), int(height)
    scale = max(tw / sw, th / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    resized = im.convert("RGB").resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    cropped = resized.crop((left, top, left + tw, top + th))
    if cropped.size != (tw, th):
        cropped = cropped.resize((tw, th), Image.Resampling.LANCZOS)
    cropped.save(path)
    return True


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


def _approved_alias_path(pkg, alias: str) -> str | None:
    """Character or location package: approved/<alias>.png or manifest path."""
    p = pkg.path("approved", f"{alias}.png")
    if os.path.isfile(p):
        return p
    approved = (pkg.manifest.get("approved") or {}).get(alias)
    if approved:
        path = pkg.resolve(approved.get("path") or f"approved/{alias}.png")
        if os.path.isfile(path):
            return path
    return None


def resolve_character_ref(
    pkg: CharacterPackage,
    shot: dict,
    character_id: str,
    *,
    alias_priority: list[str] | None = None,
) -> str | None:
    """
    Community practice: bind the right sheet plate to the shot type.
    Priority: shot.character_refs → shot.character_ref_alias → type aliases → defaults.
    """
    refs = shot.get("character_refs") or {}
    rel = refs.get(character_id)
    if rel:
        path = pkg.resolve(rel)
        if os.path.isfile(path):
            return path

    alias = shot.get("character_ref_alias")
    if alias:
        path = _approved_alias_path(pkg, str(alias))
        if path:
            return path

    for a in alias_priority or []:
        path = _approved_alias_path(pkg, a)
        if path:
            return path

    for a in (
        "master_front",
        "expr_neutral",
        "costume_default",
        "master_full",
    ):
        path = _approved_alias_path(pkg, a)
        if path:
            return path
    return pkg.default_source_ref()


def resolve_location_ref(
    pkg: LocationPackage,
    shot: dict,
    *,
    alias_priority: list[str] | None = None,
) -> str | None:
    rel = shot.get("location_ref")
    if rel:
        path = pkg.resolve(rel)
        if os.path.isfile(path):
            return path

    alias = shot.get("location_ref_alias")
    if alias:
        path = _approved_alias_path(pkg, str(alias))
        if path:
            return path

    for a in alias_priority or []:
        path = _approved_alias_path(pkg, a)
        if path:
            return path

    for a in ("empty_stage", "master_wide", "angle_eye"):
        path = _approved_alias_path(pkg, a)
        if path:
            return path
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
    char_alias_priority = list(type_meta.get("character_ref_aliases") or [])
    loc_alias_priority = list(type_meta.get("location_ref_aliases") or [])
    i2v_hint = (type_meta.get("i2v_hint") or "").strip()

    char_cores: list[str] = []
    char_negs: list[str] = []
    char_source: str | None = None
    wardrobe_lock = ""
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
        app = cpkg.bible.get("appearance") or {}
        w = (app.get("wardrobe_default") or "").strip()
        if w and not wardrobe_lock:
            wardrobe_lock = w
        if char_source is None:
            char_source = resolve_character_ref(
                cpkg, shot, cid, alias_priority=char_alias_priority
            )

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
            loc_source = resolve_location_ref(
                lpkg, shot, alias_priority=loc_alias_priority
            )
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

    wardrobe_clause = f"wearing {wardrobe_lock}" if wardrobe_lock else ""
    appearance = assemble_prompt(
        core=look_pos,
        instruction=assemble_prompt(
            core=", ".join(char_cores),
            instruction=assemble_prompt(
                core=loc_core,
                instruction=action,
                style_lock=wardrobe_clause,
            ),
            style_lock=framing,
            suffix=cam_text,
        ),
        quality_tags=(
            "cinematic production keyframe still for later image-to-video, "
            "highly detailed, sharp focus, locked identity and wardrobe"
        ),
    )
    negative = assemble_prompt(
        core=look_neg,
        instruction=", ".join(char_negs + ([loc_neg] if loc_neg else [])),
        suffix="watermark, text, logo, morphing face, identity shift, different person",
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

    canvas_source = source
    if mode == "i2i":
        if not source or not os.path.isfile(source):
            print("[ERROR] code=20 I2I needs source ref", file=sys.stderr)
            return EXIT_SOURCE
        # Fit ref to episode format BEFORE I2I so latent aspect == keyframe aspect
        canvas_dir = story.path("meta", "_canvas_sources")
        os.makedirs(canvas_dir, exist_ok=True)
        canvas_source = os.path.join(canvas_dir, f"{args.shot}_{width}x{height}.png")
        _fit_image_to_canvas(source, canvas_source, width, height, mode="cover")
        print(f"  canvas_source={canvas_source} ({width}x{height} from {os.path.basename(source)})")
        # I2I body: action + framing + wardrobe; cores via prefix (identity anchors)
        # Avoid baking dialogue text into walls — action should be visual only.
        i2i_body = assemble_prompt(
            core=action,
            instruction=framing,
            style_lock=wardrobe_clause,
            suffix=assemble_prompt(
                core=cam_text,
                instruction="vertical 9:16 composition" if format_id == "shorts_9x16" else "",
                suffix="no text overlays, no readable signage letters, no logos",
            ),
        )
        result = generate_i2i_image(
            input_image_path=canvas_source,
            prompt_text=i2i_body,
            denoise_val=denoise,
            cfg_val=cfg,
            model_type=model,
            output_filename=out_path,
            seed=seed,
            negative_text=negative,
            core_prefix=assemble_prompt(
                core=look_pos, instruction=", ".join(char_cores + [loc_core])
            ),
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

    # Hard guarantee: final PNG matches format work size
    if os.path.isfile(out_path) and _ensure_output_size(out_path, width, height):
        print(f"[WARN] output resized to format canvas {width}x{height}: {out_path}")

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
    # Community: I2V should animate motion only — do not re-describe face identity
    motion_prompt = (shot.get("motion_prompt") or "").strip() or i2v_hint or (
        f"subtle natural motion, {cam_text or 'locked camera'}, keep identity and wardrobe fixed"
    )
    meta.update(
        {
            "mode": "shot_compose",
            "role": "production_keyframe",
            "episode_id": args.episode,
            "shot_id": args.shot,
            "look_id": look_id,
            "format": format_id,
            "work_preset": work_preset_id,
            "width": width,
            "height": height,
            "shot_type": shot_type,
            "character_ids": char_ids,
            "location_id": location_id,
            "compose_mode": mode,
            "source": os.path.abspath(source) if source else None,
            "canvas_source": os.path.abspath(canvas_source) if canvas_source else None,
            "char_source": os.path.abspath(char_source) if char_source else None,
            "loc_source": os.path.abspath(loc_source) if loc_source else None,
            "wardrobe_lock": wardrobe_lock or None,
            "output_path": os.path.abspath(out_path),
            "motion_prompt_suggested": motion_prompt,
            "i2v_rule": "Prompt motion/camera only; do not re-describe face or wardrobe.",
            "created_at": utc_now_iso(),
        }
    )
    write_meta(meta_path, meta)

    # Persist motion suggestion on shot if empty
    if not (shot.get("motion_prompt") or "").strip():
        story.update_shot(args.shot, motion_prompt=motion_prompt)

    print(f"OK keyframe={out_path} status=draft")
    print(f"  motion_prompt_suggested={motion_prompt[:120]}")
    print("  next: python scripts/storyboard_export.py -e", args.episode)
    print("  approve: python scripts/shot_approve.py --episode", args.episode, "--shot", args.shot)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
