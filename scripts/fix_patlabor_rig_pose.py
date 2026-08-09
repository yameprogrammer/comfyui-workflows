#!/usr/bin/env python3
"""Fix spine chain continuity and re-test arm poses with world-axis rotations."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3_rigged.blend"
BLEND_MAIN = EXPORTS / "mecha_patlabor_v3.blend"


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "blend_main": str(BLEND_MAIN).replace("\\", "/"),
        "r_raise": str(EXPORTS / "viewport_rig_raise_arms.png").replace("\\", "/"),
        "r_wave": str(EXPORTS / "viewport_rig_wave.png").replace("\\", "/"),
        "r_tpose": str(EXPORTS / "viewport_rig_tpose.png").replace("\\", "/"),
        "r_side_raise": str(EXPORTS / "viewport_rig_raise_side.png").replace("\\", "/"),
    }

    code = f'''
import bpy
import math
import shutil
from mathutils import Vector, Matrix, Quaternion

paths = {repr(paths)}
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# MCP-safe mode switch
for o in bpy.data.objects:
    o.select_set(o == arm)
win = bpy.context.window_manager.windows[0]
area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
with bpy.context.temp_override(window=win, area=area, region=region, active_object=arm, object=arm, selected_editable_objects=[arm]):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
hips = eb["Hips"]
spine = eb["Spine"]
chest = eb["Chest"]
neck = eb["Neck"]
head = eb["Head"]

z_hips = hips.head.z
z_head_j = head.head.z
cx, cy = hips.head.x, hips.head.y
zs = [
    z_hips,
    z_hips + (z_head_j - z_hips) * 0.18,
    z_hips + (z_head_j - z_hips) * 0.42,
    z_hips + (z_head_j - z_hips) * 0.70,
    z_head_j,
]
hips.head = Vector((cx, cy, zs[0]))
hips.tail = Vector((cx, cy, zs[1]))
spine.head = Vector((cx, cy, zs[1]))
spine.tail = Vector((cx, cy, zs[2]))
chest.head = Vector((cx, cy, zs[2]))
chest.tail = Vector((cx, cy, zs[3]))
neck.head = Vector((cx, cy, zs[3]))
neck.tail = Vector((cx, cy, zs[4]))
head.head = Vector((head.head.x, head.head.y, zs[4]))

spine.parent = hips
chest.parent = spine
neck.parent = chest
head.parent = neck
eb["LeftShoulder"].parent = chest
eb["RightShoulder"].parent = chest

for side in ("Left", "Right"):
    sh = eb[f"{{side}}Shoulder"]
    ua = eb[f"{{side}}UpperArm"]
    la = eb[f"{{side}}LowerArm"]
    ha = eb[f"{{side}}Hand"]
    ua.head = sh.tail.copy()
    la.head = ua.tail.copy()
    ha.head = la.tail.copy()
    ua.parent = sh
    la.parent = ua
    ha.parent = la
    sh.parent = chest

for side in ("Left", "Right"):
    ul = eb[f"{{side}}UpperLeg"]
    ll = eb[f"{{side}}LowerLeg"]
    ft = eb[f"{{side}}Foot"]
    ll.head = ul.tail.copy()
    ft.head = ll.tail.copy()
    ul.parent = hips
    ll.parent = ul
    ft.parent = ll

bone_info = {{
    b.name: {{
        "head": [round(b.head.x, 3), round(b.head.y, 3), round(b.head.z, 3)],
        "tail": [round(b.tail.x, 3), round(b.tail.y, 3), round(b.tail.z, 3)],
        "len": round((b.tail - b.head).length, 3),
    }}
    for b in eb
}}
with bpy.context.temp_override(window=win, area=area, region=region, active_object=arm, object=arm):
    bpy.ops.object.mode_set(mode="OBJECT")

def world_rot(pb, axis, degrees):
    pb.rotation_mode = "QUATERNION"
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest = pb.matrix.copy()
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    R = Matrix.Rotation(math.radians(degrees), 4, axis)
    head = rest.translation
    T1 = Matrix.Translation(head)
    T0 = Matrix.Translation(-head)
    pb.matrix = T1 @ R @ T0 @ rest
    bpy.context.view_layer.update()

def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

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

reset_pose()
frame(20)
rend(paths["r_tpose"])

reset_pose()
world_rot(arm.pose.bones["LeftUpperArm"], "Y", -80)
world_rot(arm.pose.bones["RightUpperArm"], "Y", 80)
frame(15)
rend(paths["r_raise"])
frame(90, elev=5, dist=2.8)
rend(paths["r_side_raise"])

reset_pose()
world_rot(arm.pose.bones["LeftUpperArm"], "Y", -100)
world_rot(arm.pose.bones["LeftLowerArm"], "Z", -40)
frame(25)
rend(paths["r_wave"])

reset_pose()
bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
shutil.copyfile(paths["blend"], paths["blend_main"])

result = {{"status": "ok", "bones": bone_info}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    return 0 if payload.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
