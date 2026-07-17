#!/usr/bin/env python3
"""CLI: run ComfyUI API-format workflow with port patches only."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.workflow_api_runner import (
    load_capabilities,
    load_feature_presets,
    run_workflow_api,
    select_lonecat_preset,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Run workflows/agent *.api.json via POST /prompt (port patch only)"
    )
    p.add_argument(
        "--preset",
        "-p",
        default=None,
        help="Catalog alias, presets/name, or path to .api.json",
    )
    p.add_argument(
        "--mode",
        choices=["t2i", "i2i", "t2i_low_vram", "gguf"],
        default=None,
        help="Auto-select preset when --preset omitted",
    )
    p.add_argument(
        "--family",
        choices=["zimage", "lonecat", "krea2", "krea"],
        default=None,
        help="Model family for auto-preset (krea2 → krea2_t2i_v10)",
    )
    p.add_argument(
        "--list-features",
        action="store_true",
        help="Print Lonecat feature_id map for agents and exit",
    )
    p.add_argument("--positive", default=None, help="Positive prompt text")
    p.add_argument("--negative", default=None, help="Negative prompt text")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--denoise", type=float, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--input-image", default=None, help="Path for I2I LoadImage port")
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--meta", default=None, help="Meta JSON path")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument(
        "--port",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra port patch, e.g. --port filename_prefix=myrun",
    )
    args = p.parse_args(argv)

    if args.list_features:
        caps = load_capabilities(args.family)
        fp = load_feature_presets()
        print("=== workflows ===")
        for w in caps.get("workflows") or []:
            print(f"  {w}")
        if not caps.get("workflows") and caps.get("workflow"):
            print(f"  {caps.get('workflow')}")
        print("=== features (agent) ===")
        for f in caps.get("features") or []:
            print(
                f"  [{f.get('family', '?')}] {f.get('feature_id')}: {f.get('name')} "
                f"| preset={f.get('agent_preset')} | status={f.get('status', '?')}"
            )
        print("=== ready presets ===")
        for name, e in (fp.get("presets") or {}).items():
            if e.get("status") == "ready":
                print(f"  {name}: file={e.get('file')} family={e.get('family')}")
        print("=== all presets (incl planned) ===")
        for name, e in (fp.get("presets") or {}).items():
            print(f"  {name}: status={e.get('status')} file={e.get('file')}")
        print("=== select_preset / families ===")
        print(json.dumps({
            "select_preset": fp.get("select_preset") or {},
            "families": fp.get("families") or {},
        }, ensure_ascii=False, indent=2))
        return 0

    ports: dict = {}
    if args.positive is not None:
        ports["positive"] = args.positive
    if args.negative is not None:
        ports["negative"] = args.negative
    if args.seed is not None:
        ports["seed"] = args.seed
    if args.denoise is not None:
        ports["denoise"] = args.denoise
    if args.width is not None:
        ports["width"] = args.width
    if args.height is not None:
        ports["height"] = args.height
    if args.input_image is not None:
        ports["input_image"] = args.input_image
    unet_from_port = None
    for item in args.port:
        if "=" not in item:
            print(f"[ERROR] bad --port {item!r}, want KEY=VALUE", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        # try numeric
        if v.isdigit():
            ports[k] = int(v)
        else:
            try:
                ports[k] = float(v)
            except ValueError:
                ports[k] = v
        if k == "unet_name":
            unet_from_port = str(ports[k])

    preset = args.preset
    if not preset:
        mode = args.mode or ("i2i" if args.input_image else "t2i")
        preset = select_lonecat_preset(
            mode=mode, unet_name=unet_from_port, family=args.family
        )
        print(f"auto-preset={preset} (mode={mode} family={args.family})")

    if "positive" not in ports and "input_image" not in ports:
        print(
            "[ERROR] provide --positive and/or --input-image (or --port …)",
            file=sys.stderr,
        )
        return 2

    print(f"run_workflow_api preset={preset}")
    r = run_workflow_api(
        preset,
        ports=ports,
        output_path=args.output,
        meta_out=args.meta,
        timeout_sec=args.timeout,
        seed=args.seed,
    )
    if not r.get("ok"):
        print(
            f"[ERROR] {r.get('error')}: {r.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"OK output={r.get('output_path')}")
    print(f"  seed={r.get('seed')} prompt_id={r.get('prompt_id')}")
    print(f"  workflow_api={r.get('workflow_api')}")
    if r.get("meta_path"):
        print(f"  meta={r.get('meta_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
