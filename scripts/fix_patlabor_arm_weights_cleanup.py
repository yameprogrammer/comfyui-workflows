#!/usr/bin/env python3
"""Cleanup arm skin weights without moving bones. Re-export Warudo VRM."""

from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3_warudo_rebuild.blend"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_weight_cleanup.vrm")
VERSION = "0.4.3"
WARUDO_CHARS = Path(
    r"G:\SteamLibrary\steamapps\common\Warudo\Warudo_Data\StreamingAssets\Characters"
)


def load_glb(path: Path):
    data = path.read_bytes()
    off = 12
    gltf = bin_chunk = None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off : off + clen]
        off += clen
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            bin_chunk = chunk
    return gltf, bin_chunk


def save_glb(path: Path, gltf, bin_chunk):
    jb = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    chunks = struct.pack("<I4s", len(jb), b"JSON") + jb
    if bin_chunk is not None:
        bb = bin_chunk + b"\x00" * ((4 - len(bin_chunk) % 4) % 4)
        chunks += struct.pack("<I4s", len(bb), b"BIN\x00") + bb
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks)


def postprocess(path: Path):
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i
    remap = {
        "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
        "leftShoulder": "LeftShoulder", "leftUpperArm": "LeftUpperArm",
        "leftLowerArm": "LeftLowerArm", "leftHand": "LeftHand",
        "rightShoulder": "RightShoulder", "rightUpperArm": "RightUpperArm",
        "rightLowerArm": "RightLowerArm", "rightHand": "RightHand",
        "leftUpperLeg": "LeftUpperLeg", "leftLowerLeg": "LeftLowerLeg", "leftFoot": "LeftFoot",
        "rightUpperLeg": "RightUpperLeg", "rightLowerLeg": "RightLowerLeg", "rightFoot": "RightFoot",
    }
    if "VRMC_vrm" in gltf.get("extensions", {}):
        vrm = gltf["extensions"]["VRMC_vrm"]
        hb = vrm.setdefault("humanoid", {}).setdefault("humanBones", {})
        for drop in list(hb.keys()):
            if drop not in remap:
                del hb[drop]
        for k, bone in remap.items():
            if bone in name_to_idx:
                hb[k] = {"node": name_to_idx[bone]}
        meta = vrm.setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = VERSION
        meta["authors"] = ["yameprogrammer"]
        if gltf.get("skins"):
            gltf["skins"][0].pop("skeleton", None)
        gltf.pop("animations", None)
    save_glb(path, gltf, bin_chunk)


