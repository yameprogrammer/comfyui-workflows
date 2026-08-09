#!/usr/bin/env python3
"""Automated Blender 3D Rigging and VRM Setup Script via MCP."""

import json
import sys
from pathlib import Path
from blender_mcp_client import exec_blender_code

def check_blender_environment():
    code = """
import bpy
import addon_utils

addons = [mod.__name__ for mod in addon_utils.modules()]
enabled_addons = [mod.__name__ for mod in addon_utils.modules() if addon_utils.check(mod.__name__)[0]]

vrm_addons = [a for a in addons if 'vrm' in a.lower()]

result = {
    "blender_version": list(bpy.app.version),
    "enabled_addons_count": len(enabled_addons),
    "vrm_addons_found": vrm_addons
}
"""
    return exec_blender_code(code)

def setup_and_rig_model(glb_path: str):
    code = f"""
import bpy
import math

# 1. Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import GLB
glb_file = r"{glb_path}"
bpy.ops.import_scene.gltf(filepath=glb_file)

# 3. Get imported mesh objects
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {{"status": "error", "message": "No mesh objects imported"}}
else:
    main_mesh = mesh_objs[0]
    bpy.context.view_layer.objects.active = main_mesh
    main_mesh.select_set(True)

    # 4. Center and scale mesh
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main_mesh.location = (0, 0, 0)
    
    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 5. Create Humanoid Armature (Basic Rigging)
    bpy.ops.object.armature_add(radius=0.1, enter_editmode=False, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Mecha_Humanoid_Rig"

    # Parent mesh to armature with automatic weights
    main_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    # 6. Add ARKit / VRM Blendshapes (Shape Keys) for facial tracking
    if not main_mesh.data.shape_keys:
        main_mesh.shape_key_add(name="Basis", from_mix=False)

    arkit_blendshapes = [
        "A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
        "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile"
    ]
    
    created_keys = []
    for key_name in arkit_blendshapes:
        if key_name not in main_mesh.data.shape_keys.key_blocks:
            sk = main_mesh.shape_key_add(name=key_name, from_mix=False)
            created_keys.append(key_name)

    # 7. Export rigged GLB model
    out_glb = r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_rigged.glb"
    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format='GLB',
        export_skins=True,
        export_morph=True,
        export_animations=False
    )

    result = {{
        "status": "success",
        "mesh_name": main_mesh.name,
        "poly_count": len(main_mesh.data.polygons),
        "armature_name": armature.name,
        "blendshapes_count": len(main_mesh.data.shape_keys.key_blocks),
        "created_shape_keys": created_keys,
        "exported_glb": out_glb
    }}
"""
    return exec_blender_code(code)

if __name__ == "__main__":
    print("=== Checking Blender Environment via MCP ===")
    env_info = check_blender_environment()
    print(json.dumps(env_info, indent=2, ensure_ascii=False))

    glb_target = r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_v1.glb"
    print(f"\n=== Executing Automated Rigging on {glb_target} ===")
    rig_res = setup_and_rig_model(glb_target)
    print(json.dumps(rig_res, indent=2, ensure_ascii=False))
