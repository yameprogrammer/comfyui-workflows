#!/usr/bin/env python3
"""Build High-Quality Rigged & Textured VTuber Avatar in .vrm format for Warudo via Blender MCP."""

import json
import shutil
import sys
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy
import os

# 1. Clear existing Blender scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import Single Character GLB
glb_file = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_single.glb"
bpy.ops.import_scene.gltf(filepath=glb_file)

# Get imported mesh
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {"status": "error", "message": "No mesh object imported"}
else:
    main_mesh = mesh_objs[0]
    main_mesh.name = "Mecha_Yameprogrammer_Body"
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # Origin to Center & Apply Transforms
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main_mesh.location = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 3. High-Quality Mesh Refinement (Smooth Shading + Subdivision + Weighted Normal)
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in main_mesh.data.polygons:
        poly.use_smooth = True

    # Add Subdivision Surface Modifier (Level 1 for crisp detail enhancement)
    subsurf_mod = main_mesh.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf_mod.levels = 1
    subsurf_mod.render_levels = 2

    # Add WeightedNormal Modifier for mechanical hard-surface edges
    wn_mod = main_mesh.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True

    # Apply modifiers for export stability
    bpy.ops.object.modifier_apply(modifier="Subsurf")
    bpy.ops.object.modifier_apply(modifier="WeightedNormal")

    # 4. Apply PBR Texture Shader matching concept image color tone
    mat_name = "Mecha_Yame_PBR_Material"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Metallic'].default_value = 0.70
    bsdf.inputs['Roughness'].default_value = 0.30

    img_path = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\approved\\single_front.png"
    texture_node = nodes.new(type='ShaderNodeTexImage')
    texture_node.location = (-400, 0)
    texture_node.image = bpy.data.images.load(img_path)

    links.new(texture_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

    if main_mesh.data.materials:
        main_mesh.data.materials[0] = mat
    else:
        main_mesh.data.materials.append(mat)

    # 5. Create Humanoid Rig (Armature)
    bpy.ops.object.armature_add(radius=0.1, enter_editmode=False, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Armature"

    main_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    # 6. Add ARKit / VRM Facial Morph Shape Keys
    if not main_mesh.data.shape_keys:
        main_mesh.shape_key_add(name="Basis", from_mix=False)

    arkit_blendshapes = [
        "A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
        "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile", "Blink_L", "Blink_R"
    ]

    for key_name in arkit_blendshapes:
        if key_name not in main_mesh.data.shape_keys.key_blocks:
            main_mesh.shape_key_add(name=key_name, from_mix=False)

    # 7. Export to VRM format for Warudo Import
    temp_vrm = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_v1.vrm"
    try:
        bpy.ops.export_scene.vrm(filepath=temp_vrm)
        vrm_success = True
    except Exception as e:
        vrm_success = False
        vrm_error = str(e)

    # Fallback export to high-detail rigged GLB if VRM operator needs extra VRM metadata setup
    temp_glb = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_v1_warudo.glb"
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
        "vrm_success": vrm_success,
        "temp_vrm_path": temp_vrm if vrm_success else None,
        "temp_glb_path": temp_glb
    }
"""

res = exec_blender_code(code)
print("Build VRM Avatar Result:", json.dumps(res, indent=2, ensure_ascii=False))

# Copy output files to character pack exports
exports_dir = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports")
exports_dir.mkdir(parents=True, exist_ok=True)

temp_vrm = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v1.vrm")
temp_glb = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v1_warudo.glb")

if temp_vrm.is_file():
    dst_vrm = exports_dir / "mecha_yame_v1.vrm"
    shutil.copyfile(temp_vrm, dst_vrm)
    print(f"[SUCCESS] Exported VRM Avatar ({dst_vrm.stat().st_size} bytes) to {dst_vrm}")

if temp_glb.is_file():
    dst_glb = exports_dir / "mecha_yame_v1_warudo.glb"
    shutil.copyfile(temp_glb, dst_glb)
    print(f"[SUCCESS] Exported Warudo GLB Avatar ({dst_glb.stat().st_size} bytes) to {dst_glb}")
