#!/usr/bin/env python3
"""
Shoulder fix v2 for mecha_patlabor_v3.

User report: arms move but bend at wrong place (not at shoulder).

Strategy:
- Put UpperArm joint at body/arm junction (outer torso wall), NOT mid-sleeve
- Short clavicle Shoulder from near-neck to that ball joint
- Elbow ~55% along remaining arm
- Harder weight zones: Chest owns torso, Shoulder owns deltoid pad,
  UpperArm owns upper sleeve, LowerArm/Hand outer arm
- Export Warudo VRM
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3_warudo_rebuild.blend"
if not BLEND.is_file():
    BLEND = EXPORTS / "mecha_patlabor_v3.blend"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_shoulder_v2.vrm")
OUT_READY = EXPORTS / "mecha_patlabor_v3_WARUDO_READY.vrm"
OUT_WARUDO = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
OUT_STD = EXPORTS / "mecha_patlabor_v3.vrm"
OUT_BLEND = EXPORTS / "mecha_patlabor_v3_warudo_rebuild.blend"
OUT_MAIN = EXPORTS / "mecha_patlabor_v3.blend"
WARUDO_CHARS = Path(
    r"G:\SteamLibrary\steamapps\common\Warudo\Warudo_Data\StreamingAssets\Characters"
)
VERSION = "0.4.2"


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


def postprocess_vrm(path: Path) -> dict:
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i
    remap = {
        "hips": "Hips",
        "spine": "Spine",
        "chest": "Chest",
        "neck": "Neck",
        "head": "Head",
        "leftShoulder": "LeftShoulder",
        "leftUpperArm": "LeftUpperArm",
        "leftLowerArm": "LeftLowerArm",
        "leftHand": "LeftHand",
        "rightShoulder": "RightShoulder",
        "rightUpperArm": "RightUpperArm",
        "rightLowerArm": "RightLowerArm",
        "rightHand": "RightHand",
        "leftUpperLeg": "LeftUpperLeg",
        "leftLowerLeg": "LeftLowerLeg",
        "leftFoot": "LeftFoot",
        "rightUpperLeg": "RightUpperLeg",
        "rightLowerLeg": "RightLowerLeg",
        "rightFoot": "RightFoot",
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
    return {"size": path.stat().st_size}


def main() -> int:
    blend = str(BLEND).replace("\\", "/")
    code = f'''
import bpy
import addon_utils
import math
from mathutils import Vector, Quaternion, Matrix, Euler
from pathlib import Path

blend_path = r"{blend}"
out_blend = r"{str(OUT_BLEND).replace(chr(92), '/')}"
out_main = r"{str(OUT_MAIN).replace(chr(92), '/')}"
vrm_out = r"{str(TEMP_VRM).replace(chr(92), '/')}"
prev_t = r"{str(EXPORTS / 'viewport_shoulder_v2_tpose.png').replace(chr(92), '/')}"
prev_r = r"{str(EXPORTS / 'viewport_shoulder_v2_raise.png').replace(chr(92), '/')}"
log = []

for name in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

bpy.ops.wm.open_mainfile(filepath=blend_path)
window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")


def set_mode(mode):
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
        bpy.ops.object.mode_set(mode=mode)


set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
set_mode("OBJECT")

mw = mesh.matrix_world
verts = [mw @ v.co for v in mesh.data.vertices]


def arm_extent(side):
    """Return outer tip x, body-wall x estimate, mean y, shoulder z."""
    pts = []
    for p in verts:
        if p.z < 0.78 or p.z > 1.22:
            continue
        if side == "Left" and p.x < 0.05:
            continue
        if side == "Right" and p.x > -0.05:
            continue
        pts.append(p)
    if not pts:
        return None
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    y_mean = sum(ys) / len(ys)
    # shoulder band z: top quartile of arm-band verts with |x| in mid
    if side == "Left":
        band = [p for p in pts if 0.10 < p.x < 0.35]
        tip_x = max(p.x for p in pts)
        # body wall: x where cumulative thickness drops — use 15th percentile of x among upper torso shoulder height
        sh_pts = [p for p in pts if 0.06 < p.x < 0.40 and p.z > 0.92]
        wall_x = sorted(p.x for p in sh_pts)[max(0, int(0.12 * len(sh_pts)))] if sh_pts else 0.18
    else:
        band = [p for p in pts if -0.35 < p.x < -0.10]
        tip_x = min(p.x for p in pts)
        sh_pts = [p for p in pts if -0.40 < p.x < -0.06 and p.z > 0.92]
        wall_x = sorted((p.x for p in sh_pts), reverse=True)[max(0, int(0.12 * len(sh_pts)))] if sh_pts else -0.18
    z_sh = sum(p.z for p in band) / len(band) if band else sum(zs) / len(zs)
    # neck-side clavicle root
    chest_b = arm.data.bones["Chest"]
    ch = arm.matrix_world @ chest_b.head_local
    ct = arm.matrix_world @ chest_b.tail_local
    clav_x = 0.10 if side == "Left" else -0.10
    # blend wall with geometric estimate
    if side == "Left":
        ball_x = max(wall_x, 0.16)
        ball_x = min(ball_x, 0.24)  # keep joint at body edge not mid-sleeve
        clav_x = max(0.08, ball_x - 0.10)
    else:
        ball_x = min(wall_x, -0.16)
        ball_x = max(ball_x, -0.24)
        clav_x = min(-0.08, ball_x + 0.10)
    # elbow 55% from ball to tip
    elbow_x = ball_x + 0.55 * (tip_x - ball_x)
    wrist_x = ball_x + 0.88 * (tip_x - ball_x)
    return {{
        "clav": Vector((clav_x, y_mean, z_sh)),
        "ball": Vector((ball_x, y_mean, z_sh)),
        "elbow": Vector((elbow_x, y_mean, z_sh)),
        "wrist": Vector((wrist_x, y_mean, z_sh)),
        "tip": Vector((tip_x, y_mean, z_sh)),
        "wall_x": wall_x,
        "tip_x": tip_x,
        "z_sh": z_sh,
    }}


L = arm_extent("Left")
R = arm_extent("Right")
log.append(
    f"L clav={{L['clav'].x:.3f}} ball={{L['ball'].x:.3f}} elbow={{L['elbow'].x:.3f}} tip={{L['tip_x']:.3f}} z={{L['z_sh']:.3f}}"
)
log.append(
    f"R clav={{R['clav'].x:.3f}} ball={{R['ball'].x:.3f}} elbow={{R['elbow'].x:.3f}} tip={{R['tip_x']:.3f}} z={{R['z_sh']:.3f}}"
)

set_mode("EDIT")
eb = arm.data.edit_bones
imw = arm.matrix_world.inverted()


def apply_side(side, j):
    sh, ua, la, ha = eb[f"{{side}}Shoulder"], eb[f"{{side}}UpperArm"], eb[f"{{side}}LowerArm"], eb[f"{{side}}Hand"]
    sh.parent = eb["Chest"]
    ua.parent = sh
    la.parent = ua
    ha.parent = la
    for b in (sh, ua, la, ha):
        b.use_connect = False

    def loc(v):
        return imw @ v

    sh.head = loc(j["clav"])
    sh.tail = loc(j["ball"])
    ua.head = sh.tail.copy()
    ua.tail = loc(j["elbow"])
    la.head = ua.tail.copy()
    la.tail = loc(j["wrist"])
    ha.head = la.tail.copy()
    ha.tail = loc(j["tip"])
    # ensure min lengths without breaking chain direction
    sign = 1.0 if side == "Left" else -1.0
    for b, mn in ((sh, 0.045), (ua, 0.10), (la, 0.07), (ha, 0.03)):
        if b.length < mn:
            d = b.tail - b.head
            if d.length < 1e-8:
                d = Vector((sign, 0, 0))
            b.tail = b.head + d.normalized() * mn
    ua.head = sh.tail.copy()
    la.head = ua.tail.copy()
    ha.head = la.tail.copy()
    if ha.length < 0.025:
        ha.tail = ha.head + Vector((sign * 0.04, 0, 0))


apply_side("Left", L)
apply_side("Right", R)
set_mode("OBJECT")
bpy.context.view_layer.update()

# --- zone-based skin weights for arms ---
arm_bones = [
    "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
]
for name in list(arm.data.bones.keys()):
    if name not in mesh.vertex_groups:
        mesh.vertex_groups.new(name=name)

# clear arm groups fully
all_idx = [v.index for v in mesh.data.vertices]
for name in arm_bones:
    try:
        mesh.vertex_groups[name].remove(all_idx)
    except Exception:
        pass

segs = {{}}
for name, b in arm.data.bones.items():
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    segs[name] = (h, t)


def dist_seg(p, h, t):
    d = t - h
    L2 = d.length_squared
    if L2 < 1e-12:
        return (p - h).length
    u = max(0.0, min(1.0, (p - h).dot(d) / L2))
    return (p - (h + d * u)).length


def assign_side(side, j):
    sh_n = f"{{side}}Shoulder"
    ua_n = f"{{side}}UpperArm"
    la_n = f"{{side}}LowerArm"
    ha_n = f"{{side}}Hand"
    ball_x = j["ball"].x
    elbow_x = j["elbow"].x
    wrist_x = j["wrist"].x
    tip_x = j["tip"].x
    sign = 1.0 if side == "Left" else -1.0

    def along(p):
        # 0 at body center, 1 at tip — use x projected
        if side == "Left":
            return p.x
        return -p.x

    ball_a = along(j["ball"])
    elbow_a = along(j["elbow"])
    wrist_a = along(j["wrist"])
    tip_a = along(j["tip"])
    clav_a = along(j["clav"])

    for v in mesh.data.vertices:
        p = mw @ v.co
        # arm height band + correct side
        if p.z < 0.72 or p.z > 1.28:
            continue
        if side == "Left" and p.x < 0.04:
            continue
        if side == "Right" and p.x > -0.04:
            continue
        # skip head blob
        if p.z > 1.12 and abs(p.x) < 0.16 and abs(p.y) < 0.20:
            continue

        a = along(p)
        # soft zones in parameter a
        # torso: a < clav -> chest only (don't touch much)
        # clav..ball: Chest + Shoulder
        # ball..elbow: Shoulder + UpperArm
        # elbow..wrist: UpperArm + LowerArm
        # wrist..tip: LowerArm + Hand

        w = {{"Chest": 0.0, sh_n: 0.0, ua_n: 0.0, la_n: 0.0, ha_n: 0.0}}

        # also use distance to segments as blend
        d_sh = dist_seg(p, *segs[sh_n])
        d_ua = dist_seg(p, *segs[ua_n])
        d_la = dist_seg(p, *segs[la_n])
        d_ha = dist_seg(p, *segs[ha_n])
        d_ch = dist_seg(p, *segs["Chest"])

        # base inverse-distance on relevant bones by zone
        if a < clav_a + 0.02:
            # still body — only chest if close to chest bone
            if d_ch < 0.12 and abs(p.x) < abs(ball_x) + 0.02:
                w["Chest"] = 1.0
            else:
                continue
        elif a < ball_a:
            # clavicle region: mostly Chest + Shoulder, tiny UpperArm near ball
            t = (a - clav_a) / max(1e-4, ball_a - clav_a)
            w["Chest"] = 0.75 * (1 - t) + 0.15
            w[sh_n] = 0.20 + 0.55 * t
            w[ua_n] = 0.05 * t
        elif a < elbow_a:
            # upper arm: Shoulder fades, UpperArm dominates — THIS is the main raise bend
            t = (a - ball_a) / max(1e-4, elbow_a - ball_a)
            w["Chest"] = max(0.0, 0.12 * (1 - t) - 0.05)
            w[sh_n] = max(0.0, 0.45 * (1 - t) - 0.05 * t)
            w[ua_n] = 0.40 + 0.50 * t
            w[la_n] = 0.08 * t
        elif a < wrist_a:
            t = (a - elbow_a) / max(1e-4, wrist_a - elbow_a)
            w[ua_n] = 0.55 * (1 - t)
            w[la_n] = 0.40 + 0.45 * t
            w[ha_n] = 0.05 * t
        else:
            t = (a - wrist_a) / max(1e-4, tip_a - wrist_a + 1e-4)
            w[la_n] = 0.45 * (1 - t)
            w[ha_n] = 0.55 + 0.40 * t

        # distance sharpening: boost closest bone
        dist_map = {{"Chest": d_ch, sh_n: d_sh, ua_n: d_ua, la_n: d_la, ha_n: d_ha}}
        for bn in list(w.keys()):
            if w[bn] <= 0:
                continue
            # closer -> keep, far -> cut
            fall = math.exp(-dist_map[bn] * 14.0)
            w[bn] *= 0.35 + 0.65 * fall

        s = sum(w.values())
        if s < 1e-6:
            continue
        w = {{k: v / s for k, v in w.items() if v > 0.01}}
        s = sum(w.values())
        w = {{k: v / s for k, v in w.items()}}

        # write arm groups; chest REPLACE only if significant and in shoulder region
        for bn in arm_bones:
            if bn.startswith(side) or (side == "Left" and bn.startswith("Left")) or (side == "Right" and bn.startswith("Right")):
                pass
        for bn in (sh_n, ua_n, la_n, ha_n):
            try:
                mesh.vertex_groups[bn].remove([v.index])
            except Exception:
                pass
        for bn, wt in w.items():
            if bn == "Chest":
                if wt > 0.05 and a < ball_a + 0.05:
                    # mix: take max with existing chest fraction for shoulder pad
                    mesh.vertex_groups["Chest"].add([v.index], float(wt), "REPLACE")
            else:
                mesh.vertex_groups[bn].add([v.index], float(wt), "REPLACE")


assign_side("Left", L)
assign_side("Right", R)

# normalize all verts
for v in mesh.data.vertices:
    total = sum(g.weight for g in v.groups)
    if total <= 1e-8:
        continue
    items = [(g.group, g.weight / total) for g in v.groups]
    for g in list(v.groups):
        mesh.vertex_groups[g.group].remove([v.index])
    for gi, wt in items:
        mesh.vertex_groups[gi].add([v.index], wt, "REPLACE")

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

# --- previews with correct world-axis raise ---
def clear_pose():
    set_mode("POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    set_mode("OBJECT")


def raise_arms(amount=1.1):
    """Rotate upper arms around world -Y (forward) so arms lift up in T-pose."""
    set_mode("POSE")
    bpy.context.view_layer.update()
    for name, sign in (("LeftUpperArm", 1), ("RightUpperArm", -1)):
        pb = arm.pose.bones.get(name)
        if not pb:
            continue
        # world rotation around Y
        R = Matrix.Rotation(sign * amount, 4, "Y")
        # convert to pose bone local
        # M_final = M_basis_rest * M_pose; we set pose so world bone gets R applied
        bone = pb.bone
        # rest matrix world
        mw_bone = arm.matrix_world @ bone.matrix_local
        # parent world
        if bone.parent:
            parent_mw = arm.matrix_world @ bone.parent.matrix_local
        else:
            parent_mw = arm.matrix_world
        # desired world = R * rest_world (rotate around origin? better around bone head)
        head = mw_bone.translation
        T1 = Matrix.Translation(head)
        T0 = Matrix.Translation(-head)
        desired = T1 @ R @ T0 @ mw_bone
        # pose matrix: parent_mw * (bone.matrix_local) * pose = desired
        # pose = inv(bone.matrix_local) * inv(parent_mw) * desired  — for connected armature
        ml = bone.matrix_local
        if bone.parent:
            local = parent_mw.inverted() @ desired
            pose = ml.inverted() @ local
        else:
            local = arm.matrix_world.inverted() @ desired
            pose = ml.inverted() @ local
        pb.matrix_basis = pose
    # assist shoulder slightly
    for name, sign in (("LeftShoulder", 1), ("RightShoulder", -1)):
        pb = arm.pose.bones.get(name)
        if not pb:
            continue
        R = Matrix.Rotation(sign * 0.35, 4, "Y")
        bone = pb.bone
        mw_bone = arm.matrix_world @ bone.matrix_local
        head = mw_bone.translation
        desired = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ mw_bone
        ml = bone.matrix_local
        if bone.parent:
            parent_mw = arm.matrix_world @ bone.parent.matrix_local
            local = parent_mw.inverted() @ desired
            pose = ml.inverted() @ local
        else:
            local = arm.matrix_world.inverted() @ desired
            pose = ml.inverted() @ local
        pb.matrix_basis = pose
    set_mode("OBJECT")
    bpy.context.view_layer.update()


def render(path):
    scene = bpy.context.scene
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.filepath = path
    arm.hide_viewport = False
    arm.show_in_front = True
    arm.data.display_type = "OCTAHEDRAL"
    with bpy.context.temp_override(window=window, area=area, region=region):
        try:
            bpy.ops.view3d.view_all(center=True)
        except Exception:
            pass
        try:
            bpy.ops.render.opengl(write_still=True)
        except Exception as e:
            log.append(f"render {{e}}")


clear_pose()
render(prev_t)
raise_arms(1.15)
render(prev_r)
clear_pose()

# save
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
try:
    bpy.ops.wm.save_as_mainfile(filepath=out_main, copy=True)
except Exception as e:
    log.append(f"save main {{e}}")

# VRM
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
mesh.select_set(True)
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
    for k,v in mapping.items():
        slot = getattr(hb, k, None)
        if slot and slot.node and v in arm.data.bones:
            slot.node.bone_name = v
    try:
        if getattr(hb, "upper_chest", None) and hb.upper_chest.node:
            hb.upper_chest.node.bone_name = ""
    except Exception:
        pass
except Exception as e:
    log.append(f"hb {{e}}")
try:
    bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically()
except Exception:
    pass
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "{VERSION}"
except Exception:
    pass

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
        try:
            export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)
        except Exception as e2:
            log.append(f"export2 {{e2}}")

size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
final = {{}}
for nm in arm_bones:
    b = arm.data.bones[nm]
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    final[nm] = {{"h":[round(float(x),3) for x in h], "t":[round(float(x),3) for x in t], "len": round(b.length,3)}}

result = {{
    "status": "success" if size > 1000 else "error",
    "size": size,
    "export": list(export_result) if export_result else None,
    "log": log,
    "final": final,
}}
'''

    print("=== shoulder v2 ===")
    res = exec_blender_code(code)
    payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:7000])
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return 1

    postprocess_vrm(TEMP_VRM)
    for dest in [OUT_READY, OUT_WARUDO, OUT_STD]:
        shutil.copyfile(TEMP_VRM, dest)
        print("wrote", dest)
    if WARUDO_CHARS.is_dir():
        for name in ["mecha_patlabor_v3_WARUDO_READY.vrm", "mecha_patlabor_v3_warudo.vrm"]:
            shutil.copyfile(TEMP_VRM, WARUDO_CHARS / name)
            print("Warudo <-", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
