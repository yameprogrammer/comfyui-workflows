#!/usr/bin/env python3
"""Fix materials to clean black head + charcoal fabric, re-export VRM."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.blend")
VRM = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.vrm")
VRM2 = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2_warudo.vrm")
RENDER = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\viewport_render.png")
GLB = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2_warudo.glb")
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")


def main() -> int:
    code = f"""
import bpy
import bmesh
import addon_utils
from mathutils import Vector
from pathlib import Path

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

bpy.ops.wm.open_mainfile(filepath=r"{str(BLEND).replace(chr(92),'/')}")
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

def pbr(name, color, metallic, roughness, emit=None, es=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    bsdf = n.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = metallic
    if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = roughness
    if emit is not None:
        for k in ('Emission Color','Emission'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = (*emit, 1)
                break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = es
    l.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

mat_body = pbr('Body_Fabric', (0.04, 0.042, 0.045), 0.06, 0.55)
mat_head = pbr('Head_Black', (0.01, 0.01, 0.012), 0.95, 0.1, emit=(0.05, 0.55, 0.7), es=0.45)
mat_hand = pbr('Hand_Metal', (0.02, 0.02, 0.022), 0.85, 0.22)
mat_gold = pbr('Ear_Gold', (0.55, 0.45, 0.28), 0.95, 0.2)

main.data.materials.clear()
for m in (mat_body, mat_head, mat_hand, mat_gold):
    main.data.materials.append(m)

bm = bmesh.new()
bm.from_mesh(main.data)
bm.faces.ensure_lookup_table()
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
minz = min(v.z for v in bbox)
maxz = max(v.z for v in bbox)
h = max(maxz - minz, 1e-6)
maxx = max(abs(max(v.x for v in bbox)), abs(min(v.x for v in bbox)), 0.1)

# big spherical head sits high; use top 22% for head
for f in bm.faces:
    cents = [main.matrix_world @ v.co for v in f.verts]
    cz = sum(v.z for v in cents)/len(cents)
    cx = abs(sum(v.x for v in cents)/len(cents))
    t = (cz - minz)/h
    if t > 0.78:
        f.material_index = 1  # head
    elif t > 0.40 and t < 0.78 and cx > maxx * 0.40:
        f.material_index = 2  # hands/outer arms
    elif t > 0.72 and t < 0.88 and cx > maxx * 0.18:
        f.material_index = 3  # ear gold band
    else:
        f.material_index = 0
bm.to_mesh(main.data)
bm.free()
main.data.update()

# simple render
for o in list(bpy.data.objects):
    if o.type in {{'LIGHT','CAMERA'}}:
        bpy.data.objects.remove(o, do_unlink=True)
world = bpy.context.scene.world or bpy.data.worlds.new('W')
bpy.context.scene.world = world
world.use_nodes = True
wn=world.node_tree.nodes; wl=world.node_tree.links; wn.clear()
bg=wn.new('ShaderNodeBackground'); bg.inputs[0].default_value=(0.8,0.82,0.85,1); bg.inputs[1].default_value=1.0
wout=wn.new('ShaderNodeOutputWorld'); wl.new(bg.outputs[0], wout.inputs[0])
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector())/8.0
height = max(v.z for v in bbox)-min(v.z for v in bbox)
cam_data=bpy.data.cameras.new('C'); cam=bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(center.x, center.y-max(height*2.3, 3.6), center.z)
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=cam
ld=bpy.data.lights.new('K','AREA'); ld.energy=500; ld.size=2
lo=bpy.data.objects.new('K', ld); bpy.context.scene.collection.objects.link(lo)
lo.location=(center.x+1.4, center.y-2, center.z+1.5)
if arm: arm.hide_render=True
scene=bpy.context.scene
try: scene.render.engine='BLENDER_EEVEE'
except Exception: scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=768; scene.render.resolution_y=1152
scene.render.filepath=r"{str(RENDER).replace(chr(92),'/')}"
bpy.ops.render.render(write_still=True)

# export
window=bpy.context.window_manager.windows[0]
area=next((a for a in window.screen.areas if a.type=='VIEW_3D'), window.screen.areas[0])
region=next((r for r in area.regions if r.type=='WINDOW'), area.regions[0])
bpy.ops.object.select_all(action='DESELECT')
main.select_set(True)
if arm:
    arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
else:
    bpy.context.view_layer.objects.active=main
vrm_path=r"{str(VRM).replace(chr(92),'/')}"
temp=r"{str(TEMP).replace(chr(92),'/')}"
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=(arm or main)):
    bpy.ops.export_scene.gltf(filepath=temp, export_format='GLB', use_selection=True, export_skins=True, export_morph=True, export_materials='EXPORT', export_animations=False)
    vrm_ok=None
    if hasattr(bpy.ops.export_scene, 'vrm'):
        try:
            vrm_ok=list(bpy.ops.export_scene.vrm(filepath=vrm_path, ignore_warning=True, check_existing=False, armature_object_name=(arm.name if arm else '')))
        except Exception as e:
            vrm_ok=str(e)
bpy.ops.wm.save_mainfile()
result={{'vrm_ok': vrm_ok, 'vrm_size': Path(vrm_path).stat().st_size if Path(vrm_path).is_file() else 0, 'temp': Path(temp).stat().st_size if Path(temp).is_file() else 0}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:2500])
    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
    if VRM.is_file() and VRM.stat().st_size > 10000:
        shutil.copyfile(VRM, VRM2)
        print("VRM", VRM.stat().st_size, "has_VRM", b"VRM" in VRM.read_bytes())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
