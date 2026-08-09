#!/usr/bin/env python3
"""Inspect mecha_patlabor_v3.blend rest bones without saving."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3.blend")


def main() -> int:
    blend = str(BLEND).replace("\\", "/")
    code = f'''
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"{blend}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")

bones = []
for b in arm.data.bones:
    m = b.matrix_local
    loc, rot, sc = m.decompose()
    eul = rot.to_euler("XYZ")
    # world direction of bone
    head = arm.matrix_world @ b.head_local
    tail = arm.matrix_world @ b.tail_local
    direction = (tail - head).normalized() if (tail - head).length > 1e-8 else Vector((0,0,0))
    bones.append({{
        "name": b.name,
        "parent": b.parent.name if b.parent else None,
        "head": [round(x, 4) for x in head],
        "tail": [round(x, 4) for x in tail],
        "length": round(b.length, 4),
        "dir": [round(x, 4) for x in direction],
        "rot_euler": [round(x, 4) for x in eul],
        "use_connect": b.use_connect,
    }})

pose_nonid = []
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    q = pb.rotation_quaternion
    if abs(q.w - 1) > 1e-4 or abs(q.x) > 1e-4 or abs(q.y) > 1e-4 or abs(q.z) > 1e-4:
        pose_nonid.append(pb.name)

import collections
weights = collections.defaultdict(float)
for v in mesh.data.vertices:
    for g in v.groups:
        weights[mesh.vertex_groups[g.group].name] += g.weight
top = sorted(weights.items(), key=lambda x: -x[1])[:25]

# arm horizontal check
def bone_world(name):
    b = arm.data.bones[name]
    head = arm.matrix_world @ b.head_local
    tail = arm.matrix_world @ b.tail_local
    return head, tail

checks = {{}}
for nm in ["LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "Head", "Neck"]:
    if nm in arm.data.bones:
        h, t = bone_world(nm)
        checks[nm] = {{
            "head": [round(x, 4) for x in h],
            "tail": [round(x, 4) for x in t],
            "dx": round(t.x - h.x, 4),
            "dy": round(t.y - h.y, 4),
            "dz": round(t.z - h.z, 4),
        }}

result = {{
    "arm_name": arm.name,
    "mesh_name": mesh.name,
    "bone_count": len(bones),
    "bones": bones,
    "pose_nonidentity": pose_nonid,
    "weight_mass_top": [(n, round(w, 2)) for n, w in top],
    "arm_geometry": checks,
    "mesh_dims": {{
        "verts": len(mesh.data.vertices),
        "bbox": [list(mesh.bound_box[i]) for i in (0, 6)],
    }},
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
