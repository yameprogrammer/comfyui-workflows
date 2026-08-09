from blender_mcp_client import exec_blender_code
import json
from pathlib import Path

for p in sorted(Path(r"F:/ComfyUI_data/output/3D").glob("mecha_mv*"), key=lambda x: x.stat().st_mtime):
    print(p.name, p.stat().st_size)

code = r"""
import bpy
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=r'D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2_mv_raw.glb')
m = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bbox = [m.matrix_world @ Vector(c) for c in m.bound_box]
center = sum(bbox, Vector()) / 8.0
h = max(v.z for v in bbox) - min(v.z for v in bbox)
for o in list(bpy.data.objects):
    if o.type in {'LIGHT', 'CAMERA'}:
        bpy.data.objects.remove(o, do_unlink=True)
cam_d = bpy.data.cameras.new('C')
cam = bpy.data.objects.new('C', cam_d)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(h * 2.2, 3.5), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam
ld = bpy.data.lights.new('K', 'AREA')
ld.energy = 400
ld.size = 2
lo = bpy.data.objects.new('K', ld)
bpy.context.scene.collection.objects.link(lo)
lo.location = (1.5, -2, 2)
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
scene.render.resolution_x = 640
scene.render.resolution_y = 960
scene.render.filepath = r'D:/캐릭터/drafts/mecha_yame_v2/exports/mv_preview.png'
bpy.ops.render.render(write_still=True)
coords = [m.matrix_world @ v.co for v in m.data.vertices]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
hh = maxz - minz
top = [c for c in coords if c.z > minz + hh * 0.8]
hc = sum(top, Vector()) / len(top) if top else Vector()
above = sum(1 for c in top if c.z > hc.z)
below = sum(1 for c in top if c.z < hc.z)
result = {
    'verts': len(m.data.vertices),
    'polys': len(m.data.polygons),
    'dims': [float(x) for x in m.dimensions],
    'head_ratio': (min(above, below) / max(max(above, below), 1)),
}
"""
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
