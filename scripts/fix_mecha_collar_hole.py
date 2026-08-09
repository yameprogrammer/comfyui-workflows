#!/usr/bin/env python3
"""Fill collar hole / lower head using bmesh only (MCP-safe), re-export VRM."""

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
RENDER = EXPORTS / "viewport_render.png"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")


def main() -> int:
    code = f"""
import bpy
import bmesh
import addon_utils
from mathutils import Vector
from pathlib import Path

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

bpy.ops.wm.open_mainfile(filepath=r"{str(BLEND).replace(chr(92), '/')}")
main = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)

# clear parent via matrix
if main.parent:
    mw = main.matrix_world.copy()
    main.parent = None
    main.matrix_world = mw

# remove armature mods temporarily
for mod in list(main.modifiers):
    if mod.type == "ARMATURE":
        main.modifiers.remove(mod)

# bmesh edit in object mode
bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

mw = main.matrix_world
imw = mw.inverted()
coords = [mw @ v.co for v in bm.verts]
zs = [c.z for c in coords]
minz, maxz = min(zs), max(zs)
h = maxz - minz
top = [c for c in coords if c.z > minz + h * 0.78]
hc = sum(top, Vector()) / len(top) if top else Vector((0, 0, maxz))
head_r = h * 0.13
shift = h * 0.05

moved = 0
for v in bm.verts:
    w = mw @ v.co
    if (w - hc).length < head_r * 1.4:
        w2 = Vector((w.x, w.y, w.z - shift))
        v.co = imw @ w2
        moved += 1
    elif (
        w.z > hc.z - head_r * 1.8
        and w.z < hc.z - head_r * 0.35
        and abs(w.x - hc.x) < head_r * 0.45
        and abs(w.y - hc.y) < head_r * 0.45
    ):
        w2 = Vector((w.x, w.y, w.z - shift * 0.7))
        v.co = imw @ w2

# close boundary loops roughly: extrude boundary edges of hole toward center
# find boundary edges
boundary = [e for e in bm.edges if e.is_boundary]
# try bmesh.ops.holes_fill
try:
    bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    filled = "holes_fill"
except Exception as e:
    filled = str(e)
    # fallback: face from each boundary edge loop
    try:
        loops = []
        # collect boundary verts loops via bmesh.ops.edgenet_prepare not available
        bmesh.ops.edgeloop_fill(bm, edges=boundary)
        filled = "edgeloop_fill"
    except Exception as e2:
        filled = f"{{filled}} | {{e2}}"

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(main.data)
bm.free()
main.data.update()

# re-skin
weight = None
if arm:
    main.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        weight = "AUTO"
    except Exception as e:
        weight = str(e)
        main.parent = arm
        m = main.modifiers.new("Armature", "ARMATURE")
        m.object = arm

# render
scene = bpy.context.scene
scene.render.filepath = r"{str(RENDER).replace(chr(92), '/')}"
if arm:
    arm.hide_render = True
try:
    bpy.ops.render.render(write_still=True)
except Exception as e:
    pass

# export with override
window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
if arm:
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
else:
    bpy.context.view_layer.objects.active = main
temp = r"{str(TEMP).replace(chr(92), '/')}"
vrm = r"{str(VRM).replace(chr(92), '/')}"
notes = {{}}
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=(arm or main)):
    bpy.ops.export_scene.gltf(
        filepath=temp,
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_morph=True,
        export_materials="EXPORT",
        export_animations=False,
    )
    if hasattr(bpy.ops.export_scene, "vrm"):
        try:
            notes["vrm"] = list(
                bpy.ops.export_scene.vrm(
                    filepath=vrm,
                    ignore_warning=True,
                    check_existing=False,
                    armature_object_name=(arm.name if arm else ""),
                )
            )
        except Exception as e:
            notes["vrm"] = str(e)

bpy.ops.wm.save_mainfile()
result = {{
    "filled": filled,
    "moved": moved,
    "head_r": head_r,
    "shift": shift,
    "weight": weight,
    "notes": notes,
    "vrm": Path(vrm).stat().st_size if Path(vrm).is_file() else 0,
    "temp": Path(temp).stat().st_size if Path(temp).is_file() else 0,
    "poly": len(main.data.polygons),
}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:3500])
    if TEMP.is_file():
        shutil.copyfile(TEMP, GLB)
        print("glb", GLB.stat().st_size)
    if VRM.is_file() and VRM.stat().st_size > 10000:
        shutil.copyfile(VRM, VRM2)
        print("VRM", VRM.stat().st_size, "has_VRM", b"VRM" in VRM.read_bytes())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
