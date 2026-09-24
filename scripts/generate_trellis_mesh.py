#!/usr/bin/env python3
"""Image → 3D mesh (GLB) via Microsoft TRELLIS 2. Agent MESH default.

Requires ComfyUI + ComfyUI-TRELLIS2 and trellis2 / dinov3 weights.

  python scripts/generate_trellis_mesh.py -i hero_front.png -o out.glb --seed 42
  python scripts/generate_trellis_mesh.py -i hero_front.png -o scout.glb --profile draft
  python scripts/generate_trellis_mesh.py -i hero_front.png -o geo.glb --profile work --no-texture
  python scripts/generate_trellis_mesh.py --list-profiles

Hunyuan3D (`generate_hy3d_mesh`) is KR Community License blocked — not this CLI.

Guide: workflows/human/trellis/AGENT_GUIDE.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import sys

from lib.comfy_client import DEFAULT_SERVER
from lib.trellis2_mesh_runner import (
    FAMILY_TRELLIS2_MESH,
    PROFILES,
    RESOLUTION_MODES,
    generate_trellis_mesh,
    list_profiles,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="TRELLIS 2 image-to-mesh (GLB) — agent MESH default"
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
    p.add_argument(
        "--resolution",
        choices=RESOLUTION_MODES,
        default=None,
        help="override profile resolution (512|1024|1024_cascade|1536_cascade)",
    )
    p.add_argument(
        "--no-texture",
        action="store_true",
        help="geometry only (skip PBR). draft already does this",
    )
    p.add_argument(
        "--texture",
        action="store_true",
        help="force PBR even on draft",
    )
    p.add_argument("--remesh", action="store_true", help="ProcessMesh remesh=on (PBR path)")
    p.add_argument("--ss-steps", type=int, default=None)
    p.add_argument("--shape-steps", type=int, default=None)
    p.add_argument("--tex-steps", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--target-faces", type=int, default=None)
    p.add_argument("--texture-size", type=int, default=None)
    p.add_argument("--prefix", default=None, help="Comfy filename prefix (no slashes)")
    p.add_argument("--timeout", type=int, default=1800)
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
        print("=== TRELLIS 2 mesh profiles ===\n")
        for k, v in list_profiles().items():
            print(
                f"  {k}: res={v['resolution']} ss={v['ss_steps']} "
                f"shape={v['shape_steps']} tex={v['tex_steps']} "
                f"pbr={v['texture']} faces={v['target_faces']}"
            )
            print(f"       {v['notes']}")
        print(f"\nEngine family: {FAMILY_TRELLIS2_MESH}")
        print("Requires: ComfyUI-TRELLIS2 + models/trellis2 + models/dinov3")
        print("Not Hunyuan3D. KR commercial default is this CLI.")
        return 0

    if not args.image or not args.output:
        p.error("--image/-i and --output/-o required (unless --list-profiles)")

    if args.texture and args.no_texture:
        p.error("use only one of --texture / --no-texture")
    texture_flag: bool | None
    if args.texture:
        texture_flag = True
    elif args.no_texture:
        texture_flag = False
    else:
        texture_flag = None

    print(
        f"TRELLIS 2 mesh profile={args.profile} texture={texture_flag} "
        f"remesh={args.remesh} out={args.output}"
    )
    result = generate_trellis_mesh(
        image_path=args.image,
        output_path=args.output,
        seed=args.seed,
        profile=args.profile,
        resolution=args.resolution,
        texture=texture_flag,
        remesh=args.remesh,
        ss_steps=args.ss_steps,
        shape_steps=args.shape_steps,
        tex_steps=args.tex_steps,
        max_tokens=args.max_tokens,
        target_faces=args.target_faces,
        texture_size=args.texture_size,
        prefix=args.prefix,
        timeout_sec=float(args.timeout),
        server_address=args.server,
        free_policy=args.free_policy,
        free_after=not args.no_free_after,
    )
    if not result.get("ok"):
        print(
            f"[trellis2_mesh] FAIL {result.get('error')}: {result.get('message')}",
            file=sys.stderr,
        )
        return 1
    print(f"[trellis2_mesh] ok → {result.get('output_path')}")
    if result.get("elapsed_sec") is not None:
        print(f"[trellis2_mesh] elapsed={result.get('elapsed_sec')}s mode={result.get('mode')}")
    if result.get("meta_path"):
        print(f"[trellis2_mesh] meta → {result.get('meta_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
