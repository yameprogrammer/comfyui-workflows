#!/usr/bin/env python3
"""
OpenPose → ControlNet pose stills (agent-friendly one-stop).

Stack (already validated in this toolbox):
  OpenPose / DWPose RGB map
    → Z-Image Fun Union ControlNet (Pose condition)
    → optional identity via character_consistency pose mode

Qwen note:
  Qwen Edit/Angle are **instruction / multi-view** tools — they do **not** take
  OpenPose stick maps. For skeleton-locked limbs use this CLI (ControlNet).
  Use Qwen for “turn the camera 45°” style edits, not for gait keyframes.

Examples:
  # 1) Extract skeleton map from a photo / green plate still
  python scripts/generate_openpose_pose.py extract \\
    -i character.png -o pose_map.png

  # 2) Generate from a built-in template (side walk / jog keys)
  python scripts/generate_openpose_pose.py generate \\
    -i identity.png --template jog_contact \\
    -p "office worker navy suit, cel anime, solid green screen" \\
    -o out_contact.png --strength 0.85

  # 3) Generate from a custom OpenPose map
  python scripts/generate_openpose_pose.py generate \\
    -i identity.png --control pose_map.png -p "..." -o out.png

  # 4) List templates
  python scripts/generate_openpose_pose.py list-templates
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.comfy_client import fail_result, ok_result, resolve_meta_out, write_meta
from lib.still_model_profiles import ZIMAGE_MODEL_CHOICES
from lib.openpose_maps import (
    ensure_all_openpose_maps,
    ensure_openpose_map,
    extract_openpose_from_image,
)


TEMPLATE_HELP = (
    "stand_front|stand_side|stand_back|stand_idle|stand_qf|"
    "walk_side|jog_contact|jog_recoil|jog_pass|jog_high|"
    "sit_chair|hands_hips|wave|look_aside|head_*"
)


def cmd_list(_args: argparse.Namespace) -> int:
    paths = ensure_all_openpose_maps(force=False)
    print("OpenPose templates (synthetic BODY_18 maps):")
    for tid, path in sorted(paths.items()):
        print(f"  {tid:16s}  {path}")
    print()
    print("Jog cycle keys (side view, facing right):")
    print("  jog_contact → jog_recoil → jog_pass → jog_high → (loop)")
    print()
    print("Pipeline:")
    print("  extract|template → generate (ControlNet Union Pose)")
    print("  NOT Qwen — Qwen has no OpenPose input; use generate_qwen_angle for camera yaw only")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    if not args.input or not os.path.isfile(args.input):
        print(fail_result(error="INPUT_MISSING", message=args.input or ""))
        return 2
    out = args.output or os.path.splitext(args.input)[0] + "_openpose.png"
    path = extract_openpose_from_image(
        args.input,
        out,
        include_hand=not args.no_hands,
        include_face=not args.no_face,
    )
    print(ok_result(path=path, meta={"mode": "extract", "source": os.path.abspath(args.input)}))
    if args.meta_out:
        write_meta(
            resolve_meta_out(args.meta_out, out),
            {
                "tool": "generate_openpose_pose.extract",
                "input": os.path.abspath(args.input),
                "output": os.path.abspath(path),
            },
        )
    print(f"[openpose] extract → {path}")
    return 0 if os.path.isfile(path) else 1


def cmd_generate(args: argparse.Namespace) -> int:
    # Resolve control map
    control = args.control
    if args.template:
        control = ensure_openpose_map(
            args.template,
            width=int(args.map_width or 1024),
            height=int(args.map_height or 1536),
            force=bool(args.force_template),
        )
        print(f"[openpose] template={args.template} → {control}")
    if not control or not os.path.isfile(control):
        print(
            fail_result(
                error="CONTROL_REQUIRED",
                message="pass --control openpose.png OR --template jog_contact|walk_side|...",
            )
        )
        return 2

    prompt = args.prompt or ""
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read().strip()
    if not prompt:
        print(fail_result(error="PROMPT_REQUIRED", message="-p / --prompt-file"))
        return 2

    out = args.output
    if not out:
        print(fail_result(error="OUTPUT_REQUIRED", message="-o"))
        return 2

    # Prefer character_consistency pose mode when identity ref given
    if args.input and os.path.isfile(args.input) and not args.cn_only:
        from lib.character_consistency import run_pose

        r = run_pose(
            input_image=args.input,
            control_image=control,
            prompt=prompt,
            output_path=out,
            denoise=args.denoise,
            strength=float(args.strength),
            model_type=args.model,
            seed=args.seed,
            negative=args.negative or "",
            core_prefix="",
            timeout_sec=int(args.timeout),
            width=args.width,
            height=args.height,
            meta_out=args.meta_out,
        )
    else:
        from generate_moody_controlnet import generate_controlnet_image

        r = generate_controlnet_image(
            input_image_path=args.input or control,
            control_image_path=control,
            prompt_text=prompt,
            denoise_val=float(args.denoise if args.denoise is not None else 1.0),
            control_strength=float(args.strength),
            model_type=args.model,
            output_filename=out,
            seed=args.seed,
            negative_text=args.negative or "",
            timeout_sec=int(args.timeout),
            meta_out=args.meta_out,
            empty_latent=True,
            latent_width=args.width or 1024,
            latent_height=args.height or 1536,
            control_preprocess="openpose",
        )

    ok = isinstance(r, dict) and r.get("ok")
    print(r if isinstance(r, dict) else r)
    if ok:
        print(f"[openpose] generate → {out}")
    return 0 if ok else 1


def cmd_ensure_templates(args: argparse.Namespace) -> int:
    paths = ensure_all_openpose_maps(
        width=int(args.map_width or 1024),
        height=int(args.map_height or 1536),
        force=bool(args.force_template),
    )
    for tid, path in sorted(paths.items()):
        print(f"OK {tid} {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="OpenPose extract + ControlNet pose generate (not Qwen)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-templates", help="List synthetic OpenPose templates")
    p_list.set_defaults(func=cmd_list)

    p_ex = sub.add_parser("extract", help="Detect OpenPose map from an image")
    p_ex.add_argument("--input", "-i", required=True)
    p_ex.add_argument("--output", "-o", default=None)
    p_ex.add_argument("--no-hands", action="store_true")
    p_ex.add_argument("--no-face", action="store_true")
    p_ex.add_argument("--meta-out", default=None)
    p_ex.set_defaults(func=cmd_extract)

    p_gen = sub.add_parser(
        "generate",
        help="Generate still from OpenPose control (+ optional identity ref)",
    )
    p_gen.add_argument("--input", "-i", default=None, help="Identity / face-body reference")
    p_gen.add_argument("--control", default=None, help="OpenPose RGB map path")
    p_gen.add_argument(
        "--template",
        default=None,
        help=f"Built-in template id ({TEMPLATE_HELP})",
    )
    p_gen.add_argument("--prompt", "-p", default=None)
    p_gen.add_argument("--prompt-file", default=None)
    p_gen.add_argument("--output", "-o", default=None)
    p_gen.add_argument("--negative", default="")
    p_gen.add_argument("--strength", type=float, default=0.85, help="ControlNet strength")
    p_gen.add_argument("--denoise", type=float, default=None)
    p_gen.add_argument("--model", choices=list(ZIMAGE_MODEL_CHOICES), default="pro")
    p_gen.add_argument("--seed", type=int, default=None)
    p_gen.add_argument("--width", type=int, default=768)
    p_gen.add_argument("--height", type=int, default=1280)
    p_gen.add_argument("--map-width", type=int, default=1024)
    p_gen.add_argument("--map-height", type=int, default=1536)
    p_gen.add_argument("--force-template", action="store_true")
    p_gen.add_argument(
        "--cn-only",
        action="store_true",
        help="Skip character_consistency wrapper; call ControlNet only",
    )
    p_gen.add_argument("--timeout", type=int, default=600)
    p_gen.add_argument("--meta-out", default=None)
    p_gen.set_defaults(func=cmd_generate)

    p_ens = sub.add_parser("ensure-templates", help="Write all synthetic maps to disk")
    p_ens.add_argument("--map-width", type=int, default=1024)
    p_ens.add_argument("--map-height", type=int, default=1536)
    p_ens.add_argument("--force-template", action="store_true")
    p_ens.set_defaults(func=cmd_ensure_templates)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
