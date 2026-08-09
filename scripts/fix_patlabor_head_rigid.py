#!/usr/bin/env python3
"""
Make mecha_patlabor_v3 head/face rigid under Head bone.

Problem: head/face verts mixed with Chest/Arm weights → face collapses when head turns.
Fix: entire helmet volume → 100% Head; narrow neck collar blend only.
"""

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
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_head_rigid.vrm")
VERSION = "0.4.4"
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
from mathutils import Vector, Quaternion
from pathlib import Path
from collections import defaultdict

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

# landmarks
neck_b = arm.data.bones["Neck"]
head_b = arm.data.bones["Head"]
chest_b = arm.data.bones["Chest"]
neck_head = arm.matrix_world @ neck_b.head_local  # chest-neck joint
neck_tail = arm.matrix_world @ neck_b.tail_local  # neck-head joint
head_head = arm.matrix_world @ head_b.head_local
head_tail = arm.matrix_world @ head_b.tail_local

# Head bone too long is ok; ensure pivot at base of helmet
# Shorten visual? Keep length but fix weights.

z_neck_start = neck_head.z          # ~1.006
z_head_base = head_head.z           # ~1.076
z_helmet_bottom = z_head_base - 0.02

# Estimate helmet: all verts above z_head_base - 0.03 with |x|<0.45, or high head mass
# Force rigid head for z >= z_head_base - 0.01 (almost entire screen head)

for name in ["Head", "Neck", "Chest", "Spine", "Hips"]:
    if name not in mesh.vertex_groups:
        mesh.vertex_groups.new(name=name)

ARM_BONES = [
    "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
]

n_rigid = 0
n_collar = 0
n_arm_strip = 0

for v in mesh.data.vertices:
    p = mw @ v.co
    # read weights
    wmap = {{}}
    for g in v.groups:
        wmap[mesh.vertex_groups[g.group].name] = g.weight

    # --- strip any arm influence on upper body near head ---
    if p.z > 1.02:
        stripped = False
        for a in ARM_BONES:
            if wmap.get(a, 0) > 0:
                wmap.pop(a, None)
                stripped = True
        if stripped:
            n_arm_strip += 1

    # --- HELMET / FACE: fully rigid Head ---
    # big chibi head: z from ~1.08 to 1.60, radius ~0.35
    in_helmet = False
    if p.z >= z_head_base - 0.005:
        in_helmet = True
    # also catch hanging face/chin of helmet slightly below joint if within head XY radius
    if p.z >= z_head_base - 0.08:
        # distance to head axis (x=0,y near 0)
        radial = (p.x ** 2 + p.y ** 2) ** 0.5
        # if clearly part of big head sphere (not thin neck)
        if radial > 0.10 and p.z > z_neck_start + 0.02:
            in_helmet = True
        if radial > 0.14 and p.z > 1.04:
            in_helmet = True

    if in_helmet and p.z > z_neck_start + 0.015:
        # 100% Head — no chest/neck/arm mix that tears face
        for g in list(v.groups):
            mesh.vertex_groups[g.group].remove([v.index])
        mesh.vertex_groups["Head"].add([v.index], 1.0, "REPLACE")
        n_rigid += 1
        continue

    # --- NECK COLLAR: narrow blend Neck ↔ Head ↔ Chest ---
    # only thin band between chest top and head base, small radius
    if z_neck_start - 0.02 <= p.z <= z_head_base + 0.02 and (p.x ** 2 + p.y ** 2) ** 0.5 < 0.14:
        # parameter 0 at neck start, 1 at head base
        t = (p.z - z_neck_start) / max(1e-4, (z_head_base - z_neck_start))
        t = max(0.0, min(1.0, t))
        # lower collar: Chest+Neck, upper: Neck+Head
        if t < 0.45:
            u = t / 0.45
            w_chest = 0.65 * (1 - u) + 0.15
            w_neck = 0.25 + 0.45 * u
            w_head = 0.05 * u
        else:
            u = (t - 0.45) / 0.55
            w_chest = max(0.0, 0.15 * (1 - u))
            w_neck = 0.55 * (1 - u) + 0.15
            w_head = 0.20 + 0.65 * u
        # preserve non-torso groups? clear and set collar only for torso bones
        # keep leg weights if any (shouldn't be)
        keep = {{}}
        for k, wv in wmap.items():
            if k not in ("Head", "Neck", "Chest", "Spine", "Hips") and k not in ARM_BONES:
                keep[k] = wv
        for g in list(v.groups):
            mesh.vertex_groups[g.group].remove([v.index])
        total_keep = sum(keep.values())
        scale = 1.0
        collar = {{"Chest": w_chest, "Neck": w_neck, "Head": w_head}}
        s = sum(collar.values())
        collar = {{k: v / s for k, v in collar.items()}}
        # if had keep weights, blend 10%
        for k, wv in collar.items():
            mesh.vertex_groups[k].add([v.index], float(wv), "REPLACE")
        for k, wv in keep.items():
            if k not in mesh.vertex_groups:
                mesh.vertex_groups.new(name=k)
            mesh.vertex_groups[k].add([v.index], float(wv * 0.05), "ADD")
        # renormalize
        # read back
        items = []
        total = 0.0
        for g in v.groups:
            items.append((g.group, g.weight))
            total += g.weight
        if total > 1e-8:
            for g in list(v.groups):
                mesh.vertex_groups[g.group].remove([v.index])
            for gi, wv in items:
                mesh.vertex_groups[gi].add([v.index], wv / total, "REPLACE")
        n_collar += 1
        continue

    # --- other verts that still have partial Head with Chest tearing face-ish ---
    # if Head weight present and z high, push to pure head
    if p.z > 1.08 and wmap.get("Head", 0) > 0.3:
        for g in list(v.groups):
            mesh.vertex_groups[g.group].remove([v.index])
        mesh.vertex_groups["Head"].add([v.index], 1.0, "REPLACE")
        n_rigid += 1

