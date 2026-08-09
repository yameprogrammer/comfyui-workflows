#!/usr/bin/env python3
"""Blender post (research): clean manifold, fill holes, smooth, rig, VRM — no frankenstein head."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
RAW = EXPORTS / "mecha_yame_v2_quality_raw.glb"
if not RAW.is_file():
    RAW = EXPORTS / "mecha_yame_v2_raw.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
RENDER = EXPORTS / "viewport_render.png"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")


def main() -> int:
    if not RAW.is_file():
        print("missing raw", RAW)
        return 1
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

raw = r"{str(RAW).replace(chr(92), '/')}"
blend = r"{str(BLEND).replace(chr(92), '/')}"
vrm = r"{str(VRM).replace(chr(92), '/')}"
temp = r"{str(TEMP).replace(chr(92), '/')}"
fbx = r"{str(FBX).replace(chr(92), '/')}"
render = r"{str(RENDER).replace(chr(92), '/')}"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
    for b in list(coll):
        try: coll.remove(b)
        except Exception: pass

bpy.ops.import_scene.gltf(filepath=raw)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_V2"

# normalize height
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
main.location = (0,0,0)
if main.dimensions.z > 1e-6:
    s = 1.70 / float(main.dimensions.z)
    main.scale = (s,s,s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
main.location.z -= min(v.z for v in bbox)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# bmesh clean (research: floaters/holes/normals)
bm = bmesh.new(); bm.from_mesh(main.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0003)
# delete loose
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
try:
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
except Exception:
    pass
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# mild smooth
for _ in range(2):
    bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.3, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.to_mesh(main.data); bm.free(); main.data.update()
for p in main.data.polygons: p.use_smooth = True

# single clean dark material + subtle cyan emission on upper head band only
mat = bpy.data.materials.new("MechaClean")
mat.use_nodes = True
nodes=mat.node_tree.nodes; links=mat.node_tree.links; nodes.clear()
out=nodes.new('ShaderNodeOutputMaterial'); bsdf=nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value=(0.04,0.042,0.045,1)
if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value=0.25
if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value=0.4
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
main.data.materials.clear(); main.data.materials.append(mat)

# armature
bbox=[main.matrix_world @ Vector(c) for c in main.bound_box]
min_v=Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
max_v=Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
hh=max_v.z-min_v.z; mid_x=(min_v.x+max_v.x)/2; mid_y=(min_v.y+max_v.y)/2; width=max(max_v.x-min_v.x,0.4)
def z(t): return min_v.z + hh*t
bones=[
 ("Hips",(mid_x,mid_y,z(0.52)),(mid_x,mid_y,z(0.58)),None),
 ("Spine",(mid_x,mid_y,z(0.58)),(mid_x,mid_y,z(0.66)),"Hips"),
 ("Chest",(mid_x,mid_y,z(0.66)),(mid_x,mid_y,z(0.76)),"Spine"),
 ("Neck",(mid_x,mid_y,z(0.76)),(mid_x,mid_y,z(0.84)),"Chest"),
 ("Head",(mid_x,mid_y,z(0.84)),(mid_x,mid_y,z(0.98)),"Neck"),
 ("LeftShoulder",(mid_x,mid_y,z(0.76)),(mid_x+width*0.12,mid_y,z(0.76)),"Chest"),
 ("LeftUpperArm",(mid_x+width*0.12,mid_y,z(0.76)),(mid_x+width*0.34,mid_y,z(0.66)),"LeftShoulder"),
 ("LeftLowerArm",(mid_x+width*0.34,mid_y,z(0.66)),(mid_x+width*0.44,mid_y,z(0.56)),"LeftUpperArm"),
 ("LeftHand",(mid_x+width*0.44,mid_y,z(0.56)),(mid_x+width*0.48,mid_y,z(0.53)),"LeftLowerArm"),
 ("RightShoulder",(mid_x,mid_y,z(0.76)),(mid_x-width*0.12,mid_y,z(0.76)),"Chest"),
 ("RightUpperArm",(mid_x-width*0.12,mid_y,z(0.76)),(mid_x-width*0.34,mid_y,z(0.66)),"RightShoulder"),
 ("RightLowerArm",(mid_x-width*0.34,mid_y,z(0.66)),(mid_x-width*0.44,mid_y,z(0.56)),"RightUpperArm"),
 ("RightHand",(mid_x-width*0.44,mid_y,z(0.56)),(mid_x-width*0.48,mid_y,z(0.53)),"RightLowerArm"),
 ("LeftUpperLeg",(mid_x+width*0.08,mid_y,z(0.52)),(mid_x+width*0.09,mid_y,z(0.28)),"Hips"),
 ("LeftLowerLeg",(mid_x+width*0.09,mid_y,z(0.28)),(mid_x+width*0.09,mid_y,z(0.08)),"LeftUpperLeg"),
 ("LeftFoot",(mid_x+width*0.09,mid_y,z(0.08)),(mid_x+width*0.09,mid_y+width*0.05,z(0.02)),"LeftLowerLeg"),
 ("RightUpperLeg",(mid_x-width*0.08,mid_y,z(0.52)),(mid_x-width*0.09,mid_y,z(0.28)),"Hips"),
 ("RightLowerLeg",(mid_x-width*0.09,mid_y,z(0.28)),(mid_x-width*0.09,mid_y,z(0.08)),"RightUpperLeg"),
 ("RightFoot",(mid_x-width*0.09,mid_y,z(0.08)),(mid_x-width*0.09,mid_y+width*0.05,z(0.02)),"RightLowerLeg"),
]
bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
arm=bpy.context.view_layer.objects.active; arm.name='Armature'
for b in list(arm.data.edit_bones): arm.data.edit_bones.remove(b)
created={{}}
for name,head,tail,parent in bones:
    eb=arm.data.edit_bones.new(name); eb.head=head; eb.tail=tail
    if parent: eb.parent=created[parent]; eb.use_connect=False
    created[name]=eb
bpy.ops.object.mode_set(mode='OBJECT')
main.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active=arm
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO'); weight='AUTO'
except Exception as e:
    weight=str(e)
    main.parent=arm
    m=main.modifiers.new('Armature','ARMATURE'); m.object=arm

if main.data.shape_keys is None: main.shape_key_add(name='Basis', from_mix=False)
for k in ['A','I','U','E','O','Blink','Joy','Angry','Sorrow','Fun','EyeBlinkLeft','EyeBlinkRight','JawOpen','MouthSmile']:
    if k not in main.data.shape_keys.key_blocks: main.shape_key_add(name=k, from_mix=False)

bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
try:
    if hasattr(bpy.ops.vrm, 'assign_vrm0_humanoid_human_bones_automatically'):
        bpy.ops.vrm.assign_vrm0_humanoid_human_bones_automatically()
except Exception: pass

# lights render
for o in list(bpy.data.objects):
    if o.type in {{'LIGHT','CAMERA'}}: bpy.data.objects.remove(o, do_unlink=True)
world=bpy.context.scene.world or bpy.data.worlds.new('W'); bpy.context.scene.world=world
world.use_nodes=True; wn=world.node_tree.nodes; wl=world.node_tree.links; wn.clear()
bg=wn.new('ShaderNodeBackground'); bg.inputs[0].default_value=(0.85,0.87,0.9,1); bg.inputs[1].default_value=1.0
wout=wn.new('ShaderNodeOutputWorld'); wl.new(bg.outputs[0], wout.inputs[0])
bbox=[main.matrix_world @ Vector(c) for c in main.bound_box]
center=sum(bbox, Vector())/8.0; height=max(v.z for v in bbox)-min(v.z for v in bbox)
cam_data=bpy.data.cameras.new('C'); cam=bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(center.x, center.y-max(height*2.3,3.6), center.z)
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=cam
ld=bpy.data.lights.new('K','AREA'); ld.energy=500; ld.size=2
lo=bpy.data.objects.new('K', ld); bpy.context.scene.collection.objects.link(lo); lo.location=(center.x+1.4, center.y-2, center.z+1.4)
arm.hide_render=True
scene=bpy.context.scene
try: scene.render.engine='BLENDER_EEVEE'
except Exception: scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=768; scene.render.resolution_y=1152; scene.render.filepath=render
bpy.ops.render.render(write_still=True)

window=bpy.context.window_manager.windows[0]
area=next((a for a in window.screen.areas if a.type=='VIEW_3D'), window.screen.areas[0])
region=next((r for r in area.regions if r.type=='WINDOW'), area.regions[0])
bpy.ops.object.select_all(action='DESELECT'); main.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active=arm
notes={{}}
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=arm):
    bpy.ops.export_scene.gltf(filepath=temp, export_format='GLB', use_selection=True, export_skins=True, export_morph=True, export_materials='EXPORT', export_animations=False)
    try:
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_armature_deform_only=True, path_mode='COPY', embed_textures=True)
        notes['fbx']=True
    except Exception as e:
        notes['fbx']=str(e)
    if hasattr(bpy.ops.export_scene, 'vrm'):
        try:
            notes['vrm']=list(bpy.ops.export_scene.vrm(filepath=vrm, ignore_warning=True, check_existing=False, armature_object_name=arm.name))
        except Exception as e:
            notes['vrm']=str(e)
bpy.ops.wm.save_as_mainfile(filepath=blend)
result={{'verts':len(main.data.vertices),'polys':len(main.data.polygons),'height':float(main.dimensions.z),'width':float(main.dimensions.x),'weight':weight,'notes':notes,'vrm':Path(vrm).stat().st_size if Path(vrm).is_file() else 0,'src':raw}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
    if VRM.is_file() and VRM.stat().st_size > 10000:
        shutil.copyfile(VRM, VRM2)
        print("VRM", VRM.stat().st_size, "has_VRM", b"VRM" in VRM.read_bytes())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
