#!/usr/bin/env python3
"""Apply PBR Textures, UV Mapping, Shader Nodes, and Smooth Normal Refinement in Blender via MCP."""

import json
import shutil
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

# 1. Get main mesh object in active scene
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {"status": "error", "message": "No mesh object found in scene"}
else:
    main_mesh = mesh_objs[0]
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # 2. Smooth Shading & Mechanical Contour Refinement
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in main_mesh.data.polygons:
        poly.use_smooth = True

    # Add WeightedNormal modifier for sharp mechanical edges
    wn_mod = main_mesh.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True

    # 3. Create UV Unwrapping (Front Projection for 2D Concept Alignment)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Smart UV Project + Front View UV projection
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 4. Create PBR Material Shader with Texture Mapping
    mat_name = "Mecha_Cyborg_PBR_Material"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    nodes.clear()

    # Create Material Output
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    # Create Principled BSDF Shader
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Adjust PBR parameters for sleek industrial cyborg look
    bsdf.inputs['Metallic'].default_value = 0.65
    bsdf.inputs['Roughness'].default_value = 0.35

    # Load 2D Concept Texture Image
    img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
    texture_node = nodes.new(type='ShaderNodeTexImage')
    texture_node.location = (-400, 0)
    texture_node.image = bpy.data.images.load(img_path)

    # Link Texture -> Principled BSDF Base Color
    links.new(texture_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

    # Assign material to main mesh
    if main_mesh.data.materials:
        main_mesh.data.materials[0] = mat
    else:
        main_mesh.data.materials.append(mat)

    # 5. Export updated Textured GLB model
    temp_glb = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_textured.glb"
    bpy.ops.export_scene.gltf(
        filepath=temp_glb,
        export_format='GLB',
        export_skins=True,
        export_morph=True,
        export_materials='EXPORT',
        export_animations=False
    )

    result = {
        "status": "success",
        "mesh_name": main_mesh.name,
        "material_name": mat.name,
        "texture_file": img_path,
        "smooth_shading": True,
        "weighted_normals": True,
        "metallic": 0.65,
        "roughness": 0.35
    }
"""

res = exec_blender_code(code)
print("Blender Material & Texture Result:", json.dumps(res, indent=2, ensure_ascii=False))

src = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_textured.glb")
dst = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_textured.glb")

if src.is_file():
    shutil.copyfile(src, dst)
    print(f"[SUCCESS] Exported textured & refined GLB ({dst.stat().st_size} bytes) to {dst}")
else:
    print(f"[ERROR] Source GLB not found at {src}")
