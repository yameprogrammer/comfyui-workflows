#!/usr/bin/env python3
"""Inspect all generated GLB files to find the connected solid 3D character mesh."""

import json
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy
import math
import mathutils

glb_candidates = [
    r"F:\\ComfyUI_data\\output\\3d\\mecha_yame_v1_00001_.glb",
    r"F:\\ComfyUI_data\\output\\3d\\mecha_yame_single_00001_.glb",
    r"F:\\ComfyUI_data\\output\\mesh\\ComfyUI_00001_.glb"
]

results = []

for glb_path in glb_candidates:
    if not bpy.path.abspath(glb_path):
        continue
        
    bpy.ops.wm.read_homefile(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=glb_path)
        mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
        if mesh_objs:
            m = mesh_objs[0]
            polys = len(m.data.polygons)
            verts = len(m.data.vertices)
            
            # Check bounding box size
            bbox = [m.matrix_world @ mathutils.Vector(c) for c in m.bound_box]
            dims = (max(v.x for v in bbox) - min(v.x for v in bbox),
                    max(v.y for v in bbox) - min(v.y for v in bbox),
                    max(v.z for v in bbox) - min(v.z for v in bbox))
                    
            results.append({
                "path": glb_path,
                "verts": verts,
                "polys": polys,
                "dimensions": [round(d, 3) for d in dims]
            })
    except Exception as e:
        results.append({"path": glb_path, "error": str(e)})

result = {"candidates": results}
"""

res = exec_blender_code(code)
print("Solid Mesh Inspection:", json.dumps(res, indent=2, ensure_ascii=False))