def main() -> int:
    code = f'''
import bpy
import addon_utils
from mathutils import Quaternion, Vector, Matrix
from pathlib import Path

for n in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(n, default_set=True, persistent=True)
    except Exception:
        pass

bpy.ops.wm.open_mainfile(filepath=r"{str(BLEND).replace(chr(92), '/')}")
window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
mw = mesh.matrix_world
log = []

def set_mode(m):
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
        bpy.ops.object.mode_set(mode=m)

set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
set_mode("OBJECT")

# bone landmarks
def bhead(name):
    b = arm.data.bones[name]
    return arm.matrix_world @ b.head_local

ball_L = bhead("LeftUpperArm").x   # ~0.16
ball_R = bhead("RightUpperArm").x
elbow_L = bhead("LeftLowerArm").x
elbow_R = bhead("RightLowerArm").x

ARM = {{
    "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
}}
TORSO = {{"Hips", "Spine", "Chest", "Neck", "Head"}}

stripped_head = 0
boosted_torso = 0
sharpened = 0

for v in mesh.data.vertices:
    p = mw @ v.co
    wmap = {{}}
    for g in v.groups:
        wmap[mesh.vertex_groups[g.group].name] = g.weight
    if not wmap:
        continue
    changed = False

    # 1) Head volume: strip arm influence
    if p.z > 1.10 and abs(p.x) < 0.22:
        arm_w = sum(wmap.get(a, 0) for a in ARM)
        if arm_w > 0.02:
            for a in ARM:
                wmap.pop(a, None)
            # ensure head/neck
            if "Head" not in wmap and "Neck" not in wmap:
                wmap["Head"] = 1.0
            stripped_head += 1
            changed = True

    # 2) Torso core: kill outer arm bones (|x| well inside ball)
    if abs(p.x) < 0.10 and 0.70 < p.z < 1.12:
        for a in ("LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand"):
            if wmap.get(a, 0) > 0:
                wmap.pop(a, None)
                changed = True
        # shoulder only tiny
        for a in ("LeftShoulder", "RightShoulder"):
            if wmap.get(a, 0) > 0.15:
                wmap[a] = 0.08
                changed = True
        if changed:
            if sum(wmap.get(t, 0) for t in TORSO) < 0.3:
                wmap["Chest"] = wmap.get("Chest", 0) + 0.7
            boosted_torso += 1

    # 3) Inner shoulder pad (between neck and ball): prefer Shoulder+Chest, not UpperArm
    if 0.95 < p.z < 1.12:
        if 0.08 < p.x < ball_L + 0.02:
            ua = wmap.get("LeftUpperArm", 0)
            if ua > 0.25:
                wmap["LeftUpperArm"] = ua * 0.35
                wmap["LeftShoulder"] = wmap.get("LeftShoulder", 0) + ua * 0.40
                wmap["Chest"] = wmap.get("Chest", 0) + ua * 0.25
                changed = True
                sharpened += 1
        if -ball_L - 0.02 < p.x < -0.08:  # use abs ball
            ua = wmap.get("RightUpperArm", 0)
            if ua > 0.25:
                wmap["RightUpperArm"] = ua * 0.35
                wmap["RightShoulder"] = wmap.get("RightShoulder", 0) + ua * 0.40
                wmap["Chest"] = wmap.get("Chest", 0) + ua * 0.25
                changed = True
                sharpened += 1

    # 4) Outer sleeve past ball: UpperArm owns, reduce Chest/Shoulder drag
    if 0.90 < p.z < 1.12:
        if p.x > ball_L + 0.04:
            ch = wmap.get("Chest", 0)
            if ch > 0.08:
                wmap["Chest"] = ch * 0.15
                wmap["LeftUpperArm"] = wmap.get("LeftUpperArm", 0) + ch * 0.70
                wmap["LeftShoulder"] = wmap.get("LeftShoulder", 0) + ch * 0.15
                changed = True
            # past mid-upperarm: kill shoulder
            if p.x > (ball_L + elbow_L) * 0.5:
                sh = wmap.get("LeftShoulder", 0)
                if sh > 0.05:
                    wmap["LeftShoulder"] = sh * 0.15
                    wmap["LeftUpperArm"] = wmap.get("LeftUpperArm", 0) + sh * 0.85
                    changed = True
        if p.x < ball_R - 0.04:
            ch = wmap.get("Chest", 0)
            if ch > 0.08:
                wmap["Chest"] = ch * 0.15
                wmap["RightUpperArm"] = wmap.get("RightUpperArm", 0) + ch * 0.70
                wmap["RightShoulder"] = wmap.get("RightShoulder", 0) + ch * 0.15
                changed = True
            if p.x < (ball_R + elbow_R) * 0.5:
                sh = wmap.get("RightShoulder", 0)
                if sh > 0.05:
                    wmap["RightShoulder"] = sh * 0.15
                    wmap["RightUpperArm"] = wmap.get("RightUpperArm", 0) + sh * 0.85
                    changed = True

    if not changed:
        continue

    # rewrite groups for this vert
    total = sum(max(0.0, w) for w in wmap.values())
    if total <= 1e-8:
        continue
    # clear all
    for g in list(v.groups):
        mesh.vertex_groups[g.group].remove([v.index])
    for name, wt in wmap.items():
        wt = max(0.0, wt) / total
        if wt < 0.01:
            continue
        if name not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=name)
        mesh.vertex_groups[name].add([v.index], wt, "REPLACE")

log.append(f"stripped_head={{stripped_head}} boosted_torso={{boosted_torso}} sharpened={{sharpened}}")

# ensure armature mod
for m in list(mesh.modifiers):
    if m.type == "ARMATURE":
        mesh.modifiers.remove(m)
am = mesh.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
mworld = mesh.matrix_world.copy()
mesh.parent = arm
mesh.matrix_world = mworld

# preview raise
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
arm.pose.bones["LeftUpperArm"].rotation_mode = "XYZ"
arm.pose.bones["LeftUpperArm"].rotation_euler = (1.15, 0, 0)
arm.pose.bones["RightUpperArm"].rotation_mode = "XYZ"
arm.pose.bones["RightUpperArm"].rotation_euler = (-1.15, 0, 0)
arm.pose.bones["LeftShoulder"].rotation_mode = "XYZ"
arm.pose.bones["LeftShoulder"].rotation_euler = (0.35, 0, 0)
arm.pose.bones["RightShoulder"].rotation_mode = "XYZ"
arm.pose.bones["RightShoulder"].rotation_euler = (-0.35, 0, 0)
set_mode("OBJECT")
bpy.context.view_layer.update()
scene = bpy.context.scene
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.filepath = r"{str(EXPORTS / 'viewport_shoulder_v2_raise_clean.png').replace(chr(92), '/')}"
arm.show_in_front = True
with bpy.context.temp_override(window=window, area=area, region=region):
    try:
        bpy.ops.view3d.view_all(center=True)
    except Exception:
        pass
    try:
        bpy.ops.render.opengl(write_still=True)
    except Exception as e:
        log.append(f"render {{e}}")

# reset pose before export
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
set_mode("OBJECT")

bpy.ops.wm.save_as_mainfile(filepath=r"{str(BLEND).replace(chr(92), '/')}")
try:
    bpy.ops.wm.save_as_mainfile(filepath=r"{str(EXPORTS / 'mecha_patlabor_v3.blend').replace(chr(92), '/')}", copy=True)
except Exception:
    pass

# export VRM
ext = arm.data.vrm_addon_extension
try:
    ext.spec_version = "1.0"
except Exception:
    pass
try:
    hb = ext.vrm1.humanoid.human_bones
    hb.filter_by_human_bone_hierarchy = False
    mapping = {{
        "hips":"Hips","spine":"Spine","chest":"Chest","neck":"Neck","head":"Head",
        "left_shoulder":"LeftShoulder","left_upper_arm":"LeftUpperArm","left_lower_arm":"LeftLowerArm","left_hand":"LeftHand",
        "right_shoulder":"RightShoulder","right_upper_arm":"RightUpperArm","right_lower_arm":"RightLowerArm","right_hand":"RightHand",
        "left_upper_leg":"LeftUpperLeg","left_lower_leg":"LeftLowerLeg","left_foot":"LeftFoot",
        "right_upper_leg":"RightUpperLeg","right_lower_leg":"RightLowerLeg","right_foot":"RightFoot",
    }}
    for k, v in mapping.items():
        slot = getattr(hb, k, None)
        if slot and slot.node and v in arm.data.bones:
            slot.node.bone_name = v
except Exception as e:
    log.append(f"hb {{e}}")
try:
    bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically()
except Exception:
    pass
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.version = "{VERSION}"
except Exception:
    pass

vrm_out = r"{str(TEMP_VRM).replace(chr(92), '/')}"
Path(vrm_out).unlink(missing_ok=True)
export_result = None
with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=arm):
    try:
        export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True, check_existing=False, armature_object_name=arm.name)
    except Exception as e:
        log.append(f"export {{e}}")
        export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)

size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
result = {{"status": "success" if size > 1000 else "error", "size": size, "export": list(export_result) if export_result else None, "log": log}}
'''
    res = exec_blender_code(code)
    payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:4000])
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return 1
    postprocess(TEMP_VRM)
    for name in ["mecha_patlabor_v3_WARUDO_READY.vrm", "mecha_patlabor_v3_warudo.vrm", "mecha_patlabor_v3.vrm"]:
        dest = EXPORTS / name
        shutil.copyfile(TEMP_VRM, dest)
        print("wrote", dest)
    if WARUDO_CHARS.is_dir():
        for name in ["mecha_patlabor_v3_WARUDO_READY.vrm", "mecha_patlabor_v3_warudo.vrm"]:
            shutil.copyfile(TEMP_VRM, WARUDO_CHARS / name)
            print("Warudo <-", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
