#!/usr/bin/env python3
"""
Refit humanoid armature to actual mecha_yame_v2 mesh proportions
(head / hands / feet / hips from geometry), re-weight, export VRM.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
# Prefer clean multiview textured source (no broken sphere-head experiment)
SRC = EXPORTS / "mecha_yame_v2_simple_mv_tex.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_yame_v2_warudo.glb"

BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
RENDER = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_v2_front.png")
OGL = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_v2_ogl.png")
RENDER_DST = EXPORTS / "viewport_render.png"
OGL_DST = EXPORTS / "viewport_opengl.png"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_refit.glb")


def main() -> int:
    if not SRC.is_file():
        print("[ERROR] missing", SRC)
        return 1
    print("[src]", SRC)

    p = {k: str(v).replace("\\", "/") for k, v in {
        "src": SRC, "blend": BLEND, "vrm": VRM, "vrm2": VRM2,
        "temp": TEMP, "fbx": FBX, "render": RENDER, "ogl": OGL,
    }.items()}

    code = f'''
import bpy
import addon_utils
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

# clear
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
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
main.name = "MechaYame_V2"

# clear any existing armature parents/mods
for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
main.parent = None

# normalize height 1.70, feet on ground
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

# --- geometry landmarks from vertices ---
vs = [main.matrix_world @ v.co for v in main.data.vertices]
xs = [v.x for v in vs]
ys = [v.y for v in vs]
zs = [v.z for v in vs]
minx, maxx = min(xs), max(xs)
miny, maxy = min(ys), max(ys)
minz, maxz = min(zs), max(zs)
h = maxz - minz
w = maxx - minx
mid_x = (minx + maxx) * 0.5
mid_y = (miny + maxy) * 0.5

def band(z0, z1, x_abs_max=None, x_sign=None, y_range=None):
    out = []
    for v in vs:
        if not (z0 <= v.z <= z1):
            continue
        if x_abs_max is not None and abs(v.x - mid_x) > x_abs_max:
            continue
        if x_sign == "L" and v.x < mid_x:
            continue
        if x_sign == "R" and v.x > mid_x:
            continue
        if y_range is not None and not (y_range[0] <= v.y <= y_range[1]):
            continue
        out.append(v)
    return out

def avg(pts):
    if not pts:
        return Vector((mid_x, mid_y, (minz+maxz)*0.5))
    return Vector((
        sum(p.x for p in pts)/len(pts),
        sum(p.y for p in pts)/len(pts),
        sum(p.z for p in pts)/len(pts),
    ))

def extremum(pts, axis, which="max"):
    if not pts:
        return avg(pts)
    key = (lambda p: p.x) if axis == "x" else (lambda p: p.y) if axis == "y" else (lambda p: p.z)
    p = max(pts, key=key) if which == "max" else min(pts, key=key)
    return p

# feet: lowest 4% verts, left/right
foot_band = [v for v in vs if v.z <= minz + h * 0.06]
left_foot_pts = [v for v in foot_band if v.x >= mid_x]
right_foot_pts = [v for v in foot_band if v.x < mid_x]
left_foot = avg(left_foot_pts) if left_foot_pts else Vector((mid_x + w*0.12, mid_y, minz + 0.02))
right_foot = avg(right_foot_pts) if right_foot_pts else Vector((mid_x - w*0.12, mid_y, minz + 0.02))
# foot tip slightly forward (prefer min Y if character faces -Y)
if foot_band:
    # detect facing: majority of mesh mass
    face_sign = -1.0 if (sum(v.y for v in vs)/len(vs) < mid_y) else -1.0
else:
    face_sign = -1.0

# ankles / lower legs
left_ankle_z = minz + h * 0.08
right_ankle_z = minz + h * 0.08
left_knee_pts = band(minz + h*0.22, minz + h*0.38, x_sign="L")
right_knee_pts = band(minz + h*0.22, minz + h*0.38, x_sign="R")
left_knee = avg(left_knee_pts)
right_knee = avg(right_knee_pts)

# hips / crotch: mid-low central
hip_pts = band(minz + h*0.42, minz + h*0.55, x_abs_max=w*0.22)
hips = avg(hip_pts)
hips = Vector((mid_x, mid_y, hips.z))

# upper legs
left_thigh = Vector((left_knee.x * 0.3 + (mid_x + w*0.08)*0.7, mid_y, hips.z - h*0.02))
right_thigh = Vector((right_knee.x * 0.3 + (mid_x - w*0.08)*0.7, mid_y, hips.z - h*0.02))
# better: from hip side
left_hip_j = Vector((mid_x + w*0.10, mid_y, hips.z))
right_hip_j = Vector((mid_x - w*0.10, mid_y, hips.z))

# torso
spine_pts = band(minz + h*0.52, minz + h*0.62, x_abs_max=w*0.25)
chest_pts = band(minz + h*0.62, minz + h*0.74, x_abs_max=w*0.30)
spine = avg(spine_pts)
chest = avg(chest_pts)
spine = Vector((mid_x, mid_y, spine.z))
chest = Vector((mid_x, mid_y, chest.z))

# head: top 18% of height, center
head_pts = [v for v in vs if v.z >= minz + h * 0.82]
head_c = avg(head_pts)
head_top_z = max(v.z for v in head_pts) if head_pts else maxz
head_bot_z = min(v.z for v in head_pts) if head_pts else (minz + h*0.82)
# neck under head
neck_pts = band(head_bot_z - h*0.06, head_bot_z + h*0.01, x_abs_max=w*0.18)
neck = avg(neck_pts)
neck = Vector((mid_x, mid_y, min(neck.z, head_bot_z - 0.01)))
head_bone_head = Vector((mid_x, mid_y, neck.z + (head_top_z - neck.z)*0.15))
head_bone_tail = Vector((mid_x, mid_y, head_top_z - h*0.01))

# shoulders: widest in upper torso band
shoulder_band = band(minz + h*0.68, minz + h*0.80)
if shoulder_band:
    left_sh_pt = max(shoulder_band, key=lambda v: v.x)
    right_sh_pt = min(shoulder_band, key=lambda v: v.x)
    left_sh = Vector((left_sh_pt.x * 0.85 + mid_x * 0.15, mid_y, left_sh_pt.z))
    right_sh = Vector((right_sh_pt.x * 0.85 + mid_x * 0.15, mid_y, right_sh_pt.z))
else:
    left_sh = Vector((mid_x + w*0.22, mid_y, minz + h*0.74))
    right_sh = Vector((mid_x - w*0.22, mid_y, minz + h*0.74))

# hands: extreme left/right in mid-height
hand_band = [v for v in vs if minz + h*0.28 <= v.z <= minz + h*0.55]
left_hand_pts = [v for v in hand_band if v.x > mid_x + w*0.22]
right_hand_pts = [v for v in hand_band if v.x < mid_x - w*0.22]
if not left_hand_pts:
    left_hand_pts = [v for v in vs if v.x > mid_x + w*0.28]
if not right_hand_pts:
    right_hand_pts = [v for v in vs if v.x < mid_x - w*0.28]
left_hand = avg(left_hand_pts) if left_hand_pts else Vector((maxx - 0.02, mid_y, minz + h*0.40))
right_hand = avg(right_hand_pts) if right_hand_pts else Vector((minx + 0.02, mid_y, minz + h*0.40))

# elbows ~ midpoint shoulder-hand, slightly lower
left_elbow = (left_sh + left_hand) * 0.5
left_elbow = Vector((left_elbow.x, mid_y, left_elbow.z - h*0.02))
right_elbow = (right_sh + right_hand) * 0.5
right_elbow = Vector((right_elbow.x, mid_y, right_elbow.z - h*0.02))

# chest center for shoulder parent
chest_joint = Vector((mid_x, mid_y, (left_sh.z + right_sh.z) * 0.5))

# feet bone tips
left_foot_tip = Vector((left_foot.x, left_foot.y + face_sign * w * 0.06, minz + 0.01))
right_foot_tip = Vector((right_foot.x, right_foot.y + face_sign * w * 0.06, minz + 0.01))
left_ankle = Vector((left_foot.x, left_foot.y, minz + h*0.09))
right_ankle = Vector((right_foot.x, right_foot.y, minz + h*0.09))

# build bones (head, tail, parent)
bones_def = [
    ("Hips", hips, Vector((hips.x, hips.y, hips.z + h*0.04)), None),
    ("Spine", Vector((mid_x, mid_y, hips.z + h*0.04)), spine, "Hips"),
    ("Chest", spine, chest_joint, "Spine"),
    ("Neck", chest_joint, neck, "Chest"),
    ("Head", neck, head_bone_tail, "Neck"),
    ("LeftShoulder", chest_joint, left_sh, "Chest"),
    ("LeftUpperArm", left_sh, left_elbow, "LeftShoulder"),
    ("LeftLowerArm", left_elbow, left_hand, "LeftUpperArm"),
    ("LeftHand", left_hand, left_hand + Vector((w*0.04, 0, -h*0.01)), "LeftLowerArm"),
    ("RightShoulder", chest_joint, right_sh, "Chest"),
    ("RightUpperArm", right_sh, right_elbow, "RightShoulder"),
    ("RightLowerArm", right_elbow, right_hand, "RightUpperArm"),
    ("RightHand", right_hand, right_hand + Vector((-w*0.04, 0, -h*0.01)), "RightLowerArm"),
    ("LeftUpperLeg", left_hip_j, left_knee, "Hips"),
    ("LeftLowerLeg", left_knee, left_ankle, "LeftUpperLeg"),
    ("LeftFoot", left_ankle, left_foot_tip, "LeftLowerLeg"),
    ("RightUpperLeg", right_hip_j, right_knee, "Hips"),
    ("RightLowerLeg", right_knee, right_ankle, "RightUpperLeg"),
    ("RightFoot", right_ankle, right_foot_tip, "RightLowerLeg"),
]

# remove zero-length bones
fixed = []
for name, head, tail, parent in bones_def:
    if (tail - head).length < 0.001:
        tail = head + Vector((0, 0, 0.02))
    fixed.append((name, head, tail, parent))
bones_def = fixed

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
arm_obj.show_in_front = True

# skin
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

# shape keys stub for VRM
if main.data.shape_keys is None:
    main.shape_key_add(name="Basis", from_mix=False)
for key in ["A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun"]:
    if key not in main.data.shape_keys.key_blocks:
        main.shape_key_add(name=key, from_mix=False)

# landmark report
lm = {{
    "hips": [round(hips.x,3), round(hips.y,3), round(hips.z,3)],
    "head_tail": [round(head_bone_tail.x,3), round(head_bone_tail.y,3), round(head_bone_tail.z,3)],
    "left_hand": [round(left_hand.x,3), round(left_hand.y,3), round(left_hand.z,3)],
    "right_hand": [round(right_hand.x,3), round(right_hand.y,3), round(right_hand.z,3)],
    "left_foot": [round(left_foot.x,3), round(left_foot.y,3), round(left_foot.z,3)],
    "right_foot": [round(right_foot.x,3), round(right_foot.y,3), round(right_foot.z,3)],
    "left_sh": [round(left_sh.x,3), round(left_sh.y,3), round(left_sh.z,3)],
    "right_sh": [round(right_sh.x,3), round(right_sh.y,3), round(right_sh.z,3)],
    "height": round(h,3),
    "width": round(w,3),
}}

# preview
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
bg = wn.new("ShaderNodeBackground")
bg.inputs[0].default_value = (0.85, 0.86, 0.88, 1.0)
bg.inputs[1].default_value = 1.1
wout = wn.new("ShaderNodeOutputWorld")
wl.new(bg.outputs[0], wout.inputs[0])

bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector()) / 8.0
height = max(v.z for v in bbox) - min(v.z for v in bbox)
cam_data = bpy.data.cameras.new("PreviewCam")
cam_data.lens = 55
cam = bpy.data.objects.new("PreviewCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(height * 2.15, 3.3), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam

def add_light(name, loc, energy):
    ld = bpy.data.lights.new(name=name, type="AREA")
    ld.energy = energy
    ld.size = 1.6
    lo = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = loc

add_light("Key", (center.x + 1.3, center.y - 2.0, center.z + 1.5), 450)
add_light("Fill", (center.x - 1.5, center.y - 1.2, center.z + 0.8), 170)

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE"
except Exception:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
scene.render.resolution_x = 768
scene.render.resolution_y = 1152
scene.render.filepath = render_path
scene.render.image_settings.file_format = "PNG"
arm_obj.hide_render = True
bpy.ops.render.render(write_still=True)

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
arm_obj.hide_render = False  # visible in viewport for user check
arm_obj.show_in_front = True

# export
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

# bone positions in edit for verify
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")
bone_pos = {{}}
for b in arm.edit_bones:
    bone_pos[b.name] = {{
        "head": [round(b.head.x,3), round(b.head.y,3), round(b.head.z,3)],
        "tail": [round(b.tail.x,3), round(b.tail.y,3), round(b.tail.z,3)],
    }}
bpy.ops.object.mode_set(mode="OBJECT")

result = {{
    "status": "ok",
    "weight_mode": weight_mode,
    "vrm_status": vrm_status,
    "landmarks": lm,
    "bones": bone_pos,
    "verts": len(main.data.vertices),
    "dims": [round(float(x),3) for x in main.dimensions],
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:5000])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] refit failed")
        return 1

    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("[OK glb]", GLB.stat().st_size)
    for tmp, dst in ((RENDER, RENDER_DST), (OGL, OGL_DST)):
        if tmp.is_file():
            shutil.copyfile(tmp, dst)
            print("[OK]", dst.name)
    print("[OK vrm]", VRM.exists(), payload.get("vrm_status"))
    print("[landmarks]", json.dumps(payload.get("landmarks"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
