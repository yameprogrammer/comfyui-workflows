#!/usr/bin/env python3
"""
Replace incomplete Hunyuan head with a full sphere — careful not to delete torso.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
RAW = EXPORTS / "mecha_yame_v2_raw.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
RENDER = EXPORTS / "viewport_render.png"
OGL = EXPORTS / "viewport_opengl.png"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")


def main() -> int:
    code = f"""
import bpy
import bmesh
import addon_utils
import math
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
ogl = r"{str(OGL).replace(chr(92), '/')}"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=raw)
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_V2"

# normalize
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
main.location = (0, 0, 0)
if main.dimensions.z > 1e-6:
    s = 1.70 / float(main.dimensions.z)
    main.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
min_z0 = min(v.z for v in bbox)
main.location.z -= min_z0
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

coords = [main.matrix_world @ v.co for v in main.data.vertices]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
h = maxz - minz

# body width at mid torso
mid_pts = [c for c in coords if minz + h*0.35 < c.z < minz + h*0.55]
body_half_w = 0.5 * (max(c.x for c in mid_pts) - min(c.x for c in mid_pts)) if mid_pts else 0.25

# Estimate broken head center: top-most central verts
top_central = [c for c in coords if c.z > minz + h*0.88 and abs(c.x) < body_half_w*0.45]
if top_central:
    hx = sum(c.x for c in top_central)/len(top_central)
    hy = sum(c.y for c in top_central)/len(top_central)
    hz = sum(c.z for c in top_central)/len(top_central)
else:
    hx, hy, hz = 0.0, 0.0, maxz - h*0.06
old_head_center = Vector((hx, hy, hz))
# only delete verts inside a ball around old head (not torso)
old_head_r = h * 0.16

bpy.context.view_layer.objects.active = main
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(main.data)
bm.verts.ensure_lookup_table()
deleted = 0
for v in bm.verts:
    w = main.matrix_world @ v.co
    # delete only if near estimated head AND above hoodie line
    if w.z > minz + h*0.80 and (w - old_head_center).length < old_head_r * 1.35 and abs(w.x) < body_half_w * 0.55:
        v.select = True
        deleted += 1
    else:
        v.select = False
bmesh.update_edit_mesh(main.data)
bpy.ops.mesh.delete(type='VERT')
# fill small holes if any
bpy.ops.mesh.select_all(action='SELECT')
try:
    bpy.ops.mesh.fill_holes(sides=8)
