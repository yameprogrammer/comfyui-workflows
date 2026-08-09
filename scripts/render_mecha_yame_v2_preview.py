#!/usr/bin/env python3
"""Fix camera/lights and render a usable preview of mecha_yame_v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.blend")
RENDER = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\viewport_render.png")
VIEWPORT = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\viewport_opengl.png")


def main() -> int:
    blend = str(BLEND).replace("\\", "/")
    render = str(RENDER).replace("\\", "/")
    viewport = str(VIEWPORT).replace("\\", "/")

    code = f"""
import bpy
import math
from mathutils import Vector

blend_path = r"{blend}"
render_path = r"{render}"
viewport_path = r"{viewport}"

bpy.ops.wm.open_mainfile(filepath=blend_path)

# find mesh
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
main = meshes[0] if meshes else None
if main is None:
    result = {{"status": "error", "message": "no mesh"}}
else:
    # world bright
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    wn = world.node_tree.nodes
    wl = world.node_tree.links
    wn.clear()
    bg = wn.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.85, 0.87, 0.90, 1.0)
    bg.inputs[1].default_value = 1.0
    wout = wn.new("ShaderNodeOutputWorld")
    wl.new(bg.outputs[0], wout.inputs[0])

    # remove old cameras/lights
    for o in list(bpy.data.objects):
        if o.type in {{'CAMERA', 'LIGHT'}}:
            bpy.data.objects.remove(o, do_unlink=True)

    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bbox, Vector()) / 8.0
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    # place camera in front (-Y typical for A-pose product)
    dist = max(height * 1.9, 2.5)
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (center.x, center.y - dist, center.z)
    # look at center
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    # lights
    def add_light(name, loc, energy, size=1.5):
        ld = bpy.data.lights.new(name=name, type='AREA')
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = loc
        return lo

    add_light("Key", (center.x + 1.2, center.y - 1.8, center.z + 1.4), 250)
    add_light("Fill", (center.x - 1.6, center.y - 1.0, center.z + 0.8), 120)
    add_light("Rim", (center.x, center.y + 1.5, center.z + 1.2), 180)

    # ensure material base color visible
    for slot in main.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                # Blender 4+/5 may use different emission socket names
                for key in ("Emission Color", "Emission"):
                    if key in n.inputs:
                        n.inputs[key].default_value = (1, 1, 1, 1)
                if "Emission Strength" in n.inputs:
                    n.inputs["Emission Strength"].default_value = 0.0

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys() else 'BLENDER_EEVEE'
    # fallback cycles if needed
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        try:
            scene.render.engine = 'BLENDER_EEVEE'
        except Exception:
            scene.render.engine = 'CYCLES'
            scene.cycles.samples = 32

    scene.render.resolution_x = 768
    scene.render.resolution_y = 1152
    scene.render.film_transparent = False
    scene.render.filepath = render_path
    scene.render.image_settings.file_format = 'PNG'

    # EEVEE settings if present
    if hasattr(scene, 'eevee'):
        try:
            scene.eevee.taa_render_samples = 32
        except Exception:
            pass

    bpy.ops.render.render(write_still=True)

    # also OpenGL viewport render (often more reliable for preview)
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.region_3d.view_perspective = 'CAMERA'
                override = {{
                    'window': window,
                    'screen': screen,
                    'area': area,
                    'region': next(r for r in area.regions if r.type == 'WINDOW'),
                    'scene': scene,
                }}
                try:
                    with bpy.context.temp_override(**override):
                        scene.render.filepath = viewport_path
                        bpy.ops.render.opengl(write_still=True)
                    ogl = True
                except Exception as e:
                    ogl = str(e)
                break

    bpy.ops.wm.save_mainfile()

    result = {{
        "status": "success",
        "engine": scene.render.engine,
        "cam_loc": list(cam.location),
        "center": list(center),
        "height": float(height),
        "render": render_path,
        "viewport": viewport_path,
        "ogl": ogl if 'ogl' in dir() else None,
        "mesh": main.name,
        "dims": list(main.dimensions),
    }}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    print("render exists:", RENDER.is_file(), RENDER.stat().st_size if RENDER.is_file() else 0)
    print("viewport exists:", VIEWPORT.is_file(), VIEWPORT.stat().st_size if VIEWPORT.is_file() else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
