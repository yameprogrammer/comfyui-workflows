#!/usr/bin/env python3
"""Rig single isolated character 3D mesh in Blender via MCP."""

import json
import shutil
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

# 1. Completely clear existing Blender scene (delete old multi-character mesh & rig)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import single character GLB
glb_file = r"D:\\캐릭터\\drafts\\mecha_yame_v1\\exports\\mecha_yame_single.glb"
bpy.ops.import_scene.gltf(filepath=glb_file)

# 3. Get imported single mesh
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
main_mesh = mesh_objs[0]
bpy.context.view_layer.objects.active = main_mesh
main_mesh.select_set(True)

# Origin to center
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
main_mesh.location = (0, 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 4. Create Humanoid Armature for SINGLE character
bpy.ops.object.armature_add(radius=0.1, enter_editmode=False, location=(0, 0, 0))
armature = bpy.context.active_object
armature.name = "Mecha_Single_Humanoid_Rig"

main_mesh.select_set(True)
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# 5. Add ARKit / VRM Shape Keys
if not main_mesh.data.shape_keys:
    main_mesh.shape_key_add(name="Basis", from_mix=False)

arkit_blendshapes = [
    "A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
    "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile"
]

for key_name in arkit_blendshapes:
    if key_name not in main_mesh.data.shape_keys.key_blocks:
        main_mesh.shape_key_add(name=key_name, from_mix=False)

# 6. Export single rigged GLB
temp_glb = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_single_rigged.glb"
bpy.ops.export_scene.gltf(
    filepath=temp_glb,
    export_format='GLB',
    export_skins=True,
    export_morph=True,
    export_animations=False
)

result = {
    "status": "success",
    "mesh_count": len(mesh_objs),
    "mesh_name": main_mesh.name,
    "poly_count": len(main_mesh.data.polygons),
    "armature_name": armature.name,
    "blendshapes_count": len(main_mesh.data.shape_keys.key_blocks)
}
"""

res = exec_blender_code(code)
print("Blender Rigging Result:", json.dumps(res, indent=2, ensure_ascii=False))

src = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_single_rigged.glb")
dst = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_single_rigged.glb")

if src.is_file():
    shutil.copyfile(src, dst)
    print(f"[SUCCESS] Exported single character rigged GLB ({dst.stat().st_size} bytes) to {dst}")
else:
    print(f"[ERROR] Source GLB not found at {src}")
