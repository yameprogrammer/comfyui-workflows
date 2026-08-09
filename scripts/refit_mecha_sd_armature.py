#!/usr/bin/env python3
"""
Refit armature for SD/chibi (~3-head-tall) proportions from mesh geometry.
Previous rig used adult human ratios — wrong for this toy robot.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
# Prefer T-pose textured mesh when present
SRC = EXPORTS / "mecha_yame_v2_tpose_tex.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_yame_v2_simple_mv_tex.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sd_rig.glb")
RENDER_TMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sd_front.png")
RENDER_DST = EXPORTS / "viewport_render.png"


def main() -> int:
    if not SRC.is_file():
        print("missing", SRC)
        return 1

    paths = {
        "src": str(SRC).replace("\\", "/"),
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(VRM).replace("\\", "/"),
        "vrm2": str(VRM2).replace("\\", "/"),
        "temp": str(TEMP).replace("\\", "/"),
        "fbx": str(FBX).replace("\\", "/"),
        "render": str(RENDER_TMP).replace("\\", "/"),
    }

    # Use double braces only for Python dicts inside the Blender code
    code = """
import bpy
import addon_utils
from mathutils import Vector

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

src = r"__SRC__"
blend = r"__BLEND__"
vrm = r"__VRM__"
vrm2 = r"__VRM2__"
temp = r"__TEMP__"
fbx = r"__FBX__"
render_path = r"__RENDER__"

# --- clean scene ---
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
for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
main.parent = None
if main.vertex_groups:
    main.vertex_groups.clear()

# normalize 1.70m, feet on floor
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

# --- detect HEAD as top blob (large for SD) ---
# Head is roughly top 30-40% of height for 3-head-tall character
head_slice = [v for v in vs if v.z >= pct(0.62)]
if not head_slice:
    head_slice = [v for v in vs if v.z >= pct(0.55)]
hx = sum(v.x for v in head_slice) / len(head_slice)
hy = sum(v.y for v in head_slice) / len(head_slice)
hz = sum(v.z for v in head_slice) / len(head_slice)
# radius estimate from head verts
hr = max(
    ((v.x - hx) ** 2 + (v.y - hy) ** 2 + (v.z - hz) ** 2) ** 0.5
    for v in head_slice
)
# tighter: mean of upper percentile distances
dists = sorted(
    ((v.x - hx) ** 2 + (v.y - hy) ** 2 + (v.z - hz) ** 2) ** 0.5
    for v in head_slice
)
hr = dists[int(len(dists) * 0.85)]
head_top = max(v.z for v in head_slice)
head_bot = min(v.z for v in head_slice)
# neck sits just under head bottom, central
neck_z = head_bot - H * 0.015
neck = Vector((cx, cy, neck_z))
head_c = Vector((hx, hy, (head_bot + head_top) * 0.5))

# --- feet ---
foot_band = [v for v in vs if v.z <= pct(0.08)]
lf = [v for v in foot_band if v.x >= cx]
rf = [v for v in foot_band if v.x < cx]
def avg(pts, fallback):
    if not pts:
        return fallback
    return Vector((
        sum(p.x for p in pts) / len(pts),
        sum(p.y for p in pts) / len(pts),
        sum(p.z for p in pts) / len(pts),
    ))
left_foot = avg(lf, Vector((cx + W * 0.12, cy, minz + 0.02)))
right_foot = avg(rf, Vector((cx - W * 0.12, cy, minz + 0.02)))

# --- SD proportions (chibi, SHORT legs) ---
# measured head height
head_h = max(head_top - head_bot, H * 0.28)
# IMPORTANT: lower hips = shorter leg bones (distance hip→foot).
# Adult hips ~50%H. Previous SD 36% still long. User wants ~1 head shorter.
# Target legs ~ bottom 22–24% of height (user: hips a bit lower still)
hips_z = pct(0.23)
spine_z = pct(0.37)
chest_z = min(pct(0.50), neck_z - H * 0.12)
# shoulders: lower again (user: a bit more so arm length matches)
shoulder_z = neck_z - H * 0.16
# ensure torso chain goes upward: hips < spine < chest < neck
if chest_z >= neck_z:
    chest_z = neck_z - H * 0.06
