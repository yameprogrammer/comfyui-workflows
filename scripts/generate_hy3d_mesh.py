#!/usr/bin/env python3
"""Image → 3D mesh (GLB) via Hunyuan3D / Kijai Hy3D wrapper.

Requires ComfyUI + ComfyUI-Hunyuan3DWrapper and DiT weights.

  # Default work profile (geometry + postprocess)
  python scripts/generate_hy3d_mesh.py -i hero_front.png -o out.glb --seed 42

  # Fast scout
  python scripts/generate_hy3d_mesh.py -i hero_front.png -o scout.glb --profile draft

  # Optional paint texture path (high VRAM)
  python scripts/generate_hy3d_mesh.py -i hero_front.png -o textured.glb --profile hero --texture

  python scripts/generate_hy3d_mesh.py --list-profiles

Guide: workflows/human/hy3d_mesh/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.hy3d_mesh_runner import (
    DEFAULT_DIT_MODEL,
    FAMILY_HY3D,
    PROFILES,
    generate_hy3d_mesh,
    list_profiles,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Hunyuan3D / Hy3D image-to-mesh (GLB) — agent toolbox"
    )
    p.add_argument("--image", "-i", required=False, help="input 2D image (front preferred)")
    p.add_argument("--output", "-o", required=False, help="output .glb path")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--profile",
        choices=tuple(PROFILES.keys()),
        default="work",
        help="draft|work|hero (default work)",
    )
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--guidance", type=float, default=None)
    p.add_argument("--octree", type=int, default=None)
    p.add_argument("--max-faces", type=int, default=None)
    p.add_argument("--remesh", action="store_true", help="IM remesh after postprocess")
    p.add_argument(
        "--texture",
        action="store_true",
        help="full delight+paint path (high VRAM; experimental quality)",
    )
    p.add_argument("--view-size", type=int, default=768)
    p.add_argument("--paint-steps", type=int, default=25)
    p.add_argument("--prefix", default=None, help="Comfy filename_prefix (default 3D/agent_hy3d_*)")
    p.add_argument("--dit-model", default=DEFAULT_DIT_MODEL)
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--free-policy", default=None, help="on_switch|always|never")
    p.add_argument(
        "--no-free-after",
        action="store_true",
        help="skip /free unload after success",
    )
    p.add_argument("--list-profiles", action="store_true")
    args = p.parse_args(argv)

    if args.list_profiles:
        print("=== Hy3D mesh profiles ===\n")
        for k, v in list_profiles().items():
            print(
                f"  {k}: steps={v['steps']} guidance={v['guidance']} "
                f"octree={v['octree']} max_faces={v['max_faces']}"
            )
            print(f"       {v['notes']}")
        print(f"\nEngine family: {FAMILY_HY3D}")
        print(f"Default DiT: {DEFAULT_DIT_MODEL}")
        print("Requires: ComfyUI-Hunyuan3DWrapper (Kijai)")
        return 0

    if not args.image or not args.output:
        p.error("--image/-i and --output/-o required (unless --list-profiles)")

    print(
        f"Hy3D mesh profile={args.profile} texture={args.texture} "
        f"remesh={args.remesh} out={args.output}"
    )
    result = generate_hy3d_mesh(
        image_path=args.image,
        output_path=args.output,
        seed=args.seed,
        profile=args.profile,
        steps=args.steps,
        guidance=args.guidance,
        octree=args.octree,
        max_faces=args.max_faces,
        remesh=args.remesh,
        texture=args.texture,
        view_size=args.view_size,
        paint_steps=args.paint_steps,
        prefix=args.prefix,
        dit_model=args.dit_model,
        timeout_sec=float(args.timeout),
        server_address=args.server,
        free_policy=args.free_policy,
        free_after=not args.no_free_after,
    )
    if not result.get("ok"):
        print(
            f"[hy3d_mesh] FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[hy3d_mesh] ok → {result.get('output_path')}")
    if result.get("elapsed_sec") is not None:
        print(f"[hy3d_mesh] elapsed={result.get('elapsed_sec')}s mode={result.get('mode')}")
    if result.get("meta_path"):
        print(f"[hy3d_mesh] meta → {result.get('meta_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
