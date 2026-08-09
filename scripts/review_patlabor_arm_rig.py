#!/usr/bin/env python3
"""Review current Blender session / saved blend arm rig after user edits."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3.blend")
EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "r_tpose": str(EXPORTS / "viewport_user_tpose.png").replace("\\", "/"),
        "r_raise": str(EXPORTS / "viewport_user_raise.png").replace("\\", "/"),
        "r_side": str(EXPORTS / "viewport_user_raise_side.png").replace("\\", "/"),
        "r_wave": str(EXPORTS / "viewport_user_wave.png").replace("\\", "/"),
    }

    code = f'''
import bpy
import math
from mathutils import Vector, Matrix, Quaternion

paths = {repr(paths)}
# ensure math available
_ = math.pi

# Prefer currently open scene if already has our mesh+armature
main = next((o for o in bpy.data.objects if o.type == "MESH" and "Mecha" in o.name), None)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
loaded = "session"
if main is None or arm is None:
    bpy.ops.wm.open_mainfile(filepath=paths["blend"])
    main = next(o for o in bpy.data.objects if o.type == "MESH")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    loaded = "file"

# reset pose first
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

# bone report in rest
issues = []
bones = {{}}
required = [
    "Hips","Spine","Chest","Neck","Head",
    "LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand",
    "RightShoulder","RightUpperArm","RightLowerArm","RightHand",
    "LeftUpperLeg","LeftLowerLeg","LeftFoot",
    "RightUpperLeg","RightLowerLeg","RightFoot",
]
for name in required:
    b = arm.data.bones.get(name)
    if not b:
        issues.append(f"missing:{{name}}")
        continue
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    ln = (t - h).length
    bones[name] = {{
        "head": [round(h.x, 3), round(h.y, 3), round(h.z, 3)],
        "tail": [round(t.x, 3), round(t.y, 3), round(t.z, 3)],
        "len": round(ln, 3),
        "parent": b.parent.name if b.parent else None,
    }}
    if ln < 0.012:
        issues.append(f"short:{{name}}={{ln:.4f}}")

# arm chain continuity (head of child ~ tail of parent)
def near(a, b, eps=0.05):
    return (Vector(a) - Vector(b)).length <= eps

for side in ("Left", "Right"):
    sh = bones.get(f"{{side}}Shoulder")
    ua = bones.get(f"{{side}}UpperArm")
    la = bones.get(f"{{side}}LowerArm")
    ha = bones.get(f"{{side}}Hand")
    if not all((sh, ua, la, ha)):
        continue
    if not near(ua["head"], sh["tail"], 0.08):
        issues.append(f"{{side}} UpperArm head not at Shoulder tail dist={{(Vector(ua['head'])-Vector(sh['tail'])).length:.3f}}")
    if not near(la["head"], ua["tail"], 0.08):
        issues.append(f"{{side}} LowerArm head not at UpperArm tail dist={{(Vector(la['head'])-Vector(ua['tail'])).length:.3f}}")
    if not near(ha["head"], la["tail"], 0.08):
        issues.append(f"{{side}} Hand head not at LowerArm tail dist={{(Vector(ha['head'])-Vector(la['tail'])).length:.3f}}")
    # T-pose-ish: hands outside shoulders
    if side == "Left" and ha["head"][0] <= sh["tail"][0]:
        issues.append("Left hand not outside shoulder on +X")
    if side == "Right" and ha["head"][0] >= sh["tail"][0]:
        issues.append("Right hand not outside shoulder on -X")
    # shoulder height similar
    if abs(sh["tail"][2] - ua["head"][2]) > 0.12:
        issues.append(f"{{side}} shoulder/upper height mismatch")

# spine continuity
for a, b in (("Hips","Spine"),("Spine","Chest"),("Chest","Neck"),("Neck","Head")):
    if a in bones and b in bones:
        d = (Vector(bones[b]["head"]) - Vector(bones[a]["tail"])).length
        if d > 0.08:
            issues.append(f"spine gap {{a}}->{{b}} d={{d:.3f}}")

# weights
vg = [g.name for g in main.vertex_groups]
missing_vg = [n for n in required if n not in vg]
if missing_vg:
    issues.append("missing_vgroups:" + ",".join(missing_vg))
has_arm_mod = any(m.type == "ARMATURE" and m.object == arm for m in main.modifiers)
if not has_arm_mod:
    issues.append("no Armature modifier linked")

# dimensions
dims = [round(float(x), 3) for x in main.dimensions]

# pose tests + renders
cam = bpy.context.scene.camera
if cam is None:
    cd = bpy.data.cameras.new("ReviewCam")
    cam = bpy.data.objects.new("ReviewCam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

def frame(az=20, elev=8, dist=3.1):
    bpy.context.view_layer.update()
    bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bb, Vector()) / 8.0
    center.z = max(0.8, center.z)
    azr, el = math.radians(az), math.radians(elev)
    loc = Vector((
        center.x + dist * math.cos(el) * math.sin(azr),
        center.y - dist * math.cos(el) * math.cos(azr),
        center.z + dist * math.sin(el),
    ))
    cam.location = loc
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.resolution_x = 1024
scene.render.resolution_y = 1280
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass

def rend(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def world_rot(pb, axis, degrees):
    pb.rotation_mode = "QUATERNION"
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest = pb.matrix.copy()
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    R = Matrix.Rotation(math.radians(degrees), 4, axis)
    head = rest.translation
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ rest
    bpy.context.view_layer.update()

def reset():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1,0,0,0))
        pb.location = (0,0,0)
        pb.scale = (1,1,1)
    bpy.context.view_layer.update()

reset()
frame(20)
rend(paths["r_tpose"])

reset()
if "LeftUpperArm" in arm.pose.bones and "RightUpperArm" in arm.pose.bones:
    world_rot(arm.pose.bones["LeftUpperArm"], "Y", -80)
    world_rot(arm.pose.bones["RightUpperArm"], "Y", 80)
frame(15)
rend(paths["r_raise"])
frame(90, elev=5, dist=2.8)
rend(paths["r_side"])

reset()
if "LeftUpperArm" in arm.pose.bones:
    world_rot(arm.pose.bones["LeftUpperArm"], "Y", -100)
if "LeftLowerArm" in arm.pose.bones:
    world_rot(arm.pose.bones["LeftLowerArm"], "Z", -40)
frame(25)
rend(paths["r_wave"])

reset()

# severity
critical = [i for i in issues if i.startswith("missing") or "no Armature" in i]
warn = [i for i in issues if i not in critical]
ok_for_warudo = len(critical) == 0

result = {{
    "status": "ok",
    "loaded_from": loaded,
    "mesh": main.name,
    "armature": arm.name,
    "verts": len(main.data.vertices),
    "faces": len(main.data.polygons),
    "dims": dims,
    "bone_count": len(arm.data.bones),
    "bones": bones,
    "vertex_groups": len(vg),
    "has_armature_mod": has_arm_mod,
    "issues": issues,
    "critical": critical,
    "warnings": warn,
    "ok_for_warudo": ok_for_warudo,
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
