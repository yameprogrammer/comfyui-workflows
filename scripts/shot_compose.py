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
from generate_moody_i2i_lock import generate_i2i_lock
from generate_moody_i2i_ipadapter import generate_i2i_ipadapter
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

# Production keyframe denoise caps (identity-safe). Heavy remix uses higher only with lock.
DENOISE_CHAR_DEFAULT = 0.52
DENOISE_CHAR_MAX = 0.58
DENOISE_LOC_DEFAULT = 0.55
DENOISE_LOC_MAX = 0.65
DENOISE_LEGACY_HIGH_WARN = 0.70


def _strip_prompt_meta_tags(text: str) -> str:
    """Remove [intent:S01]-style tags that models often render as on-image text."""
    import re

    if not text:
        return text
    # [intent:S01], [intent: about to leave], etc.
    text = re.sub(r"\[intent:[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;")
    return text

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


def _infer_space_mode(action: str, shot_type: str) -> str:
    """interior | exterior | neutral — for location core filtering."""
    t = f"{action or ''} {shot_type or ''}".lower()
    interior_hits = sum(
        1
        for k in (
            "checkout",
            "interior",
            "inside",
            "shelves",
            "fluorescent",
            "counter",
            "fridge",
            "aisle",
            "cashier",
        )
        if k in t
    )
    exterior_hits = sum(
        1
        for k in (
            "sidewalk",
            "parasol",
            "wet street",
            "outside",
            "exterior",
            "asphalt",
            "under pure yellow",
            "under yellow",
            "street overcast",
            "utility pole",
            "empty of people",
            "wet road",
        )
        if k in t
    )
    if shot_type in ("establishing", "wide") and exterior_hits >= interior_hits:
        return "exterior"
    if interior_hits > exterior_hits:
        return "interior"
    if exterior_hits > interior_hits:
        return "exterior"
    return "neutral"


