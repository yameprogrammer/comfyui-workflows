#!/usr/bin/env python3
"""
Community-style character turnaround sheet generation.

Generates ONE multi-view image (front | 3/4 | side | back) with OpenPose strip
+ empty-latent ControlNet, then crops panels into refs/ for the character package.

Based on community research (see docs/character_turnaround_community_research.md):
  multi-view OpenPose template, orthographic model-sheet language, flat lighting,
  consistent identity/outfit tags, plain background.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_moody_controlnet import generate_controlnet_image
from lib.character_package import CharacterPackage
from lib.contact_sheet import build_contact_sheet
from lib.openpose_multiview import (
    crop_strip_to_panels,
    ensure_body_turnaround_strip,
    ensure_head_turnaround_strip,
)
from lib.profiles import ensure_export_dirs, get_profile


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_GEN = 30


def _wardrobe(pkg: CharacterPackage) -> str:
    w = (pkg.bible.get("appearance") or {}).get("wardrobe_default")
    return w or (
        "black crew-neck t-shirt, light wash blue jeans, white sneakers, fully clothed casual"
    )


def _body_prompt(core: str, wardrobe: str) -> str:
    return (
        f"{core}, "
        "character design turnaround sheet, orthographic camera, professional model sheet, "
        "same character shown in four full-body standing views arranged left to right — "
        "front view, three-quarter view, strict side profile, back view, "
        "neutral A-pose or relaxed standing with arms slightly away from torso in every panel, "
        f"fully clothed wearing {wardrobe}, no nude, no nsfw, "
        "consistent facial features across all views, consistent hair across all views, "
        "consistent body proportions across all views, consistent outfit across all views, "
        "flat even studio lighting, plain light gray background, clean spacing between figures, "
        "no merged panels, head-to-toe visible in each panel, animation game character reference, "
        "clean photoreal final render, no stick figure, no openpose skeleton overlay"
    )


def _head_prompt(core: str) -> str:
    return (
        f"{core}, "
        "character head turnaround reference sheet, orthographic head-and-shoulders, "
        "same character face shown in four views arranged left to right — "
        "front face, three-quarter face, strict side profile, back of head only, "
        "technical model sheet head rotation not beauty portrait, "
        "consistent facial structure and hairstyle across views, "
        "flat even studio lighting, plain light gray background, clean spacing, "
        "back panel shows only hair and nape no face, "
        "clean photoreal final render, no stick figure, no openpose skeleton overlay"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Multi-view OpenPose character turnaround sheet")
    ap.add_argument("--id", required=True)
    ap.add_argument("--mode", choices=["body", "head", "both"], default="both")
    ap.add_argument("--model", default="pro", choices=["real", "pro", "wild"])
    ap.add_argument("--strength", type=float, default=0.78)
    ap.add_argument("--seed", type=int, default=99001)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--panel-w", type=int, default=512)
    ap.add_argument("--panel-h-body", type=int, default=768)
    ap.add_argument("--panel-h-head", type=int, default=512)
    args = ap.parse_args(argv)

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] package missing {args.id}", file=sys.stderr)
        return EXIT_USAGE

    core = pkg.read_positive_core()
    wardrobe = _wardrobe(pkg)
    profile = get_profile(pkg.active_profile_id() or "full_sheet")
    export_root = ensure_export_dirs(pkg.root, profile)
    work = os.path.join(export_root, "turnaround_work")
    os.makedirs(work, exist_ok=True)

    modes = []
    if args.mode in ("body", "both"):
        modes.append("body")
    if args.mode in ("head", "both"):
        modes.append("head")

    ok = 0
    fail = 0
    review_paths = []

    for mode in modes:
        if mode == "body":
            strip = ensure_body_turnaround_strip(
                args.panel_w, args.panel_h_body, force=True
            )
            out_img = os.path.join(work, f"{args.id}__multiview_body_turn.png")
            prompt = _body_prompt(core, wardrobe)
            seed = args.seed
            lat_w = args.panel_w * 4
            lat_h = args.panel_h_body
            ref_subdir = "turnaround"
            prefix = f"{args.id}__turn_mv"
        else:
            strip = ensure_head_turnaround_strip(
                args.panel_w, args.panel_h_head, force=True
            )
            out_img = os.path.join(work, f"{args.id}__multiview_head_turn.png")
            prompt = _head_prompt(core)
            seed = args.seed + 17
            lat_w = args.panel_w * 4
            lat_h = args.panel_h_head
            ref_subdir = "head"
            prefix = f"{args.id}__head_mv"

        print(f"\n=== multiview {mode} strip={strip} → {out_img} ===")
        r = generate_controlnet_image(
            input_image_path=None,
            control_image_path=strip,
            prompt_text=prompt,
            denoise_val=1.0,
            cfg_val=3.5,
            control_strength=args.strength,
            model_type=args.model,
            output_filename=out_img,
            seed=seed,
            core_prefix="",
            empty_latent=True,
            latent_width=lat_w,
            latent_height=lat_h,
            control_preprocess="openpose",
            timeout_sec=args.timeout,
        )
        if not (isinstance(r, dict) and r.get("ok") and os.path.isfile(out_img)):
            print(f"  FAIL {mode}: {r}")
            fail += 1
            continue
        ok += 1
        panels_dir = pkg.path("refs", ref_subdir)
        panels = crop_strip_to_panels(out_img, panels_dir, 4, prefix)
        print(f"  cropped {len(panels)} panels → {panels_dir}")
        review_paths.append(out_img)
        for p in panels:
            print(f"    {os.path.basename(p)}")

    if review_paths:
        sheet = os.path.join(export_root, "review_multiview_turns.png")
        build_contact_sheet(review_paths, sheet, cols=1, thumb_max=900)
        print(f"\nreview={sheet}")

    print(f"\nDone multiview turns ok={ok} fail={fail}")
    return EXIT_OK if fail == 0 else EXIT_GEN


if __name__ == "__main__":
    raise SystemExit(main())
