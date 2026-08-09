#!/usr/bin/env python3
"""Switch Blender 3D Viewport Shading to MATERIAL (Material Preview Mode) via MCP."""

import json
from blender_mcp_client import exec_blender_code

code = """
import bpy

viewport_updated = 0
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = False
                    viewport_updated += 1

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if mesh_objs:
    main_mesh = mesh_objs[0]
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

result = {
    "status": "success",
    "viewports_updated": viewport_updated,
    "active_object": main_mesh.name if mesh_objs else None,
    "shading_mode": "MATERIAL"
}
"""

res = exec_blender_code(code)
print("Blender Viewport Update Result:", json.dumps(res, indent=2, ensure_ascii=False))
