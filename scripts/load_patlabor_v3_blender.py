#!/usr/bin/env python3
"""Import mecha_patlabor_v3 multiview GLB into running Blender (MCP) and save review assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")


def main() -> int:
    glb = EXPORTS / "mecha_patlabor_v3_mv_tex.glb"
    if not glb.is_file():
        glb = EXPORTS / "mecha_patlabor_v3_mv_geo.glb"
    if not glb.is_file():
        print("[ERROR] missing glb", glb, file=sys.stderr)
        return 1

    blend_out = EXPORTS / "mecha_patlabor_v3.blend"
    render_front = EXPORTS / "viewport_front.png"
    render_side = EXPORTS / "viewport_side.png"
    render_back = EXPORTS / "viewport_back.png"
    render_3q = EXPORTS / "viewport_3q.png"
    ogl = EXPORTS / "viewport_opengl.png"

    g = str(glb).replace("\\", "/")
    b = str(blend_out).replace("\\", "/")
    rf = str(render_front).replace("\\", "/")
    rs = str(render_side).replace("\\", "/")
    rb = str(render_back).replace("\\", "/")
    r3 = str(render_3q).replace("\\", "/")
    ro = str(ogl).replace("\\", "/")

    code = f'''
import bpy
from mathutils import Vector
import math

glb = r"{g}"
blend_path = r"{b}"
paths = {{
    "front": r"{rf}",
    "side": r"{rs}",
    "back": r"{rb}",
    "q3": r"{r3}",
    "ogl": r"{ro}",
}}

# clear scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for coll in (
    bpy.data.meshes,
    bpy.data.materials,
    bpy.data.images,
    bpy.data.armatures,
    bpy.data.cameras,
    bpy.data.lights,
):
    for item in list(coll):
        try:
            coll.remove(item)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=glb)
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objs:
    result = {{"status": "error", "message": "no mesh after import"}}
else:
    for o in mesh_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    if len(mesh_objs) > 1:
        bpy.ops.object.join()
    main = bpy.context.view_layer.objects.active
    main.name = "MechaPatlabor_V3"

    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    dims = main.dimensions
    h = max(float(dims.z), 1e-6)
    s = 1.6 / h
    main.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()
    mn = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_z = min(v.z for v in mn)
    main.location.z -= min_z
    bpy.context.view_layer.update()

    bpy.ops.object.light_add(type="AREA", location=(2.5, -2.0, 3.0))
    key = bpy.context.active_object
    key.data.energy = 400
    key.data.size = 3.0
    bpy.ops.object.light_add(type="AREA", location=(-2.5, 2.0, 2.0))
    fill = bpy.context.active_object
    fill.data.energy = 150
    fill.data.size = 4.0
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    sun = bpy.context.active_object
    sun.data.energy = 2.0

    bpy.ops.object.camera_add(location=(0, -3.2, 0.9))
    cam = bpy.context.active_object
    cam.name = "ReviewCam"
    bpy.context.scene.camera = cam

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.95, 0.95, 0.97, 1.0)
        bg.inputs[1].default_value = 1.0

    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except Exception:
            continue
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1280
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"

    def frame_cam(az_deg, elev=8.0, dist=3.0):
        bpy.context.view_layer.update()
        bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
        center = sum(bb, Vector()) / 8.0
        center.z = max(0.75, center.z)
        az = math.radians(az_deg)
        el = math.radians(elev)
        loc = Vector((
            center.x + dist * math.cos(el) * math.sin(az),
            center.y - dist * math.cos(el) * math.cos(az),
            center.z + dist * math.sin(el),
        ))
        cam.location = loc
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def render_to(path, az):
        frame_cam(az)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)

    ogl_err = None
    try:
        frame_cam(0)
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "MATERIAL"
                scene.render.filepath = paths["ogl"]
                bpy.ops.render.opengl(write_still=True)
                break
    except Exception as e:
        ogl_err = str(e)

    render_to(paths["front"], 0)
    render_to(paths["side"], 90)
    render_to(paths["back"], 180)
    render_to(paths["q3"], 35)
    frame_cam(35)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    verts = len(main.data.vertices)
    faces = len(main.data.polygons)
    mats = [m.name for m in main.data.materials if m]
    has_tex = False
    for mat in main.data.materials:
        if not mat or not mat.use_nodes:
            continue
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                has_tex = True
    result = {{
        "status": "ok",
        "object": main.name,
        "verts": verts,
        "faces": faces,
        "materials": mats,
        "has_texture_image": has_tex,
        "dimensions_m": [float(x) for x in main.dimensions],
        "blend": blend_path,
        "glb": glb,
        "renders": paths,
        "engine": scene.render.engine,
        "ogl_err": ogl_err,
    }}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    status = (res.get("result") or res).get("status") if isinstance(res.get("result"), dict) else res.get("status")
    # MCP wraps as {status:ok, result:{...}} or just result
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if payload.get("status") != "ok":
        return 2
    print("[OK] blend", blend_out)
    for p in (render_front, render_side, render_back, render_3q, ogl):
        print(("OK" if p.is_file() else "MISS"), p, p.stat().st_size if p.is_file() else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