log.append(f"rigid_head={{n_rigid}} collar={{n_collar}} arm_strip={{n_arm_strip}}")

# final normalize all
for v in mesh.data.vertices:
    total = sum(g.weight for g in v.groups)
    if total <= 1e-8:
        continue
    items = [(g.group, g.weight / total) for g in v.groups]
    for g in list(v.groups):
        mesh.vertex_groups[g.group].remove([v.index])
    for gi, wv in items:
        mesh.vertex_groups[gi].add([v.index], wv, "REPLACE")

# armature mod
for m in list(mesh.modifiers):
    if m.type == "ARMATURE":
        mesh.modifiers.remove(m)
am = mesh.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
mworld = mesh.matrix_world.copy()
mesh.parent = arm
mesh.matrix_world = mworld

# QA: rigid ratio after fix
import random
random.seed(1)
head_idx = []
for v in mesh.data.vertices:
    for g in v.groups:
        if mesh.vertex_groups[g.group].name == "Head" and g.weight > 0.85:
            head_idx.append(v.index)
            break

# pose head
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
arm.pose.bones["Head"].rotation_mode = "XYZ"
arm.pose.bones["Head"].rotation_euler = (0.6, 0.5, 0.35)
set_mode("OBJECT")
bpy.context.view_layer.update()

rest_pos = {{i: mw @ mesh.data.vertices[i].co for i in head_idx}}
deps = bpy.context.evaluated_depsgraph_get()
me = mesh.evaluated_get(deps).to_mesh()
posed_pos = {{i: mw @ me.vertices[i].co for i in head_idx}}
mesh.evaluated_get(deps).to_mesh_clear()
ratios = []
for _ in range(50):
    if len(head_idx) < 10:
        break
    a, b = random.sample(head_idx, 2)
    dr = (rest_pos[a] - rest_pos[b]).length
    dp = (posed_pos[a] - posed_pos[b]).length
    if dr > 0.01:
        ratios.append(dp / dr)
rigid_qa = {{
    "n_head": len(head_idx),
    "mean_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
    "min_ratio": round(min(ratios), 4) if ratios else None,
    "max_ratio": round(max(ratios), 4) if ratios else None,
}}

# render previews
def render(path):
    scene = bpy.context.scene
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.filepath = path
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

render(r"{str(EXPORTS / 'viewport_head_turn.png').replace(chr(92), '/')}")

# also neck turn
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
arm.pose.bones["Neck"].rotation_mode = "XYZ"
arm.pose.bones["Neck"].rotation_euler = (0.35, 0.4, 0.0)
arm.pose.bones["Head"].rotation_mode = "XYZ"
arm.pose.bones["Head"].rotation_euler = (0.25, 0.25, 0.0)
set_mode("OBJECT")
bpy.context.view_layer.update()
render(r"{str(EXPORTS / 'viewport_head_neck_turn.png').replace(chr(92), '/')}")

# reset
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
set_mode("OBJECT")

# skull weak-head check
weak = 0
skull = 0
for v in mesh.data.vertices:
    p = mw @ v.co
    if p.z < 1.15:
        continue
    skull += 1
    hw = 0
    for g in v.groups:
        if mesh.vertex_groups[g.group].name == "Head":
            hw = g.weight
            break
    if hw < 0.95:
        weak += 1

bpy.ops.wm.save_as_mainfile(filepath=r"{str(BLEND).replace(chr(92), '/')}")
try:
    bpy.ops.wm.save_as_mainfile(filepath=r"{str(EXPORTS / 'mecha_patlabor_v3.blend').replace(chr(92), '/')}", copy=True)
except Exception:
    pass

# VRM export
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
        export_result = bpy.ops.export_scene.vrm(
            filepath=vrm_out, ignore_warning=True, check_existing=False,
            armature_object_name=arm.name,
        )
    except Exception as e:
        log.append(f"export {{e}}")
        export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)

size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
result = {{
    "status": "success" if size > 1000 else "error",
    "size": size,
    "export": list(export_result) if export_result else None,
    "log": log,
    "rigid_qa": rigid_qa,
    "skull_weak_frac": round(weak / skull, 4) if skull else None,
    "skull_n": skull,
    "z_head_base": round(float(z_head_base), 4),
    "z_neck_start": round(float(z_neck_start), 4),
}}
'''
    res = exec_blender_code(code)
    payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:5000])
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return 1

    postprocess(TEMP_VRM)
    for name in [
        "mecha_patlabor_v3_WARUDO_READY.vrm",
        "mecha_patlabor_v3_warudo.vrm",
        "mecha_patlabor_v3.vrm",
    ]:
        shutil.copyfile(TEMP_VRM, EXPORTS / name)
        print("wrote", EXPORTS / name)
    if WARUDO_CHARS.is_dir():
        for name in ["mecha_patlabor_v3_WARUDO_READY.vrm", "mecha_patlabor_v3_warudo.vrm"]:
            shutil.copyfile(TEMP_VRM, WARUDO_CHARS / name)
            print("Warudo <-", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