def _space_filter_loc_core(loc_core: str, space_mode: str) -> str:
    """Drop conflicting interior/exterior clauses from a combined location core."""
    if not loc_core or space_mode == "neutral":
        return loc_core
    # Split on common separators; keep clauses matching space
    raw = loc_core.replace(";", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    exterior_kw = (
        "asphalt",
        "sidewalk",
        "parasol",
        "vinyl",
        "utility",
        "overcast rain",
        "wet street",
        "lane paint",
        "pole",
        "wires",
    )
    interior_kw = (
        "shelf",
        "shelves",
        "fridge",
        "fluorescent",
        "interior",
        "snack",
        "checkout",
        "aisle",
        "counter",
    )
    kept: list[str] = []
    for p in parts:
        pl = p.lower()
        is_ext = any(k in pl for k in exterior_kw)
        is_int = any(k in pl for k in interior_kw)
        if space_mode == "interior":
            if is_ext and not is_int:
                continue
            kept.append(p)
        elif space_mode == "exterior":
            if is_int and not is_ext:
                continue
            kept.append(p)
        else:
            kept.append(p)
    return ", ".join(kept) if kept else loc_core


def _gray_key_rgba(im, tolerance: int = 42):
    """Soft-key near-neutral studio backdrop so character can composite onto set."""
    from PIL import Image

    rgba = im.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    # Sample border median as studio color
    border = []
    step = max(1, min(w, h) // 64)
    for x in range(0, w, step):
        border.append(pixels[x, 0][:3])
        border.append(pixels[x, h - 1][:3])
    for y in range(0, h, step):
        border.append(pixels[0, y][:3])
        border.append(pixels[w - 1, y][:3])
    if not border:
        return rgba
    br = sum(c[0] for c in border) / len(border)
    bg = sum(c[1] for c in border) / len(border)
    bb = sum(c[2] for c in border) / len(border)
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            # neutral + close to border gray
            mx, mn = max(r, g, b), min(r, g, b)
            neutral = (mx - mn) < 28
            dist = abs(r - br) + abs(g - bg) + abs(b - bb)
            if neutral and dist < tolerance * 3:
                # feather: fully transparent near exact match
                if dist < tolerance:
                    pixels[x, y] = (r, g, b, 0)
                elif dist < tolerance * 2:
                    pixels[x, y] = (r, g, b, 90)
                else:
                    pixels[x, y] = (r, g, b, 160)
    return rgba


def _layout_char_on_location(
    char_path: str,
    loc_path: str,
    dest_path: str,
    width: int,
    height: int,
    *,
    char_height_ratio: float = 0.88,
    anchor: str = "center",
    crop_mode: str = "full",
) -> str:
    """Build a 16:9 layout: location plate + gray-keyed character. Better I2I base than face crop.

    crop_mode:
      full — full body plate
      waist — keep upper ~68% (head→mid-thigh) for medium shots
      chest — upper ~55% for tighter medium/close
    """
    from PIL import Image

    tw, th = int(width), int(height)
    # Location cover-fit as set
    loc = Image.open(loc_path).convert("RGB")
    sw, sh = loc.size
    scale = max(tw / sw, th / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    loc_r = loc.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    canvas = loc_r.crop((left, top, left + tw, top + th)).convert("RGBA")

    char = _gray_key_rgba(Image.open(char_path))
    cw, ch = char.size
    if crop_mode == "waist":
        char = char.crop((0, 0, cw, max(1, int(ch * 0.68))))
        cw, ch = char.size
    elif crop_mode == "chest":
        char = char.crop((0, 0, cw, max(1, int(ch * 0.55))))
        cw, ch = char.size
    target_h = max(1, int(th * char_height_ratio))
    scale_c = target_h / ch
    # Avoid ultra-wide stretch: also cap width ~50% for medium
    max_w = int(tw * (0.48 if crop_mode != "full" else 0.55))
    if int(cw * scale_c) > max_w:
        scale_c = max_w / cw
    cnw, cnh = max(1, int(round(cw * scale_c))), max(1, int(round(ch * scale_c)))
    char_r = char.resize((cnw, cnh), Image.Resampling.LANCZOS)

    if anchor == "right":
        px = int(tw * 0.52)
    elif anchor == "left":
        px = int(tw * 0.08)
    else:
        px = (tw - cnw) // 2
    # waist/chest: lower third; full: feet near bottom
    if crop_mode in ("waist", "chest"):
        py = int(th * 0.12)
    else:
        py = th - cnh
    py = max(0, min(py, th - cnh))
    canvas.paste(char_r, (px, py), char_r)
    out = canvas.convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
    out.save(dest_path)
    return dest_path


def _source_has_face_heuristic(path: str) -> bool:
    """True if upper third is not empty/gray-only (rough face/body presence check)."""
    from PIL import Image

    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return False
    w, h = im.size
    # costume_default style: head cropped — upper 12% nearly uniform
    band = im.crop((0, 0, w, max(1, int(h * 0.12))))
    pixels = list(band.getdata())
    if not pixels:
        return False
    avg = tuple(sum(c[i] for c in pixels) / len(pixels) for i in range(3))
    var = sum(sum((c[i] - avg[i]) ** 2 for i in range(3)) for c in pixels) / len(pixels)
    # low variance top band → likely studio with no head
    return var > 180.0


def _pick_canvas_mode(source_path: str, prefer: str, layout_used: bool) -> str:
    if layout_used:
        return "cover"  # layout already exact size
    try:
        from PIL import Image

        im = Image.open(source_path)
        sw, sh = im.size
        # Near 16:9 location plates → cover (no letterbox bars)
        if sw > sh * 1.2:
            return "cover"
        # Square character plates → contain so we don't crop heads
        if sw > 0 and abs(sw - sh) / max(sw, sh) < 0.12:
            return "contain"
        # Portrait taller than wide
        if sh > sw * 1.15:
            return "contain"
    except Exception:
        pass
    if prefer == "location":
        return "cover"
    return "contain"


def _resolve_denoise(
    *,
    requested: float | None,
    episode_default: float | None,
    has_character: bool,
    layout_used: bool,
) -> float:
    base = (
        float(requested)
        if requested is not None
        else float(episode_default if episode_default is not None else DENOISE_CHAR_DEFAULT)
    )
    if has_character:
        # Never inherit legacy 0.78 story defaults for face shots
        if requested is None and base >= DENOISE_LEGACY_HIGH_WARN:
            base = DENOISE_CHAR_DEFAULT
        cap = DENOISE_CHAR_MAX if layout_used or True else DENOISE_CHAR_MAX
        return min(base, cap)
    if requested is None and base >= DENOISE_LEGACY_HIGH_WARN:
        base = DENOISE_LOC_DEFAULT
    return min(base, DENOISE_LOC_MAX)


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
    parser.add_argument(
        "--engine",
        choices=["auto", "i2i", "i2i_lock", "ipadapter"],
        default="auto",
        help="I2I engine: auto=ipadapter→lock for characters, plain i2i for sets",
    )
    parser.add_argument(
        "--canvas-mode",
        choices=["auto", "cover", "contain"],
        default="auto",
        help="How to fit source to work canvas (auto: contain for square char plates)",
    )
    parser.add_argument(
        "--no-layout",
        action="store_true",
        help="Disable character-on-location layout composite",
    )
    parser.add_argument("--source", default=None, help="Force I2I source image path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--from-prev-shot",
        action="store_true",
        help=(
            "One-take: write keyframe from previous shot's last work-clip frame "
            "(requires prev clip_status=approved unless --force-clip-gate)"
        ),
    )
    parser.add_argument(
        "--force-clip-gate",
        action="store_true",
        help="With --from-prev-shot, allow unapproved previous clip (debug)",
    )
    parser.add_argument(
        "--prev-shot",
        default=None,
        help="With --from-prev-shot, explicit previous shot id (default: order-1)",
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    if args.all:
        if args.shot:
            print("[ERROR] code=2 use either --shot or --all, not both", file=sys.stderr)
            return EXIT_USAGE
        if args.from_prev_shot:
            print("[ERROR] code=2 --from-prev-shot is single-shot only", file=sys.stderr)
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

    # P1-2: last-frame keyframe from previous work clip (no Moody gen)
    if args.from_prev_shot:
        from lib.one_take import keyframe_from_prev_clip

        format_id = story.format_id()
        work_preset = story.doc.get("default_work_preset")
        try:
            width, height, _, _ = resolve_work_size(format_id, work_preset)
        except Exception:
            width, height = 544, 960
        width = int(round(width / 16) * 16)
        height = int(round(height / 16) * 16)
        if args.dry_run:
            print(f"[dry-run] from-prev-shot {args.shot} canvas={width}x{height}")
            return EXIT_OK
        kr = keyframe_from_prev_clip(
            story,
            args.shot,
            width=width,
            height=height,
            force_clip_gate=bool(args.force_clip_gate),
            prev_shot_id=args.prev_shot,
        )
        if not kr.get("ok"):
            code = int(kr.get("exit_code") or EXIT_SOURCE)
            print(f"[ERROR] code={code} {kr.get('error')}: {kr.get('message')}", file=sys.stderr)
            return code if code in (EXIT_USAGE, EXIT_MISSING, EXIT_SOURCE, 22) else EXIT_GEN
        story.update_shot(
            args.shot,
            keyframe=kr["keyframe_rel"],
            keyframe_status="draft",
            continuity={
                "style": "one_take",
                "chain": "last_frame",
                "match_from": kr.get("prev_sid"),
                "from_clip": os.path.relpath(kr["prev_clip"], story.root).replace(
                    "\\", "/"
                ),
            },
            composed_at=utc_now_iso(),
            source="from_prev_shot",
        )
        print(
            f"OK keyframe from prev {kr.get('prev_sid')} → {kr['keyframe_path']} "
            f"(status=draft — shot_approve when ready)"
        )
        return EXIT_OK

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

    action = _strip_prompt_meta_tags((args.action or shot.get("action") or "").strip())
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

    # Space-aware location text (avoid interior+exterior soup)
    space_mode = _infer_space_mode(action, shot_type)
    loc_core = _space_filter_loc_core(loc_core, space_mode)

    prefer = type_meta.get("prefer_source") or "character"
    # Empty / no-character shots must use location plate even if type prefers character
    if not char_ids:
        prefer = "location"
    source = args.source
    if not source:
        if prefer == "location":
            source = loc_source or char_source
        else:
            # Prefer face-bearing character plates over headless costume
            if char_source and not _source_has_face_heuristic(char_source):
                for alt_alias in (
                    "pose_stand_idle",
                    "pose_walk",
                    "turn_front",
                    "master_full",
                    "master_front",
                ):
                    if char_ids:
                        try:
                            cpkg_alt = CharacterPackage.load(char_ids[0])
                            alt = _approved_alias_path(cpkg_alt, alt_alias)
                            if alt and _source_has_face_heuristic(alt):
                                print(
                                    f"  [source-fix] headless/low-face plate → {alt_alias}"
                                )
                                char_source = alt
                                break
                        except FileNotFoundError:
                            pass
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
    # Leaner quality tags — avoid drowning framing
    quality_tags = (
        "photoreal cinematic film still, natural skin texture, sharp focus, "
        "locked identity and wardrobe"
    )
    appearance = assemble_prompt(
        core=action,
        instruction=assemble_prompt(
            core=framing,
            instruction=assemble_prompt(
                core=", ".join(char_cores),
                instruction=loc_core,
                style_lock=wardrobe_clause,
            ),
            suffix=cam_text,
        ),
        quality_tags=quality_tags,
    )
    neg_extra = "morphing face, identity shift, different person, watermark, text, logo"
    if space_mode == "interior":
        neg_extra += ", outdoor street only, sidewalk parasol dominating frame, extra people"
    elif space_mode == "exterior":
        neg_extra += ", indoor-only empty aisle, face close-up fill frame"
    if char_ids:
        neg_extra += ", close-up face only, cropped head, headless, extra person, crowd"
    neg_extra += ", text on umbrella, text on awning, written words, letters, numbers on props"
    negative = assemble_prompt(
        core=look_neg,
        instruction=", ".join(char_negs + ([loc_neg] if loc_neg else [])),
        suffix=neg_extra,
    )

    model = args.model or story.doc.get("default_model") or "pro"
    has_character = bool(char_ids and char_source)
    # layout decision later; provisional denoise
    denoise = _resolve_denoise(
        requested=args.denoise,
        episode_default=story.doc.get("default_denoise"),
        has_character=has_character,
        layout_used=False,
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
    print(f"  chars={char_ids} loc={location_id} type={shot_type} space={space_mode}")
    print(f"  source={source or '(none)'}")

    if args.dry_run:
        print(f"[dry-run] out={out_path}")
        print(f"[dry-run] denoise={denoise} cfg={cfg} engine={args.engine}")
        print(f"[dry-run] loc_core[:180]={loc_core[:180]}")
        print(f"[dry-run] appearance[:200]={appearance[:200]}")
        return EXIT_OK

    canvas_source = source
    layout_used = False
    engine_used = "i2i"
    if mode == "i2i":
        if not source or not os.path.isfile(source):
            print("[ERROR] code=20 I2I needs source ref", file=sys.stderr)
            return EXIT_SOURCE
        canvas_dir = story.path("meta", "_canvas_sources")
        os.makedirs(canvas_dir, exist_ok=True)
        canvas_source = os.path.join(canvas_dir, f"{args.shot}_{width}x{height}.png")

        # Character + location → layout composite (set plate + keyed figure)
        use_layout = (
            not args.no_layout
            and has_character
            and loc_source
            and os.path.isfile(loc_source)
            and char_source
            and os.path.isfile(char_source)
            and shot_type in ("medium", "wide", "closeup")
            and prefer != "location"
        )
        if use_layout:
            anchor = "right" if "right third" in (action or "").lower() else "center"
            if shot_type == "wide":
                ratio, crop_mode = 0.92, "full"
            elif shot_type == "closeup":
                ratio, crop_mode = 0.90, "chest"
            else:
                # medium default: waist-up plate, fill frame height
                ratio, crop_mode = 0.95, "waist"
            _layout_char_on_location(
                char_source,
                loc_source,
                canvas_source,
                width,
                height,
                char_height_ratio=ratio,
                anchor=anchor,
                crop_mode=crop_mode,
            )
            layout_used = True
            source = canvas_source
            print(
                f"  layout=char_on_loc char={os.path.basename(char_source)} "
                f"loc={os.path.basename(loc_source)} anchor={anchor} crop={crop_mode}"
            )
        else:
            cmode = args.canvas_mode
            if cmode == "auto":
                cmode = _pick_canvas_mode(source, prefer, layout_used=False)
            _fit_image_to_canvas(source, canvas_source, width, height, mode=cmode)
            print(
                f"  canvas_source={canvas_source} ({width}x{height} "
                f"mode={cmode} from {os.path.basename(source)})"
            )

        denoise = _resolve_denoise(
            requested=args.denoise,
            episode_default=story.doc.get("default_denoise"),
            has_character=has_character,
            layout_used=layout_used,
        )
        # Slightly higher denoise when blending layout seams
        if layout_used and args.denoise is None:
            denoise = min(0.56, max(denoise, 0.50))
        # Inserts need enough denoise to add props onto empty plates
        if shot_type == "insert" and args.denoise is None:
            denoise = max(denoise, 0.58)

        # I2I body: action first, then framing — short, not look-essay
        no_text = (
            "no text overlays, no readable signage letters, no logos, "
            "no watermarks, no intent labels, no shot id text on objects"
        )
        i2i_body = assemble_prompt(
            core=action,
            instruction=framing,
            style_lock=wardrobe_clause,
            suffix=assemble_prompt(
                core=cam_text,
                instruction="vertical 9:16 composition" if format_id == "shorts_9x16" else "",
                suffix=no_text,
            ),
        )
        # lean prefix: look + identity + space-filtered loc
        core_prefix = assemble_prompt(
            core=look_pos,
            instruction=", ".join([c for c in char_cores + [loc_core] if c]),
        )

        eng = args.engine
        if eng == "auto":
            eng = "ipadapter" if has_character else "i2i"

        def _run_i2i(engine_name: str) -> dict:
            if engine_name == "ipadapter":
                return generate_i2i_ipadapter(
                    input_image_path=canvas_source,
                    prompt_text=i2i_body,
                    denoise_val=denoise,
                    cfg_val=cfg,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=core_prefix,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                    ipa_weight=0.72,
                )
            if engine_name == "i2i_lock":
                return generate_i2i_lock(
                    input_image_path=canvas_source,
                    prompt_text=i2i_body,
                    denoise_val=denoise,
                    cfg_val=cfg,
                    model_type=model,
                    output_filename=out_path,
                    seed=seed,
                    negative_text=negative,
                    core_prefix=core_prefix,
                    meta_out=meta_path,
                    timeout_sec=args.timeout,
                    max_denoise=DENOISE_CHAR_MAX if has_character else DENOISE_LOC_MAX,
                )
            return generate_i2i_image(
                input_image_path=canvas_source,
                prompt_text=i2i_body,
                denoise_val=denoise,
                cfg_val=cfg,
                model_type=model,
                output_filename=out_path,
                seed=seed,
                negative_text=negative,
                core_prefix=core_prefix,
                meta_out=meta_path,
                timeout_sec=args.timeout,
            )

        print(f"  engine={eng} denoise={denoise} cfg={cfg} layout={layout_used}")
        result = _run_i2i(eng)
        engine_used = eng
        if (
            eng == "ipadapter"
            and not result.get("ok")
            and result.get("error")
            in ("IPADAPTER_FAILED", "QUEUE_FAILED", "COMFY_NO_OUTPUT", "WF_INCOMPLETE")
        ):
            print(
                f"[WARN] IPAdapter failed ({result.get('error')}); fallback → i2i_lock"
            )
            result = _run_i2i("i2i_lock")
            engine_used = "i2i_lock_fallback"
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
        engine_used = "t2i"

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
            "engine": engine_used,
            "layout_used": layout_used if mode == "i2i" else False,
            "space_mode": space_mode,
            "denoise": denoise if mode == "i2i" else None,
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
