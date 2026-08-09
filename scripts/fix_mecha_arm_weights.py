#!/usr/bin/env python3
"""
Reweight arms vs hoodie WITHOUT breaking the head.

Previous pass assigned side-of-head verts to arm bones (lat>0.32, t<0.70)
→ head "melted" in Warudo. This version hard-locks Head region first.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_armfix.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_armfix.glb")


def main() -> int:
    if not BLEND.is_file():
        print("missing", BLEND)
        return 1

    p = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP_VRM).replace("\\", "/"),
        "glb": str(TEMP_GLB).replace("\\", "/"),
    }

    code = f'''
import bpy
import addon_utils
from mathutils import Vector

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

blend = r"{p['blend']}"
vrm_path = r"{p['vrm']}"
glb_path = r"{p['glb']}"

bpy.ops.wm.open_mainfile(filepath=blend)
main = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

mw = main.matrix_world
vs = [mw @ v.co for v in main.data.vertices]
xs = [v.x for v in vs]
zs = [v.z for v in vs]
minx, maxx = min(xs), max(xs)
minz, maxz = min(zs), max(zs)
W = maxx - minx
H = maxz - minz
cx = (minx + maxx) * 0.5
cy = sum(v.y for v in vs) / len(vs)

arm_mw = arm.matrix_world
# Head bone world span
hb = arm.data.bones.get("Head")
nb = arm.data.bones.get("Neck")
if hb:
    head_bot = (arm_mw @ hb.head_local).z
    head_top = (arm_mw @ hb.tail_local).z
else:
    head_bot = minz + H * 0.58
    head_top = maxz
if nb:
    neck_z = (arm_mw @ nb.tail_local).z
else:
    neck_z = head_bot

# Head center / radius from mesh top blob (verts above neck)
head_pts = [v for v in vs if v.z >= neck_z - H * 0.02]
if not head_pts:
    head_pts = [v for v in vs if v.z >= minz + H * 0.55]
hcx = sum(v.x for v in head_pts) / len(head_pts)
hcy = sum(v.y for v in head_pts) / len(head_pts)
hcz = sum(v.z for v in head_pts) / len(head_pts)
dists = sorted(((v.x-hcx)**2 + (v.y-hcy)**2 + (v.z-hcz)**2)**0.5 for v in head_pts)
head_r = dists[int(len(dists) * 0.90)] * 1.08  # slightly generous

bone_pts = {{}}
for b in arm.data.bones:
    h = arm_mw @ b.head_local
    t = arm_mw @ b.tail_local
    bone_pts[b.name] = (h, (h+t)*0.5, t)

ARM_L = ["LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand"]
ARM_R = ["RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand"]
TORSO = ["Hips", "Spine", "Chest", "Neck"]
LEG_L = ["LeftUpperLeg", "LeftLowerLeg", "LeftFoot"]
LEG_R = ["RightUpperLeg", "RightLowerLeg", "RightFoot"]

def nearest_in(names, wco):
    best, bd = None, 1e18
    for n in names:
        if n not in bone_pts:
            continue
        h, m, t = bone_pts[n]
        d = min((wco-h).length, (wco-m).length, (wco-t).length)
        if d < bd:
            bd, best = d, n
    return best, bd

main.vertex_groups.clear()
for b in arm.data.bones:
    main.vertex_groups.new(name=b.name)

counts = {{"head": 0, "neck": 0, "arm_l": 0, "arm_r": 0, "torso": 0, "leg_l": 0, "leg_r": 0}}

for vi, vloc in enumerate(main.data.vertices):
    wco = mw @ vloc.co
    lat = abs(wco.x - cx) / max(W * 0.5, 1e-6)
    t = (wco.z - minz) / max(H, 1e-6)
    side_L = wco.x >= cx
    dist_head = ((wco.x - hcx)**2 + (wco.y - hcy)**2 + (wco.z - hcz)**2) ** 0.5

    # 1) HARD head lock — never give head verts to arms
    in_head_sphere = dist_head <= head_r and wco.z >= neck_z - H * 0.04
    in_head_height = wco.z >= neck_z - H * 0.01
    if in_head_sphere or (in_head_height and lat < 0.55):
        main.vertex_groups["Head"].add([vi], 1.0, "REPLACE")
        # tiny neck blend only at bottom of head
        if wco.z < neck_z + H * 0.04 and "Neck" in main.vertex_groups:
            main.vertex_groups["Neck"].add([vi], 0.08, "ADD")
        counts["head"] += 1
        continue

    # 2) neck ring
    if neck_z - H * 0.06 <= wco.z <= neck_z + H * 0.03 and lat < 0.35:
        main.vertex_groups["Neck"].add([vi], 0.75, "REPLACE")
        if "Chest" in main.vertex_groups:
            main.vertex_groups["Chest"].add([vi], 0.25, "REPLACE")
        counts["neck"] += 1
        continue

    # 3) legs
    if t < 0.28 and lat < 0.55:
        names = LEG_L if side_L else LEG_R
        n0, _ = nearest_in(names, wco)
        main.vertex_groups[n0 or "Hips"].add([vi], 1.0, "REPLACE")
        counts["leg_l" if side_L else "leg_r"] += 1
        continue

    # 4) arms — only if clearly NOT head and outer enough
    # exclude anything near head sphere
    if dist_head < head_r * 1.15:
        n0, _ = nearest_in(TORSO, wco)
        if n0 == "Head" or (n0 is None):
            n0 = "Chest"
        main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
        counts["torso"] += 1
        continue

    is_arm = (lat > 0.36 and t < 0.68 and wco.z < neck_z - H * 0.03)
    if is_arm:
        names = ARM_L if side_L else ARM_R
        n0, _ = nearest_in(names, wco)
        n0 = n0 or ("LeftUpperArm" if side_L else "RightUpperArm")
        if lat > 0.48:
            main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
        elif lat > 0.38:
            main.vertex_groups[n0].add([vi], 0.88, "REPLACE")
            if "Chest" in main.vertex_groups:
                main.vertex_groups["Chest"].add([vi], 0.12, "REPLACE")
        else:
            main.vertex_groups[n0].add([vi], 0.60, "REPLACE")
            if "Chest" in main.vertex_groups:
                main.vertex_groups["Chest"].add([vi], 0.40, "REPLACE")
        counts["arm_l" if side_L else "arm_r"] += 1
        continue

    # 5) torso default — never Head for body
    n0, _ = nearest_in(TORSO, wco)
    if n0 is None or n0 == "Head":
        if t > 0.55:
            n0 = "Chest"
        elif t > 0.40:
            n0 = "Spine"
        else:
            n0 = "Hips"
    main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
    counts["torso"] += 1

# armature mod
for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
main.parent = arm

window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm

with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=arm, selected_objects=[main, arm]):
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    vrm_ok = False
    vrm_err = ""
    try:
        bpy.ops.export_scene.vrm(filepath=vrm_path)
        vrm_ok = True
    except Exception as e:
        vrm_err = str(e)

# verify head weights
head_pure = 0
head_contaminated = 0
for vi, vloc in enumerate(main.data.vertices):
    wco = mw @ vloc.co
    dist_head = ((wco.x-hcx)**2+(wco.y-hcy)**2+(wco.z-hcz)**2)**0.5
    if dist_head <= head_r and wco.z >= neck_z - H*0.04:
        gnames = {{main.vertex_groups[g.group].name for g in main.data.vertices[vi].groups}}
        if gnames <= {{"Head", "Neck"}}:
            head_pure += 1
        else:
            head_contaminated += 1

result = {{
    "status": "ok",
    "counts": counts,
    "head_r": round(head_r, 3),
    "neck_z": round(neck_z, 3),
    "head_pure": head_pure,
    "head_contaminated": head_contaminated,
    "vrm_ok": vrm_ok,
    "vrm_err": vrm_err,
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:3000])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR]")
        return 1
    if TEMP_VRM.is_file():
        shutil.copyfile(TEMP_VRM, VRM)
        shutil.copyfile(TEMP_VRM, VRM2)
        print("[OK vrm]", VRM.stat().st_size)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB)
        print("[OK glb]", GLB.stat().st_size)
    print(
        "head_pure", payload.get("head_pure"),
        "head_contaminated", payload.get("head_contaminated"),
        "counts", payload.get("counts"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
