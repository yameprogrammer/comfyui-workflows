#!/usr/bin/env python3
"""
Fix mecha_patlabor_v3 shoulder/arm bend locations for Warudo.

Problem: raise-arm bends at wrong place (mid-torso / mid-sleeve) instead of
true shoulder ball joint.

Approach:
1. Load warudo_rebuild blend (true T-pose arms) or main blend
2. Detect arm mesh centerline slices by X along each side
3. Place joints at anatomical landmarks:
   - Shoulder root: torso-side of sleeve (body/arm junction)
   - UpperArm root: lateral deltoid / outer shoulder ball
   - Elbow: mid forearm thickness change / half arm length
   - Wrist / hand tip from outer mesh
4. Re-skin arm chain with heat-ish distance weights (preserve torso/head/legs)
5. Export VRM + copy to Warudo Characters
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
BLEND_CANDIDATES = [
    EXPORTS / "mecha_patlabor_v3_warudo_rebuild.blend",
    EXPORTS / "mecha_patlabor_v3.blend",
    EXPORTS / "mecha_patlabor_v3_rigged.blend",
]
OUT_BLEND = EXPORTS / "mecha_patlabor_v3_warudo_rebuild.blend"
OUT_MAIN = EXPORTS / "mecha_patlabor_v3.blend"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_shoulder_fix.vrm")
OUT_READY = EXPORTS / "mecha_patlabor_v3_WARUDO_READY.vrm"
OUT_WARUDO = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
OUT_STD = EXPORTS / "mecha_patlabor_v3.vrm"
WARUDO_CHARS = Path(
    r"G:\SteamLibrary\steamapps\common\Warudo\Warudo_Data\StreamingAssets\Characters"
)
VERSION = "0.4.1"


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
    changes = []
    if "VRMC_vrm" in gltf.get("extensions", {}):
        vrm = gltf["extensions"]["VRMC_vrm"]
        hb = vrm.setdefault("humanoid", {}).setdefault("humanBones", {})
        for drop in list(hb.keys()):
            if drop not in remap:
                del hb[drop]
                changes.append(f"drop {drop}")
        for k, bone in remap.items():
            if bone not in name_to_idx:
                continue
            new_i = name_to_idx[bone]
            old = hb.get(k, {}).get("node")
            old_n = nodes[old].get("name") if old is not None else None
            hb[k] = {"node": new_i}
            if old != new_i:
                changes.append(f"{k}: {old_n}->{bone}")
        meta = vrm.setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = VERSION
        meta["authors"] = ["yameprogrammer"]
        if gltf.get("skins"):
            gltf["skins"][0].pop("skeleton", None)
        gltf.pop("animations", None)
    save_glb(path, gltf, bin_chunk)
    g2, _ = load_glb(path)
    nodes2 = g2["nodes"]
    skin = g2["skins"][0]
    hb2 = g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    return {
        "changes": changes,
        "joints": [nodes2[j].get("name") for j in skin["joints"]],
        "humanoid_count": len(hb2),
        "size": path.stat().st_size,
    }


def main() -> int:
    blend_src = next((p for p in BLEND_CANDIDATES if p.is_file()), None)
    if blend_src is None:
        print("No blend found")
        return 1

    blend = str(blend_src).replace("\\", "/")
    out_blend = str(OUT_BLEND).replace("\\", "/")
    out_main = str(OUT_MAIN).replace("\\", "/")
    vrm_out = str(TEMP_VRM).replace("\\", "/")
    prev_front = str(EXPORTS / "viewport_shoulder_fix_front.png").replace("\\", "/")
    prev_raise = str(EXPORTS / "viewport_shoulder_fix_raise.png").replace("\\", "/")
    prev_bones = str(EXPORTS / "viewport_shoulder_fix_bones.png").replace("\\", "/")

    code = f'''
import bpy
import addon_utils
import bmesh
import math
from mathutils import Vector, Quaternion, Matrix
from collections import defaultdict
from pathlib import Path

blend_path = r"{blend}"
out_blend = r"{out_blend}"
out_main = r"{out_main}"
vrm_out = r"{vrm_out}"
prev_front = r"{prev_front}"
prev_raise = r"{prev_raise}"
prev_bones = r"{prev_bones}"
log = []

for name in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception as e:
        log.append(f"addon {{e}}")

bpy.ops.wm.open_mainfile(filepath=blend_path)
window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")


def set_mode(mode):
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
        bpy.ops.object.mode_set(mode=mode)


# clear pose
set_mode("POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
set_mode("OBJECT")

mw = mesh.matrix_world
verts_w = [mw @ v.co for v in mesh.data.vertices]

# --- analyze arm centerline by X slices ---
def side_points(side):
    pts = []
    for p in verts_w:
        if p.z < 0.75 or p.z > 1.25:
            continue
        if side == "Left" and p.x < 0.05:
            continue
        if side == "Right" and p.x > -0.05:
            continue
        # arm band roughly around shoulder height ±
        pts.append(p)
    return pts


def centerline(x_lo, x_hi, bins=28):
    """Return centerline samples for verts with x in [x_lo, x_hi] and arm Z band."""
    pts = []
    for p in verts_w:
        if not (x_lo <= p.x <= x_hi):
            continue
        if p.z < 0.70 or p.z > 1.30:
            continue
        pts.append(p)
    if not pts:
        return []
    xs = [p.x for p in pts]
    lo, hi = min(xs), max(xs)
    if abs(hi - lo) < 1e-4:
        return []
    out = []
    for i in range(bins):
        a = lo + (hi - lo) * i / bins
        b = lo + (hi - lo) * (i + 1) / bins
        if i < bins - 1:
            bucket = [p for p in pts if a <= p.x < b]
        else:
            bucket = [p for p in pts if a <= p.x <= b]
        if len(bucket) < 8:
            continue
        cx = sum(p.x for p in bucket) / len(bucket)
        cy = sum(p.y for p in bucket) / len(bucket)
        cz = sum(p.z for p in bucket) / len(bucket)
        r = sum(math.sqrt((p.y - cy) ** 2 + (p.z - cz) ** 2) for p in bucket) / len(bucket)
        out.append({{"x": cx, "y": cy, "z": cz, "n": len(bucket), "r": r}})
    return out


# Left arm: x from ~0.08 body to outer tip; Right mirrored
cl_l = centerline(0.08, 0.70, bins=28)
cl_r = centerline(-0.70, -0.08, bins=28)
log.append(f"cl_l {{len(cl_l)}} cl_r {{len(cl_r)}}")


def pick_joints(cl, side):
    """From centerline samples pick shoulder_root, upper_arm, elbow, wrist, hand_tip."""
    if len(cl) < 4:
        return None
    # sort inner->outer
    if side == "Left":
        cl = sorted(cl, key=lambda d: d["x"])
    else:
        cl = sorted(cl, key=lambda d: -d["x"])  # less neg first (body) to more neg (tip)

    # shoulder root: first samples near body where radius still large (torso+shoulder)
    # Find radius drop: sleeve start = where r drops from torso bulk
    rs = [d["r"] for d in cl]
    # smooth
    def smooth(a, k=3):
        o = []
        for i in range(len(a)):
            s = a[max(0, i - k) : i + k + 1]
            o.append(sum(s) / len(s))
        return o

    rs_s = smooth(rs)
    # find max radius near body (first third)
    n = len(cl)
    body_r = max(rs_s[: max(3, n // 4)])
    # sleeve index: first where r < 0.72 * body_r after first few
    sleeve_i = 1
    for i in range(2, n - 2):
        if rs_s[i] < body_r * 0.70 and rs_s[i] < rs_s[i - 1]:
            sleeve_i = i
            break
    # outer tip
    tip_i = n - 1
    # elbow: around 55-65% along sleeve->tip, or local radius minimum / bend
    sleeve_to_tip = list(range(sleeve_i, n))
    if len(sleeve_to_tip) < 4:
        sleeve_to_tip = list(range(n))
        sleeve_i = 0
    # elbow candidate at ~0.55 of arm length along chain from sleeve
    elbow_i = sleeve_i + max(1, int(0.48 * (tip_i - sleeve_i)))
    # refine elbow: local min radius in mid band
    mid_lo = sleeve_i + max(1, int(0.35 * (tip_i - sleeve_i)))
    mid_hi = sleeve_i + max(2, int(0.70 * (tip_i - sleeve_i)))
    band = list(range(mid_lo, min(mid_hi + 1, tip_i)))
    if band:
        elbow_i = min(band, key=lambda i: rs_s[i])

    # upper arm joint (shoulder ball) slightly OUTBOARD of sleeve start
    # for humanoid: Shoulder bone short clavicle, UpperArm starts at shoulder ball
    ua_i = sleeve_i + max(1, int(0.12 * (tip_i - sleeve_i)))
    # shoulder bone root: slightly INBOARD of sleeve (on torso)
    sh_i = max(0, sleeve_i - max(1, int(0.08 * n)))
    # wrist: near tip but before hand
    wrist_i = sleeve_i + max(2, int(0.88 * (tip_i - sleeve_i)))
    wrist_i = min(wrist_i, tip_i - 1)

    def pt(i):
        d = cl[i]
        return Vector((d["x"], d["y"], d["z"]))

    # force same Y (forward) as chain mean for T-pose cleanliness
    y_mean = sum(d["y"] for d in cl) / len(cl)
    # shoulder height: use median z of sleeve region
    z_sh = sum(cl[i]["z"] for i in range(sh_i, min(ua_i + 1, n))) / max(1, (min(ua_i + 1, n) - sh_i))

    def flat(i, z=None):
        d = cl[i]
        return Vector((d["x"], y_mean, z if z is not None else d["z"]))

    # Keep arm mostly horizontal at shoulder height for T-pose tracking
    sh = flat(sh_i, z_sh)
    ua = flat(ua_i, z_sh)
    el = flat(elbow_i, z_sh * 0.15 + cl[elbow_i]["z"] * 0.85)  # slight natural drop ok but keep near
    # better: fully horizontal for Warudo T-pose
    el = Vector((cl[elbow_i]["x"], y_mean, z_sh))
    wr = Vector((cl[wrist_i]["x"], y_mean, z_sh))
    tip = Vector((cl[tip_i]["x"], y_mean, z_sh))

    # ensure monotonic outer direction
    if side == "Left":
        # x increasing
        xs = [sh.x, ua.x, el.x, wr.x, tip.x]
        if not all(xs[i] < xs[i + 1] - 0.01 for i in range(4)):
            # rebuild evenly spaced
            x0 = cl[sh_i]["x"]
            x1 = cl[tip_i]["x"]
            def lerp_x(t):
                return Vector((x0 + (x1 - x0) * t, y_mean, z_sh))
            sh, ua, el, wr, tip = lerp_x(0.0), lerp_x(0.18), lerp_x(0.55), lerp_x(0.88), lerp_x(1.0)
    else:
        # x decreasing (more negative)
        xs = [sh.x, ua.x, el.x, wr.x, tip.x]
        if not all(xs[i] > xs[i + 1] + 0.01 for i in range(4)):
            x0 = cl[sh_i]["x"]
            x1 = cl[tip_i]["x"]
            def lerp_x(t):
                return Vector((x0 + (x1 - x0) * t, y_mean, z_sh))
            sh, ua, el, wr, tip = lerp_x(0.0), lerp_x(0.18), lerp_x(0.55), lerp_x(0.88), lerp_x(1.0)

    # clamp shoulder root not past body center
    if side == "Left":
        sh.x = max(sh.x, 0.08)
        ua.x = max(ua.x, sh.x + 0.06)
    else:
        sh.x = min(sh.x, -0.08)
        ua.x = min(ua.x, sh.x - 0.06)

    return {{
        "shoulder_head": sh,
        "upper_head": ua,
        "elbow": el,
        "wrist": wr,
        "tip": tip,
        "sleeve_i": sleeve_i,
        "elbow_i": elbow_i,
        "z_sh": z_sh,
        "samples": len(cl),
        "body_r": body_r,
        "sh_x": sh.x,
        "ua_x": ua.x,
        "el_x": el.x,
        "wr_x": wr.x,
        "tip_x": tip.x,
    }}


jl = pick_joints(cl_l, "Left")
jr = pick_joints(cl_r, "Right")
if jl:
    log.append(
        "joints_L "
        + str({{k: (round(v.x, 3), round(v.y, 3), round(v.z, 3)) if hasattr(v, "x") else v for k, v in jl.items()}})
    )
if jr:
    log.append(
        "joints_R "
        + str({{k: (round(v.x, 3), round(v.y, 3), round(v.z, 3)) if hasattr(v, "x") else v for k, v in jr.items()}})
    )

if not jl or not jr:
    result = {{"status": "error", "message": "centerline failed", "log": log, "cl_l": cl_l[:5], "cl_r": cl_r[:5]}}
else:
    # Chest top for shoulder parent height
    chest = arm.data.bones["Chest"]
    chest_head = arm.matrix_world @ chest.head_local
    chest_tail = arm.matrix_world @ chest.tail_local
    # place shoulder heads at chest height slightly below neck
    for j in (jl, jr):
        # blend z toward chest upper third
        target_z = chest_head.z + (chest_tail.z - chest_head.z) * 0.85
        # keep detected z_sh but pull toward chest shoulder height
        z = j["z_sh"] * 0.35 + target_z * 0.65
        for key in ("shoulder_head", "upper_head", "elbow", "wrist", "tip"):
            p = j[key]
            j[key] = Vector((p.x, p.y, z))
        j["z_sh"] = z

    set_mode("EDIT")
    eb = arm.data.edit_bones
    imw = arm.matrix_world.inverted()

    def set_chain(side, j):
        sh = eb[f"{{side}}Shoulder"]
        ua = eb[f"{{side}}UpperArm"]
        la = eb[f"{{side}}LowerArm"]
        ha = eb[f"{{side}}Hand"]
        # world -> local
        def L(v):
            return imw @ v

        sh.use_connect = False
        ua.use_connect = False
        la.use_connect = False
        ha.use_connect = False
        sh.parent = eb["Chest"]
        ua.parent = sh
        la.parent = ua
        ha.parent = la

        sh.head = L(j["shoulder_head"])
        sh.tail = L(j["upper_head"])
        ua.head = sh.tail.copy()
        ua.tail = L(j["elbow"])
        la.head = ua.tail.copy()
        la.tail = L(j["wrist"])
        ha.head = la.tail.copy()
        ha.tail = L(j["tip"])
        # chibi/mecha arms are short — small mins, then re-link head->tail chain
        sign = 1.0 if side == "Left" else -1.0
        mins = ((sh, 0.04), (ua, 0.08), (la, 0.06), (ha, 0.03))
        for b, mln in mins:
            if b.length < mln:
                direction = b.tail - b.head
                if direction.length < 1e-6:
                    direction = Vector((sign * mln, 0, 0))
                else:
                    direction = direction.normalized() * mln
                    # keep direction as vector already scaled
                    b.tail = b.head + direction
                    continue
                b.tail = b.head + direction.normalized() * mln
        # re-link sequential heads to parent tails (no gaps / overlaps)
        ua.head = sh.tail.copy()
        la.head = ua.tail.copy()
        ha.head = la.tail.copy()
        # if hand tip collapsed, extend outward
        if ha.length < 0.025:
            ha.tail = ha.head + Vector((sign * 0.04, 0, 0))

    set_chain("Left", jl)
    set_chain("Right", jr)
    set_mode("OBJECT")

    # --- reweight arm-related groups only ---
    # Keep existing groups for torso/legs/head; rebuild shoulder+arm weights
    arm_bones = [
        "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
        "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
    ]
    # ensure vertex groups exist
    for name in arm_bones + ["Chest", "Spine", "Neck", "Head", "Hips",
                             "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
                             "RightUpperLeg", "RightLowerLeg", "RightFoot"]:
        if name not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=name)

    # clear arm group weights
    for name in arm_bones:
        vg = mesh.vertex_groups[name]
        idxs = [v.index for v in mesh.data.vertices]
        try:
            vg.remove(idxs)
        except Exception:
            pass

    # bone segments world for distance
    set_mode("OBJECT")
    bpy.context.view_layer.update()
    segs = {{}}
    for name in arm.data.bones.keys():
        b = arm.data.bones[name]
        h = arm.matrix_world @ b.head_local
        t = arm.matrix_world @ b.tail_local
        segs[name] = (h, t)

    def dist_to_seg(p, h, t):
        d = t - h
        L2 = d.length_squared
        if L2 < 1e-12:
            return (p - h).length
        u = max(0.0, min(1.0, (p - h).dot(d) / L2))
        return (p - (h + d * u)).length

    def dist_to_bone(p, name):
        return dist_to_seg(p, *segs[name])

    # For each vertex in arm region, assign soft weights among arm chain + chest
    # Torso verts keep existing weights (we only zeroed arm groups)
    # Strategy: for verts with |x| large or already arm-ish, assign arm chain.
    # Also transfer some chest weight near shoulder.

    # Read remaining non-arm weights and rebuild only arm-side verts fully for arm bones
    left_chain = ["Chest", "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand"]
    right_chain = ["Chest", "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand"]

    # influence falloff power
    power = 3.5

    for v in mesh.data.vertices:
        p = mw @ v.co
        # decide side
        if p.x > 0.06 and 0.72 < p.z < 1.28:
            chain = left_chain
            side = "Left"
        elif p.x < -0.06 and 0.72 < p.z < 1.28:
            chain = right_chain
            side = "Right"
        else:
            continue

        # skip pure head blob (high z and near center x of head)
        if p.z > 1.15 and abs(p.x) < 0.18 and abs(p.y) < 0.18:
            # head region - don't steal to arms
            continue

        # distances to chain bones
        dists = []
        for bn in chain:
            if bn not in segs:
                continue
            d = dist_to_bone(p, bn)
            dists.append((bn, d))
        if not dists:
            continue

        # if closest arm bone is far and chest is closer for body, allow chest only
        # Always compute inverse-distance weights
        inv = []
        for bn, d in dists:
            inv.append((bn, 1.0 / max(d, 0.008) ** power))
        s = sum(w for _, w in inv)
        if s <= 0:
            continue
        weights = {{bn: w / s for bn, w in inv}}

        # Near body (|x| small), boost Chest so bend isn't mid-sleeve only from UpperArm
        body_x = abs(p.x)
        if body_x < 0.18:
            # strongly chest
            for bn in list(weights.keys()):
                if bn != "Chest":
                    weights[bn] *= 0.25
            weights["Chest"] = weights.get("Chest", 0) + 0.75
            s = sum(weights.values())
            weights = {{k: v / s for k, v in weights.items()}}
        elif body_x < 0.28:
            # shoulder zone: prefer Shoulder over UpperArm for inner part
            sh_name = f"{{side}}Shoulder"
            ua_name = f"{{side}}UpperArm"
            if sh_name in weights and ua_name in weights:
                # increase shoulder share
                wsh = weights[sh_name]
                wua = weights[ua_name]
                weights[sh_name] = wsh * 0.45 + wua * 0.35 + 0.15
                weights[ua_name] = wua * 0.55
                # renormalize later
            s = sum(weights.values())
            weights = {{k: v / s for k, v in weights.items()}}

        # Outer arm: reduce Chest influence so limbs move free
        if body_x > 0.32:
            if "Chest" in weights:
                weights["Chest"] *= 0.08
            s = sum(weights.values())
            weights = {{k: v / s for k, v in weights.items()}}

        # Apply: remove old arm weights on this vert, keep other groups (legs etc)
        for bn in arm_bones:
            try:
                mesh.vertex_groups[bn].remove([v.index])
            except Exception:
                pass
        # also lightly clear chest only if we're assigning significant chest? Don't remove all chest —
        # instead set arm groups and optionally mix chest
        for bn, w in weights.items():
            if w < 0.02:
                continue
            if bn == "Chest":
                # blend with existing chest rather than overwrite entirely
                try:
                    existing = 0.0
                    for g in v.groups:
                        if mesh.vertex_groups[g.group].name == "Chest":
                            existing = g.weight
                            break
                    # for arm-side verts use computed chest weight
                    mesh.vertex_groups["Chest"].add([v.index], float(w), "REPLACE")
                except Exception:
                    mesh.vertex_groups["Chest"].add([v.index], float(w), "REPLACE")
            else:
                mesh.vertex_groups[bn].add([v.index], float(w), "REPLACE")

    # Normalize all vertex groups (sum to 1)
    for v in mesh.data.vertices:
        total = sum(g.weight for g in v.groups)
        if total <= 1e-8:
            continue
        # collect
        items = []
        for g in v.groups:
            items.append((g.group, g.weight / total))
        # clear and readd
        for g in list(v.groups):
            mesh.vertex_groups[g.group].remove([v.index])
        for gi, w in items:
            mesh.vertex_groups[gi].add([v.index], w, "REPLACE")

    # ensure armature modifier
    for m in list(mesh.modifiers):
        if m.type == "ARMATURE":
            mesh.modifiers.remove(m)
    am = mesh.modifiers.new("Armature", "ARMATURE")
    am.object = arm
    am.use_vertex_groups = True
    mworld = mesh.matrix_world.copy()
    mesh.parent = arm
    mesh.matrix_world = mworld

    # --- previews ---
    def frame_view():
        for o in bpy.data.objects:
            o.select_set(o in (arm, mesh))
        bpy.context.view_layer.objects.active = mesh
        with bpy.context.temp_override(window=window, area=area, region=region):
            try:
                bpy.ops.view3d.view_all(center=True)
            except Exception:
                pass

    def render_png(path, raise_arms=False, show_bones=False):
        # set pose
        set_mode("POSE")
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        if raise_arms:
            # raise both upper arms ~80 deg around Y (world) via local Z-ish
            for name, sign in (("LeftUpperArm", 1), ("RightUpperArm", -1)):
                if name in arm.pose.bones:
                    pb = arm.pose.bones[name]
                    pb.rotation_mode = "XYZ"
                    # local rotation that lifts arms in T-pose (bone along X)
                    pb.rotation_euler = (0.0, 0.0, sign * (-1.2))
            # slight shoulder assist
            for name, sign in (("LeftShoulder", 1), ("RightShoulder", -1)):
                if name in arm.pose.bones:
                    pb = arm.pose.bones[name]
                    pb.rotation_mode = "XYZ"
                    pb.rotation_euler = (0.0, 0.0, sign * (-0.35))
        set_mode("OBJECT")
        bpy.context.view_layer.update()
        # camera / viewport
        scene = bpy.context.scene
        scene.render.resolution_x = 1024
        scene.render.resolution_y = 1024
        scene.render.filepath = path
        # show armature
        arm.hide_viewport = False
        arm.show_in_front = True
        if show_bones:
            arm.data.display_type = "OCTAHEDRAL"
        frame_view()
        with bpy.context.temp_override(window=window, area=area, region=region):
            try:
                bpy.ops.render.opengl(write_still=True)
            except Exception as e:
                log.append(f"render {{path}}: {{e}}")
        # reset pose
        set_mode("POSE")
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
            pb.location = (0, 0, 0)
        set_mode("OBJECT")

    try:
        render_png(prev_front, raise_arms=False, show_bones=True)
        render_png(prev_raise, raise_arms=True, show_bones=True)
        render_png(prev_bones, raise_arms=False, show_bones=True)
    except Exception as e:
        log.append(f"preview {{e}}")

    # save blends
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=out_main, copy=True)
    except Exception as e:
        log.append(f"save main {{e}}")

    # VRM export
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
            "hips": "Hips", "spine": "Spine", "chest": "Chest",
            "neck": "Neck", "head": "Head",
            "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm",
            "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
            "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm",
            "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
            "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg",
            "left_foot": "LeftFoot",
            "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg",
            "right_foot": "RightFoot",
        }}
        for k, v in mapping.items():
            slot = getattr(hb, k, None)
            if slot and slot.node and v in arm.data.bones:
                slot.node.bone_name = v
        try:
            if getattr(hb, "upper_chest", None) and hb.upper_chest.node:
                hb.upper_chest.node.bone_name = ""
        except Exception:
            pass
    except Exception as e:
        log.append(f"humanoid {{e}}")
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
    export_err = None
    with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=arm):
        try:
            export_result = bpy.ops.export_scene.vrm(
                filepath=vrm_out,
                export_invisibles=False,
                export_only_selections=False,
                armature_object_name=arm.name,
                ignore_warning=True,
                check_existing=False,
            )
        except Exception as e:
            export_err = str(e)
            try:
                export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)
            except Exception as e2:
                export_err = f"{{export_err}} | {{e2}}"

    size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0

    # report final bone positions
    final = {{}}
    for nm in arm_bones:
        b = arm.data.bones[nm]
        h = arm.matrix_world @ b.head_local
        t = arm.matrix_world @ b.tail_local
        final[nm] = {{
            "head": [round(float(x), 4) for x in h],
            "tail": [round(float(x), 4) for x in t],
            "len": round(float(b.length), 4),
        }}

    result = {{
        "status": "success" if size > 1000 else "error",
        "log": log,
        "export_result": list(export_result) if export_result else None,
        "export_err": export_err,
        "size": size,
        "final_bones": final,
        "jl": {{k: (round(v.x, 3), round(v.y, 3), round(v.z, 3)) if hasattr(v, "x") else v for k, v in jl.items()}},
        "jr": {{k: (round(v.x, 3), round(v.y, 3), round(v.z, 3)) if hasattr(v, "x") else v for k, v in jr.items()}},
    }}
'''

    print("=== Shoulder/arm fix ===")
    res = exec_blender_code(code)
    payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:8000])
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return 1

    print("=== Postprocess VRM ===")
    info = postprocess_vrm(TEMP_VRM)
    print(json.dumps(info, indent=2, ensure_ascii=False))

    for dest in [OUT_READY, OUT_WARUDO, OUT_STD]:
        shutil.copyfile(TEMP_VRM, dest)
        print("wrote", dest, dest.stat().st_size)

    if WARUDO_CHARS.is_dir():
        for name in ["mecha_patlabor_v3_WARUDO_READY.vrm", "mecha_patlabor_v3_warudo.vrm"]:
            dest = WARUDO_CHARS / name
            shutil.copyfile(TEMP_VRM, dest)
            print("Warudo <-", dest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
