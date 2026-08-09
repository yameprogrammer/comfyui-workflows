#!/usr/bin/env python3
from blender_mcp_client import exec_blender_code
import json

code = r"""
import bpy
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
path = r"D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_raw.glb"
bpy.ops.import_scene.gltf(filepath=path)
m = next(o for o in bpy.data.objects if o.type=='MESH')
coords = [m.matrix_world @ v.co for v in m.data.vertices]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
h = maxz - minz
# top 25% as head band
head = [c for c in coords if c.z > minz + h*0.75]
xs=[c.x for c in head]; ys=[c.y for c in head]; zhs=[c.z for c in head]
# for each z slice, check if bottom of head is open (few verts at lower head)
slices = []
for i in range(10):
    lo = minz + h*(0.75 + i*0.025)
    hi = minz + h*(0.75 + (i+1)*0.025)
    pts = [c for c in coords if lo <= c.z < hi]
    if pts:
        slices.append({
            'band': i,
            'n': len(pts),
            'xspan': max(c.x for c in pts)-min(c.x for c in pts),
            'yspan': max(c.y for c in pts)-min(c.y for c in pts),
            'zmid': (lo+hi)/2,
        })
result = {
    'verts': len(coords),
    'height': h,
    'head_n': len(head),
    'head_bbox': {
        'xmin': min(xs), 'xmax': max(xs),
        'ymin': min(ys), 'ymax': max(ys),
        'zmin': min(zhs), 'zmax': max(zhs),
        'xspan': max(xs)-min(xs),
        'yspan': max(ys)-min(ys),
        'zspan': max(zhs)-min(zhs),
    } if head else None,
    'slices': slices,
}
"""
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