if spine_z >= chest_z:
    spine_z = (hips_z + chest_z) * 0.5
# shoulders may be below neck (side of chest) — clamp to chest band
if shoulder_z > neck_z - H * 0.04:
    shoulder_z = neck_z - H * 0.10
if shoulder_z < chest_z:
    # allow shoulders slightly below chest joint for chibi hoodie
    pass
# chest joint for shoulder parent should not be above shoulders
if chest_z > shoulder_z:
    chest_z = shoulder_z - H * 0.02
    if chest_z <= spine_z:
        spine_z = (hips_z + chest_z) * 0.5

# T-pose: outer silhouette at shoulder height is HANDS, not shoulders.
# Place shoulders from torso width (central mass), not max X.
torso_band = [v for v in vs if shoulder_z - H * 0.08 <= v.z <= shoulder_z + H * 0.02 and abs(v.x - cx) < W * 0.28]
if torso_band:
    torso_half = 0.5 * (max(v.x for v in torso_band) - min(v.x for v in torso_band))
else:
    torso_half = W * 0.18
left_sh = Vector((cx + torso_half * 0.95, cy, shoulder_z))
right_sh = Vector((cx - torso_half * 0.95, cy, shoulder_z))

# hands: outermost mesh X near shoulder height (T-pose)
hand_band = [v for v in vs if abs(v.z - shoulder_z) < H * 0.12]
if not hand_band:
    hand_band = [v for v in vs if pct(0.45) <= v.z <= pct(0.72)]
