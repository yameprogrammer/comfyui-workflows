#!/usr/bin/env python3
"""
Restore user arm bone edits (from session review snapshot), snap forearm/hand
into mesh centerline, save blend, re-export VRM — without discarding arm fix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3.blend"
BLEND_RIGGED = EXPORTS / "mecha_patlabor_v3_rigged.blend"
# User-edit snapshot captured during review (before VRM export overwrite)
USER_ARM = {
    "LeftShoulder": {"head": (0.125, 0.0, 1.006), "tail": (0.299, 0.0, 0.984)},
    "LeftUpperArm": {"head": (0.3, 0.0, 0.983), "tail": (0.458, 0.0, 0.964)},
    "LeftLowerArm": {"head": (0.458, 0.0, 0.964), "tail": (0.553, 0.0, 0.925)},
    "LeftHand": {"head": (0.551, 0.0, 0.924), "tail": (0.59, 0.0, 0.903)},
    "RightShoulder": {"head": (-0.126, 0.0, 1.002), "tail": (-0.299, 0.0, 0.969)},
    "RightUpperArm": {"head": (-0.301, 0.0, 0.969), "tail": (-0.459, 0.0, 0.938)},
    "RightLowerArm": {"head": (-0.461, 0.0, 0.938), "tail": (-0.563, 0.011, 0.911)},
    "RightHand": {"head": (-0.567, 0.011, 0.91), "tail": (-0.608, 0.009, 0.892)},
}


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "blend_rigged": str(BLEND_RIGGED).replace("\\", "/"),
        "vrm": str(EXPORTS / "mecha_patlabor_v3.vrm").replace("\\", "/"),
        "vrm_warudo": str(EXPORTS / "mecha_patlabor_v3_warudo.vrm").replace("\\", "/"),
        "glb_warudo": str(EXPORTS / "mecha_patlabor_v3_warudo.glb").replace("\\", "/"),
        "r_fit": str(EXPORTS / "viewport_arm_refit.png").replace("\\", "/"),
        "r_raise": str(EXPORTS / "viewport_arm_refit_raise.png").replace("\\", "/"),
        "user_arm": USER_ARM,
    }

    code = f'''
import bpy
import math
import addon_utils
import shutil
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree
import bmesh
from pathlib import Path

paths = {repr(paths)}
user_arm = paths["user_arm"]
log = []

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# rest pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)

# --- edit mode: restore user arm bones ---
win = bpy.context.window_manager.windows[0]
area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

def mode_set(mode):
    for o in bpy.data.objects:
        o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(window=win, area=area, region=region, active_object=arm, object=arm, selected_editable_objects=[arm]):
        bpy.ops.object.mode_set(mode=mode)

mode_set("EDIT")
eb = arm.data.edit_bones

# apply user snapshot first
for name, ht in user_arm.items():
    b = eb.get(name)
    if not b:
        log.append(f"missing {{name}}")
        continue
    b.head = Vector(ht["head"])
    b.tail = Vector(ht["tail"])
    log.append(f"restore {{name}}")

# reconnect chain head-to-tail after restore
for side in ("Left", "Right"):
    sh, ua, la, ha = eb[f"{{side}}Shoulder"], eb[f"{{side}}UpperArm"], eb[f"{{side}}LowerArm"], eb[f"{{side}}Hand"]
    ua.head = sh.tail.copy()
    la.head = ua.tail.copy()
    ha.head = la.tail.copy()
    # keep parent
    ua.parent = sh
    la.parent = ua
    ha.parent = la
    sh.parent = eb["Chest"]

# --- snap lower arm + hand into mesh arm centerline ---
mw = main.matrix_world
vs = [mw @ v.co for v in main.data.vertices]

def side_arm_verts(side, z0, z1, x_min=None, x_max=None):
    out = []
    for p in vs:
        if not (z0 <= p.z <= z1):
            continue
        if side == "Left" and p.x < 0.15:
            continue
        if side == "Right" and p.x > -0.15:
            continue
        if x_min is not None and p.x < x_min:
            continue
        if x_max is not None and p.x > x_max:
            continue
        out.append(p)
    return out

def centroid(pts):
    return sum(pts, Vector()) / len(pts)

def refine_forearm(side):
    ua = eb[f"{{side}}UpperArm"]
    la = eb[f"{{side}}LowerArm"]
    ha = eb[f"{{side}}Hand"]
    elbow = ua.tail.copy()  # elbow joint
    # mesh samples along forearm region: from elbow x toward hand
    if side == "Left":
        band = [p for p in vs if p.x >= elbow.x - 0.02 and p.x <= elbow.x + 0.28 and abs(p.z - elbow.z) < 0.18 and p.z > 0.75]
    else:
        band = [p for p in vs if p.x <= elbow.x + 0.02 and p.x >= elbow.x - 0.28 and abs(p.z - elbow.z) < 0.18 and p.z > 0.75]
    if len(band) < 30:
        log.append(f"{{side}} forearm band small {{len(band)}}")
        return
    # wrist = outer extreme of band but not past hand mesh tip; use 92nd percentile x
    xs = sorted(p.x for p in band)
    if side == "Left":
        wx = xs[int(len(xs) * 0.88)]
        wrist_pts = [p for p in band if p.x >= wx - 0.03]
    else:
        wx = xs[int(len(xs) * 0.12)]
        wrist_pts = [p for p in band if p.x <= wx + 0.03]
    wrist = centroid(wrist_pts) if wrist_pts else centroid(band)
    # mid forearm for slight curve
    if side == "Left":
        mid_pts = [p for p in band if abs(p.x - (elbow.x + wrist.x) * 0.5) < 0.04]
    else:
        mid_pts = [p for p in band if abs(p.x - (elbow.x + wrist.x) * 0.5) < 0.04]
    mid = centroid(mid_pts) if mid_pts else elbow.lerp(wrist, 0.5)
    # keep bone on y~arm center (cy of samples)
    cy = sum(p.y for p in band) / len(band)
    elbow.y = cy
    mid.y = cy
    wrist.y = cy
    # place lower arm elbow -> wrist (slightly short of tip so hand bone stays in hand)
    la.head = elbow
    la.tail = wrist
    # hand: short bone from wrist into hand mass
    if side == "Left":
        hand_pts = [p for p in vs if p.x >= wrist.x - 0.01 and p.x <= wrist.x + 0.12 and abs(p.z - wrist.z) < 0.12]
        tip = max(hand_pts, key=lambda p: p.x) if hand_pts else wrist + Vector((0.04, 0, 0))
    else:
        hand_pts = [p for p in vs if p.x <= wrist.x + 0.01 and p.x >= wrist.x - 0.12 and abs(p.z - wrist.z) < 0.12]
        tip = min(hand_pts, key=lambda p: p.x) if hand_pts else wrist + Vector((-0.04, 0, 0))
    if hand_pts:
        hc = centroid(hand_pts)
        tip = wrist.lerp(hc, 0.85)
        tip.y = sum(p.y for p in hand_pts) / len(hand_pts)
    ha.head = la.tail.copy()
    # short hand bone toward tip but keep length ~3-5cm inside
    direction = (tip - ha.head)
    if direction.length < 0.02:
        direction = Vector((0.04 if side == "Left" else -0.04, 0, 0))
    ha.tail = ha.head + direction.normalized() * min(0.045, max(0.03, direction.length * 0.5))
    log.append(f"{{side}} forearm refined len={{la.length:.3f}} hand_len={{(ha.tail-ha.head).length:.3f}}")

refine_forearm("Left")
refine_forearm("Right")

# ensure upper arm tail = lower arm head
for side in ("Left", "Right"):
    eb[f"{{side}}UpperArm"].tail = eb[f"{{side}}LowerArm"].head.copy()
    eb[f"{{side}}LowerArm"].head = eb[f"{{side}}UpperArm"].tail.copy()
    eb[f"{{side}}Hand"].head = eb[f"{{side}}LowerArm"].tail.copy()

# snapshot
bone_info = {{
    b.name: {{
        "head": [round(b.head.x, 3), round(b.head.y, 3), round(b.head.z, 3)],
        "tail": [round(b.tail.x, 3), round(b.tail.y, 3), round(b.tail.z, 3)],
        "len": round((b.tail - b.head).length, 3),
    }}
    for b in eb if any(k in b.name for k in ("Shoulder", "Arm", "Hand"))
}}

mode_set("OBJECT")

# measure outside samples for lower arms
deps = bpy.context.evaluated_depsgraph_get()
obj_eval = main.evaluated_get(deps)
bm = bmesh.new()
bm.from_object(obj_eval, deps)
bm.transform(main.matrix_world)
bmesh.ops.triangulate(bm, faces=bm.faces)
bvh = BVHTree.FromBMesh(bm)

def outside_ratio(name):
    b = arm.data.bones[name]
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    out = 0
    n = 12
    for i in range(n + 1):
        p = h.lerp(t, i / n)
        loc, nrm, idx, dist = bvh.find_nearest(p)
        if loc is None:
            out += 1
            continue
        to_p = p - loc
        if nrm is not None and to_p.length > 1e-6 and nrm.dot(to_p.normalized()) > 0.2 and dist > 0.012:
            out += 1
    return out, n + 1

fit = {{}}
for n in ("LeftLowerArm", "LeftHand", "RightLowerArm", "RightHand", "LeftUpperArm", "RightUpperArm"):
    o, t = outside_ratio(n)
    fit[n] = {{"outside": o, "total": t}}
bm.free()

# --- save blend FIRST so we don't lose work ---
bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
shutil.copyfile(paths["blend"], paths["blend_rigged"])
log.append("blend saved with arm fix")

# renders
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.hide_render = False
arm.show_in_front = True
cam = bpy.context.scene.camera
if not cam:
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bb, Vector()) / 8
cam.location = (center.x + 0.15, center.y - 2.5, center.z + 0.3)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.resolution_x = 1024
scene.render.resolution_y = 1280
scene.render.film_transparent = True
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass
scene.render.filepath = paths["r_fit"]
bpy.ops.render.render(write_still=True)

# raise pose test
def world_rot(pb, axis, deg):
    pb.rotation_mode = "QUATERNION"
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest = pb.matrix.copy()
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    head = rest.translation
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ rest
    bpy.context.view_layer.update()

for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion((1,0,0,0))
world_rot(arm.pose.bones["LeftUpperArm"], "Y", -80)
world_rot(arm.pose.bones["RightUpperArm"], "Y", 80)
scene.render.filepath = paths["r_raise"]
bpy.ops.render.render(write_still=True)
# reset
for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion((1,0,0,0))
bpy.context.view_layer.update()

# --- VRM export from CURRENT scene (no reload that would drop arms) ---
ext = arm.data.vrm_addon_extension
try:
    for val in ("1.0", getattr(ext, "SPEC_VERSION_VRM1", None)):
        if val is None:
            continue
        try:
            ext.spec_version = val
            break
        except Exception:
            pass
except Exception as e:
    log.append(f"spec {{e}}")

vrm1_map = {{
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
    "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm", "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
    "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm", "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
    "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg", "left_foot": "LeftFoot",
    "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg", "right_foot": "RightFoot",
}}
try:
    hb = ext.vrm1.humanoid.human_bones
    if hasattr(hb, "filter_by_human_bone_hierarchy"):
        hb.filter_by_human_bone_hierarchy = False
    if hasattr(hb, "allow_non_humanoid_rig"):
        hb.allow_non_humanoid_rig = True
    for prop, bone in vrm1_map.items():
        slot = getattr(hb, prop, None)
        if slot and slot.node and bone in arm.data.bones:
            slot.node.bone_name = bone
except Exception as e:
    log.append(f"vrm1 {{e}}")
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.1"
except Exception:
    pass

# export glb + vrm
for o in bpy.data.objects:
    o.select_set(o in (arm, main))
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(window=win, area=area, region=region, scene=scene, active_object=arm, selected_objects=[arm, main]):
    bpy.ops.export_scene.gltf(
        filepath=paths["glb_warudo"], export_format="GLB", use_selection=True,
        export_apply=False, export_skins=True, export_morph=True,
    )
    r = bpy.ops.export_scene.vrm(
        filepath=paths["vrm"], ignore_warning=True, check_existing=False,
        armature_object_name=arm.name, export_all_influences=True,
    )
    log.append(f"vrm_export={{list(r) if r else None}}")

vrm_size = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
if vrm_size > 1000:
    shutil.copyfile(paths["vrm"], paths["vrm_warudo"])
    # also write canonical name if different
    log.append(f"vrm_ok size={{vrm_size}}")
else:
    log.append("vrm_failed")

# save again after export (still has fixed arms)
bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
shutil.copyfile(paths["blend"], paths["blend_rigged"])

result = {{
    "status": "ok" if vrm_size > 1000 else "partial",
    "log": log,
    "bones": bone_info,
    "fit": fit,
    "vrm_size": vrm_size,
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:10000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not isinstance(payload, dict):
        return 1
    # copy vrm to mecha_patlabor_v3.vrm if warudo written
    warudo = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
    main_vrm = EXPORTS / "mecha_patlabor_v3.vrm"
    # export wrote to paths["vrm"] which is mecha_patlabor_v3.vrm
    if main_vrm.is_file() and main_vrm.stat().st_size > 1000:
        shutil = __import__("shutil")
        shutil.copyfile(main_vrm, warudo)
        print("[OK VRM]", main_vrm, main_vrm.stat().st_size)
        print("[OK VRM warudo]", warudo, warudo.stat().st_size)
    return 0 if payload.get("status") in ("ok", "partial") else 1


if __name__ == "__main__":
    raise SystemExit(main())
