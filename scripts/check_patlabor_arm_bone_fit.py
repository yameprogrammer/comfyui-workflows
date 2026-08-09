#!/usr/bin/env python3
"""Check whether arm bones stay inside mesh envelope."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3.blend"
OUT = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/viewport_arm_bone_fit.png"


def main() -> int:
    code = f'''
import bpy
import math
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import bmesh

bpy.ops.wm.open_mainfile(filepath=r"{BLEND}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# rest pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)
bpy.context.view_layer.update()

# BVH in world space
deps = bpy.context.evaluated_depsgraph_get()
obj_eval = main.evaluated_get(deps)
bm = bmesh.new()
bm.from_object(obj_eval, deps)
bm.transform(main.matrix_world)
bmesh.ops.triangulate(bm, faces=bm.faces)
bvh = BVHTree.FromBMesh(bm)

def nearest_dist(p: Vector):
    loc, normal, idx, dist = bvh.find_nearest(p)
    return dist, loc, normal

def sample_bone(name, n=12):
    b = arm.data.bones.get(name)
    if not b:
        return None
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    pts = []
    for i in range(n + 1):
        u = i / n
        p = h.lerp(t, u)
        d, loc, nrm = nearest_dist(p)
        # sign: if raycast outward? use inside test via raycast from far
        # Approximate: if point is outside, nearest normal points away and p is outside surface
        # Better inside test: cast many rays
        inside = point_inside(p)
        pts.append({{
            "u": round(u, 2),
            "p": [round(p.x, 3), round(p.y, 3), round(p.z, 3)],
            "nearest_dist": round(float(d), 4),
            "inside": inside,
        }})
    return {{
        "name": name,
        "head": [round(h.x, 3), round(h.y, 3), round(h.z, 3)],
        "tail": [round(t.x, 3), round(t.y, 3), round(t.z, 3)],
        "len": round((t - h).length, 3),
        "samples": pts,
        "outside_count": sum(1 for s in pts if not s["inside"]),
        "max_dist": max(s["nearest_dist"] for s in pts),
        "mean_dist": round(sum(s["nearest_dist"] for s in pts) / len(pts), 4),
    }}

def point_inside(p, rays=16):
    # count hits with odd/even from random directions; mesh may be open so also use threshold
    import random
    hits = 0
    for i in range(rays):
        # quasi directions
        a = (i + 0.5) / rays * math.pi * 2
        b = (i * 0.37) % math.pi - math.pi/2
        d = Vector((math.cos(a)*math.cos(b), math.sin(a)*math.cos(b), math.sin(b)))
        hit = bvh.ray_cast(p, d)
        if hit[0] is not None:
            hits += 1
    # open mesh: prefer distance-based: if nearest dist small AND local verts surround
    d, loc, nrm = nearest_dist(p)
    # For thin limbs: inside if dist to surface less than local radius estimate
    # radius estimate: average dist of nearby surface? use 5cm default limb half-width
    # outside if nearest surface is far (>4cm) OR point is outside by normal side
    if loc is None:
        return False
    to_p = p - loc
    # if normal points toward point from surface, point is outside
    if nrm is not None and to_p.length > 1e-6:
        if nrm.dot(to_p.normalized()) > 0.15 and d > 0.008:
            return False
    # close to surface or inside
    return d < 0.06

arm_bones = [
    "LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand",
    "RightShoulder","RightUpperArm","RightLowerArm","RightHand",
]
reports = []
for name in arm_bones:
    r = sample_bone(name)
    if r:
        reports.append(r)

# also compare forearm axis vs mesh arm axis (PCA of arm verts)
def arm_mesh_axis(side):
    # verts weighted to this side arm groups
    names = [f"{{side}}UpperArm", f"{{side}}LowerArm", f"{{side}}Hand", f"{{side}}Shoulder"]
    idxs = set()
    for n in names:
        vg = main.vertex_groups.get(n)
        if not vg:
            continue
        for v in main.data.vertices:
            for g in v.groups:
                if g.group == vg.index and g.weight > 0.3:
                    idxs.add(v.index)
    if not idxs:
        return None
    pts = [main.matrix_world @ main.data.vertices[i].co for i in idxs]
    c = sum(pts, Vector()) / len(pts)
    # extreme x as hand-ish
    if side == "Left":
        tip = max(pts, key=lambda p: p.x)
        root = min(pts, key=lambda p: p.x)
    else:
        tip = min(pts, key=lambda p: p.x)
        root = max(pts, key=lambda p: p.x)
    axis = (tip - root).normalized()
    return {{
        "root": [round(root.x,3), round(root.y,3), round(root.z,3)],
        "tip": [round(tip.x,3), round(tip.y,3), round(tip.z,3)],
        "axis": [round(axis.x,3), round(axis.y,3), round(axis.z,3)],
        "nverts": len(pts),
        "center": [round(c.x,3), round(c.y,3), round(c.z,3)],
    }}

# bone chain axis
def bone_axis(name):
    b = arm.data.bones[name]
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    a = (t - h)
    if a.length < 1e-8:
        return None
    a.normalize()
    return a

align = {{}}
for side in ("Left", "Right"):
    mesh_ax = arm_mesh_axis(side)
    ba = bone_axis(f"{{side}}LowerArm")
    ua = bone_axis(f"{{side}}UpperArm")
    if mesh_ax and ba:
        mesh_v = Vector(mesh_ax["axis"])
        # angle between forearm bone and mesh arm direction
        ang = math.degrees(ba.angle(mesh_v))
        if ang > 90:
            ang = 180 - ang
        align[side] = {{
            "mesh": mesh_ax,
            "lower_bone_axis": [round(ba.x,3), round(ba.y,3), round(ba.z,3)],
            "upper_bone_axis": [round(ua.x,3), round(ua.y,3), round(ua.z,3)] if ua else None,
            "angle_deg_lower_vs_mesh": round(ang, 1),
        }}

# render overlay: show armature in front
arm.show_in_front = True
arm.data.display_type = "OCTAHEDRAL"
try:
    arm.data.show_names = True
except Exception:
    pass
# viewport display solid for mesh
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.hide_render = False

cam = bpy.context.scene.camera
if not cam:
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
# front slightly high
bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bb, Vector())/8
cam.location = (center.x + 0.2, center.y - 2.6, center.z + 0.35)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.resolution_x = 1280
scene.render.resolution_y = 1280
scene.render.film_transparent = True
scene.render.filepath = r"{OUT}"
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass
bpy.ops.render.render(write_still=True)

# judgment
problems = []
for r in reports:
    if r["name"].endswith("LowerArm") or r["name"].endswith("UpperArm"):
        if r["outside_count"] >= 4:
            problems.append(f"{{r['name']}}: {{r['outside_count']}}/13 samples outside mesh (max_dist={{r['max_dist']}})")
        if r["mean_dist"] > 0.04:
            problems.append(f"{{r['name']}}: mean surface dist {{r['mean_dist']}}m (bone far from surface center?)")
for side, a in align.items():
    if a["angle_deg_lower_vs_mesh"] > 25:
        problems.append(f"{{side}}LowerArm angle vs mesh arm {{a['angle_deg_lower_vs_mesh']}}deg")

bm.free()
result = {{
    "status": "ok",
    "bones": reports,
    "align": align,
    "problems": problems,
    "verdict": "bad" if problems else "ok_or_borderline",
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
