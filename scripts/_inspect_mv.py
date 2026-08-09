from blender_mcp_client import exec_blender_code
import json

code = r"""
import bpy
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=r'D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_mv_raw.glb')
ms = [o for o in bpy.data.objects if o.type == 'MESH']
m = ms[0]
coords = [m.matrix_world @ v.co for v in m.data.vertices]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
h = maxz - minz
top = [c for c in coords if c.z > minz + h * 0.82]
hc = sum(top, Vector()) / len(top) if top else Vector()
above = sum(1 for c in top if c.z > hc.z)
below = sum(1 for c in top if c.z < hc.z)
result = {
    'verts': len(m.data.vertices),
    'polys': len(m.data.polygons),
    'dims': [float(x) for x in m.dimensions],
    'head_n': len(top),
    'above': above,
    'below': below,
    'ratio': (min(above, below) / max(max(above, below), 1)),
}
"""
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
