#!/usr/bin/env python3
"""
Retarget shoulder / arm bones on current mecha blend to mesh landmarks (T-pose),
re-skin, export VRM. Keeps SD hip/head proportions; fixes shoulder joint only.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
# Prefer cleaned T-pose mesh
SRC = EXPORTS / "mecha_yame_v2_tpose_clean.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_yame_v2_tpose_tex.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sh.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sh.glb")
RENDER = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sh.png")
RENDER_DST = EXPORTS / "viewport_render.png"


def main() -> int:
    p = {k: str(v).replace("\\", "/") for k, v in {
        "src": SRC, "blend": BLEND, "vrm": TEMP_VRM, "glb": TEMP_GLB, "render": RENDER,
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
vrm_path = r"{p['vrm']}"
glb_path = r"{p['glb']}"
render_path = r"{p['render']}"

# fresh import of clean mesh
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

# normalize 1.70
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

vs = [main.matrix_world @ v.co for v in main.data.vertices]
xs = [v.x for v in vs]
ys = [v.y for v in vs]
zs = [v.z for v in vs]
minx, maxx = min(xs), max(xs)
miny, maxy = min(ys), max(ys)
minz, maxz = min(zs), max(zs)
H = maxz - minz
W = maxx - minx
cx = (minx + maxx) * 0.5
cy = (miny + maxy) * 0.5

def pct(t):
    return minz + H * t

def avg(pts, fb):
    if not pts:
        return fb
    return Vector((
        sum(p.x for p in pts)/len(pts),
        sum(p.y for p in pts)/len(pts),
        sum(p.z for p in pts)/len(pts),
    ))

# --- head ---
head_pts = [v for v in vs if v.z >= pct(0.58)]
hcx = sum(v.x for v in head_pts)/len(head_pts)
hcy = sum(v.y for v in head_pts)/len(head_pts)
head_top = max(v.z for v in head_pts)
head_bot = min(v.z for v in head_pts)
neck_z = head_bot - H * 0.01
neck = Vector((cx, cy, neck_z))
head_tail = Vector((hcx, hcy, head_top - H*0.01))

# --- torso landmarks ---
hips_z = pct(0.23)
spine_z = pct(0.37)
chest_z = min(pct(0.50), neck_z - H * 0.10)
hips = Vector((cx, cy, hips_z))
spine = Vector((cx, cy, spine_z))
chest = Vector((cx, cy, chest_z))

# --- T-pose shoulder from MESH: armpit pit + sleeve root ---
# Find torso width at chest (central mass only)
chest_band = [v for v in vs if abs(v.z - chest_z) < H*0.05 and abs(v.x-cx) < W*0.22]
if chest_band:
    torso_half = 0.5 * (max(v.x for v in chest_band) - min(v.x for v in chest_band))
else:
    torso_half = W * 0.16

# Armpit: lowest verts just outside torso under shoulder height
# Sample ring around sleeve root
shoulder_band_z = neck_z - H * 0.08
armpit_L = [v for v in vs
            if cx + torso_half*0.7 < v.x < cx + torso_half*1.35
            and shoulder_band_z - H*0.12 < v.z < shoulder_band_z + H*0.04]
armpit_R = [v for v in vs
            if cx - torso_half*1.35 < v.x < cx - torso_half*0.7
            and shoulder_band_z - H*0.12 < v.z < shoulder_band_z + H*0.04]

# shoulder joint slightly above armpit, at torso edge
if armpit_L:
    al = avg(armpit_L, Vector((cx+torso_half, cy, shoulder_band_z)))
    left_sh = Vector((al.x, cy, al.z + H*0.035))
else:
    left_sh = Vector((cx + torso_half * 1.05, cy, neck_z - H*0.10))
if armpit_R:
    ar = avg(armpit_R, Vector((cx-torso_half, cy, shoulder_band_z)))
    right_sh = Vector((ar.x, cy, ar.z + H*0.035))
else:
    right_sh = Vector((cx - torso_half * 1.05, cy, neck_z - H*0.10))

# force similar height / mirror-ish
sh_z = 0.5 * (left_sh.z + right_sh.z)
left_sh = Vector((left_sh.x, cy, sh_z))
right_sh = Vector((right_sh.x, cy, sh_z))

# clavicle root on chest sides (short shoulder bones)
left_clav = Vector((cx + torso_half * 0.55, cy, sh_z + H*0.01))
right_clav = Vector((cx - torso_half * 0.55, cy, sh_z + H*0.01))

# hands: outermost at arm height
hand_band = [v for v in vs if abs(v.z - sh_z) < H*0.14]
lh = sorted([v for v in hand_band if v.x > cx], key=lambda v: v.x, reverse=True)
rh = sorted([v for v in hand_band if v.x < cx], key=lambda v: v.x)
lh_tip = lh[:max(10, len(lh)//15)] if lh else []
rh_tip = rh[:max(10, len(rh)//15)] if rh else []
left_hand = avg(lh_tip, Vector((maxx, cy, sh_z)))
right_hand = avg(rh_tip, Vector((minx, cy, sh_z)))
left_hand = Vector((left_hand.x, cy, sh_z))
right_hand = Vector((right_hand.x, cy, sh_z))
# ensure reach
if left_hand.x < left_sh.x + W*0.12:
    left_hand = Vector((left_sh.x + W*0.22, cy, sh_z))
if right_hand.x > right_sh.x - W*0.12:
    right_hand = Vector((right_sh.x - W*0.22, cy, sh_z))

# elbows 50% along upper arm line (horizontal T)
left_elbow = Vector((left_sh.x*0.5 + left_hand.x*0.5, cy, sh_z))
right_elbow = Vector((right_sh.x*0.5 + right_hand.x*0.5, cy, sh_z))

# legs
foot_band = [v for v in vs if v.z <= pct(0.08)]
lf = [v for v in foot_band if v.x >= cx]
rf = [v for v in foot_band if v.x < cx]
left_foot = avg(lf, Vector((cx+W*0.1, cy, minz+0.02)))
right_foot = avg(rf, Vector((cx-W*0.1, cy, minz+0.02)))
left_hip_j = Vector((cx + W*0.10, cy, hips_z))
right_hip_j = Vector((cx - W*0.10, cy, hips_z))
left_ankle = Vector((left_foot.x, left_foot.y, minz + H*0.06))
right_ankle = Vector((right_foot.x, right_foot.y, minz + H*0.06))
left_knee = (left_hip_j + left_ankle) * 0.5
right_knee = (right_hip_j + right_ankle) * 0.5
left_foot_tip = Vector((left_foot.x, left_foot.y - W*0.05, minz+0.01))
right_foot_tip = Vector((right_foot.x, right_foot.y - W*0.05, minz+0.01))

def bone(name, head, tail, parent):
    h, t = Vector(head), Vector(tail)
    if (t - h).length < 0.012:
        t = h + Vector((0.02, 0, 0)) if abs(t.x-h.x) >= abs(t.z-h.z) else h + Vector((0, 0, 0.02))
    return (name, h, t, parent)

# SHORT shoulder (clavicle): chest side → shoulder joint
# UpperArm: shoulder → elbow (main arm length)
bones_def = [
    bone("Hips", hips, hips + Vector((0,0,H*0.05)), None),
    bone("Spine", hips + Vector((0,0,H*0.05)), spine, "Hips"),
    bone("Chest", spine, chest, "Spine"),
    bone("Neck", chest, neck, "Chest"),
    bone("Head", neck, head_tail, "Neck"),
    bone("LeftShoulder", left_clav, left_sh, "Chest"),
    bone("LeftUpperArm", left_sh, left_elbow, "LeftShoulder"),
    bone("LeftLowerArm", left_elbow, left_hand, "LeftUpperArm"),
    bone("LeftHand", left_hand, left_hand + Vector((W*0.03, 0, 0)), "LeftLowerArm"),
    bone("RightShoulder", right_clav, right_sh, "Chest"),
    bone("RightUpperArm", right_sh, right_elbow, "RightShoulder"),
    bone("RightLowerArm", right_elbow, right_hand, "RightUpperArm"),
    bone("RightHand", right_hand, right_hand + Vector((-W*0.03, 0, 0)), "RightLowerArm"),
    bone("LeftUpperLeg", left_hip_j, left_knee, "Hips"),
    bone("LeftLowerLeg", left_knee, left_ankle, "LeftUpperLeg"),
    bone("LeftFoot", left_ankle, left_foot_tip, "LeftLowerLeg"),
    bone("RightUpperLeg", right_hip_j, right_knee, "Hips"),
    bone("RightLowerLeg", right_knee, right_ankle, "RightUpperLeg"),
    bone("RightFoot", right_ankle, right_foot_tip, "RightLowerLeg"),
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
bpy.ops.object.mode_set(mode="OBJECT")
arm_obj.show_in_front = True

# skin: nearest bone with head lock + arm line preference
arm_mw = arm_obj.matrix_world
samples = []
for b in arm.bones:
    h = arm_mw @ b.head_local
    t = arm_mw @ b.tail_local
    samples.append((b.name, h, (h+t)*0.5, t))
    if b.name not in main.vertex_groups:
        main.vertex_groups.new(name=b.name)

# clear groups
main.vertex_groups.clear()
for b in arm.bones:
    main.vertex_groups.new(name=b.name)

head_c = Vector((hcx, hcy, (head_bot+head_top)*0.5))
head_r = max(((v.x-hcx)**2+(v.y-hcy)**2+(v.z-head_c.z)**2)**0.5 for v in head_pts) * 1.05

ARM_L = {{"LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand"}}
ARM_R = {{"RightShoulder","RightUpperArm","RightLowerArm","RightHand"}}
TORSO = {{"Hips","Spine","Chest","Neck"}}
LEG_L = {{"LeftUpperLeg","LeftLowerLeg","LeftFoot"}}
LEG_R = {{"RightUpperLeg","RightLowerLeg","RightFoot"}}

def nearest(names, wco):
    best, bd = None, 1e18
    for n, h, m, t in samples:
        if n not in names:
            continue
        d = min((wco-h).length, (wco-m).length, (wco-t).length)
        if d < bd:
            bd, best = d, n
    return best, bd

mw = main.matrix_world
counts = {{"head":0,"arm":0,"torso":0,"leg":0}}
for vi, v in enumerate(main.data.vertices):
    wco = mw @ v.co
    lat = abs(wco.x - cx) / max(W*0.5, 1e-6)
    th = (wco.z - minz) / max(H, 1e-6)
    d_head = (wco - head_c).length
    side_L = wco.x >= cx

    if d_head <= head_r and wco.z >= neck_z - H*0.04:
        main.vertex_groups["Head"].add([vi], 1.0, "REPLACE")
        counts["head"] += 1
        continue
    if th < 0.27 and lat < 0.55:
        n0, _ = nearest(LEG_L if side_L else LEG_R, wco)
        main.vertex_groups[n0 or "Hips"].add([vi], 1.0, "REPLACE")
        counts["leg"] += 1
        continue
    # arm: outside torso_half and near shoulder height band or outer
    if wco.z < neck_z - H*0.02 and lat > 0.28 and th > 0.25:
        # distance to arm bone line
        n0, d0 = nearest(ARM_L if side_L else ARM_R, wco)
        n_t, dt = nearest(TORSO, wco)
        if n0 and (d0 < dt * 0.95 or lat > 0.38):
            if lat > 0.42:
                main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
            else:
                main.vertex_groups[n0].add([vi], 0.85, "REPLACE")
                if "Chest" in main.vertex_groups:
                    main.vertex_groups["Chest"].add([vi], 0.15, "REPLACE")
            counts["arm"] += 1
            continue
    n0, _ = nearest(TORSO, wco)
    if n0 is None or n0 == "Head":
        n0 = "Chest" if th > 0.45 else ("Spine" if th > 0.32 else "Hips")
    main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
    counts["torso"] += 1

for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm_obj
main.parent = arm_obj

if main.data.shape_keys is None:
    main.shape_key_add(name="Basis", from_mix=False)
for key in ["A","I","U","E","O","Blink","Joy","Angry","Sorrow","Fun"]:
    if key not in main.data.shape_keys.key_blocks:
        main.shape_key_add(name=key, from_mix=False)

# report bone lengths
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")
bone_info = {{}}
for b in arm.edit_bones:
    bone_info[b.name] = {{
        "head": [round(b.head.x,3), round(b.head.y,3), round(b.head.z,3)],
        "tail": [round(b.tail.x,3), round(b.tail.y,3), round(b.tail.z,3)],
        "len": round((b.tail-b.head).length, 3),
    }}
bpy.ops.object.mode_set(mode="OBJECT")

# render
for o in list(bpy.data.objects):
    if o.type in ("LIGHT","CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
wn.clear()
bg = wn.new("ShaderNodeBackground")
bg.inputs[0].default_value = (0.85,0.86,0.88,1)
bg.inputs[1].default_value = 1.1
wout = wn.new("ShaderNodeOutputWorld")
wl.new(bg.outputs[0], wout.inputs[0])
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector())/8.0
height = max(v.z for v in bbox)-min(v.z for v in bbox)
cam_data = bpy.data.cameras.new("PreviewCam")
cam_data.lens = 55
cam = bpy.data.objects.new("PreviewCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(height*2.3, 3.5), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z","Y").to_euler()
bpy.context.scene.camera = cam
ld = bpy.data.lights.new("Key","AREA")
ld.energy = 450
ld.size = 1.6
lo = bpy.data.objects.new("Key", ld)
bpy.context.scene.collection.objects.link(lo)
lo.location = (center.x+1.3, center.y-2.0, center.z+1.4)
scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE"
except Exception:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
scene.render.resolution_x = 768
scene.render.resolution_y = 1152
scene.render.filepath = render_path
arm_obj.hide_render = True
bpy.ops.render.render(write_still=True)
arm_obj.hide_render = False
arm_obj.show_in_front = True

window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type=="VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type=="WINDOW"), area.regions[0])
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=arm_obj, selected_objects=[main, arm_obj]):
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    vrm_ok = False
    vrm_err = ""
    try:
        bpy.ops.export_scene.vrm(filepath=vrm_path)
        vrm_ok = True
    except Exception as e:
        vrm_err = str(e)

result = {{
    "status": "ok",
    "counts": counts,
    "shoulder_z": round(sh_z, 3),
    "left_sh": [round(left_sh.x,3), round(left_sh.z,3)],
    "right_sh": [round(right_sh.x,3), round(right_sh.z,3)],
    "left_hand_x": round(left_hand.x,3),
    "right_hand_x": round(right_hand.x,3),
    "bones": bone_info,
    "vrm_ok": vrm_ok,
    "vrm_err": vrm_err,
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4500])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return 1
    if TEMP_VRM.is_file():
        shutil.copyfile(TEMP_VRM, VRM)
        shutil.copyfile(TEMP_VRM, VRM2)
        print("[OK vrm]", VRM.stat().st_size)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB)
        print("[OK glb]")
    if RENDER.is_file():
        shutil.copyfile(RENDER, RENDER_DST)
        print("[OK render]")
    print("sh_z", payload.get("shoulder_z"), "L", payload.get("left_sh"), "R", payload.get("right_sh"))
    print("arms", payload.get("bones", {}).get("LeftShoulder"), payload.get("bones", {}).get("LeftUpperArm"), payload.get("bones", {}).get("LeftLowerArm"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