except Exception:
    pass
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# collar: highest remaining central verts
coords = [main.matrix_world @ v.co for v in main.data.vertices]
collar_pts = [c for c in coords if abs(c.x) < body_half_w*0.4 and c.z > minz + h*0.55]
if collar_pts:
    collar_z = max(c.z for c in collar_pts)
    # average of top 5% of collar_pts
    thr = sorted(collar_pts, key=lambda c: c.z, reverse=True)[: max(20, len(collar_pts)//20)]
    collar_x = sum(c.x for c in thr)/len(thr)
    collar_y = sum(c.y for c in thr)/len(thr)
else:
    collar_z = minz + h*0.72
    collar_x = collar_y = 0.0

# proper proportions: head diameter ~ 1/6.5 body height
head_r = h * 0.12  # ~0.20m radius on 1.7 body → ~0.41m diameter
neck_len = h * 0.04
head_center_z = collar_z + neck_len + head_r * 0.92
head_center = Vector((collar_x, collar_y, head_center_z))

def new_mat(name, color, metallic, roughness, emit=None, es=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = metallic
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = roughness
    if emit is not None:
        for k in ('Emission Color', 'Emission'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = (*emit, 1.0)
                break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = es
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

mat_body = new_mat('Body_Fabric', (0.05, 0.052, 0.055), 0.04, 0.58)
mat_head = new_mat('Head_Gloss', (0.012, 0.012, 0.014), 0.94, 0.1)
mat_eye = new_mat('Eye_Cyan', (0.05, 0.75, 0.9), 0.15, 0.2, emit=(0.15, 0.9, 1.0), es=4.0)
mat_gold = new_mat('Ear_Gold', (0.65, 0.55, 0.35), 0.95, 0.2)
mat_neck = new_mat('Neck_Metal', (0.03, 0.03, 0.035), 0.85, 0.22)
mat_hand = new_mat('Hand_Metal', (0.02, 0.02, 0.022), 0.8, 0.25)

# FULL UV sphere
bpy.ops.mesh.primitive_uv_sphere_add(segments=56, ring_count=32, radius=head_r, location=head_center)
head_obj = bpy.context.view_layer.objects.active
head_obj.name = "Head_Sphere"
bpy.ops.object.shade_smooth()
head_obj.data.materials.append(mat_head)

# neck
neck_bot = collar_z - h*0.005
neck_top = head_center_z - head_r * 0.78
neck_h = max(neck_top - neck_bot, 0.025)
neck_mid = (neck_bot + neck_top) * 0.5
bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=head_r*0.16, depth=neck_h, location=(collar_x, collar_y, neck_mid))
neck_obj = bpy.context.view_layer.objects.active
neck_obj.name = "Neck"
bpy.ops.object.shade_smooth()
neck_obj.data.materials.append(mat_neck)

# eyes on front (-Y)
eye_r = head_r * 0.14
eye_sep = head_r * 0.36
eye_z = head_center_z + head_r * 0.02
eye_y = head_center.y - head_r * 0.86
eyes = []
for side, sx in (('L', -1.0), ('R', 1.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=eye_r,
        location=(collar_x + sx*eye_sep, eye_y, eye_z))
    e = bpy.context.view_layer.objects.active
    e.name = f"Eye_{{side}}"
    bpy.ops.object.shade_smooth()
    e.data.materials.append(mat_eye)
    eyes.append(e)

# gold ears
ear_r = head_r * 0.26
ears = []
for side, sx in (('L', -1.0), ('R', 1.0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=ear_r, depth=head_r*0.1,
        location=(collar_x + sx*(head_r*0.98), head_center.y, head_center_z))
    ear = bpy.context.view_layer.objects.active
    ear.name = f"Ear_{{side}}"
    ear.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.shade_smooth()
    ear.data.materials.append(mat_gold)
    ears.append(ear)

main.data.materials.clear()
main.data.materials.append(mat_body)

# join
parts = [head_obj, neck_obj] + eyes + ears
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
main.select_set(True)
bpy.context.view_layer.objects.active = main
bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_V2"

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.00015)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
for p in main.data.polygons:
    p.use_smooth = True

# materials slots
main.data.materials.clear()
for m in (mat_body, mat_head, mat_eye, mat_gold, mat_hand):
    main.data.materials.append(m)

bm2 = bmesh.new()
bm2.from_mesh(main.data)
bm2.faces.ensure_lookup_table()
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
minz = min(v.z for v in bbox)
maxz = max(v.z for v in bbox)
hh = max(maxz-minz, 1e-6)
maxx = max(abs(max(v.x for v in bbox)), abs(min(v.x for v in bbox)), 0.1)
eye_centers = [
    Vector((collar_x - eye_sep, eye_y, eye_z)),
    Vector((collar_x + eye_sep, eye_y, eye_z)),
]
for f in bm2.faces:
    cents = [main.matrix_world @ v.co for v in f.verts]
    c = sum(cents, Vector()) / len(cents)
    t = (c.z - minz) / hh
    cx = abs(c.x)
    # eyes first
    is_eye = any((c - ec).length < eye_r * 1.5 for ec in eye_centers)
    if is_eye:
        f.material_index = 2
    elif (c - head_center).length < head_r * 1.08:
        # ears: side of head
        if cx > head_r * 0.72 and abs(c.z - head_center_z) < head_r * 0.5:
            f.material_index = 3
        else:
            f.material_index = 1
    elif t > 0.38 and t < 0.78 and cx > maxx * 0.42:
        f.material_index = 4  # hands
    else:
        f.material_index = 0
bm2.to_mesh(main.data)
bm2.free()
main.data.update()

# armature
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
hh = max_v.z - min_v.z
mid_x = (min_v.x + max_v.x) * 0.5
mid_y = (min_v.y + max_v.y) * 0.5
width = max(max_v.x - min_v.x, 0.4)

def z(t):
    return min_v.z + hh * t

bones_def = [
    ("Hips", (mid_x, mid_y, z(0.50)), (mid_x, mid_y, z(0.56)), None),
    ("Spine", (mid_x, mid_y, z(0.56)), (mid_x, mid_y, z(0.64)), "Hips"),
    ("Chest", (mid_x, mid_y, z(0.64)), (mid_x, mid_y, z(0.74)), "Spine"),
    ("Neck", (mid_x, mid_y, z(0.74)), (mid_x, mid_y, neck_mid), "Chest"),
    ("Head", (mid_x, mid_y, neck_mid), (mid_x, mid_y, head_center_z + head_r*0.5), "Neck"),
    ("LeftShoulder", (mid_x, mid_y, z(0.74)), (mid_x + width*0.13, mid_y, z(0.74)), "Chest"),
    ("LeftUpperArm", (mid_x + width*0.13, mid_y, z(0.74)), (mid_x + width*0.34, mid_y, z(0.66)), "LeftShoulder"),
    ("LeftLowerArm", (mid_x + width*0.34, mid_y, z(0.66)), (mid_x + width*0.44, mid_y, z(0.56)), "LeftUpperArm"),
    ("LeftHand", (mid_x + width*0.44, mid_y, z(0.56)), (mid_x + width*0.48, mid_y, z(0.53)), "LeftLowerArm"),
    ("RightShoulder", (mid_x, mid_y, z(0.74)), (mid_x - width*0.13, mid_y, z(0.74)), "Chest"),
    ("RightUpperArm", (mid_x - width*0.13, mid_y, z(0.74)), (mid_x - width*0.34, mid_y, z(0.66)), "RightShoulder"),
    ("RightLowerArm", (mid_x - width*0.34, mid_y, z(0.66)), (mid_x - width*0.44, mid_y, z(0.56)), "RightUpperArm"),
    ("RightHand", (mid_x - width*0.44, mid_y, z(0.56)), (mid_x - width*0.48, mid_y, z(0.53)), "RightLowerArm"),
    ("LeftUpperLeg", (mid_x + width*0.08, mid_y, z(0.50)), (mid_x + width*0.09, mid_y, z(0.28)), "Hips"),
    ("LeftLowerLeg", (mid_x + width*0.09, mid_y, z(0.28)), (mid_x + width*0.09, mid_y, z(0.08)), "LeftUpperLeg"),
    ("LeftFoot", (mid_x + width*0.09, mid_y, z(0.08)), (mid_x + width*0.09, mid_y + width*0.05, z(0.02)), "LeftLowerLeg"),
    ("RightUpperLeg", (mid_x - width*0.08, mid_y, z(0.50)), (mid_x - width*0.09, mid_y, z(0.28)), "Hips"),
    ("RightLowerLeg", (mid_x - width*0.09, mid_y, z(0.28)), (mid_x - width*0.09, mid_y, z(0.08)), "RightUpperLeg"),
    ("RightFoot", (mid_x - width*0.09, mid_y, z(0.08)), (mid_x - width*0.09, mid_y + width*0.05, z(0.02)), "RightLowerLeg"),
]

bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
arm_obj = bpy.context.view_layer.objects.active
arm_obj.name = "Armature"
arm = arm_obj.data
for b in list(arm.edit_bones):
    arm.edit_bones.remove(b)
created = {{}}
for name, head, tail, parent in bones_def:
    eb = arm.edit_bones.new(name)
    eb.head = head
    eb.tail = tail
    if parent and parent in created:
        eb.parent = created[parent]
        eb.use_connect = False
    created[name] = eb
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
main.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    weight = "AUTO"
except Exception as e:
    weight = str(e)
    main.parent = arm_obj
    mod = main.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm_obj

if main.data.shape_keys is None:
    main.shape_key_add(name="Basis", from_mix=False)
for key in ["A","I","U","E","O","Blink","Joy","Angry","Sorrow","Fun","EyeBlinkLeft","EyeBlinkRight","JawOpen","MouthSmile"]:
    if key not in main.data.shape_keys.key_blocks:
        main.shape_key_add(name=key, from_mix=False)

bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
auto_ok = None
try:
    if hasattr(bpy.ops.vrm, "assign_vrm0_humanoid_human_bones_automatically"):
        bpy.ops.vrm.assign_vrm0_humanoid_human_bones_automatically()
        auto_ok = "vrm0"
except Exception as e:
    auto_ok = str(e)
try:
    ext = getattr(arm_obj.data, "vrm_addon_extension", None)
    if ext and hasattr(ext, "vrm0") and hasattr(ext.vrm0, "meta"):
        ext.vrm0.meta.title = "Mecha Yameprogrammer v2"
        ext.vrm0.meta.author = "yameprogrammer"
        ext.vrm0.meta.version = "0.2.3"
except Exception:
    pass

# render
for o in list(bpy.data.objects):
    if o.type in {{'LIGHT','CAMERA'}}:
        bpy.data.objects.remove(o, do_unlink=True)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn=world.node_tree.nodes; wl=world.node_tree.links; wn.clear()
bg=wn.new('ShaderNodeBackground'); bg.inputs[0].default_value=(0.82,0.84,0.87,1); bg.inputs[1].default_value=1.05
wout=wn.new('ShaderNodeOutputWorld'); wl.new(bg.outputs[0], wout.inputs[0])
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector())/8.0
height = max(v.z for v in bbox)-min(v.z for v in bbox)
cam_data=bpy.data.cameras.new('PreviewCam'); cam=bpy.data.objects.new('PreviewCam', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(center.x, center.y - max(height*2.25, 3.6), center.z+0.02)
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=cam
for name, loc, e in [('Key', (center.x+1.4, center.y-2.0, center.z+1.5), 520),
                      ('Fill', (center.x-1.5, center.y-1.2, center.z+0.8), 180)]:
    ld=bpy.data.lights.new(name,'AREA'); ld.energy=e; ld.size=1.7
    lo=bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(lo); lo.location=loc

arm_obj.hide_render = True
scene=bpy.context.scene
try:
    scene.render.engine='BLENDER_EEVEE'
except Exception:
    scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=768; scene.render.resolution_y=1152
scene.render.filepath=render
bpy.ops.render.render(write_still=True)

arm_obj.hide_set(True)
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            for space in area.spaces:
                if space.type=='VIEW_3D':
                    space.shading.type='MATERIAL'
                    space.region_3d.view_perspective='CAMERA'
            region=next(r for r in area.regions if r.type=='WINDOW')
            with bpy.context.temp_override(window=window, area=area, region=region, scene=scene):
                scene.render.filepath=ogl
                bpy.ops.render.opengl(write_still=True)
            break
arm_obj.hide_set(False)

window=bpy.context.window_manager.windows[0]
area=next((a for a in window.screen.areas if a.type=='VIEW_3D'), window.screen.areas[0])
region=next((r for r in area.regions if r.type=='WINDOW'), area.regions[0])
bpy.ops.object.select_all(action='DESELECT')
main.select_set(True); arm_obj.select_set(True)
bpy.context.view_layer.objects.active=arm_obj
export_notes={{}}
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=arm_obj, selected_objects=[main, arm_obj]):
    bpy.ops.export_scene.gltf(filepath=temp, export_format='GLB', use_selection=True, export_skins=True, export_morph=True, export_materials='EXPORT', export_animations=False)
    try:
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_armature_deform_only=True, path_mode='COPY', embed_textures=True)
        export_notes['fbx']=True
    except Exception as e:
        export_notes['fbx']=str(e)
    if hasattr(bpy.ops.export_scene, 'vrm'):
        try:
            export_notes['vrm']=list(bpy.ops.export_scene.vrm(filepath=vrm, ignore_warning=True, check_existing=False, armature_object_name=arm_obj.name))
        except Exception as e:
            export_notes['vrm']=str(e)

bpy.ops.wm.save_as_mainfile(filepath=blend)

head_coords = [main.matrix_world @ v.co for v in main.data.vertices if (main.matrix_world @ v.co - head_center).length < head_r*1.12]
above = sum(1 for c in head_coords if c.z > head_center.z)
below = sum(1 for c in head_coords if c.z < head_center.z)
# torso hole check: central mid torso verts
torso = [c for c in [main.matrix_world @ v.co for v in main.data.vertices]
         if abs(c.x) < body_half_w*0.3 and minz+hh*0.55 < c.z < minz+hh*0.72]
result = {{
    "status": "success",
    "deleted_head_verts": deleted,
    "head_r": float(head_r),
    "head_center": list(head_center),
    "collar_z": float(collar_z),
    "head_verts": len(head_coords),
    "head_above": above,
    "head_below": below,
    "complete_sphere_ratio": float(min(above, below) / max(max(above, below), 1)),
    "torso_central_verts": len(torso),
    "poly": len(main.data.polygons),
    "height_m": float(main.dimensions.z),
    "weight": weight,
    "auto_ok": auto_ok,
    "export_notes": export_notes,
    "vrm_size": Path(vrm).stat().st_size if Path(vrm).is_file() else 0,
}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4500])
    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("glb", GLB.stat().st_size)
    if VRM.is_file() and VRM.stat().st_size > 10000:
        shutil.copyfile(VRM, VRM2)
        print("VRM", VRM.stat().st_size, "has_VRM", b"VRM" in VRM.read_bytes())
        print("LOAD:", VRM)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
