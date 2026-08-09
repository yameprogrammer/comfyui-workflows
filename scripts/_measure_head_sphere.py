#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

GLB = sys.argv[1] if len(sys.argv) > 1 else r"D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_simple_mv_tex.glb"

code = f"""
import bpy
from mathutils import Vector
import math

path = r"{GLB.replace(chr(92), '/')}"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=path)
main = next(o for o in bpy.data.objects if o.type == "MESH")
vs = [main.matrix_world @ v.co for v in main.data.vertices]
zs = [v.z for v in vs]
zmin, zmax = min(zs), max(zs)
h = zmax - zmin
# top 32% as head region (chibi head larger)
head = [v for v in vs if v.z >= zmin + h * 0.68]
xs = [v.x for v in head]
ys = [v.y for v in head]
zs2 = [v.z for v in head]
dx = max(xs) - min(xs)
dy = max(ys) - min(ys)
dz = max(zs2) - min(zs2)
cx = sum(xs) / len(xs)
cy = sum(ys) / len(ys)
cz = sum(zs2) / len(zs2)
rs = [math.sqrt((v.x - cx) ** 2 + (v.y - cy) ** 2 + (v.z - cz) ** 2) for v in head]
mean_r = sum(rs) / len(rs)
rms = (sum((r - mean_r) ** 2 for r in rs) / len(rs)) ** 0.5
result = {{
    "source": path,
    "n_head": len(head),
    "head_bbox_xyz": [round(dx, 4), round(dy, 4), round(dz, 4)],
    "aspect_x_over_z": round(dx / dz, 3) if dz else None,
    "aspect_y_over_z": round(dy / dz, 3) if dz else None,
    "aspect_x_over_y": round(dx / dy, 3) if dy else None,
    "sphere_mean_r": round(mean_r, 4),
    "sphere_rms_err": round(rms, 4),
    "sphere_rms_pct": round(100 * rms / mean_r, 2) if mean_r else None,
    "r_min_max": [round(min(rs), 4), round(max(rs), 4)],
    "total_height": round(h, 4),
}}
"""

res = exec_blender_code(code)
print(json.dumps(res, ensure_ascii=False, indent=2)[:3000])
