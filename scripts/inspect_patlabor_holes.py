#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

GLB = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3_clean.glb"
RAW = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3_mv_tex.glb"


def inspect(path: str) -> dict:
    code = f'''
import bpy
import bmesh
from collections import defaultdict

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r"{path}")
main = next(o for o in bpy.data.objects if o.type == "MESH")
bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

boundary = [e for e in bm.edges if e.is_boundary]
non_manifold = [e for e in bm.edges if not e.is_manifold]

adj = defaultdict(set)
for e in boundary:
    a, b = e.verts
    adj[a.index].add(b.index)
    adj[b.index].add(a.index)
visited = set()
loops = []
for vid in list(adj.keys()):
    if vid in visited:
        continue
    stack = [vid]
    visited.add(vid)
    comp = []
    while stack:
        u = stack.pop()
        comp.append(u)
        for v in adj[u]:
            if v not in visited:
                visited.add(v)
                stack.append(v)
    loops.append(comp)

coords = {{v.index: v.co.copy() for v in bm.verts}}
minz = min(c.z for c in coords.values())
maxz = max(c.z for c in coords.values())
H = max(maxz - minz, 1e-6)
minx = min(c.x for c in coords.values())
maxx = max(c.x for c in coords.values())
W = max(maxx - minx, 1e-6)
cx = (minx + maxx) * 0.5

regions = {{"head": 0, "torso": 0, "pants": 0, "hands": 0, "feet": 0, "other": 0}}
loop_details = []
for comp in sorted(loops, key=len, reverse=True):
    pts = [coords[i] for i in comp]
    z = sum(p.z for p in pts) / len(pts)
    x = sum(p.x for p in pts) / len(pts)
    t = (z - minz) / H
    if t > 0.72:
        reg = "head"
    elif t > 0.48:
        reg = "torso"
    elif t > 0.12:
        reg = "pants"
    else:
        reg = "feet"
    if abs(x - cx) > W * 0.35 and 0.28 < t < 0.58:
        reg = "hands"
    regions[reg] = regions.get(reg, 0) + 1
    if len(comp) >= 8:
        loop_details.append({{
            "n": len(comp),
            "z": round(float(z), 3),
            "t": round(float(t), 3),
            "reg": reg,
            "x": round(float(x), 3),
        }})

result = {{
    "status": "ok",
    "path": r"{path}",
    "verts": len(bm.verts),
    "faces": len(bm.faces),
    "boundary_edges": len(boundary),
    "non_manifold_edges": len(non_manifold),
    "boundary_loops": len(loops),
    "loops_by_region": regions,
    "largest_boundary_loops": loop_details[:12],
    "is_watertight": len(boundary) == 0,
}}
bm.free()
'''
    res = exec_blender_code(code)
    return res.get("result") if isinstance(res.get("result"), dict) else res


def main() -> int:
    for label, path in (("clean", GLB), ("raw_tex", RAW)):
        print("===", label, "===")
        try:
            r = inspect(path)
            print(json.dumps(r, indent=2, ensure_ascii=False))
        except Exception as e:
            print("ERR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
