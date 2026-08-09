#!/usr/bin/env python3
"""Export rigged model from Blender and copy to character pack exports directory."""

import json
import shutil
from pathlib import Path
from blender_mcp_client import exec_blender_code

code = """
import bpy

temp_glb = r"C:\\Users\\parkp\\AppData\\Local\\Temp\\mecha_yame_rigged.glb"
bpy.ops.export_scene.gltf(
    filepath=temp_glb,
    export_format='GLB',
    export_skins=True,
    export_morph=True,
    export_animations=False
)

result = {"status": "success", "temp_path": temp_glb}
"""

res = exec_blender_code(code)
print("Blender Export Result:", json.dumps(res, indent=2))

src = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_rigged.glb")
dst = Path(r"D:\캐릭터\drafts\mecha_yame_v1\exports\mecha_yame_rigged.glb")

if src.is_file():
    shutil.copyfile(src, dst)
    print(f"[SUCCESS] Exported and copied rigged GLB ({dst.stat().st_size} bytes) to {dst}")
else:
    print(f"[ERROR] Source GLB not found at {src}")
