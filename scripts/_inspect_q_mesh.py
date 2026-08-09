from blender_mcp_client import exec_blender_code
import json

code = r"""
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
p = r'D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_quality_raw.glb'
bpy.ops.import_scene.gltf(filepath=p)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if not meshes:
    result = {'status': 'empty'}
else:
    m = meshes[0]
    result = {
        'status': 'ok',
        'verts': len(m.data.vertices),
        'polys': len(m.data.polygons),
        'dims': [float(x) for x in m.dimensions],
        'name': m.name,
    }
"""
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
