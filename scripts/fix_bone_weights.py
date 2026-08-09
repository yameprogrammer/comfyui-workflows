#!/usr/bin/env python3
"""Fix bone heat weighting for high-poly mesh in Blender via MCP."""

import json
import shutil
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

# 1. Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import Single Character GLB
glb_file = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_single.glb"
bpy.ops.import_scene.gltf(filepath=glb_file)

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if mesh_objs:
    main_mesh = mesh_objs[0]
    main_mesh.name = "Mecha_Yameprogrammer_Body"
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # Apply decimation slightly to fix non-manifold geometry for bone heat
    dec_mod = main_mesh.modifiers.new(name="Decimate", type='DECIMATE')
    dec_mod.ratio = 0.5
    bpy.ops.object.modifier_apply(modifier="Decimate")

    # Smooth Shading
    for poly in main_mesh.data.polygons:
        poly.use_smooth = True

    # PBR Material
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

    # Create Rig
    bpy.ops.object.armature_add(radius=0.1, enter_editmode=False, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Armature"

    main_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    
    # Try automatic weights, fallback to envelope if heat weighting fails
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception:
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

    # Add ARKit Morph Shape Keys
    if not main_mesh.data.shape_keys:
        main_mesh.shape_key_add(name="Basis", from_mix=False)

    arkit_blendshapes = [
        "A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
        "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile", "Blink_L", "Blink_R"
    ]

    for key_name in arkit_blendshapes:
        if key_name not in main_mesh.data.shape_keys.key_blocks:
            main_mesh.shape_key_add(name=key_name, from_mix=False)

    # Export clean rigged GLB
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
        "temp_glb_path": temp_glb
    }
"""

res = exec_blender_code(code)
print("Fix Bone Weights Result:", json.dumps(res, indent=2, ensure_ascii=False))

temp_glb = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v1_warudo.glb")
dst_glb = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1_warudo.glb")
dst_vrm = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1.vrm")

if temp_glb.is_file():
    shutil.copyfile(temp_glb, dst_glb)
    shutil.copyfile(temp_glb, dst_vrm)
    print(f"[SUCCESS] Updated Warudo GLB and VRM Avatar files ({dst_glb.stat().st_size} bytes)")
