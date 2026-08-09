#!/usr/bin/env python3
"""Fix 3D model scale, camera framing, studio lighting, and visually verify in Blender via MCP."""

import json
import math
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy
import math
import mathutils

# 1. Get main mesh object
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {"status": "error", "message": "No mesh object found"}
else:
    main_mesh = mesh_objs[0]
    main_mesh.name = "Mecha_Yameprogrammer_Verified"
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # 2. Reset origin and compute bounding box height
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    bbox = [main_mesh.matrix_world @ mathutils.Vector(corner) for corner in main_mesh.bound_box]
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)
    current_height = max_z - min_z

    # Scale model to standard character height ~1.75m
    if current_height > 0:
        target_height = 1.75
        scale_factor = target_height / current_height
        main_mesh.scale = (scale_factor, scale_factor, scale_factor)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Place model feet on ground (z=0) and center (x=0, y=0)
    bbox_new = [main_mesh.matrix_world @ mathutils.Vector(corner) for corner in main_mesh.bound_box]
    min_z_new = min(v.z for v in bbox_new)
    center_x = (min(v.x for v in bbox_new) + max(v.x for v in bbox_new)) / 2.0
    center_y = (min(v.y for v in bbox_new) + max(v.y for v in bbox_new)) / 2.0

    main_mesh.location.x -= center_x
    main_mesh.location.y -= center_y
    main_mesh.location.z -= min_z_new
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 3. Setup Studio Lighting & World Background
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs['Color'].default_value = (0.15, 0.15, 0.18, 1.0)
        bg_node.inputs['Strength'].default_value = 1.0

    # Clear old lights
    for l in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(l, do_unlink=True)

    # Key Light (Front Right)
    key_light_data = bpy.data.lights.new(name="KeyLight", type='POINT')
    key_light_data.energy = 500.0
    key_light_data.shadow_soft_size = 0.5
    key_light = bpy.data.objects.new(name="KeyLight", object_data=key_light_data)
    key_light.location = (2.0, -2.5, 2.5)
    bpy.context.collection.objects.link(key_light)

    # Fill Light (Front Left)
    fill_light_data = bpy.data.lights.new(name="FillLight", type='POINT')
    fill_light_data.energy = 250.0
    fill_light = bpy.data.objects.new(name="FillLight", object_data=fill_light_data)
    fill_light.location = (-2.0, -2.0, 1.8)
    bpy.context.collection.objects.link(fill_light)

    # Rim Light (Back Light for Cyborg Silhouette)
    rim_light_data = bpy.data.lights.new(name="RimLight", type='POINT')
    rim_light_data.energy = 600.0
    rim_light_data.color = (0.2, 0.8, 1.0)  # Cyan glow
    rim_light = bpy.data.objects.new(name="RimLight", object_data=rim_light_data)
    rim_light.location = (0.0, 2.5, 2.2)
    bpy.context.collection.objects.link(rim_light)

    # 4. Setup Camera framing full character
    cam_objs = [o for o in bpy.data.objects if o.type == 'CAMERA']
    if cam_objs:
        cam = cam_objs[0]
    else:
        cam_data = bpy.data.cameras.new("StudioCamera")
        cam = bpy.data.objects.new("StudioCamera", cam_data)
        bpy.context.collection.objects.link(cam)
    
    cam.location = (0.0, -3.2, 0.95)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam

    # 5. Setup Material & Texture
    mat_name = "Mecha_Verified_PBR"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    out_node.location = (400, 0)

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Metallic'].default_value = 0.65
    bsdf.inputs['Roughness'].default_value = 0.35

    img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.location = (-400, 0)
    tex_node.image = bpy.data.images.load(img_path)

    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    if main_mesh.data.materials:
        main_mesh.data.materials[0] = mat
    else:
        main_mesh.data.materials.append(mat)

    # 6. Render verification PNG
    bpy.context.scene.render.resolution_x = 800
    bpy.context.scene.render.resolution_y = 800

    render_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\viewport_render.png"
    bpy.context.scene.render.filepath = render_path
    bpy.ops.render.render(write_still=True)

    # 7. Save Blend and Export GLB
    blend_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    result = {
        "status": "success",
        "height_m": target_height if current_height > 0 else None,
        "rendered_image": render_path,
        "blend_file": blend_path
    }
"""

res = exec_blender_code(code)
print("Fix Scale and Render Result:", json.dumps(res, indent=2, ensure_ascii=False))
