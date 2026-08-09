#!/usr/bin/env python3
"""
Remove side plate / floater mesh islands from mecha T-pose model, re-export VRM.
"""

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
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_clean.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_clean.glb")
RENDER = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_clean_front.png")
RENDER_DST = EXPORTS / "viewport_render.png"


def main() -> int:
    p = {k: str(v).replace("\\", "/") for k, v in {
        "blend": BLEND, "vrm": TEMP_VRM, "glb": TEMP_GLB, "render": RENDER,
    }.items()}

    code = f'''
import bpy
import bmesh
import addon_utils
from mathutils import Vector
from collections import defaultdict, deque

for name in ["bl_ext.user_default.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

blend = r"{p['blend']}"
vrm_path = r"{p['vrm']}"
glb_path = r"{p['glb']}"
render_path = r"{p['render']}"

bpy.ops.wm.open_mainfile(filepath=blend)
main = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)

# object-mode bmesh (MCP often lacks view3d active context for mode_set)
if arm:
    try:
        arm.hide_set(True)
    except Exception:
        pass
bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# connected components via faces
visited = set()
components = []
for f in bm.faces:
    if f.index in visited:
        continue
    stack = [f]
    visited.add(f.index)
    faces = []
    verts = set()
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
# world bbox of whole mesh
all_w = [mw @ v.co for v in bm.verts]
minx = min(v.x for v in all_w)
maxx = max(v.x for v in all_w)
miny = min(v.y for v in all_w)
maxy = max(v.y for v in all_w)
minz = min(v.z for v in all_w)
maxz = max(v.z for v in all_w)
W = maxx - minx
H = maxz - minz
D = maxy - miny
cx = (minx + maxx) * 0.5
cy = (miny + maxy) * 0.5

removed_faces = 0
removed_comp = 0
comp_info = []

# mark verts to delete
del_verts = set()

for faces, verts in components:
    pts = [mw @ v.co for v in verts]
    n = len(pts)
    if n == 0:
        continue
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    bx0, bx1 = min(xs), max(xs)
    by0, by1 = min(ys), max(ys)
    bz0, bz1 = min(zs), max(zs)
    bw, bd, bh = bx1 - bx0, by1 - by0, bz1 - bz0
    bccx = (bx0 + bx1) * 0.5
    bccy = (by0 + by1) * 0.5
    bccz = (bz0 + bz1) * 0.5
    nfaces = len(faces)
    volume_proxy = max(bw, 1e-6) * max(bd, 1e-6) * max(bh, 1e-6)

    # Main body = largest component
    # Side plates: thin in one axis, away from center, moderate height
    thin_x = bw < W * 0.12
    thin_y = bd < D * 0.18 or bd < 0.08
    thin_z = bh < H * 0.15
    # vertical plate: tall, thin in depth or width, at left/right extreme
    is_vertical_plate = (
        bh > H * 0.35
        and (thin_y or thin_x)
        and (abs(bccx - cx) > W * 0.28)
        and nfaces < 8000
    )
    # small floater islands
    is_small_floater = nfaces < 400 and n < 800 and abs(bccx - cx) > W * 0.25
    # detached side slab near hands
    is_side_slab = (
        abs(bccx - cx) > W * 0.32
        and thin_y
        and bh > H * 0.25
        and nfaces < 12000
    )

    kill = is_vertical_plate or is_small_floater or is_side_slab
    # never kill the biggest component
    # (we'll identify by face count after loop)

    comp_info.append({{
        "nfaces": nfaces,
        "nverts": n,
        "bbox": [round(bw,3), round(bd,3), round(bh,3)],
        "center_x": round(bccx,3),
        "thin_y": thin_y,
        "kill_candidate": kill,
    }})

# largest by faces is body
components_sorted = sorted(
    zip(components, comp_info),
    key=lambda x: x[1]["nfaces"],
    reverse=True,
)
body_nfaces = components_sorted[0][1]["nfaces"]

for (faces, verts), info in components_sorted:
    if info["nfaces"] == body_nfaces:
        info["killed"] = False
        continue
    # kill if candidate OR (not body and very lateral + not huge)
    pts = [mw @ v.co for v in verts]
    bccx = sum(p.x for p in pts) / len(pts)
    bw = max(p.x for p in pts) - min(p.x for p in pts)
    bd = max(p.y for p in pts) - min(p.y for p in pts)
    bh = max(p.z for p in pts) - min(p.z for p in pts)
    kill = info["kill_candidate"]
    # extra: any non-body island outside 30% width and thinner than body
    if abs(bccx - cx) > W * 0.30 and info["nfaces"] < body_nfaces * 0.25:
        if bd < 0.15 or bw < W * 0.15:
            kill = True
    if kill:
        for v in verts:
            del_verts.add(v)
        removed_faces += info["nfaces"]
        removed_comp += 1
        info["killed"] = True
    else:
        info["killed"] = False

if del_verts:
    bmesh.ops.delete(bm, geom=list(del_verts), context="VERTS")
# cleanup
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(main.data)
main.data.update()
bm.free()

# re-parent weights if armature exists — keep existing groups
if arm:
    for mod in list(main.modifiers):
        if mod.type == "ARMATURE":
            mod.object = arm
    if main.parent != arm:
        main.parent = arm

# preview render
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
bg = wn.new("ShaderNodeBackground")
bg.inputs[0].default_value = (0.85, 0.86, 0.88, 1.0)
bg.inputs[1].default_value = 1.1
wout = wn.new("ShaderNodeOutputWorld")
wl.new(bg.outputs[0], wout.inputs[0])

bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector()) / 8.0
height = max(v.z for v in bbox) - min(v.z for v in bbox)
cam_data = bpy.data.cameras.new("PreviewCam")
cam_data.lens = 55
cam = bpy.data.objects.new("PreviewCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(height * 2.3, 3.5), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam
ld = bpy.data.lights.new("Key", "AREA")
ld.energy = 450
ld.size = 1.6
lo = bpy.data.objects.new("Key", ld)
bpy.context.scene.collection.objects.link(lo)
lo.location = (center.x + 1.3, center.y - 2.0, center.z + 1.4)

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE"
except Exception:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
scene.render.resolution_x = 768
scene.render.resolution_y = 1152
scene.render.filepath = render_path
if arm:
    arm.hide_render = True
bpy.ops.render.render(write_still=True)
if arm:
    arm.hide_render = False

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

with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=bpy.context.view_layer.objects.active, selected_objects=selected):
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    vrm_ok = False
    vrm_err = ""
    try:
        bpy.ops.export_scene.vrm(filepath=vrm_path)
        vrm_ok = True
    except Exception as e:
        vrm_err = str(e)

result = {{
    "status": "ok",
    "components": len(components),
    "removed_comp": removed_comp,
    "removed_faces": removed_faces,
    "body_faces": body_nfaces,
    "comp_info": comp_info[:12],
    "verts_now": len(main.data.vertices),
    "vrm_ok": vrm_ok,
    "vrm_err": vrm_err,
    "dims": [round(float(x), 3) for x in main.dimensions],
}}
'''
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    payload = res.get("result") if isinstance(res, dict) else res
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return 1
    if TEMP_VRM.is_file():
        shutil.copyfile(TEMP_VRM, VRM)
        shutil.copyfile(TEMP_VRM, VRM2)
        print("[OK vrm]", VRM.stat().st_size)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB)
        print("[OK glb]", GLB.stat().st_size)
    if RENDER.is_file():
        shutil.copyfile(RENDER, RENDER_DST)
        print("[OK render]")
    print(
        "removed", payload.get("removed_comp"), "comps",
        "faces", payload.get("removed_faces"),
        "dims", payload.get("dims"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
