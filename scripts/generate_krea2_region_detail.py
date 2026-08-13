#!/usr/bin/env python3
"""Lonecat Krea2 v7 region detailers (Eyes / Spare / NSFW body slots).

SFW:
  python scripts/generate_krea2_region_detail.py -i still.png -o out.png --region eyes
  python scripts/generate_krea2_region_detail.py -i still.png -o out.png --region eyes_yolo
  python scripts/generate_krea2_region_detail.py -i still.png -o out.png --region spare --sam-prompt "necklace"
  python scripts/generate_krea2_region_detail.py --list

18+ (requires --i-am-18):
  python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region breasts --i-am-18
  python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region female_body --i-am-18
  python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region male_junk --i-am-18
  python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region vajayjay --i-am-18

Face/hands are aliases to dedicated CLIs (printed if chosen without --force-generic).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.comfy_engine_session import ensure_engine
from lib.krea2_region_detail import (
    PRESET_BY_MODE,
    get_region,
    list_regions,
    model_exists,
)
from lib.workflow_api_runner import run_workflow_api

FAMILY = "krea2_still"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Krea2 v7 region detailer (Eyes/Spare/Breasts/Body/Male/Vajayjay)"
    )
    p.add_argument("--image", "-i", default=None)
    p.add_argument("--output", "-o", default=None)
    p.add_argument(
        "--region",
        "-r",
        default=None,
        help="eyes|eyes_yolo|eyes_paired|spare|breasts|female_body|male_junk|penis|vajayjay|face|hands",
    )
    p.add_argument("--list", action="store_true", help="list regions and exit")
    p.add_argument(
        "--i-am-18",
        action="store_true",
        help="required for adult anatomy regions",
    )
    p.add_argument(
        "--prompt",
        "-p",
        default=None,
        help="detailer positive (overrides region default)",
    )
    p.add_argument(
        "--sam-prompt",
        default=None,
        help="SAM text class for eyes/spare (e.g. eyes, necklace, lips)",
    )
    p.add_argument(
        "--model",
        default=None,
        help="override ultralytics model path (bbox/... or segm/...)",
    )
    p.add_argument(
        "--engine",
        choices=("auto", "bbox", "segm", "sam"),
        default="auto",
        help="force detector engine (default: region map)",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.list:
        rows = list_regions()
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print(f"{'id':16s} {'mode':6s} {'adult':5s} model / note")
            for r in rows:
                m = r.get("model") or r.get("alias_cli") or r.get("note") or ""
                print(
                    f"{r['id']:16s} {r['mode']:6s} {str(r['adult']):5s} {m}"
                )
        return 0

    if not args.region or not args.image:
        p.error("--region and --image required (or use --list)")

    try:
        reg = get_region(args.region)
    except KeyError as e:
        print(f"[region_detail] {e}", file=sys.stderr)
        return 2

    rid = reg["id"]
    if reg.get("mode") == "alias":
        print(
            f"[region_detail] region={rid} is alias → {reg.get('alias_cli')} "
            f"(preset {reg.get('alias_preset')})",
            file=sys.stderr,
        )
        print(
            f"  run: {reg.get('alias_cli')} -i {args.image} -o <out.png>",
            file=sys.stderr,
        )
        return 3

    if reg.get("adult") and not args.i_am_18:
        print(
            f"[region_detail] refuse adult region {rid!r}: pass --i-am-18",
            file=sys.stderr,
        )
        return 2

    mode = args.engine if args.engine != "auto" else reg["mode"]
    if mode not in PRESET_BY_MODE:
        print(f"[region_detail] bad mode {mode}", file=sys.stderr)
        return 2

    model = args.model or reg.get("model")
    if mode in ("bbox", "segm"):
        if not model:
            print(
                f"[region_detail] region {rid} needs --model for mode={mode}",
                file=sys.stderr,
            )
            return 2
        # spare with --model switches to yolo path
        if model.startswith("segm/") and mode == "bbox":
            mode = "segm"
        elif model.startswith("bbox/") and mode == "segm":
            mode = "bbox"
        if not model_exists(model):
            print(
                f"[region_detail] missing detector model: {model}\n"
                f"  place under ComfyUI/models/ultralytics/\n"
                f"  female body: HF ms13d/Female_Body_Detection\n"
                f"  male junk: HF ashllay/YOLO_Models segm/CockAndBallYolo8x.pt",
                file=sys.stderr,
            )
            return 4

    sam_prompt = args.sam_prompt or reg.get("sam_prompt")
    if mode == "sam" and not sam_prompt:
        print(
            "[region_detail] SAM mode needs --sam-prompt "
            '(e.g. --sam-prompt "eyes" or "necklace")',
            file=sys.stderr,
        )
        return 2

    # spare + --model without forcing sam → use yolo
    if rid == "spare" and args.model and args.engine == "auto":
        mode = "segm" if args.model.startswith("segm/") else "bbox"
        model = args.model
        if not model_exists(model):
            print(f"[region_detail] missing model {model}", file=sys.stderr)
            return 4

    eng = ensure_engine(FAMILY, args.server, caller="generate_krea2_region_detail")
    if not eng.get("ok"):
        print(f"[region_detail] ENGINE FAIL {eng.get('message')}", file=sys.stderr)
        return 1

    preset = PRESET_BY_MODE[mode]
    from lib.output_policy import resolve_media_output

    out = resolve_media_output(args.output, default_name=f"krea2_region_{rid}.png")
    positive = args.prompt or reg.get("positive") or "detailed region, photoreal"
    denoise = (
        float(args.denoise)
        if args.denoise is not None
        else float(reg.get("denoise") or 0.3)
    )
    steps = int(args.steps) if args.steps is not None else 12
    threshold = (
        float(args.threshold)
        if args.threshold is not None
        else float(reg.get("threshold") or 0.35)
    )

    ports: dict = {
        "input_image": args.image,
        "positive": positive,
        "denoise": denoise,
        "steps": steps,
        "filename_prefix": f"krea2_region_{rid}",
    }
    if mode in ("bbox", "segm"):
        ports["detector_model"] = model
        ports["threshold"] = threshold
        if reg.get("guide_size"):
            ports["guide_size"] = reg["guide_size"]
    if mode == "sam":
        ports["sam_prompt"] = sam_prompt
        if reg.get("fallback_point_mode"):
            ports["fallback_point_mode"] = reg["fallback_point_mode"]

    print(
        f"region-detail region={rid} mode={mode} preset={preset} "
        f"model={model or sam_prompt!r} denoise={denoise} out={out}"
    )
    r = run_workflow_api(
        preset,
        ports=ports,
        output_path=out,
        seed=args.seed,
        server_address=args.server,
        timeout_sec=float(args.timeout),
    )
    if not r.get("ok"):
        print(
            f"[region_detail] FAIL {r.get('error')}: {r.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[region_detail] ok → {r.get('output_path')} seed={r.get('seed')}")
    if args.json:
        print(json.dumps({"ok": True, "region": rid, "mode": mode, **{k: r.get(k) for k in ('output_path','seed')}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