lh = [v for v in hand_band if v.x >= cx]
rh = [v for v in hand_band if v.x < cx]
# take extreme 5% by |x|
if lh:
    lh_sorted = sorted(lh, key=lambda v: v.x, reverse=True)
    lh_tip = lh_sorted[: max(8, len(lh_sorted) // 12)]
    left_hand = avg(lh_tip, Vector((maxx, cy, shoulder_z)))
else:
    left_hand = Vector((maxx, cy, shoulder_z))
if rh:
    rh_sorted = sorted(rh, key=lambda v: v.x)
    rh_tip = rh_sorted[: max(8, len(rh_sorted) // 12)]
    right_hand = avg(rh_tip, Vector((minx, cy, shoulder_z)))
else:
    right_hand = Vector((minx, cy, shoulder_z))
# horizontal T-pose lock
left_hand = Vector((max(left_hand.x, left_sh.x + W * 0.18), cy, shoulder_z))
right_hand = Vector((min(right_hand.x, right_sh.x - W * 0.18), cy, shoulder_z))
# shoulders slightly inward from hands
left_sh = Vector((min(left_sh.x, left_hand.x - W * 0.12), cy, shoulder_z))
right_sh = Vector((max(right_sh.x, right_hand.x + W * 0.12), cy, shoulder_z))

# elbows 50% along arm, keep horizontal
left_elbow = Vector((left_sh.x * 0.5 + left_hand.x * 0.5, cy, shoulder_z))
right_elbow = Vector((right_sh.x * 0.5 + right_hand.x * 0.5, cy, shoulder_z))

# short stubby legs: hip low, ankle near ground
left_hip_j = Vector((cx + W * 0.10, cy, hips_z))
right_hip_j = Vector((cx - W * 0.10, cy, hips_z))
left_ankle = Vector((left_foot.x, left_foot.y, minz + H * 0.06))
right_ankle = Vector((right_foot.x, right_foot.y, minz + H * 0.06))
left_knee = (left_hip_j + left_ankle) * 0.5
right_knee = (right_hip_j + right_ankle) * 0.5
left_foot_tip = Vector((left_foot.x, left_foot.y - W * 0.05, minz + 0.01))
right_foot_tip = Vector((right_foot.x, right_foot.y - W * 0.05, minz + 0.01))

hips = Vector((cx, cy, hips_z))
spine = Vector((cx, cy, spine_z))
chest = Vector((cx, cy, chest_z))

# Head bone: LARGE — from neck through top of head (SD)
head_bone_head = neck
head_bone_tail = Vector((hx, hy, head_top - H * 0.01))

def bone(name, head, tail, parent):
    if (Vector(tail) - Vector(head)).length < 0.008:
        tail = Vector(head) + Vector((0, 0, 0.02))
    return (name, Vector(head), Vector(tail), parent)

bones_def = [
    bone("Hips", hips, hips + Vector((0, 0, H * 0.05)), None),
    bone("Spine", hips + Vector((0, 0, H * 0.05)), spine, "Hips"),
    bone("Chest", spine, chest, "Spine"),
    bone("Neck", chest, neck, "Chest"),
    bone("Head", head_bone_head, head_bone_tail, "Neck"),
    bone("LeftShoulder", chest, left_sh, "Chest"),
    bone("LeftUpperArm", left_sh, left_elbow, "LeftShoulder"),
    bone("LeftLowerArm", left_elbow, left_hand, "LeftUpperArm"),
    bone("LeftHand", left_hand, left_hand + Vector((W * 0.03, 0, -H * 0.01)), "LeftLowerArm"),
    bone("RightShoulder", chest, right_sh, "Chest"),
    bone("RightUpperArm", right_sh, right_elbow, "RightShoulder"),
    bone("RightLowerArm", right_elbow, right_hand, "RightUpperArm"),
    bone("RightHand", right_hand, right_hand + Vector((-W * 0.03, 0, -H * 0.01)), "RightLowerArm"),
    bone("LeftUpperLeg", left_hip_j, left_knee, "Hips"),
    bone("LeftLowerLeg", left_knee, left_ankle, "LeftUpperLeg"),
    bone("LeftFoot", left_ankle, left_foot_tip, "LeftLowerLeg"),
    bone("RightUpperLeg", right_hip_j, right_knee, "Hips"),
    bone("RightLowerLeg", right_knee, right_ankle, "RightUpperLeg"),
    bone("RightFoot", right_ankle, right_foot_tip, "RightLowerLeg"),
]

bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm_obj = bpy.context.view_layer.objects.active
arm_obj.name = "Armature"
arm = arm_obj.data
for b in list(arm.edit_bones):
    arm.edit_bones.remove(b)
created = {}
for name, head, tail, parent in bones_def:
    eb = arm.edit_bones.new(name)
    eb.head = head
    eb.tail = tail
    # thicker display for chibi head
    eb.roll = 0
    if parent and parent in created:
        eb.parent = created[parent]
        eb.use_connect = False
    created[name] = eb
# make head bone display longer already set
bpy.ops.object.mode_set(mode="OBJECT")
arm_obj.show_in_front = True
arm_obj.data.display_type = "OCTAHEDRAL"
try:
    arm_obj.data.bone_display_type = "OCTAHEDRAL"
except Exception:
    pass

# --- skin: nearest-bone (reliable for blob mesh) ---
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
bpy.context.view_layer.objects.active = main
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm_obj
main.parent = arm_obj

arm_mw = arm_obj.matrix_world
samples = []
for b in arm.bones:
    h = arm_mw @ b.head_local
    t = arm_mw @ b.tail_local
    mid = (h + t) * 0.5
    # weight head bone more for upper verts: longer samples
    samples.append((b.name, h, mid, t))
    main.vertex_groups.new(name=b.name)

mw = main.matrix_world
# dual assign: primary + secondary soft for smoother deform
for vi, v in enumerate(main.data.vertices):
    wco = mw @ v.co
    dists = []
    for name, h, mid, t in samples:
        d = min((wco - h).length, (wco - mid).length, (wco - t).length)
        # bias: if in head region, strongly prefer Head bone
        if name == "Head" and wco.z >= neck_z - H * 0.02:
            d *= 0.35
        if name in ("LeftFoot", "RightFoot", "LeftLowerLeg", "RightLowerLeg") and wco.z < pct(0.25):
            d *= 0.7
        dists.append((d, name))
    dists.sort(key=lambda x: x[0])
    d0, n0 = dists[0]
    d1, n1 = dists[1]
    # soft blend
    if d1 < 1e-6:
        w0, w1 = 1.0, 0.0
    else:
        inv0 = 1.0 / max(d0, 1e-4)
        inv1 = 1.0 / max(d1, 1e-4)
        s = inv0 + inv1
        w0, w1 = inv0 / s, inv1 / s
        if w0 < 0.55:
            w0, w1 = 0.75, 0.25
    main.vertex_groups[n0].add([vi], w0, "REPLACE")
    if w1 > 0.05:
        main.vertex_groups[n1].add([vi], w1, "REPLACE")

if main.data.shape_keys is None:
    main.shape_key_add(name="Basis", from_mix=False)
for key in ["A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun"]:
    if key not in main.data.shape_keys.key_blocks:
        main.shape_key_add(name=key, from_mix=False)

# report measured heads-tall
heads_tall = H / max(head_h, 0.01)

# preview cam
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
cam.location = (center.x, center.y - max(height * 2.2, 3.4), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam
ld = bpy.data.lights.new("Key", "AREA")
ld.energy = 450
ld.size = 1.6
lo = bpy.data.objects.new("Key", ld)
bpy.context.scene.collection.objects.link(lo)
lo.location = (center.x + 1.3, center.y - 2.0, center.z + 1.4)

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
arm_obj.hide_render = False
arm_obj.show_in_front = True

# export with context override for Blender 5.x
window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj

with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=arm_obj, selected_objects=[main, arm_obj]):
    bpy.ops.export_scene.gltf(filepath=temp, export_format="GLB", use_selection=True, export_apply=True)
    try:
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)
    except Exception:
        pass
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

# bone summary
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")
bone_info = {}
for b in arm.edit_bones:
    bone_info[b.name] = {
        "head_z": round(b.head.z, 3),
        "tail_z": round(b.tail.z, 3),
        "len": round((b.tail - b.head).length, 3),
    }
bpy.ops.object.mode_set(mode="OBJECT")

weighted = sum(1 for v in main.data.vertices if v.groups)
result = {
    "status": "ok",
    "style": "SD_3head",
    "height": round(H, 3),
    "head_height": round(head_h, 3),
    "heads_tall": round(heads_tall, 2),
    "head_top": round(head_top, 3),
    "neck_z": round(neck_z, 3),
    "hips_z": round(hips_z, 3),
    "head_bone_len": round((head_bone_tail - head_bone_head).length, 3),
    "leg_len_L": round((left_hip_j - left_ankle).length, 3),
    "bones": bone_info,
    "vertex_groups": len(main.vertex_groups),
    "weighted": weighted,
    "total_verts": len(main.data.vertices),
    "vrm_status": vrm_status,
}
"""
    for k, v in {
        "__SRC__": paths["src"],
        "__BLEND__": paths["blend"],
        "__VRM__": paths["vrm"],
        "__VRM2__": paths["vrm2"],
        "__TEMP__": paths["temp"],
        "__FBX__": paths["fbx"],
        "__RENDER__": paths["render"],
    }.items():
        code = code.replace(k, v)

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4500])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] SD refit failed")
        return 1

    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("[OK glb]", GLB.stat().st_size)
    if RENDER_TMP.is_file():
        shutil.copyfile(RENDER_TMP, RENDER_DST)
        print("[OK render]")
    print(
        f"[SD rig] heads_tall={payload.get('heads_tall')} "
        f"head_bone={payload.get('head_bone_len')} "
        f"hips_z={payload.get('hips_z')} "
        f"weighted={payload.get('weighted')}/{payload.get('total_verts')} "
        f"vrm={payload.get('vrm_status')}"
    )
    print("[bones z]", json.dumps(payload.get("bones"), ensure_ascii=False)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
