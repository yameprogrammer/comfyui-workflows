#!/usr/bin/env python3
"""Ensure mesh has armature skin weights; re-export VRM/GLB."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX = EXPORTS / "mecha_yame_v2.fbx"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_refit.glb")


def main() -> int:
    p = {k: str(v).replace("\\", "/") for k, v in {
        "blend": BLEND, "vrm": VRM, "vrm2": VRM2, "temp": TEMP, "fbx": FBX,
    }.items()}

    code = f'''
import bpy
import addon_utils
from mathutils import Vector

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

blend = r"{p['blend']}"
vrm = r"{p['vrm']}"
vrm2 = r"{p['vrm2']}"
temp = r"{p['temp']}"
fbx = r"{p['fbx']}"

bpy.ops.wm.open_mainfile(filepath=blend)
main = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)
main.parent = None
main.vertex_groups.clear()

bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
bpy.context.view_layer.objects.active = main
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

arm.select_set(True)
bpy.context.view_layer.objects.active = arm
main.select_set(True)
auto_err = ""
try:
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
except Exception as e:
    auto_err = str(e)

vg_count = len(main.vertex_groups)
weighted = sum(1 for v in main.data.vertices if v.groups)
method = "ARMATURE_AUTO"

# nearest-bone fallback if heat weighting mostly failed
if vg_count < 5 or weighted < len(main.data.vertices) * 0.5:
    method = "nearest_bone"
    for mod in list(main.modifiers):
        if mod.type == "ARMATURE":
            main.modifiers.remove(mod)
    main.parent = None
    main.vertex_groups.clear()

    am = main.modifiers.new("Armature", "ARMATURE")
    am.object = arm
    main.parent = arm

    arm_mw = arm.matrix_world
    # sample head+tail midpoints of each deform bone
    samples = []
    for b in arm.data.bones:
        h = arm_mw @ b.head_local
        t = arm_mw @ b.tail_local
        mid = (h + t) * 0.5
        samples.append((b.name, h, mid, t))
        if b.name not in main.vertex_groups:
            main.vertex_groups.new(name=b.name)

    mw = main.matrix_world
    for vi, v in enumerate(main.data.vertices):
        wco = mw @ v.co
        best = None
        best_d = 1e18
        for name, h, mid, t in samples:
            d = min((wco - h).length, (wco - mid).length, (wco - t).length)
            if d < best_d:
                best_d = d
                best = name
        if best:
            main.vertex_groups[best].add([vi], 1.0, "REPLACE")

    vg_count = len(main.vertex_groups)
    weighted = sum(1 for v in main.data.vertices if v.groups)

bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=temp, export_format="GLB", use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=blend)

vrm_status = "skipped"
if hasattr(bpy.ops.export_scene, "vrm"):
    try:
        bpy.ops.export_scene.vrm(filepath=vrm)
        vrm_status = "ok"
        import shutil as _sh
        _sh.copyfile(vrm, vrm2)
    except Exception as e:
        vrm_status = "error:" + str(e)

result = {{
    "status": "ok",
    "method": method,
    "auto_err": auto_err,
    "vertex_groups": vg_count,
    "weighted_verts": weighted,
    "total_verts": len(main.data.vertices),
    "vrm_status": vrm_status,
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:3000])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return 1
    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("[OK glb]", GLB.stat().st_size)
    print("[skin]", payload.get("method"), "groups", payload.get("vertex_groups"),
          "weighted", payload.get("weighted_verts"), "/", payload.get("total_verts"),
          "vrm", payload.get("vrm_status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
