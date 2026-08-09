#!/usr/bin/env python3
"""Export GLB/blend mesh to VRM via Blender MCP + VRM addon.

  python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm
  python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm --no-auto-rig
  python scripts/export_mesh_vrm.py --probe

Notes:
  - Needs Blender MCP + VRM_Addon_for_Blender (or bl_ext user_default.vrm)
  - Auto-rig is basic ARMATURE_AUTO (prototype). For Warudo-quality humanoid,
    re-rig / bone-map in Blender manually after export check.

Guide: workflows/human/hy3d_mesh/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.blender_mcp import DEFAULT_HOST, DEFAULT_PORT, probe_blender
from lib.mesh_blender_ops import export_mesh_vrm


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="GLB/blend → VRM via Blender MCP")
    p.add_argument("--input", "-i", default=None, help="input .glb or .blend")
    p.add_argument("--output", "-o", default=None, help="output .vrm")
    p.add_argument(
        "--no-auto-rig",
        action="store_true",
        help="do not create ARMATURE_AUTO when missing (export may fail)",
    )
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--timeout", type=float, default=240.0)
    p.add_argument("--probe", action="store_true")
    args = p.parse_args(argv)

    if args.probe:
        r = probe_blender(host=args.host, port=args.port)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required (unless --probe)")

    result = export_mesh_vrm(
        input_path=args.input,
        output_vrm=args.output,
        auto_rig_if_missing=not args.no_auto_rig,
        host=args.host,
        port=args.port,
        timeout_sec=float(args.timeout),
    )
    if not result.get("ok"):
        print(
            f"[export_mesh_vrm] FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        if result.get("detail"):
            print(json.dumps(result["detail"], ensure_ascii=False)[:800], file=sys.stderr)
        return 1
    print(f"[export_mesh_vrm] ok → {result.get('output_path')}")
    if result.get("sidecar_glb"):
        print(f"[export_mesh_vrm] sidecar GLB → {result.get('sidecar_glb')}")
    print(
        f"  mesh={result.get('mesh')} armature={result.get('armature')} "
        f"verts={result.get('verts')} faces={result.get('faces')}"
    )
    if result.get("note"):
        print(f"  note: {result.get('note')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
