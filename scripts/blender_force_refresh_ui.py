#!/usr/bin/env python3
"""Force import master GLB into active Blender UI workspace and save as .blend file via MCP."""

import json
from blender_mcp_client import exec_blender_code

code = """
import bpy

# Clear scene completely
bpy.ops.wm.read_homefile(use_empty=True)

# Import the 183MB masterpiece GLB model directly into Blender UI
glb_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_v1_warudo.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)

# Frame selected object
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if mesh_objs:
    main_mesh = mesh_objs[0]
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

# Set 3D Viewport Shading to MATERIAL (Material Preview)
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

# Force Redraw all Blender UI areas
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        area.tag_redraw()

# Save mainfile so user can open directly
blend_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

result = {
    "status": "success",
    "blend_file": blend_path,
    "objects_in_scene": [o.name for o in bpy.data.objects]
}
"""

res = exec_blender_code(code)
print("Blender UI Refresh Result:", json.dumps(res, indent=2, ensure_ascii=False))
