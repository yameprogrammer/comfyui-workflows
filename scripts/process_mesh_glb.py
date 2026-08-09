#!/usr/bin/env python3
"""Clean / light auto-rig a GLB mesh via Blender MCP.

Requires Blender running with MCP addon (default 127.0.0.1:9876).

  # Clean floaters-ish doubles + normals, re-export
  python scripts/process_mesh_glb.py -i raw.glb -o clean.glb

  # Clean + basic ARMATURE_AUTO (prototype only)
  python scripts/process_mesh_glb.py -i raw.glb -o rigged.glb --auto-rig

  python scripts/process_mesh_glb.py --probe

Guide: workflows/human/hy3d_mesh/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.blender_mcp import DEFAULT_HOST, DEFAULT_PORT, probe_blender
from lib.mesh_blender_ops import process_mesh_glb


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="GLB clean / light auto-rig via Blender MCP")
    p.add_argument("--input", "-i", default=None, help="input .glb")
    p.add_argument("--output", "-o", default=None, help="output .glb")
    p.add_argument("--no-clean", action="store_true", help="skip mesh clean ops")
    p.add_argument(
        "--auto-rig",
        action="store_true",
        help="add basic humanoid armature (ARMATURE_AUTO) — prototype quality",
    )
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--probe", action="store_true", help="check Blender MCP only")
    args = p.parse_args(argv)

    if args.probe:
        r = probe_blender(host=args.host, port=args.port)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    if not args.input or not args.output:
        p.error("--input/-i and --output/-o required (unless --probe)")

    result = process_mesh_glb(
        input_glb=args.input,
        output_glb=args.output,
        clean=not args.no_clean,
        auto_rig=bool(args.auto_rig),
        host=args.host,
        port=args.port,
        timeout_sec=float(args.timeout),
    )
    if not result.get("ok"):
        print(
            f"[process_mesh_glb] FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[process_mesh_glb] ok → {result.get('output_path')}")
    print(
        f"  mesh={result.get('mesh')} verts={result.get('verts')} "
        f"faces={result.get('faces')} armature={result.get('armature')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
