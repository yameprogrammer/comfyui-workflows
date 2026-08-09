#!/usr/bin/env python3
from blender_mcp_client import exec_blender_code
import json

code = r"""
import bpy
from mathutils import Vector
from pathlib import Path

# clear
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

raw = r"D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_raw.glb"
bpy.ops.import_scene.gltf(filepath=raw)
meshes = [o for o in bpy.data.objects if o.type=='MESH']
info = []
for m in meshes:
    coords = [m.matrix_world @ v.co for v in m.data.vertices]
    xs = [c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    # island estimate via loose parts
    bpy.context.view_layer.objects.active = m
    m.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # count loose
    bpy.ops.object.mode_set(mode='OBJECT')
    info.append({
        "name": m.name,
        "verts": len(m.data.vertices),
        "polys": len(m.data.polygons),
        "edges": len(m.data.edges),
        "materials": len(m.data.materials),
        "bounds_min": [min(xs), min(ys), min(zs)] if coords else None,
        "bounds_max": [max(xs), max(ys), max(zs)] if coords else None,
        "has_uv": bool(m.data.uv_layers),
    })

# solidify check: average face area
if meshes:
    m = meshes[0]
    areas = [p.area for p in m.data.polygons]
    info[0]["face_area_min"] = min(areas) if areas else None
    info[0]["face_area_max"] = max(areas) if areas else None
    info[0]["face_area_avg"] = sum(areas)/len(areas) if areas else None

result = {"meshes": info, "object_count": len(bpy.data.objects)}
"""
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
