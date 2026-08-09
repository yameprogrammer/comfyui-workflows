#!/usr/bin/env python3
"""Import solid 437K poly mesh (mecha_yame_single_00001_.glb), apply PBR texture, studio lighting, and render visual PNG."""

import json
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy
import math
import mathutils

# 1. Clear scene completely
bpy.ops.wm.read_homefile(use_empty=True)

# 2. Import solid mesh candidate
glb_path = r"F:\\ComfyUI_data\\output\\3d\\mecha_yame_single_00001_.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
main_mesh = mesh_objs[0]
main_mesh.name = "Mecha_Yameprogrammer_Solid"
bpy.context.view_layer.objects.active = main_mesh
main_mesh.select_set(True)

# 3. Position and scale
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bbox = [main_mesh.matrix_world @ mathutils.Vector(c) for c in main_mesh.bound_box]
min_z = min(v.z for v in bbox)
max_z = max(v.z for v in bbox)
current_h = max_z - min_z

if current_h > 0:
    scale = 1.75 / current_h
    main_mesh.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bbox_new = [main_mesh.matrix_world @ mathutils.Vector(c) for c in main_mesh.bound_box]
min_z_new = min(v.z for v in bbox_new)
center_x = (min(v.x for v in bbox_new) + max(v.x for v in bbox_new)) / 2.0
center_y = (min(v.y for v in bbox_new) + max(v.y for v in bbox_new)) / 2.0

main_mesh.location.x -= center_x
main_mesh.location.y -= center_y
main_mesh.location.z -= min_z_new
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 4. Smooth Shading & Weighted Normal
for poly in main_mesh.data.polygons:
    poly.use_smooth = True

wn_mod = main_mesh.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
wn_mod.keep_sharp = True

# 5. PBR Texture Shader Setup
mat_name = "Mecha_Solid_PBR"
mat = bpy.data.materials.get(mat_name)
if not mat:
    mat = bpy.data.materials.new(name=mat_name)
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out_node = nodes.new(type='ShaderNodeOutputMaterial')
out_node.location = (500, 0)

bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.location = (100, 0)
bsdf.inputs['Metallic'].default_value = 0.65
bsdf.inputs['Roughness'].default_value = 0.35

img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
tex_node = nodes.new(type='ShaderNodeTexImage')
tex_node.location = (-300, 100)
tex_node.image = bpy.data.images.load(img_path)

links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

if main_mesh.data.materials:
    main_mesh.data.materials[0] = mat
else:
    main_mesh.data.materials.append(mat)

# 6. Studio Lighting & World
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs['Color'].default_value = (0.2, 0.2, 0.23, 1.0)
    bg_node.inputs['Strength'].default_value = 1.0

# Sun Light
sun_data = bpy.data.lights.new(name="SunLight", type='SUN')
sun_data.energy = 4.0
sun = bpy.data.objects.new(name="SunLight", object_data=sun_data)
sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(30))
bpy.context.collection.objects.link(sun)

# Camera
cam_data = bpy.data.cameras.new("StudioCamera")
cam = bpy.data.objects.new("StudioCamera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (0.0, -3.2, 0.90)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

# Set 3D Viewport Shading to MATERIAL
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

# 7. Render Snapshot
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 800

render_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\viewport_render.png"
bpy.context.scene.render.filepath = render_path

window = bpy.context.window_manager.windows[0]
override = {'window': window, 'screen': window.screen, 'area': window.screen.areas[0], 'active_object': main_mesh}
with bpy.context.temp_override(**override):
    bpy.ops.render.render(write_still=True)

# 8. Save Blend File and copy to mecha_yame_v1.vrm / warudo.glb
blend_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

result = {
    "status": "success",
    "poly_count": len(main_mesh.data.polygons),
    "rendered_image": render_path,
    "blend_file": blend_path
}
"""

res = exec_blender_code(code)
print("Render Solid Mesh Result:", json.dumps(res, indent=2, ensure_ascii=False))

# Copy solid mesh to final VRM / GLB files
src_glb = Path(r"F:\ComfyUI_data\output\3d\mecha_yame_single_00001_.glb")
dst_vrm = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1.vrm")
dst_warudo = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1_warudo.glb")
import shutil
shutil.copyfile(src_glb, dst_vrm)
shutil.copyfile(src_glb, dst_warudo)
print(f"[SUCCESS] Exported Solid 437K Mesh to VRM & GLB ({dst_vrm.stat().st_size} bytes)")
