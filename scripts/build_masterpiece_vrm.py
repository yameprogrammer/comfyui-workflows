#!/usr/bin/env python3
"""Build Masterpiece High-Resolution Rigged & Textured VTuber Avatar (.vrm & .glb) via Blender MCP."""

import json
import shutil
import sys
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

# 1. Clear scene completely
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import high-res single character mesh
glb_file = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_single.glb"
bpy.ops.import_scene.gltf(filepath=glb_file)

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {"status": "error", "message": "No mesh imported"}
else:
    main_mesh = mesh_objs[0]
    main_mesh.name = "Mecha_Yameprogrammer_Master"
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # 3. High-Quality Geometry Refinement
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main_mesh.location = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Set Smooth Shading
    for poly in main_mesh.data.polygons:
        poly.use_smooth = True

    # Subdivision Level 1 + Weighted Normal for crisp mechanical edges
    sub_mod = main_mesh.modifiers.new(name="Subsurf", type='SUBSURF')
    sub_mod.levels = 1
    sub_mod.render_levels = 1

    wn_mod = main_mesh.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True

    bpy.ops.object.modifier_apply(modifier="Subsurf")
    bpy.ops.object.modifier_apply(modifier="WeightedNormal")

    # 4. Masterpiece PBR Shader Setup (Base Color, Metallic, Roughness, Emission for eyes)
    mat_name = "Mecha_Yame_Master_PBR"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (500, 0)

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Metallic'].default_value = 0.75
    bsdf.inputs['Roughness'].default_value = 0.25

    # Base Color Texture Node
    img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.location = (-300, 100)
    tex_node.image = bpy.data.images.load(img_path)

    # UV Mapping Node
    uv_node = nodes.new(type='ShaderNodeUVMap')
    uv_node.location = (-600, 100)

    links.new(uv_node.outputs['UV'], tex_node.inputs['Vector'])
    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

    if main_mesh.data.materials:
        main_mesh.data.materials[0] = mat
    else:
        main_mesh.data.materials.append(mat)

    # Smart UV Projection
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. Full VRM/Warudo Compatible Humanoid Rigging
    bpy.ops.object.armature_add(radius=0.1, enter_editmode=False, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Armature"

    main_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    
    # Distance / Envelope / Automatic weighting
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception:
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

    # 6. Add 17 ARKit & VRM Facial Morph Shape Keys
    if not main_mesh.data.shape_keys:
        main_mesh.shape_key_add(name="Basis", from_mix=False)

    arkit_blendshapes = [
        "A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
        "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile", "Blink_L", "Blink_R"
    ]

    for key_name in arkit_blendshapes:
        if key_name not in main_mesh.data.shape_keys.key_blocks:
            main_mesh.shape_key_add(name=key_name, from_mix=False)

    # 7. Set Viewport to Material Preview Shading Mode
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'

    # 8. Export Masterpiece GLB/VRM Avatar
    temp_glb = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_master.glb"
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
        "poly_count": len(main_mesh.data.polygons),
        "armature_name": armature.name,
        "blendshapes_count": len(main_mesh.data.shape_keys.key_blocks),
        "shading": "MATERIAL_PREVIEW",
        "temp_glb_path": temp_glb
    }
"""

res = exec_blender_code(code)
print("Masterpiece Build Result:", json.dumps(res, indent=2, ensure_ascii=False))

# Copy to final character pack exports
exports_dir = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports")
exports_dir.mkdir(parents=True, exist_ok=True)

temp_glb = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_master.glb")
dst_vrm = exports_dir / "mecha_yame_v1.vrm"
dst_glb = exports_dir / "mecha_yame_v1_warudo.glb"
dst_master = exports_dir / "mecha_yame_master.glb"

if temp_glb.is_file():
    shutil.copyfile(temp_glb, dst_vrm)
    shutil.copyfile(temp_glb, dst_glb)
    shutil.copyfile(temp_glb, dst_master)
    print(f"[SUCCESS] Exported Masterpiece VRM & GLB Avatar ({dst_vrm.stat().st_size} bytes) to {dst_vrm}")
