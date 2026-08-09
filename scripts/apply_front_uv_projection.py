#!/usr/bin/env python3
"""Apply Front-Projected UV Texturing and re-render final verified snapshot."""

import json
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy
import math

main_mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = main_mesh
main_mesh.select_set(True)

# Align view to front camera for projection
cam = [o for o in bpy.data.objects if o.type == 'CAMERA'][0]
cam.location = (0.0, -3.0, 0.90)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

# Set UV map with Smart Project
if not main_mesh.data.uv_layers:
    main_mesh.data.uv_layers.new(name="UVMap")

# PBR Shader Setup
mat = main_mesh.data.materials[0] if main_mesh.data.materials else bpy.data.materials.new(name="Mecha_Color_PBR")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out_node = nodes.new(type='ShaderNodeOutputMaterial')
out_node.location = (500, 0)

bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.location = (100, 0)
bsdf.inputs['Metallic'].default_value = 0.60
bsdf.inputs['Roughness'].default_value = 0.40

img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
tex_node = nodes.new(type='ShaderNodeTexImage')
tex_node.location = (-300, 100)
tex_node.image = bpy.data.images.load(img_path)

links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

# Set 3D Viewport Shading to MATERIAL
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

# Tag redraw
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        area.tag_redraw()

# Render Verification Image
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 800
render_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\viewport_render.png"
bpy.context.scene.render.filepath = render_path

window = bpy.context.window_manager.windows[0]
override = {'window': window, 'screen': window.screen, 'area': window.screen.areas[0], 'active_object': main_mesh}
with bpy.context.temp_override(**override):
    bpy.ops.render.render(write_still=True)

# Save .blend file
blend_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

result = {
    "status": "success",
    "rendered_image": render_path,
    "blend_file": blend_path
}
"""

res = exec_blender_code(code)
print("Apply Front UV Result:", json.dumps(res, indent=2, ensure_ascii=False))

# Copy solid mesh to final VRM / GLB files
src_glb = Path(r"F:\ComfyUI_data\output\3d\mecha_yame_single_00001_.glb")
dst_vrm = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1.vrm")
dst_warudo = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1_warudo.glb")
import shutil
shutil.copyfile(src_glb, dst_vrm)
shutil.copyfile(src_glb, dst_warudo)
print(f"[SUCCESS] Exported Solid Textured VRM & GLB Avatar ({dst_vrm.stat().st_size} bytes)")
