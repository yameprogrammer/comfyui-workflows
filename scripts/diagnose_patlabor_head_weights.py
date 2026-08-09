#!/usr/bin/env python3
"""Diagnose head/neck/face skin weights for mecha_patlabor_v3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3_warudo_rebuild.blend"


def main() -> int:
    code = f'''
import bpy
from mathutils import Vector, Quaternion
from collections import defaultdict

bpy.ops.wm.open_mainfile(filepath=r"{BLEND}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
mw = mesh.matrix_world

# clear pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)

bones = {{}}
for name in ["Hips", "Spine", "Chest", "Neck", "Head"]:
    b = arm.data.bones[name]
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    bones[name] = {{
        "h": [round(float(x), 4) for x in h],
        "t": [round(float(x), 4) for x in t],
        "len": round(float(b.length), 4),
        "parent": b.parent.name if b.parent else None,
    }}

# weight mass
mass = defaultdict(float)
for v in mesh.data.vertices:
    for g in v.groups:
        mass[mesh.vertex_groups[g.group].name] += g.weight

# face/head region analysis (z high)
# screen face is front of big head
regions = {{
    "skull": [],   # z>1.15
    "face_front": [],  # z>1.05, y front
    "neck_band": [],
    "jaw_like": [],
}}
bad_mix = []
for v in mesh.data.vertices:
    p = mw @ v.co
    w = {{mesh.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 0.01}}
    if not w:
        continue
    entry = {{
        "p": [round(p.x, 3), round(p.y, 3), round(p.z, 3)],
        "w": {{k: round(v, 2) for k, v in sorted(w.items(), key=lambda x: -x[1])[:6]}},
        "head": round(w.get("Head", 0), 2),
        "neck": round(w.get("Neck", 0), 2),
        "chest": round(w.get("Chest", 0), 2),
        "other_arm": round(sum(w.get(a, 0) for a in [
            "LeftShoulder","LeftUpperArm","RightShoulder","RightUpperArm",
            "LeftLowerArm","RightLowerArm","LeftHand","RightHand",
        ]), 2),
    }}
    if p.z > 1.15:
        regions["skull"].append(entry)
    if p.z > 1.05 and p.y < -0.05:  # front face (Blender -Y often forward? check)
        regions["face_front"].append(entry)
    if 1.00 < p.z < 1.12 and abs(p.x) < 0.15:
        regions["neck_band"].append(entry)

# also try +Y as front
face_pos_y = []
face_neg_y = []
for v in mesh.data.vertices:
    p = mw @ v.co
    if p.z < 1.08 or p.z > 1.45:
        continue
    if abs(p.x) > 0.25:
        continue
    w = {{mesh.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 0.01}}
    e = {{
        "p": [round(p.x, 3), round(p.y, 3), round(p.z, 3)],
        "w": {{k: round(vv, 2) for k, vv in sorted(w.items(), key=lambda x: -x[1])[:5]}},
        "head": round(w.get("Head", 0), 2),
        "neck": round(w.get("Neck", 0), 2),
    }}
    if p.y > 0.08:
        face_pos_y.append(e)
    if p.y < -0.08:
        face_neg_y.append(e)

def stats(entries):
    if not entries:
        return {{"n": 0}}
    n = len(entries)
    avg_head = sum(e["head"] for e in entries) / n
    avg_neck = sum(e["neck"] for e in entries) / n
    avg_chest = sum(e.get("chest", 0) for e in entries) / n
    avg_arm = sum(e.get("other_arm", 0) for e in entries) / n
    # fraction with head < 0.7
    weak_head = sum(1 for e in entries if e["head"] < 0.7) / n
    multi = sum(1 for e in entries if e["head"] > 0.1 and e["neck"] > 0.15) / n
    return {{
        "n": n,
        "avg_head": round(avg_head, 3),
        "avg_neck": round(avg_neck, 3),
        "avg_chest": round(avg_chest, 3),
        "avg_arm": round(avg_arm, 3),
        "frac_weak_head": round(weak_head, 3),
        "frac_head_neck_mix": round(multi, 3),
        "samples": entries[:8],
    }}

# pose head and measure max vertex delta on face
def face_centroid_and_spread(group_thr=0.3):
    deps = bpy.context.evaluated_depsgraph_get()
    me = mesh.evaluated_get(deps).to_mesh()
    # use original groups
    pts = []
    for i, v in enumerate(me.vertices):
        ov = mesh.data.vertices[i]
        hw = 0
        for g in ov.groups:
            if mesh.vertex_groups[g.group].name == "Head" and g.weight > group_thr:
                hw = g.weight
                break
        if hw > group_thr:
            pts.append(mw @ v.co)
    mesh.evaluated_get(deps).to_mesh_clear()
    if not pts:
        return None
    c = sum(pts, Vector()) / len(pts)
    # max dist from centroid
    md = max((p - c).length for p in pts)
    return {{
        "c": [round(float(x), 4) for x in c],
        "spread": round(float(md), 4),
        "n": len(pts),
    }}

rest = face_centroid_and_spread()
# rotate head
window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
    bpy.ops.object.mode_set(mode="POSE")
arm.pose.bones["Head"].rotation_mode = "XYZ"
arm.pose.bones["Head"].rotation_euler = (0.7, 0.4, 0.3)
with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()
posed = face_centroid_and_spread()

# measure non-rigid: compare relative positions of face verts
# sample pairs of high-head-weight verts distance change
import random
random.seed(0)
head_idx = []
for v in mesh.data.vertices:
    for g in v.groups:
        if mesh.vertex_groups[g.group].name == "Head" and g.weight > 0.8:
            head_idx.append(v.index)
            break
# rest positions stored before pose? need re-clear and store
# re-open approach: store rest from bone bind — use undeformed mesh.data for rest, eval for posed

def pair_dist_change(n_pairs=40):
    if len(head_idx) < 10:
        return None
    rest_pos = {{i: mw @ mesh.data.vertices[i].co for i in head_idx}}
    deps = bpy.context.evaluated_depsgraph_get()
    me = mesh.evaluated_get(deps).to_mesh()
    posed_pos = {{i: mw @ me.vertices[i].co for i in head_idx}}
    mesh.evaluated_get(deps).to_mesh_clear()
    ratios = []
    for _ in range(n_pairs):
        a, b = random.sample(head_idx, 2)
        dr = (rest_pos[a] - rest_pos[b]).length
        dp = (posed_pos[a] - posed_pos[b]).length
        if dr > 0.01:
            ratios.append(dp / dr)
    return {{
        "mean_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
        "min_ratio": round(min(ratios), 4) if ratios else None,
        "max_ratio": round(max(ratios), 4) if ratios else None,
        "n_head_verts": len(head_idx),
    }}

rigid = pair_dist_change()

result = {{
    "bones": bones,
    "mass_top": {{k: round(v, 1) for k, v in sorted(mass.items(), key=lambda x: -x[1])[:20]}},
    "skull": stats(regions["skull"]),
    "neck_band": stats(regions["neck_band"]),
    "face_pos_y": stats([{{**e, "chest": 0, "other_arm": 0}} for e in face_pos_y]),
    "face_neg_y": stats([{{**e, "chest": 0, "other_arm": 0}} for e in face_neg_y]),
    "rest_face": rest,
    "posed_face": posed,
    "rigid_check": rigid,
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
