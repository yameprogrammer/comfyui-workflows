#!/usr/bin/env python3
"""
Reload clean T-pose mesh, delete ONLY thin vertical side plates (not hands).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
SRC = EXPORTS / "mecha_yame_v2_tpose_tex.glb"
if not SRC.is_file():
    SRC = EXPORTS / "mecha_yame_v2_simple_mv_tex.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM = EXPORTS / "mecha_yame_v2.vrm"
VRM2 = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB = EXPORTS / "mecha_yame_v2_warudo.glb"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_plates.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_plates.glb")
RENDER = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_plates.png")
RENDER_DST = EXPORTS / "viewport_render.png"


def main() -> int:
    # reuse SD armature script after clean? We'll clean then call refit via subprocess
    p = {
        "src": str(SRC).replace("\\", "/"),
        "blend": str(BLEND).replace("\\", "/"),
        "out_glb": str(EXPORTS / "mecha_yame_v2_tpose_clean.glb").replace("\\", "/"),
    }

    code = f'''
import bpy
import bmesh
from mathutils import Vector

src = r"{p['src']}"
out_glb = r"{p['out_glb']}"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.images, bpy.data.cameras, bpy.data.lights):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=src)
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()
main = bpy.context.view_layer.objects.active
main.name = "MechaYame_V2"

bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# components
visited = set()
components = []
for f in bm.faces:
    if f.index in visited:
        continue
    stack = [f]
    visited.add(f.index)
    faces, verts = [], set()
    while stack:
        cur = stack.pop()
        faces.append(cur)
        for v in cur.verts:
            verts.add(v)
        for e in cur.edges:
            for lf in e.link_faces:
                if lf.index not in visited:
                    visited.add(lf.index)
                    stack.append(lf)
    components.append((faces, verts))

mw = main.matrix_world
all_w = [mw @ v.co for v in bm.verts]
minx, maxx = min(v.x for v in all_w), max(v.x for v in all_w)
miny, maxy = min(v.y for v in all_w), max(v.y for v in all_w)
minz, maxz = min(v.z for v in all_w), max(v.z for v in all_w)
W, H, D = maxx - minx, maxz - minz, maxy - miny
cx = (minx + maxx) * 0.5

del_verts = set()
killed = []
for faces, verts in components:
    pts = [mw @ v.co for v in verts]
    xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
    bw, bd, bh = max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)
    bccx = (min(xs)+max(xs))*0.5
    nfaces = len(faces)

    # ONLY kill paper-thin tall vertical slabs at extreme X
    # plate signature from previous analysis: bw ~ 0.005, bh ~ 1.7, center ~ +/-0.71
    is_paper_plate = (
        bw < 0.04  # very thin in X (or)
        and bh > H * 0.5  # tall
        and abs(bccx - cx) > W * 0.35  # far left/right
        and nfaces < 5000
    )
    # also: thin in X relative, tall, lateral
    is_side_wall = (
        bw < W * 0.04
        and bh > H * 0.45
        and abs(bccx - cx) > W * 0.38
    )
    # do NOT kill hand islands (small, medium height, thick enough)
    if is_paper_plate or is_side_wall:
        for v in verts:
            del_verts.add(v)
        killed.append({{
            "nfaces": nfaces,
            "bbox": [round(bw,4), round(bd,4), round(bh,4)],
            "cx": round(bccx,3),
        }})

if del_verts:
    bmesh.ops.delete(bm, geom=list(del_verts), context="VERTS")
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00015)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(main.data)
main.data.update()
bm.free()

# export clean mesh only (rig later)
window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
bpy.ops.object.select_all(action="DESELECT")
main.select_set(True)
bpy.context.view_layer.objects.active = main
with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=main, selected_objects=[main]):
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", use_selection=True, export_apply=True)

result = {{
    "status": "ok",
    "killed": killed,
    "n_killed": len(killed),
    "verts": len(main.data.vertices),
    "faces": len(main.data.polygons),
    "dims": [round(float(x),3) for x in main.dimensions],
    "out": out_glb,
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

    clean = EXPORTS / "mecha_yame_v2_tpose_clean.glb"
    if not clean.is_file():
        print("clean glb missing")
        return 1
    # overwrite tpose_tex so SD refit uses cleaned mesh
    shutil.copyfile(clean, EXPORTS / "mecha_yame_v2_tpose_tex.glb")
    print("[OK clean]", clean, payload.get("n_killed"), "plates", payload.get("dims"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
