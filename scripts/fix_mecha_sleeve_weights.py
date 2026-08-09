#!/usr/bin/env python3
"""
Separate sleeve weights from hoodie torso so arms raise without dragging cloth.
HEAD region is hard-locked (previous melt bug must not return).
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
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sleeve.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_sleeve.glb")


def main() -> int:
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
vs_w = [mw @ v.co for v in main.data.vertices]
xs = [v.x for v in vs_w]
zs = [v.z for v in vs_w]
ys = [v.y for v in vs_w]
minx, maxx = min(xs), max(xs)
minz, maxz = min(zs), max(zs)
W = maxx - minx
H = maxz - minz
cx = (minx + maxx) * 0.5

arm_mw = arm.matrix_world
hb = arm.data.bones.get("Head")
nb = arm.data.bones.get("Neck")
head_bot = (arm_mw @ hb.head_local).z if hb else (minz + H * 0.58)
neck_z = (arm_mw @ nb.tail_local).z if nb else head_bot

# head sphere from mesh
head_pts = [v for v in vs_w if v.z >= neck_z - H * 0.02]
hcx = sum(v.x for v in head_pts) / len(head_pts)
hcy = sum(v.y for v in head_pts) / len(head_pts)
hcz = sum(v.z for v in head_pts) / len(head_pts)
dists = sorted(((v.x-hcx)**2+(v.y-hcy)**2+(v.z-hcz)**2)**0.5 for v in head_pts)
head_r = dists[int(len(dists)*0.90)] * 1.06

# arm bone chains world samples
def bone_chain_pts(names):
    pts = []
    for n in names:
        b = arm.data.bones.get(n)
        if not b:
            continue
        h = arm_mw @ b.head_local
        t = arm_mw @ b.tail_local
        pts.append((n, h, (h+t)*0.5, t))
    return pts

chain_L = bone_chain_pts(["LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand"])
chain_R = bone_chain_pts(["RightShoulder","RightUpperArm","RightLowerArm","RightHand"])
torso_bones = bone_chain_pts(["Hips","Spine","Chest","Neck"])
leg_L = bone_chain_pts(["LeftUpperLeg","LeftLowerLeg","LeftFoot"])
leg_R = bone_chain_pts(["RightUpperLeg","RightLowerLeg","RightFoot"])

# shoulder joint height / lateral for sleeve cylinder
l_ua = arm.data.bones.get("LeftUpperArm")
r_ua = arm.data.bones.get("RightUpperArm")
l_sh_w = arm_mw @ l_ua.head_local if l_ua else Vector((cx+W*0.3, 0, neck_z-H*0.15))
r_sh_w = arm_mw @ r_ua.head_local if r_ua else Vector((cx-W*0.3, 0, neck_z-H*0.15))
l_hand = arm.data.bones.get("LeftHand")
r_hand = arm.data.bones.get("RightHand")
l_hand_w = arm_mw @ l_hand.tail_local if l_hand else Vector((maxx, 0, minz+H*0.3))
r_hand_w = arm_mw @ r_hand.tail_local if r_hand else Vector((minx, 0, minz+H*0.3))

def dist_to_segment(p, a, b):
    ab = b - a
    L2 = ab.length_squared
    if L2 < 1e-12:
        return (p - a).length
    u = max(0.0, min(1.0, (p - a).dot(ab) / L2))
    return (p - (a + ab * u)).length

def nearest_chain(chain, wco):
    best, bd, bn = None, 1e18, None
    for n, h, m, t in chain:
        d = min((wco-h).length, (wco-m).length, (wco-t).length)
        if d < bd:
            bd, best, bn = d, n, n
    return best, bd

main.vertex_groups.clear()
for b in arm.data.bones:
    main.vertex_groups.new(name=b.name)

counts = {{"head":0,"arm_l":0,"arm_r":0,"torso":0,"leg_l":0,"leg_r":0,"armpit":0}}

for vi, v in enumerate(main.data.vertices):
    wco = mw @ v.co
    lat = abs(wco.x - cx) / max(W*0.5, 1e-6)
    th = (wco.z - minz) / max(H, 1e-6)
    side_L = wco.x >= cx
    d_head = ((wco.x-hcx)**2+(wco.y-hcy)**2+(wco.z-hcz)**2)**0.5

    # --- HEAD lock (never arms) ---
    if d_head <= head_r and wco.z >= neck_z - H*0.05:
        main.vertex_groups["Head"].add([vi], 1.0, "REPLACE")
        if wco.z < neck_z + H*0.03 and "Neck" in main.vertex_groups:
            main.vertex_groups["Neck"].add([vi], 0.06, "ADD")
        counts["head"] += 1
        continue

    # --- legs ---
    if th < 0.27 and lat < 0.55:
        chain = leg_L if side_L else leg_R
        n0, _ = nearest_chain(chain, wco)
        main.vertex_groups[n0 or "Hips"].add([vi], 1.0, "REPLACE")
        counts["leg_l" if side_L else "leg_r"] += 1
        continue

    # --- sleeve cylinder test: distance to shoulder→hand bone line ---
    if side_L:
        d_line = dist_to_segment(wco, l_sh_w, l_hand_w)
        chain = chain_L
    else:
        d_line = dist_to_segment(wco, r_sh_w, r_hand_w)
        chain = chain_R

    # sleeve if close to arm line AND below neck AND not head
    below_neck = wco.z < neck_z - H*0.02
    # arm tube radius scales with body
    tube_r = W * 0.14
    tube_r_loose = W * 0.20
    on_arm_line = d_line < tube_r and below_neck and th > 0.20 and th < 0.70
    near_arm_line = d_line < tube_r_loose and below_neck and th > 0.22 and th < 0.68 and lat > 0.28

    if on_arm_line or (near_arm_line and lat > 0.40):
        n0, _ = nearest_chain(chain, wco)
        n0 = n0 or ("LeftUpperArm" if side_L else "RightUpperArm")
        # pure arm on tight tube
        if d_line < tube_r * 0.85 and lat > 0.34:
            main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
            counts["arm_l" if side_L else "arm_r"] += 1
        else:
            # armpit: mostly arm, tiny chest so cloth doesn't glue
            main.vertex_groups[n0].add([vi], 0.92, "REPLACE")
            if "Chest" in main.vertex_groups:
                main.vertex_groups["Chest"].add([vi], 0.08, "REPLACE")
            counts["armpit"] += 1
        continue

    # lateral hoodie side panels: still prefer arm if very outer mid-height
    if below_neck and lat > 0.52 and 0.28 < th < 0.62 and d_head > head_r * 1.2:
        n0, _ = nearest_chain(chain, wco)
        n0 = n0 or ("LeftUpperArm" if side_L else "RightUpperArm")
        main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
        counts["arm_l" if side_L else "arm_r"] += 1
        continue

    # --- torso / hoodie body: NO arm weights ---
    n0, _ = nearest_chain(torso_bones, wco)
    if n0 is None or n0 == "Head":
        if th > 0.55:
            n0 = "Chest"
        elif th > 0.38:
            n0 = "Spine"
        else:
            n0 = "Hips"
    # armpit cloth on body: stay on chest only (do not add arm)
    main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
    counts["torso"] += 1

# armature
for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
main.parent = arm

# verify no head contamination
head_bad = 0
head_ok = 0
arm_names = {{"LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand","RightShoulder","RightUpperArm","RightLowerArm","RightHand"}}
for vi, v in enumerate(main.data.vertices):
    wco = mw @ v.co
    d_head = ((wco.x-hcx)**2+(wco.y-hcy)**2+(wco.z-hcz)**2)**0.5
    if d_head <= head_r and wco.z >= neck_z - H*0.05:
        gset = {{main.vertex_groups[g.group].name for g in main.data.vertices[vi].groups}}
        if gset & arm_names:
            head_bad += 1
        else:
            head_ok += 1

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

result = {{
    "status": "ok",
    "counts": counts,
    "head_ok": head_ok,
    "head_bad": head_bad,
    "tube_r": round(tube_r, 4),
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
        return 1
    if TEMP_VRM.is_file():
        shutil.copyfile(TEMP_VRM, VRM)
        shutil.copyfile(TEMP_VRM, VRM2)
        print("[OK vrm]", VRM.stat().st_size)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB)
        print("[OK glb]")
    print("counts", payload.get("counts"), "head_ok", payload.get("head_ok"), "head_bad", payload.get("head_bad"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
