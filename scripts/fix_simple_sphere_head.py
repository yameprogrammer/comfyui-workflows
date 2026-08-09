#!/usr/bin/env python3
"""
Blender correction: wipe AI head, attach true UV sphere + cyan eyes, re-export VRM.
Body (hoodie/arms) kept from multiview mesh.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
SRC = EXPORTS / "mecha_yame_v2_simple_mv_tex.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_yame_v2_example01_tex.glb"

BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
RENDER = EXPORTS / "viewport_render.png"
OGL = EXPORTS / "viewport_opengl.png"
SIDE = EXPORTS / "viewport_side.png"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_sphere_head.glb")
TMP_RENDER = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_v2_front.png")
TMP_OGL = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_v2_ogl.png")
TMP_SIDE = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_v2_side.png")


def main() -> int:
    if not SRC.is_file():
        print("[ERROR] missing", SRC)
        return 1
    print("[src]", SRC)

    # paths as plain strings for embedding
    p = {
        "src": str(SRC).replace("\\", "/"),
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(VRM).replace("\\", "/"),
        "vrm2": str(VRM2).replace("\\", "/"),
        "temp": str(TEMP).replace("\\", "/"),
        "fbx": str(FBX).replace("\\", "/"),
        "render": str(TMP_RENDER).replace("\\", "/"),
        "ogl": str(TMP_OGL).replace("\\", "/"),
        "side": str(TMP_SIDE).replace("\\", "/"),
    }

    code = f'''
import bpy
import bmesh
import addon_utils
import math
from mathutils import Vector

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

src = r"{p['src']}"
blend = r"{p['blend']}"
vrm = r"{p['vrm']}"
vrm2 = r"{p['vrm2']}"
temp = r"{p['temp']}"
fbx = r"{p['fbx']}"
render_path = r"{p['render']}"
ogl_path = r"{p['ogl']}"
side_path = r"{p['side']}"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights, bpy.data.images):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=src)
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_Body"

bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
main.location = (0, 0, 0)
main.rotation_euler = (0, 0, 0)
if main.dimensions.z > 1e-6:
    s = 1.70 / float(main.dimensions.z)
    main.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
main.location.z -= min(v.z for v in bbox)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

coords = [main.matrix_world @ v.co for v in main.data.vertices]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
h = maxz - minz
mid_pts = [c for c in coords if minz + h * 0.35 < c.z < minz + h * 0.55]
body_half_w = 0.5 * (max(c.x for c in mid_pts) - min(c.x for c in mid_pts)) if mid_pts else 0.25
mid_x0 = (max(c.x for c in mid_pts) + min(c.x for c in mid_pts)) * 0.5 if mid_pts else 0.0

# cut plane: wipe entire head (chibi head is large ~ top 30%)
cut_z = minz + h * 0.70
arm_x = body_half_w * 0.52

bpy.context.view_layer.objects.active = main
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(main.data)
bm.verts.ensure_lookup_table()
deleted = 0
for v in bm.verts:
    w = main.matrix_world @ v.co
    high = w.z > cut_z
    arm = abs(w.x - mid_x0) > arm_x and w.z < cut_z + h * 0.10
    if high and not arm:
        v.select = True
        deleted += 1
    else:
        v.select = False
bmesh.update_edit_mesh(main.data)
bpy.ops.mesh.delete(type="VERT")
bpy.ops.mesh.select_all(action="SELECT")
try:
    bpy.ops.mesh.delete_loose()
except Exception:
    pass
try:
    bpy.ops.mesh.fill_holes(sides=20)
except Exception:
    pass
try:
    bpy.ops.mesh.remove_doubles(threshold=0.0003)
except Exception:
    pass
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")

coords = [main.matrix_world @ v.co for v in main.data.vertices]
maxz2 = max(c.z for c in coords)
collar_pts = [c for c in coords if abs(c.x - mid_x0) < body_half_w * 0.40 and c.z > maxz2 - 0.12]
if not collar_pts:
    collar_pts = sorted(coords, key=lambda c: c.z, reverse=True)[:40]
thr = sorted(collar_pts, key=lambda c: c.z, reverse=True)[: max(40, len(collar_pts) // 6)]
collar_z = sum(c.z for c in thr) / len(thr)
collar_x = sum(c.x for c in thr) / len(thr)
collar_y = sum(c.y for c in thr) / len(thr)

head_r = 0.27
neck_r = head_r * 0.26
neck_h = 0.06
head_center = Vector((collar_x, collar_y, collar_z + neck_h + head_r * 0.80))

def new_mat(name, color, metallic, roughness, emit=None, es=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    if emit is not None:
        for k in ("Emission Color", "Emission"):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = (*emit, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = es
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

mat_head = new_mat("Head_Matte", (0.72, 0.74, 0.76), 0.02, 0.72)
mat_eye = new_mat("Eye_Cyan", (0.25, 0.85, 0.95), 0.05, 0.35, emit=(0.2, 0.85, 1.0), es=1.8)
mat_neck = new_mat("Neck_Matte", (0.68, 0.70, 0.72), 0.05, 0.65)
for mat in main.data.materials:
    if mat:
        mat.use_backface_culling = False

bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=neck_r, depth=neck_h * 1.2, location=(collar_x, collar_y, collar_z + neck_h * 0.4))
neck_obj = bpy.context.view_layer.objects.active
neck_obj.name = "Neck"
neck_obj.data.materials.append(mat_neck)

bpy.ops.mesh.primitive_uv_sphere_add(segments=72, ring_count=48, radius=head_r, location=head_center)
head_obj = bpy.context.view_layer.objects.active
head_obj.name = "Head_Sphere"
bpy.ops.object.shade_smooth()
head_obj.data.materials.append(mat_head)

bpy.ops.mesh.primitive_torus_add(major_radius=head_r * 0.985, minor_radius=head_r * 0.01, major_segments=72, minor_segments=10, location=head_center + Vector((0, 0, head_r * 0.06)))
seam = bpy.context.view_layer.objects.active
seam.name = "Head_Seam"
seam.rotation_euler = (math.radians(90), 0, 0)
seam.data.materials.append(mat_head)

eye_r = head_r * 0.15
eye_x_off = head_r * 0.24
for side, sign in (("L", 1.0), ("R", -1.0)):
    local = Vector((sign * eye_x_off, -1.0, 0.04)).normalized() * (head_r * 0.995)
    pos = head_center + local
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=eye_r, depth=head_r * 0.035, location=pos)
    eye = bpy.context.view_layer.objects.active
    eye.name = "Eye_" + side
    eye.rotation_mode = "QUATERNION"
    eye.rotation_quaternion = local.normalized().to_track_quat("Z", "Y")
    eye.data.materials.append(mat_eye)

bpy.ops.object.select_all(action="DESELECT")
for o in (head_obj, neck_obj, seam):
    o.select_set(True)
for o in bpy.data.objects:
    if o.name.startswith("Eye_"):
        o.select_set(True)
bpy.context.view_layer.objects.active = head_obj
bpy.ops.object.join()
head_obj = bpy.context.view_layer.objects.active
head_obj.name = "Head_Assembly"

bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
head_obj.select_set(True)
bpy.context.view_layer.objects.active = main
bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_V2"

bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
main.location.z -= min(v.z for v in bbox)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if main.dimensions.z > 1e-6:
    s = 1.75 / float(main.dimensions.z)
    main.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    main.location.z -= min(v.z for v in bbox)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
for p in main.data.polygons:
    p.use_smooth = True

bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
height = max_v.z - min_v.z
mid_x = (min_v.x + max_v.x) * 0.5
mid_y = (min_v.y + max_v.y) * 0.5
width = max(max_v.x - min_v.x, 0.3)

def z(t):
    return min_v.z + height * t

bones_def = [
    ("Hips", (mid_x, mid_y, z(0.48)), (mid_x, mid_y, z(0.54)), None),
    ("Spine", (mid_x, mid_y, z(0.54)), (mid_x, mid_y, z(0.62)), "Hips"),
    ("Chest", (mid_x, mid_y, z(0.62)), (mid_x, mid_y, z(0.72)), "Spine"),
    ("Neck", (mid_x, mid_y, z(0.72)), (mid_x, mid_y, z(0.78)), "Chest"),
    ("Head", (mid_x, mid_y, z(0.78)), (mid_x, mid_y, z(0.98)), "Neck"),
    ("LeftShoulder", (mid_x, mid_y, z(0.71)), (mid_x + width*0.14, mid_y, z(0.70)), "Chest"),
    ("LeftUpperArm", (mid_x + width*0.14, mid_y, z(0.70)), (mid_x + width*0.30, mid_y, z(0.54)), "LeftShoulder"),
    ("LeftLowerArm", (mid_x + width*0.30, mid_y, z(0.54)), (mid_x + width*0.38, mid_y, z(0.40)), "LeftUpperArm"),
    ("LeftHand", (mid_x + width*0.38, mid_y, z(0.40)), (mid_x + width*0.42, mid_y, z(0.36)), "LeftLowerArm"),
    ("RightShoulder", (mid_x, mid_y, z(0.71)), (mid_x - width*0.14, mid_y, z(0.70)), "Chest"),
    ("RightUpperArm", (mid_x - width*0.14, mid_y, z(0.70)), (mid_x - width*0.30, mid_y, z(0.54)), "RightShoulder"),
    ("RightLowerArm", (mid_x - width*0.30, mid_y, z(0.54)), (mid_x - width*0.38, mid_y, z(0.40)), "RightUpperArm"),
    ("RightHand", (mid_x - width*0.38, mid_y, z(0.40)), (mid_x - width*0.42, mid_y, z(0.36)), "RightLowerArm"),
    ("LeftUpperLeg", (mid_x + width*0.10, mid_y, z(0.48)), (mid_x + width*0.11, mid_y, z(0.26)), "Hips"),
    ("LeftLowerLeg", (mid_x + width*0.11, mid_y, z(0.26)), (mid_x + width*0.11, mid_y, z(0.08)), "LeftUpperLeg"),
    ("LeftFoot", (mid_x + width*0.11, mid_y, z(0.08)), (mid_x + width*0.11, mid_y + width*0.06, z(0.02)), "LeftLowerLeg"),
    ("RightUpperLeg", (mid_x - width*0.10, mid_y, z(0.48)), (mid_x - width*0.11, mid_y, z(0.26)), "Hips"),
    ("RightLowerLeg", (mid_x - width*0.11, mid_y, z(0.26)), (mid_x - width*0.11, mid_y, z(0.08)), "RightUpperLeg"),
    ("RightFoot", (mid_x - width*0.11, mid_y, z(0.08)), (mid_x - width*0.11, mid_y + width*0.06, z(0.02)), "RightLowerLeg"),
]

bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
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
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
weight_mode = "ARMATURE_AUTO"
try:
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
except Exception as e:
    weight_mode = "FALLBACK:" + str(e)
    main.parent = arm_obj
    mod = main.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj

if main.data.shape_keys is None:
    main.shape_key_add(name="Basis", from_mix=False)
for key in ["A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun"]:
    if key not in main.data.shape_keys.key_blocks:
        main.shape_key_add(name=key, from_mix=False)

arm_obj.hide_render = True
arm_obj.show_in_front = True

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
bg = wn.new("ShaderNodeBackground")
bg.inputs[0].default_value = (0.85, 0.86, 0.88, 1.0)
bg.inputs[1].default_value = 1.15
wout = wn.new("ShaderNodeOutputWorld")
wl.new(bg.outputs[0], wout.inputs[0])

for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)

bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector()) / 8.0
height = max(v.z for v in bbox) - min(v.z for v in bbox)

cam_data = bpy.data.cameras.new("PreviewCam")
cam_data.lens = 55
cam = bpy.data.objects.new("PreviewCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(height * 2.15, 3.3), center.z + 0.02)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam

def add_light(name, loc, energy):
    ld = bpy.data.lights.new(name=name, type="AREA")
    ld.energy = energy
    ld.size = 1.7
    lo = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = loc

add_light("Key", (center.x + 1.4, center.y - 2.1, center.z + 1.6), 480)
add_light("Fill", (center.x - 1.7, center.y - 1.3, center.z + 0.9), 180)
add_light("Rim", (center.x, center.y + 1.7, center.z + 1.3), 220)

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE"
except Exception:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
scene.render.resolution_x = 768
scene.render.resolution_y = 1152
scene.render.filepath = render_path
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)

cam.location = (center.x + max(height * 2.15, 3.3), center.y, center.z + 0.02)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = side_path
bpy.ops.render.render(write_still=True)

cam.location = (center.x, center.y - max(height * 2.15, 3.3), center.z + 0.02)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

arm_obj.hide_set(True)
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "MATERIAL"
                    space.region_3d.view_perspective = "CAMERA"
            region = next(r for r in area.regions if r.type == "WINDOW")
            with bpy.context.temp_override(window=window, area=area, region=region, scene=scene):
                scene.render.filepath = ogl_path
                bpy.ops.render.opengl(write_still=True)
            break
arm_obj.hide_set(False)

bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.export_scene.gltf(filepath=temp, export_format="GLB", use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=blend)

vrm_status = "skipped"
if hasattr(bpy.ops.export_scene, "vrm"):
    try:
        bpy.ops.export_scene.vrm(filepath=vrm)
        vrm_status = "ok"
        import shutil as _sh
        _sh.copyfile(vrm, vrm2)
    except Exception as e:
        vrm_status = "error:" + str(e)

result = {{
    "status": "ok",
    "deleted_head_verts": deleted,
    "cut_z": round(cut_z, 4),
    "head_r": round(head_r, 4),
    "head_center": [round(float(head_center.x), 4), round(float(head_center.y), 4), round(float(head_center.z), 4)],
    "collar_z": round(collar_z, 4),
    "verts": len(main.data.vertices),
    "faces": len(main.data.polygons),
    "weight_mode": weight_mode,
    "vrm_status": vrm_status,
    "dims": [round(float(x), 4) for x in main.dimensions],
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] failed")
        return 1

    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("[OK glb]", GLB, GLB.stat().st_size)
    for tmp, dst in ((TMP_RENDER, RENDER), (TMP_OGL, OGL), (TMP_SIDE, SIDE)):
        if tmp.is_file():
            shutil.copyfile(tmp, dst)
            print("[OK]", dst.name, dst.stat().st_size)
    print("[OK vrm]", VRM.exists(), payload.get("vrm_status"))
    print("deleted", payload.get("deleted_head_verts"), "head_r", payload.get("head_r"), "cut_z", payload.get("cut_z"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
