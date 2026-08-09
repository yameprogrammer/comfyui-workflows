#!/usr/bin/env python3
"""Export current mecha_yame_v2.blend as Warudo-ready VRM (+ backup GLB)."""

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
VRM_WARUDO = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB_WARUDO = EXPORTS / "mecha_yame_v2_warudo.glb"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_warudo_export.glb")
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_warudo_export.vrm")


def main() -> int:
    if not BLEND.is_file():
        print("[ERROR] missing blend", BLEND)
        return 1

    p = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP_VRM).replace("\\", "/"),
        "glb": str(TEMP_GLB).replace("\\", "/"),
    }

    code = f'''
import bpy
import addon_utils

for name in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

blend = r"{p['blend']}"
vrm_path = r"{p['vrm']}"
glb_path = r"{p['glb']}"

bpy.ops.wm.open_mainfile(filepath=blend)
main = next((o for o in bpy.data.objects if o.type == "MESH"), None)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if main is None:
    result = {{"status": "error", "message": "no mesh"}}
else:
    # ensure armature visible for export selection, not required in render
    if arm:
        arm.hide_set(False)
        arm.hide_viewport = False

    mats = []
    has_tex = False
    for slot in main.material_slots:
        m = slot.material
        if not m:
            continue
        tex = []
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    tex.append(n.image.name)
                    has_tex = True
        mats.append({{"name": m.name, "textures": tex}})

    vg = [g.name for g in main.vertex_groups]
    bones = [b.name for b in arm.data.bones] if arm else []

    window = bpy.context.window_manager.windows[0]
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
    region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

    bpy.ops.object.select_all(action="DESELECT")
    main.select_set(True)
    selected = [main]
    if arm:
        arm.select_set(True)
        selected.append(arm)
        bpy.context.view_layer.objects.active = arm
    else:
        bpy.context.view_layer.objects.active = main

    glb_ok = False
    glb_err = ""
    with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=bpy.context.view_layer.objects.active, selected_objects=selected):
        try:
            bpy.ops.export_scene.gltf(
                filepath=glb_path,
                export_format="GLB",
                use_selection=True,
                export_apply=True,
            )
            glb_ok = True
        except Exception as e:
            glb_err = str(e)

    vrm_ok = False
    vrm_err = ""
    if hasattr(bpy.ops.export_scene, "vrm"):
        with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=bpy.context.view_layer.objects.active, selected_objects=selected):
            try:
                bpy.ops.export_scene.vrm(filepath=vrm_path)
                vrm_ok = True
            except Exception as e:
                vrm_err = str(e)
    else:
        vrm_err = "export_scene.vrm not available"

    result = {{
        "status": "ok" if vrm_ok else "error",
        "mesh": main.name,
        "armature": arm.name if arm else None,
        "verts": len(main.data.vertices),
        "faces": len(main.data.polygons),
        "has_texture": has_tex,
        "materials": mats,
        "vertex_groups": len(vg),
        "bones": bones,
        "dims": [round(float(x), 3) for x in main.dimensions],
        "glb_ok": glb_ok,
        "glb_err": glb_err,
        "vrm_ok": vrm_ok,
        "vrm_err": vrm_err,
    }}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:3500])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] VRM export failed")
        return 1

    if TEMP_VRM.is_file():
        shutil.copyfile(TEMP_VRM, VRM)
        shutil.copyfile(TEMP_VRM, VRM_WARUDO)
        print("[OK VRM]", VRM, VRM.stat().st_size)
        print("[OK VRM warudo]", VRM_WARUDO, VRM_WARUDO.stat().st_size)
    else:
        print("[ERROR] temp vrm missing")
        return 1

    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_WARUDO)
        print("[OK GLB]", GLB_WARUDO, GLB_WARUDO.stat().st_size)

    print(
        "mesh", payload.get("mesh"),
        "tex", payload.get("has_texture"),
        "bones", len(payload.get("bones") or []),
        "vgroups", payload.get("vertex_groups"),
        "dims", payload.get("dims"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
