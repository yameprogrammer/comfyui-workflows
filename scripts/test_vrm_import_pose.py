#!/usr/bin/env python3
"""Import VRM into Blender and test if posing humanoid bones deforms the mesh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

V2 = r"D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2.vrm"
V3 = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3_warudo.vrm"


def main() -> int:
    code = f'''
import bpy
import addon_utils
from mathutils import Vector, Quaternion, Euler
import math

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)

def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
        for b in list(coll):
            try:
                coll.remove(b)
            except Exception:
                pass

def test_vrm(path, label):
    wipe()
    # import
    err = None
    try:
        if hasattr(bpy.ops.import_scene, "vrm"):
            r = bpy.ops.import_scene.vrm(filepath=path)
        else:
            r = bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        err = str(e)
        r = None
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not meshes or not arms:
        return {{"label": label, "error": err or "no mesh/arm", "import": str(r),
                "objects": [o.name+":"+o.type for o in bpy.data.objects]}}
    main = meshes[0]
    arm = arms[0]
    # rest coords
    bpy.context.view_layer.update()
    coords0 = [v.co.copy() for v in main.data.vertices]
    # find pose bones
    bone_names = [b.name for b in arm.pose.bones]
    head = None
    for n in ("Head", "head", "J_Bip_C_Head"):
        if n in arm.pose.bones:
            head = arm.pose.bones[n]
            break
    armb = None
    for n in ("LeftUpperArm", "leftUpperArm", "J_Bip_L_UpperArm"):
        if n in arm.pose.bones:
            armb = arm.pose.bones[n]
            break
    results = {{"label": label, "import": str(r), "err": err, "bones": bone_names[:30], "bone_count": len(bone_names)}}
    # pose head
    if head:
        head.rotation_mode = "XYZ"
        head.rotation_euler = Euler((0.5, 0.0, 0.4), "XYZ")
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        me = main.evaluated_get(deps).to_mesh()
        maxd = max((me.vertices[i].co - coords0[i]).length for i in range(len(me.vertices)))
        moved = sum(1 for i in range(len(me.vertices)) if (me.vertices[i].co - coords0[i]).length > 0.001)
        main.evaluated_get(deps).to_mesh_clear()
        results["head_bone"] = head.name
        results["head_max_delta"] = round(maxd, 5)
        results["head_moved_verts"] = moved
        head.rotation_euler = Euler((0,0,0), "XYZ")
        bpy.context.view_layer.update()
    # pose arm
    if armb:
        armb.rotation_mode = "XYZ"
        armb.rotation_euler = Euler((0.0, -1.0, 0.0), "XYZ")
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        me = main.evaluated_get(deps).to_mesh()
        maxd = max((me.vertices[i].co - coords0[i]).length for i in range(len(me.vertices)))
        moved = sum(1 for i in range(len(me.vertices)) if (me.vertices[i].co - coords0[i]).length > 0.001)
        main.evaluated_get(deps).to_mesh_clear()
        results["arm_bone"] = armb.name
        results["arm_max_delta"] = round(maxd, 5)
        results["arm_moved_verts"] = moved
        armb.rotation_euler = Euler((0,0,0), "XYZ")
    # modifiers
    results["mesh_mods"] = [(m.name, m.type, getattr(m.object, "name", None) if hasattr(m, "object") else None) for m in main.modifiers]
    results["mesh_parent"] = main.parent.name if main.parent else None
    results["arm_name"] = arm.name
    return results

r2 = test_vrm(r"{V2}", "v2")
r3 = test_vrm(r"{V3}", "v3")
result = {{"v2": r2, "v3": r3}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
