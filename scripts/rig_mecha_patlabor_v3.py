#!/usr/bin/env python3
"""
Anatomy-aware humanoid rig for mecha_patlabor_v3.

- Import cleaned GLB
- Place bones from mesh landmarks (armpit, hands, feet, head) — not raw bbox %
- VRM-style bone names
- Custom skin weights (head lock, arm/leg chains) — avoids grotesque ARMATURE_AUTO spills
- Pose test renders (T-pose + arm raise + turn)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
SRC = EXPORTS / "mecha_patlabor_v3_clean.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_patlabor_v3_mv_tex.glb"
BLEND_OUT = EXPORTS / "mecha_patlabor_v3_rigged.blend"
BLEND_MAIN = EXPORTS / "mecha_patlabor_v3.blend"
GLB_OUT = EXPORTS / "mecha_patlabor_v3_rigged.glb"


def main() -> int:
    if not SRC.is_file():
        print("[ERROR] missing", SRC)
        return 1

    paths = {
        "src": str(SRC).replace("\\", "/"),
        "blend": str(BLEND_OUT).replace("\\", "/"),
        "glb": str(GLB_OUT).replace("\\", "/"),
        "r_tpose": str(EXPORTS / "viewport_rig_tpose.png").replace("\\", "/"),
        "r_raise": str(EXPORTS / "viewport_rig_raise_arms.png").replace("\\", "/"),
        "r_wave": str(EXPORTS / "viewport_rig_wave.png").replace("\\", "/"),
        "r_bones": str(EXPORTS / "viewport_rig_bones.png").replace("\\", "/"),
    }

    code = f'''
import bpy
import math
from mathutils import Vector, Matrix, Euler

paths = {repr(paths)}
report = {{"steps": []}}

# ---------- wipe ----------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights, bpy.data.images):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=paths["src"])
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objs:
    result = {{"status": "error", "message": "no mesh"}}
else:
    # join
    if len(mesh_objs) > 1:
        # apply transforms into mesh then join via bmesh-free path
        target = mesh_objs[0]
        for o in mesh_objs:
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)
        # join using data
        import bmesh
        bm = bmesh.new()
        for o in mesh_objs:
            bm.from_mesh(o.data)
        me = bpy.data.meshes.new("MechaPatlabor_V3")
        bm.to_mesh(me)
        bm.free()
        for o in mesh_objs:
            m = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if m.users == 0:
                bpy.data.meshes.remove(m)
        main = bpy.data.objects.new("MechaPatlabor_V3", me)
        bpy.context.scene.collection.objects.link(main)
    else:
        main = mesh_objs[0]
        main.name = "MechaPatlabor_V3"
        main.data.transform(main.matrix_world)
        main.matrix_world = Matrix.Identity(4)

    # clear prior skin
    for mod in list(main.modifiers):
        if mod.type == "ARMATURE":
            main.modifiers.remove(mod)
    main.parent = None
    main.vertex_groups.clear()

    # normalize height 1.60, feet on ground, center XZ
    vs0 = [v.co.copy() for v in main.data.vertices]
    minz = min(v.z for v in vs0); maxz = max(v.z for v in vs0)
    h0 = max(maxz - minz, 1e-6)
    s = 1.60 / h0
    for v in main.data.vertices:
        v.co *= s
    minz = min(v.co.z for v in main.data.vertices)
    minx = min(v.co.x for v in main.data.vertices); maxx = max(v.co.x for v in main.data.vertices)
    miny = min(v.co.y for v in main.data.vertices); maxy = max(v.co.y for v in main.data.vertices)
    cx0 = 0.5 * (minx + maxx)
    cy0 = 0.5 * (miny + maxy)
    for v in main.data.vertices:
        v.co.z -= minz
        v.co.x -= cx0
        v.co.y -= cy0
    main.data.update()
    main.location = (0, 0, 0)
    main.rotation_euler = (0, 0, 0)
    main.scale = (1, 1, 1)

    # ---------- landmarks from mesh ----------
    vs = [v.co.copy() for v in main.data.vertices]
    xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    minz, maxz = min(zs), max(zs)
    H = maxz - minz
    W = maxx - minx
    D = maxy - miny
    cx = 0.5 * (minx + maxx)
    cy = 0.5 * (miny + maxy)

    def pct(t):
        return minz + H * t

    def avg(pts, fb):
        if not pts:
            return Vector(fb)
        return Vector((
            sum(p.x for p in pts) / len(pts),
            sum(p.y for p in pts) / len(pts),
            sum(p.z for p in pts) / len(pts),
        ))

    def band(z0, z1, x_min=None, x_max=None, y_min=None, y_max=None, abs_x_max=None):
        out = []
        for v in vs:
            if not (z0 <= v.z <= z1):
                continue
            if abs_x_max is not None and abs(v.x - cx) > abs_x_max:
                continue
            if x_min is not None and v.x < x_min:
                continue
            if x_max is not None and v.x > x_max:
                continue
            if y_min is not None and v.y < y_min:
                continue
            if y_max is not None and v.y > y_max:
                continue
            out.append(v)
        return out

    # Head: top mass
    head_pts = [v for v in vs if v.z >= pct(0.72)]
    hcx = sum(v.x for v in head_pts) / max(len(head_pts), 1)
    hcy = sum(v.y for v in head_pts) / max(len(head_pts), 1)
    head_top = max((v.z for v in head_pts), default=maxz)
    head_bot = min((v.z for v in head_pts), default=pct(0.72))
    # neck at underside of helmet / cylinder
    neck_z = head_bot - H * 0.015
    neck = Vector((cx, cy, neck_z))
    head_tail = Vector((hcx, hcy, head_top - H * 0.01))
    head_c = Vector((hcx, hcy, 0.5 * (head_bot + head_top)))
    head_r = 0.0
    for v in head_pts:
        head_r = max(head_r, (v - head_c).length)
    head_r = max(head_r * 1.04, H * 0.08)

    # Torso width at mid-chest (central mass only)
    chest_z_guess = min(pct(0.58), neck_z - H * 0.08)
    chest_band = band(chest_z_guess - H * 0.04, chest_z_guess + H * 0.04, abs_x_max=W * 0.22)
    if chest_band:
        torso_half = 0.5 * (max(v.x for v in chest_band) - min(v.x for v in chest_band))
    else:
        torso_half = W * 0.14
    torso_half = max(torso_half, W * 0.10)

    # Hips: pelvis height ~ crotch of pants (central low torso)
    # Find where left-right split of legs begins: lowest central band before feet
    crotch_band = band(pct(0.40), pct(0.52), abs_x_max=W * 0.12)
    if crotch_band:
        hips_z = min(v.z for v in crotch_band) + H * 0.02
    else:
        hips_z = pct(0.48)
    # anatomical: hips joint slightly above crotch
    hips_z = max(hips_z, pct(0.45))
    hips_z = min(hips_z, pct(0.52))
    spine_z = hips_z + (chest_z_guess - hips_z) * 0.35
    chest_z = min(chest_z_guess, neck_z - H * 0.07)

    hips = Vector((cx, cy, hips_z))
    spine = Vector((cx, cy, spine_z))
    chest = Vector((cx, cy, chest_z))

    # Shoulder / armpit from mesh
    sh_search_z = neck_z - H * 0.06
    armpit_L = [
        v for v in vs
        if (cx + torso_half * 0.65) < v.x < (cx + torso_half * 1.45)
        and (sh_search_z - H * 0.10) < v.z < (sh_search_z + H * 0.05)
    ]
    armpit_R = [
        v for v in vs
        if (cx - torso_half * 1.45) < v.x < (cx - torso_half * 0.65)
        and (sh_search_z - H * 0.10) < v.z < (sh_search_z + H * 0.05)
    ]
    if armpit_L:
        al = avg(armpit_L, (cx + torso_half, cy, sh_search_z))
        left_sh = Vector((al.x, cy, al.z + H * 0.03))
    else:
        left_sh = Vector((cx + torso_half * 1.05, cy, neck_z - H * 0.09))
    if armpit_R:
        ar = avg(armpit_R, (cx - torso_half, cy, sh_search_z))
        right_sh = Vector((ar.x, cy, ar.z + H * 0.03))
    else:
        right_sh = Vector((cx - torso_half * 1.05, cy, neck_z - H * 0.09))
    sh_z = 0.5 * (left_sh.z + right_sh.z)
    # keep shoulders under neck, above chest
    sh_z = min(sh_z, neck_z - H * 0.02)
    sh_z = max(sh_z, chest_z + H * 0.02)
    left_sh = Vector((abs(left_sh.x - cx) + cx if left_sh.x >= cx else left_sh.x, cy, sh_z))
    # force mirror symmetry for cleaner T-pose skin
    sh_x = 0.5 * (abs(left_sh.x - cx) + abs(right_sh.x - cx))
    sh_x = max(sh_x, torso_half * 0.95)
    left_sh = Vector((cx + sh_x, cy, sh_z))
    right_sh = Vector((cx - sh_x, cy, sh_z))

    # short clavicles from upper chest toward shoulder joint
    left_clav = Vector((cx + torso_half * 0.45, cy, sh_z + H * 0.008))
    right_clav = Vector((cx - torso_half * 0.45, cy, sh_z + H * 0.008))

    # Hands: outermost verts near shoulder height (T-pose)
    hand_band = [v for v in vs if abs(v.z - sh_z) < H * 0.12]
    lh = sorted([v for v in hand_band if v.x > cx], key=lambda v: v.x, reverse=True)
    rh = sorted([v for v in hand_band if v.x < cx], key=lambda v: v.x)
    ntip = max(12, len(lh) // 20) if lh else 1
    left_hand = avg(lh[:ntip] if lh else [], (maxx, cy, sh_z))
    right_hand = avg(rh[:ntip] if rh else [], (minx, cy, sh_z))
    # lock to shoulder height (true T)
    left_hand = Vector((max(left_hand.x, left_sh.x + W * 0.14), cy, sh_z))
    right_hand = Vector((min(right_hand.x, right_sh.x - W * 0.14), cy, sh_z))

    # Elbows: mesh mid-arm (anatomical ~ halfway shoulder-wrist, slight drop)
    def elbow_from_mesh(side):
        x0 = left_sh.x if side == "L" else right_sh.x
        x1 = left_hand.x if side == "L" else right_hand.x
        xa, xb = (min(x0, x1), max(x0, x1))
        mid = 0.5 * (x0 + x1)
        arm_mid = [
            v for v in vs
            if xa + (xb - xa) * 0.35 <= v.x <= xa + (xb - xa) * 0.65
            and abs(v.z - sh_z) < H * 0.10
        ]
        if arm_mid:
            e = avg(arm_mid, (mid, cy, sh_z))
            # slight anatomical drop (gravity hang of soft tissue) — small for robot T
            return Vector((mid, cy, min(e.z, sh_z - H * 0.01)))
        return Vector((mid, cy, sh_z - H * 0.015))

    left_elbow = elbow_from_mesh("L")
    right_elbow = elbow_from_mesh("R")
    # keep elbows between sh and hand on X
    left_elbow = Vector((
        left_sh.x * 0.48 + left_hand.x * 0.52,
        cy,
        sh_z - H * 0.012,
    ))
    right_elbow = Vector((
        right_sh.x * 0.48 + right_hand.x * 0.52,
        cy,
        sh_z - H * 0.012,
    ))

    # Legs
    foot_band = [v for v in vs if v.z <= pct(0.07)]
    lf = [v for v in foot_band if v.x >= cx]
    rf = [v for v in foot_band if v.x < cx]
    left_foot = avg(lf, (cx + W * 0.10, cy, minz + 0.02))
    right_foot = avg(rf, (cx - W * 0.10, cy, minz + 0.02))
    # hip sockets: ~femur head, slightly below pelvis bone center, lateral
    hip_w = max(torso_half * 0.55, W * 0.08)
    left_hip_j = Vector((cx + hip_w, cy, hips_z - H * 0.01))
    right_hip_j = Vector((cx - hip_w, cy, hips_z - H * 0.01))
    left_ankle = Vector((left_foot.x, left_foot.y, minz + H * 0.055))
    right_ankle = Vector((right_foot.x, right_foot.y, minz + H * 0.055))
    # knees: ~55% down femur, slight forward ( -Y front in this scene)
    def knee(hip, ankle):
        k = hip.lerp(ankle, 0.52)
        # forward offset for natural knee joint
        k.y = cy - max(D * 0.04, 0.02)
        return k
    left_knee = knee(left_hip_j, left_ankle)
    right_knee = knee(right_hip_j, right_ankle)
    # foot tip toward front (-Y)
    left_foot_tip = Vector((left_foot.x, left_foot.y - max(W * 0.06, 0.05), minz + 0.01))
    right_foot_tip = Vector((right_foot.x, right_foot.y - max(W * 0.06, 0.05), minz + 0.01))

    def bone(name, head, tail, parent):
        h, t = Vector(head), Vector(tail)
        if (t - h).length < 0.015:
            # ensure minimum bone length
            axis = (t - h)
            if axis.length < 1e-8:
                axis = Vector((0.02, 0, 0)) if abs(h.x) > abs(h.z) else Vector((0, 0, 0.02))
            else:
                axis = axis.normalized() * 0.02
            t = h + axis
        return (name, h, t, parent)

    # Hips bone: short pelvis vertical root
    hips_tail = Vector((cx, cy, hips_z + H * 0.04))
    bones_def = [
        bone("Hips", hips, hips_tail, None),
        bone("Spine", hips_tail, spine, "Hips"),
        bone("Chest", spine, chest, "Spine"),
        bone("Neck", chest, neck, "Chest"),
        bone("Head", neck, head_tail, "Neck"),
        # clavicle then arm chain
        bone("LeftShoulder", left_clav, left_sh, "Chest"),
        bone("LeftUpperArm", left_sh, left_elbow, "LeftShoulder"),
        bone("LeftLowerArm", left_elbow, left_hand, "LeftUpperArm"),
        bone("LeftHand", left_hand, left_hand + Vector((max(W * 0.035, 0.04), 0, 0)), "LeftLowerArm"),
        bone("RightShoulder", right_clav, right_sh, "Chest"),
        bone("RightUpperArm", right_sh, right_elbow, "RightShoulder"),
        bone("RightLowerArm", right_elbow, right_hand, "RightUpperArm"),
        bone("RightHand", right_hand, right_hand + Vector((-max(W * 0.035, 0.04), 0, 0)), "RightLowerArm"),
        bone("LeftUpperLeg", left_hip_j, left_knee, "Hips"),
        bone("LeftLowerLeg", left_knee, left_ankle, "LeftUpperLeg"),
        bone("LeftFoot", left_ankle, left_foot_tip, "LeftLowerLeg"),
        bone("RightUpperLeg", right_hip_j, right_knee, "Hips"),
        bone("RightLowerLeg", right_knee, right_ankle, "RightUpperLeg"),
        bone("RightFoot", right_ankle, right_foot_tip, "RightLowerLeg"),
    ]

    # ---------- create armature (edit mode with override) ----------
    arm_data = bpy.data.armatures.new("Armature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    arm_obj.show_in_front = True

    # enter edit mode robustly
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    try:
        bpy.ops.object.mode_set(mode="EDIT")
    except Exception:
        # fallback: use temporary override
        win = bpy.context.window_manager.windows[0]
        area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
        region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
        with bpy.context.temp_override(window=win, area=area, region=region, active_object=arm_obj, object=arm_obj):
            bpy.ops.object.mode_set(mode="EDIT")

    arm = arm_obj.data
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)
    created = {{}}
    for name, head, tail, parent in bones_def:
        eb = arm.edit_bones.new(name)
        eb.head = head
        eb.tail = tail
        eb.use_connect = False
        if parent and parent in created:
            eb.parent = created[parent]
        # roll: arms along X, legs along -Z roughly
        if "Arm" in name or "Hand" in name or "Shoulder" in name:
            eb.roll = 0.0
        created[name] = eb

    # store bone info before leaving edit
    bone_info = {{
        b.name: {{
            "head": [round(b.head.x, 3), round(b.head.y, 3), round(b.head.z, 3)],
            "tail": [round(b.tail.x, 3), round(b.tail.y, 3), round(b.tail.z, 3)],
            "len": round((b.tail - b.head).length, 3),
        }}
        for b in arm.edit_bones
    }}
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass

    report["bones"] = bone_info
    report["landmarks"] = {{
        "H": round(H, 3), "W": round(W, 3), "torso_half": round(torso_half, 3),
        "sh_z": round(sh_z, 3), "hips_z": round(hips_z, 3), "neck_z": round(neck_z, 3),
        "left_sh": [round(left_sh.x, 3), round(left_sh.z, 3)],
        "left_hand": [round(left_hand.x, 3), round(left_hand.z, 3)],
    }}

    # ---------- custom weights ----------
    samples = []
    arm_mw = arm_obj.matrix_world
    for b in arm_obj.data.bones:
        h = arm_mw @ b.head_local
        t = arm_mw @ b.tail_local
        samples.append((b.name, h, (h + t) * 0.5, t, (t - h)))

    for b in arm_obj.data.bones:
        main.vertex_groups.new(name=b.name)

    ARM_L = {{"LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand"}}
    ARM_R = {{"RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand"}}
    TORSO = {{"Hips", "Spine", "Chest", "Neck"}}
    LEG_L = {{"LeftUpperLeg", "LeftLowerLeg", "LeftFoot"}}
    LEG_R = {{"RightUpperLeg", "RightLowerLeg", "RightFoot"}}

    def dist_to_segment(p, a, b):
        ab = b - a
        L2 = ab.length_squared
        if L2 < 1e-12:
            return (p - a).length
        t = max(0.0, min(1.0, (p - a).dot(ab) / L2))
        return (p - (a + ab * t)).length

    def nearest_names(names, wco):
        best, bd = None, 1e18
        for n, h, m, t, _ in samples:
            if n not in names:
                continue
            d = min(dist_to_segment(wco, h, t), (wco - m).length)
            if d < bd:
                bd, best = d, n
        return best, bd

    def blend_assign(vi, pairs):
        # pairs: list of (group, weight)
        s = sum(w for _, w in pairs) or 1.0
        for g, w in pairs:
            if g in main.vertex_groups and w > 1e-4:
                main.vertex_groups[g].add([vi], w / s, "REPLACE")

    counts = {{"head": 0, "arm": 0, "torso": 0, "leg": 0}}
    mw = main.matrix_world
    for vi, v in enumerate(main.data.vertices):
        wco = mw @ v.co
        lat = abs(wco.x - cx) / max(W * 0.5, 1e-6)
        th = (wco.z - minz) / max(H, 1e-6)
        side_L = wco.x >= cx
        d_head = (wco - head_c).length

        # HEAD lock
        if d_head <= head_r and wco.z >= neck_z - H * 0.05:
            main.vertex_groups["Head"].add([vi], 1.0, "REPLACE")
            counts["head"] += 1
            continue

        # LEGS
        if th < 0.48 and lat < 0.62:
            # crotch to feet: prefer legs if below hips or outer
            if th < 0.50 or lat > 0.18:
                n0, d0 = nearest_names(LEG_L if side_L else LEG_R, wco)
                n_t, dt = nearest_names(TORSO, wco)
                if n0 and (th < 0.47 or d0 <= dt * 1.05):
                    # soft blend near hip
                    if th > 0.42 and n_t:
                        blend_assign(vi, [(n0, 0.75), (n_t, 0.25)])
                    else:
                        main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
                    counts["leg"] += 1
                    continue

        # ARMS: outside torso, around/below shoulder height
        if wco.z < neck_z - H * 0.01 and th > 0.30:
            n0, d0 = nearest_names(ARM_L if side_L else ARM_R, wco)
            n_t, dt = nearest_names(TORSO | {{"Head"}}, wco)
            arm_side_ok = lat > 0.26 or abs(wco.x) > sh_x * 0.85
            if n0 and arm_side_ok and (d0 < dt * 1.1 or lat > 0.34):
                if lat > 0.40:
                    main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
                else:
                    # shoulder root blend into chest
                    chest_w = 0.20 if "Shoulder" in (n0 or "") or "UpperArm" in (n0 or "") else 0.10
                    blend_assign(vi, [(n0, 1.0 - chest_w), ("Chest", chest_w)])
                counts["arm"] += 1
                continue

        # TORSO default
        n0, _ = nearest_names(TORSO, wco)
        if n0 is None:
            if th > 0.62:
                n0 = "Neck"
            elif th > 0.52:
                n0 = "Chest"
            elif th > 0.46:
                n0 = "Spine"
            else:
                n0 = "Hips"
        main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
        counts["torso"] += 1

    report["weight_counts"] = counts

    for mod in list(main.modifiers):
        if mod.type == "ARMATURE":
            main.modifiers.remove(mod)
    am = main.modifiers.new("Armature", "ARMATURE")
    am.object = arm_obj
    am.use_vertex_groups = True
    main.parent = arm_obj

    # shape key stubs for later VRM
    if main.data.shape_keys is None:
        main.shape_key_add(name="Basis", from_mix=False)
    for key in ["A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun"]:
        if key not in main.data.shape_keys.key_blocks:
            main.shape_key_add(name=key, from_mix=False)

    # smooth shade
    for p in main.data.polygons:
        p.use_smooth = True

    # ---------- studio + renders ----------
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.88, 0.89, 0.91, 1)
    bg.inputs[1].default_value = 1.1
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])

    def add_light(name, ltype, loc, energy, size=None):
        data = bpy.data.lights.new(name, ltype)
        data.energy = energy
        if size is not None and hasattr(data, "size"):
            data.size = size
        o = bpy.data.objects.new(name, data)
        o.location = loc
        bpy.context.scene.collection.objects.link(o)
        return o

    add_light("Key", "AREA", (2.2, -2.4, 3.0), 420, 2.5)
    add_light("Fill", "AREA", (-2.0, 1.5, 2.2), 160, 3.0)
    add_light("Sun", "SUN", (0, 0, 5), 1.8)

    cam_data = bpy.data.cameras.new("ReviewCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except Exception:
            continue
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1280
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"

    def frame_cam(az_deg=15, elev=8.0, dist=3.1):
        bpy.context.view_layer.update()
        bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
        center = sum(bb, Vector()) / 8.0
        center.z = max(0.8, center.z)
        az = math.radians(az_deg)
        el = math.radians(elev)
        loc = Vector((
            center.x + dist * math.cos(el) * math.sin(az),
            center.y - dist * math.cos(el) * math.cos(az),
            center.z + dist * math.sin(el),
        ))
        cam.location = loc
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

    def render_path(path):
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)

    # T-pose
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    frame_cam(20)
    render_path(paths["r_tpose"])

    # bones xray style: show armature, material solid
    arm_obj.hide_render = False
    # raise both arms ~70 deg up (around Y for left +X arm: rotate about -Y or local)
    # Left arm along +X: raise = rotate around Y negative? 
    # In Blender pose: for T-pose arms along X, raising arm is rotation around Y axis (forward)
    # LeftUpperArm: rotate Z or Y depending on bone roll.
    # Safer: rotate around global Y using matrix
    def raise_arm(bone_name, degrees, axis="Y"):
        pb = arm_obj.pose.bones.get(bone_name)
        if not pb:
            return
        pb.rotation_mode = "XYZ"
        r = math.radians(degrees)
        if axis == "Y":
            # left arm +X raises with -Y rot in many setups; try both via bone local
            pb.rotation_euler = Euler((0, -r if "Left" in bone_name else r, 0), "XYZ")
        elif axis == "Z":
            pb.rotation_euler = Euler((0, 0, r if "Left" in bone_name else -r), "XYZ")

    # Try anatomically raise: UpperArm bend upward (Z-up world)
    # For bone along +X, rotation around Y lifts toward +Z
    for name, sign in (("LeftUpperArm", -1), ("RightUpperArm", 1)):
        pb = arm_obj.pose.bones.get(name)
        if pb:
            pb.rotation_mode = "XYZ"
            # local Y rotation often lifts T-pose arm
            pb.rotation_euler = Euler((0.0, sign * math.radians(-70), 0.0), "XYZ")
    bpy.context.view_layer.update()
    frame_cam(25)
    render_path(paths["r_raise"])

    # wave-ish: one arm up more, slight elbow
    for pb in arm_obj.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    pb = arm_obj.pose.bones.get("LeftUpperArm")
    if pb:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler((0.0, math.radians(-85), math.radians(15)), "XYZ")
    pb = arm_obj.pose.bones.get("LeftLowerArm")
    if pb:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler((0.0, 0.0, math.radians(-35)), "XYZ")
    bpy.context.view_layer.update()
    frame_cam(30)
    render_path(paths["r_wave"])

    # reset pose for save
    for pb in arm_obj.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    # bones preview: armature in front, wire
    arm_obj.show_in_front = True
    arm_obj.hide_render = False
    try:
        arm_data.display_type = "OCTAHEDRAL"
    except Exception:
        pass
    frame_cam(40, elev=12, dist=3.2)
    # also set viewport display
    render_path(paths["r_bones"])

    # export rigged glb
    for o in bpy.data.objects:
        o.select_set(o in (main, arm_obj))
    try:
        bpy.context.view_layer.objects.active = arm_obj
    except Exception:
        pass
    bpy.ops.export_scene.gltf(
        filepath=paths["glb"],
        use_selection=True,
        export_format="GLB",
        export_skins=True,
        export_morph=True,
        export_animations=False,
        export_apply=False,
    )
    bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])

    report["status"] = "ok"
    report["mesh"] = main.name
    report["armature"] = arm_obj.name
    report["verts"] = len(main.data.vertices)
    report["faces"] = len(main.data.polygons)
    report["vgroups"] = [g.name for g in main.vertex_groups]
    result = report
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if payload.get("status") != "ok":
        return 2

    if BLEND_OUT.is_file():
        shutil.copyfile(BLEND_OUT, BLEND_MAIN)
        print("updated", BLEND_MAIN)

    for p in (
        BLEND_OUT,
        GLB_OUT,
        EXPORTS / "viewport_rig_tpose.png",
        EXPORTS / "viewport_rig_raise_arms.png",
        EXPORTS / "viewport_rig_wave.png",
        EXPORTS / "viewport_rig_bones.png",
    ):
        print(("OK" if p.is_file() else "MISS"), p.name, p.stat().st_size if p.is_file() else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
