#!/usr/bin/env python3
"""Surgical keyframe edit: local edit on existing keyframe, never full-frame blur.

Engines (coexist — pick by task):

  moody (default)  Moody I2I denoise remix — soft expression/tone, low denoise
  qwen             Qwen-Image-Edit-2509 instruction edit — object replace/remove,
                   prop fix, multi-ref identity (see generate_qwen_edit.py)

Not for character multi-view turns — use character_qwen_turns / generate_qwen_angle.

Replaces keyframes/<shot>.png, backs up prior file, sets keyframe_status=draft
for re-approval.

  python scripts/shot_keyframe_edit.py -e cafe_gomin_ep01 -s S03 \\
    -p "remove water droplets from face, keep photoreal skin, same identity" \\
    --denoise 0.35

  python scripts/shot_keyframe_edit.py -e EP -s S03 --engine qwen \\
    -p "remove the straw from the cup, keep the same person and table"

Do NOT use global Gaussian blur / pixelize on the whole frame (2026-07-13 accident).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import sys

from generate_moody_i2i import generate_i2i_image
from generate_qwen_edit import generate_qwen_edit
from lib.comfy_client import utc_now_iso, write_meta
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_GEN = 30

# Hard refuse known destructive whole-frame operations in the prompt
_FORBIDDEN = (
    "gaussian blur entire",
    "blur the whole",
    "blur entire image",
    "pixelate whole",
    "mosaic entire",
    "destroy face identity",
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Surgical edit of episode keyframe → draft for re-approve "
            "(--engine moody|qwen)"
        )
    )
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shot", "-s", required=True)
    p.add_argument(
        "--engine",
        choices=["moody", "qwen"],
        default="moody",
        help=(
            "moody = Moody I2I soft remix (default); "
            "qwen = Qwen-Image-Edit-2509 instruction edit"
        ),
    )
    p.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="Edit instruction (localized change; keep identity/photoreal)",
    )
    p.add_argument(
        "--denoise",
        "-d",
        type=float,
        default=None,
        help=(
            "moody: I2I denoise (default 0.35, max 0.65). "
            "qwen: KSampler denoise (default 1.0)"
        ),
    )
    p.add_argument(
        "--cfg",
        type=float,
        default=None,
        help="Sampler CFG (moody default 1.0; qwen uses engine defaults if omitted)",
    )
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="real")
    p.add_argument(
        "--lightning",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "qwen only: Lightning ON by default (fast first pass). "
            "If result overshoots, re-run with --no-lightning (and prefer "
            "steps 20 / cfg 4 via generate_qwen_edit quality escalate)"
        ),
    )
    p.add_argument(
        "--input2",
        "-i2",
        default=None,
        help="qwen only: optional ref image2 (identity / product)",
    )
    p.add_argument(
        "--input3",
        "-i3",
        default=None,
        help="qwen only: optional ref image3",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument(
        "--input",
        default=None,
        help="Source image (default: current keyframe path)",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not copy previous keyframe to keyframes/_history/",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--keep-approved",
        action="store_true",
        help="Do not reset keyframe_status to draft (not recommended)",
    )
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE

    low = args.prompt.lower()
    for bad in _FORBIDDEN:
        if bad in low:
            print(
                f"[ERROR] refused destructive whole-frame op in prompt: {bad!r}. "
                "Surgical edits only — no global blur.",
                file=sys.stderr,
            )
            return EXIT_USAGE

    engine = args.engine
    if engine == "moody":
        denoise = 0.35 if args.denoise is None else float(args.denoise)
        if denoise > 0.65:
            print(
                f"[ERROR] denoise={denoise} too high for surgical Moody edit "
                "(max 0.65). Use shot_compose for full regen, or --engine qwen "
                "for instruction-level changes.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        cfg = 1.0 if args.cfg is None else float(args.cfg)
    else:
        denoise = 1.0 if args.denoise is None else float(args.denoise)
        cfg = args.cfg  # None → generate_qwen_edit defaults

    try:
        story = StoryPackage.load(args.episode)
        shot = story.get_shot(args.shot)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING
    except KeyError:
        print(f"[ERROR] shot missing {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    kf_rel = shot.get("keyframe") or f"keyframes/{args.shot}.png"
    kf_path = story.path(*str(kf_rel).replace("\\", "/").split("/"))
    src = args.input or kf_path
    if not os.path.isfile(src):
        print(f"[ERROR] source keyframe missing: {src}", file=sys.stderr)
        return EXIT_MISSING

    # Strengthen identity lock in prompt (both engines; qwen may append again)
    edit_prompt = (
        f"{args.prompt.strip()}. "
        "Keep the same person identity, face structure, wardrobe, and camera framing. "
        "Photoreal, no cartoon, no global blur, no re-skin entire image."
    )

    print(
        f"shot_keyframe_edit episode={args.episode} shot={args.shot} "
        f"engine={engine} denoise={denoise}"
        + (f" model={args.model}" if engine == "moody" else f" lightning={args.lightning}")
    )
    print(f"  src={src}")
    print(f"  prompt={edit_prompt[:160]!r}")

    if args.dry_run:
        print("[dry-run] skip generate")
        return EXIT_OK

    # Backup
    if not args.no_backup and os.path.isfile(kf_path):
        hist = story.path("keyframes", "_history")
        os.makedirs(hist, exist_ok=True)
        stamp = utc_now_iso().replace(":", "").replace("+", "p")[:18]
        bak = os.path.join(hist, f"{args.shot}_{stamp}.png")
        shutil.copy2(kf_path, bak)
        print(f"  backup={bak}")

    tmp_out = kf_path + ".edit_tmp.png"
    meta_path = story.path("meta", f"{args.shot}_keyframe_edit.json")

    if engine == "moody":
        r = generate_i2i_image(
            input_image_path=src,
            prompt_text=edit_prompt,
            denoise_val=float(denoise),
            cfg_val=float(cfg),
            model_type=args.model,
            output_filename=tmp_out,
            seed=args.seed,
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )
    else:
        r = generate_qwen_edit(
            src,
            edit_prompt,
            input_image2_path=args.input2,
            input_image3_path=args.input3,
            output_filename=tmp_out,
            seed=args.seed,
            lightning=bool(args.lightning),
            denoise=float(denoise),
            cfg=cfg,
            raw_prompt=True,  # already locked above
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )

    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return EXIT_GEN

    # Atomic replace
    os.makedirs(os.path.dirname(kf_path) or ".", exist_ok=True)
    if os.path.isfile(kf_path):
        try:
            os.replace(tmp_out, kf_path)
        except OSError:
            shutil.copy2(tmp_out, kf_path)
            try:
                os.remove(tmp_out)
            except OSError:
                pass
    else:
        shutil.move(tmp_out, kf_path)

    fields = {
        "keyframe": str(kf_rel).replace("\\", "/"),
        "keyframe_source": f"surgical_edit_{engine}",
        "keyframe_edited_at": utc_now_iso(),
        "keyframe_edit_prompt": args.prompt.strip(),
        "keyframe_edit_engine": engine,
        "keyframe_edit_denoise": float(denoise),
    }
    if not args.keep_approved:
        fields["keyframe_status"] = "draft"
        # edited still invalidates prior motion approval
        fields["clip_status"] = "pending"
        if shot.get("motion_driver") in ("si2v", "s2v"):
            fields["lip_status"] = "pending"

    story.update_shot(args.shot, **fields)

    # Extend meta
    try:
        import json

        meta = {}
        if os.path.isfile(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        meta.update(
            {
                "mode": "surgical_keyframe_edit",
                "engine": engine,
                "episode_id": args.episode,
                "shot_id": args.shot,
                "source": f"surgical_edit_{engine}",
                "keyframe_status": fields.get("keyframe_status", "kept"),
                "edit_prompt": args.prompt.strip(),
                "denoise": float(denoise),
                "output_path": os.path.abspath(kf_path),
                "created_at": utc_now_iso(),
            }
        )
        write_meta(meta_path, meta)
    except Exception:
        pass

    print(f"OK {kf_path}")
    print(
        f"  keyframe_status={fields.get('keyframe_status', 'kept')} — re-approve: "
        f"python scripts/shot_approve.py -e {args.episode} -s {args.shot}"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
