#!/usr/bin/env python3
"""Render a PNG snapshot of the Blender 3D scene to visually verify model quality."""

import json
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

# Setup camera and lighting if not present
if 'Camera' not in bpy.data.objects:
    bpy.ops.object.camera_add(location=(0, -3.5, 1.2), rotation=(1.5708, 0, 0))
    bpy.context.scene.camera = bpy.data.objects['Camera']
else:
    cam = bpy.data.objects['Camera']
    cam.location = (0, -3.5, 1.2)
    cam.rotation = (1.5708, 0, 0)
    bpy.context.scene.camera = cam

if 'Light' not in bpy.data.objects:
    bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))

# Set render settings
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 800

render_png = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\viewport_render.png"
bpy.context.scene.render.filepath = render_png
bpy.ops.render.render(write_still=True)

result = {
    "status": "success",
    "rendered_image": render_png,
    "poly_count": sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
}
"""

res = exec_blender_code(code)
print("Blender Render Result:", json.dumps(res, indent=2, ensure_ascii=False))
