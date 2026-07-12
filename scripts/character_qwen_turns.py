#!/usr/bin/env python3
"""
Character sheet head/body turns via Qwen-Image-Edit-2511 Multiple-Angles LoRA.

Replaces broken Moody I2I / OpenPose-only turn paths for identity-preserving angles.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_qwen_angle import generate_qwen_angle
from lib.character_package import CharacterPackage
from lib.contact_sheet import build_contact_sheet
from lib.profiles import ensure_export_dirs, get_profile


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 31

HEAD_VIEWS = ("head_front", "head_qf", "head_side", "head_back")
BODY_VIEWS = ("body_front", "body_qf", "body_side", "body_back")

HEAD_ALIAS = {
    "head_front": "head_front",
    "head_qf": "head_qf",
    "head_side": "head_side",
    "head_back": "head_back",
}
BODY_ALIAS = {
    "body_front": "turn_front",
    "body_qf": "turn_qf",
    "body_side": "turn_side",
    "body_back": "turn_back",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qwen multi-angle character turns")
    ap.add_argument("--id", required=True)
    ap.add_argument("--mode", choices=["head", "body", "both"], default="both")
    ap.add_argument("--seed-base", type=int, default=100001)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--angles-strength", type=float, default=0.9)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--approve", action="store_true", help="Auto-approve into approved/")
    ap.add_argument(
        "--source-head",
        default=None,
        help="Override head source (default approved/master_front.png)",
    )
    ap.add_argument(
        "--source-body",
        default=None,
        help="Override body source (default approved/master_full.png then master_front)",
    )
    args = ap.parse_args(argv)

    try:
        pkg = CharacterPackage.load(args.id)
    except FileNotFoundError:
        print(f"[ERROR] package missing {args.id}", file=sys.stderr)
        return EXIT_USAGE

    head_src = args.source_head or pkg.path("approved", "master_front.png")
    body_src = args.source_body
    if not body_src:
        # Prefer dressed costume lock → master_full → face
        for cand in (
            pkg.path("approved", "costume_default.png"),
            pkg.path("approved", "master_full.png"),
        ):
            if os.path.isfile(cand):
                body_src = cand
                break
        if not body_src:
            body_src = head_src

    if args.mode in ("head", "both") and not os.path.isfile(head_src):
        print(f"[ERROR] head source missing: {head_src}", file=sys.stderr)
        return EXIT_USAGE
    if args.mode in ("body", "both") and not os.path.isfile(body_src):
        print(f"[ERROR] body source missing: {body_src}", file=sys.stderr)
        return EXIT_USAGE

    wardrobe = (pkg.bible.get("appearance") or {}).get("wardrobe_default") or (
        "black crew-neck t-shirt, light wash blue jeans, white sneakers, fully clothed"
    )
    body_extra = (
        f"full body standing, head-to-toe visible, fully clothed wearing {wardrobe}, "
        "neutral A-pose arms slightly away, plain light gray studio background, "
        "orthographic character model sheet, no nude"
    )
    head_extra = (
        "head and shoulders portrait, plain light gray studio background, "
        "technical character head turnaround, keep same face identity and hairstyle"
    )

    jobs = []
    if args.mode in ("head", "both"):
        for i, v in enumerate(HEAD_VIEWS):
            jobs.append(("head", v, head_src, head_extra, args.seed_base + i))
    if args.mode in ("body", "both"):
        for i, v in enumerate(BODY_VIEWS):
            jobs.append(
                ("body", v, body_src, body_extra, args.seed_base + 100 + i)
            )

    profile = get_profile(pkg.active_profile_id() or "full_sheet")
    export_root = ensure_export_dirs(pkg.root, profile)
    ok_n = fail_n = 0
    review_paths = []

    for kind, view, src, extra, seed in jobs:
        sub = "head" if kind == "head" else "turnaround"
        out = pkg.path(
            "refs",
            sub,
            f"{args.id}__qwen_{view}__s{seed}__c01.png",
        )
        meta = pkg.path("meta", f"{args.id}__qwen_{view}__s{seed}__c01.json")
        print(f"\n=== Qwen {view} seed={seed} ===")
        r = generate_qwen_angle(
            src,
            view,
            output_filename=out,
            seed=seed,
            extra_prompt=extra,
            steps=args.steps,
            angles_strength=args.angles_strength,
            timeout_sec=args.timeout,
            meta_out=meta,
        )
        if r.get("ok") and os.path.isfile(out):
            ok_n += 1
            review_paths.append(out)
            if args.approve:
                alias = HEAD_ALIAS.get(view) if kind == "head" else BODY_ALIAS.get(view)
                if alias:
                    try:
                        pkg.approve(out, alias)
                        print(f"  approved as {alias}")
                    except Exception as e:
                        print(f"  approve fail {alias}: {e}")
        else:
            fail_n += 1
            print(f"  FAIL {r.get('error')}: {r.get('message')}")

    if review_paths:
        sheet = os.path.join(export_root, f"review_qwen_turns_{args.mode}.png")
        build_contact_sheet(review_paths, sheet, cols=4, thumb_max=360)
        print(f"\nreview_grid={sheet}")

    print(f"\nDone qwen turns ok={ok_n} fail={fail_n}")
    return EXIT_OK if fail_n == 0 else EXIT_PARTIAL


if __name__ == "__main__":
    raise SystemExit(main())
