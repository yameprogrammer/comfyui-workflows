#!/usr/bin/env python3
"""LTX-2.3 IC-LoRA Relight (exterior sun-direction V2V finish pass).

Fail-closed until weights + Comfy WF API preset are installed.

  python scripts/ltx_lora_status.py              # check status first
  python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 \\
      --look "warm golden low side sun" --direction "the left"

SSOT: docs/ltx_loras_agent.md · HF: Lightricks/LTX-2.3-22b-IC-LoRA-Relight
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
from pathlib import Path

from lib.ltx_lora_catalog import RELIGHT_HF_REPO, catalog, try_download_relight

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_WEIGHTS = 11
EXIT_WF = 12
EXIT_SOURCE = 1

# Trained looks from official README (fixed vocabulary)
LOOKS = [
    "hard directional sunlight",
    "hard high-angle sunlight",
    "hard low-angle sunlight",
    "soft diffused daylight",
    "soft warm afternoon light",
    "cool soft daylight",
    "dim overcast light",
    "strong backlight with rim light",
    "soft hazy backlight",
    "warm golden low front sun",
    "warm golden low side sun",
    "frontal sunlight",
]

DIRECTIONS = [
    "the front",
    "the front-right",
    "the right",
    "the back-right",
    "behind",
    "the back-left",
    "the left",
    "the front-left",
]

TRIGGER = "relight the video to match the light-direction ball."


def build_prompt(look: str, direction: str) -> str:
    look = (look or "").strip()
    direction = (direction or "").strip()
    if not look.startswith("relight"):
        return f"{TRIGGER} {look} from {direction}"
    return look


def _relight_entry() -> dict | None:
    for e in catalog():
        if e.get("id") == "relight":
            return e
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "LTX IC-LoRA Relight — exterior clip sun-direction finish pass. "
            "Requires weights (see ltx_lora_status)."
        )
    )
    p.add_argument("--video", "-v", required=False, help="Source exterior video")
    p.add_argument("--output", "-o", default=None, help="Output mp4")
    p.add_argument(
        "--look",
        default="warm golden low side sun",
        help="One of 12 trained looks (see --list-looks)",
    )
    p.add_argument(
        "--direction",
        default="the left",
        help="Sun direction phrase (the front|right|left|behind|…)",
    )
    p.add_argument("--prompt", default=None, help="Full prompt override (skips look/direction)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=704)
    p.add_argument("--frames", type=int, default=121)
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--strength", type=float, default=1.0, help="LoRA strength (default 1.0)")
    p.add_argument("--list-looks", action="store_true", help="Print trained looks/directions")
    p.add_argument(
        "--try-download",
        action="store_true",
        help="Attempt HF download if weights missing (needs gate + auth)",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true", help="JSON result to stdout")
    args = p.parse_args(argv)

    if args.list_looks:
        print("LOOKS:")
        for x in LOOKS:
            print(f"  - {x}")
        print("DIRECTIONS:")
        for x in DIRECTIONS:
            print(f"  - {x}")
        print("PROMPT FORMAT:")
        print(f"  {TRIGGER} <look> from <direction>")
        return EXIT_OK

    if not args.video:
        print("FAIL USAGE: -v source.mp4 required (or --list-looks)", file=sys.stderr)
        return EXIT_USAGE

    if not os.path.isfile(args.video):
        print("FAIL SOURCE_MISSING", args.video, file=sys.stderr)
        return EXIT_SOURCE

    entry = _relight_entry() or {}
    if entry.get("status") != "ready":
        if args.try_download:
            r = try_download_relight()
            if not r.get("ok"):
                msg = {
                    "ok": False,
                    "error": "RELIGHT_WEIGHTS_MISSING",
                    "message": r.get("message"),
                    "hint": r.get("hint"),
                    "install": entry.get("install"),
                    "docs": "docs/ltx_loras_agent.md",
                    "hf": f"https://huggingface.co/{RELIGHT_HF_REPO}",
                }
                if args.json:
                    print(json.dumps(msg, ensure_ascii=False, indent=2))
                else:
                    print("FAIL RELIGHT_WEIGHTS_MISSING", file=sys.stderr)
                    print(r.get("message", ""), file=sys.stderr)
                    print(r.get("hint", ""), file=sys.stderr)
                    print("  python scripts/ltx_lora_status.py download-relight", file=sys.stderr)
                return EXIT_WEIGHTS
            entry = _relight_entry() or entry
        else:
            msg = {
                "ok": False,
                "error": "RELIGHT_WEIGHTS_MISSING",
                "status": entry.get("status"),
                "message": (
                    "Relight IC-LoRA weights not on disk (HF gated). "
                    "Do not invent a substitute path."
                ),
                "install": entry.get("install")
                or "python scripts/ltx_lora_status.py download-relight",
                "docs": "docs/ltx_loras_agent.md",
                "hf": f"https://huggingface.co/{RELIGHT_HF_REPO}",
            }
            if args.json:
                print(json.dumps(msg, ensure_ascii=False, indent=2))
            else:
                print("FAIL RELIGHT_WEIGHTS_MISSING", file=sys.stderr)
                print(msg["message"], file=sys.stderr)
                print("  status:", entry.get("status"), file=sys.stderr)
                print("  install:", msg["install"], file=sys.stderr)
                print("  docs: docs/ltx_loras_agent.md", file=sys.stderr)
            return EXIT_WEIGHTS

    prompt = args.prompt or build_prompt(args.look, args.direction)
    out = args.output or (os.path.splitext(args.video)[0] + "_relit.mp4")

    # Full Comfy API runner is future work once WF is exported under workflows/agent/presets.
    # Until then: fail with clear next steps (weights ready path).
    wf_candidates = [
        Path("workflows/agent/presets/ltx23_relight.api.json"),
        Path("workflows/human/ltx23_relight/LTX-2.3_Relight_ICLoRA_SingleStage_Distilled.json"),
    ]
    wf_hit = next((p for p in wf_candidates if p.is_file()), None)

    plan = {
        "ok": False if not wf_hit else True,
        "mode": "planned" if not wf_hit else "ready_to_wire",
        "weights": entry.get("path"),
        "video": args.video,
        "output": out,
        "prompt": prompt,
        "look": args.look,
        "direction": args.direction,
        "seed": args.seed,
        "geometry": {
            "width": args.width,
            "height": args.height,
            "frames": args.frames,
            "fps": args.fps,
        },
        "lora_strength": args.strength,
        "workflow": str(wf_hit) if wf_hit else None,
        "when": "FINISH look pass on exterior clips after motion approved",
        "when_not": [
            "interior dialogue",
            "dance retarget / face identity",
            "first-pass generation",
        ],
        "docs": "docs/ltx_loras_agent.md",
        "human_guide": "workflows/human/ltx23_relight/AGENT_GUIDE.md",
    }

    if args.dry_run or not wf_hit:
        plan["error"] = None if wf_hit and args.dry_run else "RELIGHT_WF_NOT_WIRED"
        if not wf_hit:
            plan["ok"] = False
            plan["message"] = (
                "Weights present (or would be) but agent API preset / official WF JSON "
                "not installed yet. Open ComfyUI human pack after downloading the official "
                "graph from HF, or export workflows/agent/presets/ltx23_relight.api.json."
            )
            plan["next"] = [
                f"Download WF: HF repo {RELIGHT_HF_REPO} → "
                "LTX-2.3_Relight_ICLoRA_SingleStage_Distilled.json",
                "Copy to workflows/human/ltx23_relight/",
                "Install Sphere-Light-Render node (Eric Venti)",
                "Export API preset → workflows/agent/presets/ltx23_relight.api.json",
            ]
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print("STATUS", "dry-run" if args.dry_run else "blocked")
            print("  weights:", plan["weights"])
            print("  prompt:", prompt)
            print("  out:", out)
            if not wf_hit:
                print("FAIL RELIGHT_WF_NOT_WIRED", file=sys.stderr)
                print(plan["message"], file=sys.stderr)
                for step in plan.get("next") or []:
                    print("  -", step, file=sys.stderr)
        if args.dry_run and entry.get("status") == "ready":
            return EXIT_OK
        return EXIT_WF if not wf_hit else EXIT_OK

    # Placeholder: when API preset exists, wire run_workflow_video here.
    print("FAIL RELIGHT_RUNNER_TODO — preset found but runner not implemented", file=sys.stderr)
    print("  workflow:", wf_hit, file=sys.stderr)
    print("  Use ComfyUI human WF until agent runner is wired.", file=sys.stderr)
    if args.json:
        plan["ok"] = False
        plan["error"] = "RELIGHT_RUNNER_TODO"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return EXIT_WF


if __name__ == "__main__":
    raise SystemExit(main())
