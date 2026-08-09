#!/usr/bin/env python3
"""Diagnose hole regions + why head/arms may not move (weights / VRM / armature)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3.blend"


def main() -> int:
    code = f'''
import bpy
import bmesh
from collections import defaultdict
from mathutils import Vector, Quaternion

bpy.ops.wm.open_mainfile(filepath=r"{BLEND}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# rest pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)

# --- armature / weights ---
mods = [{{"name": m.name, "type": m.type, "object": m.object.name if getattr(m, "object", None) else None, "show_viewport": m.show_viewport, "show_render": m.show_render}} for m in main.modifiers]
vgroups = [g.name for g in main.vertex_groups]
bones = [b.name for b in arm.data.bones]
parents = {{b.name: b.parent.name if b.parent else None for b in arm.data.bones}}

# weight stats per bone
weight_stats = {{}}
for g in main.vertex_groups:
    total = 0.0
    count = 0
    maxw = 0.0
    for v in main.data.vertices:
        for ge in v.groups:
            if ge.group == g.index and ge.weight > 1e-4:
                total += ge.weight
                count += 1
                maxw = max(maxw, ge.weight)
    weight_stats[g.name] = {{"verts": count, "sum": round(total, 2), "max": round(maxw, 3)}}

# vertices with zero total weight
zero_w = 0
multi_heavy = 0
for v in main.data.vertices:
    s = sum(ge.weight for ge in v.groups)
    if s < 1e-4:
        zero_w += 1
    if sum(1 for ge in v.groups if ge.weight > 0.5) >= 2:
        multi_heavy += 1

# pose test: rotate head and left arm, measure vertex delta
import copy
coords0 = [v.co.copy() for v in main.data.vertices]
# head
pb = arm.pose.bones.get("Head")
if pb:
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0.4, 0, 0.3)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
obj_eval = main.evaluated_get(deps)
me_eval = obj_eval.to_mesh()
max_d_head = 0.0
for i, v in enumerate(me_eval.vertices):
    d = (v.co - coords0[i]).length
    if d > max_d_head:
        max_d_head = d
obj_eval.to_mesh_clear()
# reset head
pb.rotation_euler = (0,0,0)
bpy.context.view_layer.update()

# left upper arm
pb2 = arm.pose.bones.get("LeftUpperArm")
if pb2:
    pb2.rotation_mode = "XYZ"
    pb2.rotation_euler = (0, -0.8, 0)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
obj_eval = main.evaluated_get(deps)
me_eval = obj_eval.to_mesh()
max_d_arm = 0.0
moved_arm = 0
for i, v in enumerate(me_eval.vertices):
    d = (v.co - coords0[i]).length
    if d > max_d_arm:
        max_d_arm = d
    if d > 0.002:
        moved_arm += 1
obj_eval.to_mesh_clear()
pb2.rotation_euler = (0,0,0)
bpy.context.view_layer.update()

# VRM mapping
ext = getattr(arm.data, "vrm_addon_extension", None)
vrm1 = {{}}
if ext:
    try:
        hb = ext.vrm1.humanoid.human_bones
        for name in ("head","neck","left_upper_arm","left_lower_arm","left_hand","left_shoulder","hips","spine","chest"):
            slot = getattr(hb, name, None)
            vrm1[name] = slot.node.bone_name if slot and slot.node else None
    except Exception as e:
        vrm1 = {{"err": str(e)}}

# --- boundary holes by region ---
bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
boundary = [e for e in bm.edges if e.is_boundary]
# loops
adj = defaultdict(set)
for e in boundary:
    a,b = e.verts
    adj[a.index].add(b.index)
    adj[b.index].add(a.index)
vis=set(); loops=[]
for vid in list(adj.keys()):
    if vid in vis: continue
    stack=[vid]; vis.add(vid); comp=[]
    while stack:
        u=stack.pop(); comp.append(u)
        for v in adj[u]:
            if v not in vis:
                vis.add(v); stack.append(v)
    loops.append(comp)
coords={{v.index: v.co.copy() for v in bm.verts}}
minz=min(c.z for c in coords.values()); maxz=max(c.z for c in coords.values()); H=maxz-minz
cx=sum(c.x for c in coords.values())/len(coords)

def reg(z,x):
    t=(z-minz)/H
    if t>0.70: return "head_neck"
    if t>0.55: return "upper_torso"
    if t>0.40: return "torso"
    if abs(x-cx)>0.25 and t>0.45: return "arm"
    if t>0.15: return "pants"
    return "feet"

region_loops=defaultdict(list)
for comp in loops:
    if len(comp)<6: continue
    pts=[coords[i] for i in comp]
    z=sum(p.z for p in pts)/len(pts)
    x=sum(p.x for p in pts)/len(pts)
    r=reg(z,x)
    # left bias
    side="L" if x>=cx else "R"
    region_loops[f"{{r}}_{{side}}"].append(len(comp))

# open edges near neck / left arm / left torso
def count_boundary_in_box(x0,x1,z0,z1):
    n=0
    for e in boundary:
        for v in e.verts:
            p=v.co
            if x0<=p.x<=x1 and z0<=p.z<=z1:
                n+=1
                break
    return n

holes = {{
    "neck_band": count_boundary_in_box(-0.15,0.15,1.05,1.20),
    "left_arm": count_boundary_in_box(0.25,0.70,0.85,1.15),
    "left_torso": count_boundary_in_box(0.05,0.35,0.75,1.05),
    "total_boundary_edges": len(boundary),
    "loops_ge6": sum(1 for c in loops if len(c)>=6),
}}

bm.free()

result = {{
    "status": "ok",
    "modifiers": mods,
    "parent": main.parent.name if main.parent else None,
    "bone_count": len(bones),
    "parents": parents,
    "weight_stats_key": {{k: weight_stats[k] for k in ("Head","Neck","Chest","LeftUpperArm","LeftLowerArm","LeftHand","LeftShoulder","Hips") if k in weight_stats}},
    "zero_weight_verts": zero_w,
    "pose_max_delta_head": round(max_d_head, 5),
    "pose_max_delta_left_arm": round(max_d_arm, 5),
    "pose_moved_verts_left_arm": moved_arm,
    "vrm1_map": vrm1,
    "holes": holes,
    "region_loop_sizes": {{k: sorted(v, reverse=True)[:5] for k,v in region_loops.items()}},
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
