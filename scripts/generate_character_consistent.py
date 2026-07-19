#!/usr/bin/env python3
"""
Character-consistent still generation (research-backed orchestration).

Modes:
  lock   — same face, new action/scene (default I2I identity, denoise ~0.52)
  soft   — micro change (expression/light), lower denoise
  remix  — stronger scene/wardrobe change, still identity-capped
  anchor — T2I master face when you have no ref yet
  pack   — mini expression/wardrobe/scene board + contact sheet
  angle  — Qwen multi-view turn
  pose   — ControlNet pose + identity-aware prompt

Research: docs/character_consistency_research.md
Guide:    workflows/human/character_consistency/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.character_consistency import MODES, mode_denoise_defaults, run_character_consistent
from lib.prompt_assembly import load_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Keep character identity while generating stills. "
            "Default: Lonecat I2I identity lock from a reference face."
        )
    )
    p.add_argument(
        "--mode",
        choices=list(MODES),
        default="lock",
        help="lock|soft|remix|anchor|pack|angle|pose (default lock)",
    )
    p.add_argument("--input", "-i", default=None, help="Reference face/body image")
    p.add_argument("--prompt", "-p", default=None, help="Change instruction or anchor text")
    p.add_argument("--prompt-file", default=None, help="Prompt from file")
    p.add_argument("--output", "-o", default=None, help="Output image path")
    p.add_argument(
        "--pack-dir",
        default=None,
        help="Directory for --mode pack (images + contact_sheet + meta)",
    )
    p.add_argument("--control", default=None, help="Pose/control image for --mode pose")
    p.add_argument(
        "--view",
        "-v",
        default=None,
        help="Angle view key for --mode angle (e.g. head_front, head_left_45)",
    )
    p.add_argument(
        "--denoise",
        "-d",
        type=float,
        default=None,
        help="Override denoise (clamped per mode policy)",
    )
    p.add_argument(
        "--strength",
        type=float,
        default=0.75,
        help="ControlNet strength for pose mode (default 0.75)",
    )
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--negative", default="")
    p.add_argument("--negative-file", default=None)
    p.add_argument("--core-prefix-file", default=None, help="Locked bible/appearance prefix")
    p.add_argument("--core-suffix-file", default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--meta-out", default=None)
    p.add_argument(
        "--family",
        default=None,
        help="zimage|lonecat|krea2 for I2I family preset",
    )
    p.add_argument(
        "--no-contact-sheet",
        action="store_true",
        help="pack mode: skip contact sheet",
    )
    p.add_argument(
        "--print-policy",
        action="store_true",
        help="Print denoise ladder / modes and exit",
    )
    args = p.parse_args(argv)

    if args.print_policy:
        print("=== character_consistency policy ===")
        print("research: docs/character_consistency_research.md")
        for m in MODES:
            d, mx = mode_denoise_defaults(m)
            print(f"  mode={m:7s} default_denoise={d:.2f} max={mx:.2f}")
        print(
            "ladder: soft 0.45 → lock 0.52 → remix 0.62 | "
            "always pass -i face ref except anchor"
        )
        return 0

    prompt = ""
    if args.prompt_file:
        prompt = load_text(args.prompt_file)
    elif args.prompt:
        prompt = args.prompt

    negative = load_text(args.negative_file) if args.negative_file else (args.negative or "")
    core_prefix = load_text(args.core_prefix_file) if args.core_prefix_file else ""
    core_suffix = load_text(args.core_suffix_file) if args.core_suffix_file else ""

    result = run_character_consistent(
        mode=args.mode,
        prompt=prompt,
        input_image=args.input,
        output_path=args.output,
        control_image=args.control,
        view=args.view,
        pack_dir=args.pack_dir,
        denoise=args.denoise,
        model_type=args.model,
        seed=args.seed,
        negative=negative,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        width=args.width,
        height=args.height,
        timeout_sec=args.timeout,
        meta_out=args.meta_out,
        family=args.family,
        strength=args.strength,
        contact_sheet=not args.no_contact_sheet,
    )

    ok = bool(result.get("ok"))
    if ok:
        out = result.get("output_path") or result.get("pack_dir")
        print(f"[character_consistent] ok mode={args.mode} → {out}")
        if result.get("partial"):
            print("[character_consistent] partial pack (some variants failed)")
        if result.get("artifacts"):
            for a in result["artifacts"][:12]:
                print(f"  - {a.get('role')}: {a.get('path') or a.get('error')}")
    else:
        print(
            f"[character_consistent] FAIL mode={args.mode} "
            f"error={result.get('error')} message={result.get('message')}",
            file=sys.stderr,
        )
        # machine-readable tail for agents
        print(json.dumps({k: result.get(k) for k in ("ok", "error", "message")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
