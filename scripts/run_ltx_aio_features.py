#!/usr/bin/env python3
"""
List / describe LTX 2.3 AIO v44 **Select options** for agents.

Does not invent graphs — modes map to Orchestrator [[P:]] ports applied by
``ltx_aio_workflow_runner`` when you call ``generate_s2v``.

Examples:
  python scripts/run_ltx_aio_features.py --list
  python scripts/run_ltx_aio_features.py --describe i2v_audio
  python scripts/run_ltx_aio_features.py --feature mode_flf
  python scripts/run_ltx_aio_features.py --ports
"""
from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.ltx_aio_mode_select import (
    ALL_P_PORTS,
    list_features,
    load_capabilities,
    resolve_feature,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="LTX 2.3 AIO Select options — list/describe agent features"
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List all Select-options modes (feature catalog)",
    )
    p.add_argument(
        "--describe",
        metavar="MODE_OR_FEATURE",
        help="Describe one mode/feature_id/backend",
    )
    p.add_argument(
        "--feature",
        metavar="FEATURE_ID",
        help="Same as --describe (e.g. mode_i2v_audio)",
    )
    p.add_argument(
        "--ports",
        action="store_true",
        help="List raw [[P:]] port labels",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output",
    )
    p.add_argument(
        "--capabilities",
        action="store_true",
        help="Dump full CAPABILITIES.json summary",
    )
    args = p.parse_args(argv)

    if not any(
        [args.list, args.describe, args.feature, args.ports, args.capabilities]
    ):
        args.list = True

    if args.ports:
        ports = sorted(ALL_P_PORTS)
        if args.json:
            print(json.dumps({"select_options_ports": ports}, indent=2))
        else:
            print("Select options / [[P:]] ports:")
            for x in ports:
                print(f"  - {x}")
        return 0

    if args.capabilities:
        caps = load_capabilities()
        if args.json:
            print(json.dumps(caps, indent=2, ensure_ascii=False))
        else:
            print(f"workflow: {caps.get('workflow')}")
            print(f"source: {caps.get('source_ui')}")
            print(f"features: {len(caps.get('features') or [])}")
            for f in caps.get("features") or []:
                print(
                    f"  {f.get('feature_id')}: {f.get('label')} "
                    f"→ {f.get('backend')} options={f.get('select_options')}"
                )
            print("\nSee: workflows/human/LTX23_AIO_v44_AGENT_GUIDE.md")
        return 0

    if args.describe or args.feature:
        key = args.describe or args.feature
        try:
            feat = resolve_feature(key)
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(feat, indent=2, ensure_ascii=False))
        else:
            print(f"feature_id: {feat['feature_id']}")
            print(f"mode:       {feat['mode']}")
            print(f"label:      {feat['label']}")
            print(f"backend:    {feat['backend']}")
            print(f"select ON:  {', '.join(feat['select_options'])}")
            print(f"inputs:     {', '.join(feat['required_inputs'])}")
            print(f"needs_audio:{feat['needs_audio']}")
            print(f"cli:\n  {feat['cli']}")
        return 0

    # --list
    feats = list_features()
    if args.json:
        print(json.dumps({"features": feats}, indent=2, ensure_ascii=False))
        return 0

    print("LTX 2.3 AIO v44 — Select options (agent features)")
    print("Runner: lib/ltx_aio_workflow_runner.py  |  UI: ltx23AllInOneWorkflowForRTX_v44")
    print()
    print(f"{'mode':<14} {'backend':<22} select_options")
    print("-" * 78)
    for f in feats:
        opts = " + ".join(f["select_options"])
        print(f"{f['mode']:<14} {f['backend']:<22} {opts}")
    print()
    print("Run examples:")
    print("  python scripts/generate_s2v.py --backend ltx23_aio_i2v -i first.png --prompt '...'")
    print("  python scripts/generate_s2v.py --backend ltx23_aio -i first.png -a drive.wav --prompt '...'")
    print("  python scripts/generate_s2v.py --backend ltx23_aio --ltx-mode flf -i f.png --last l.png")
    print()
    print("Guide: workflows/human/LTX23_AIO_v44_AGENT_GUIDE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
