#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

code = r'''
import bpy
import addon_utils

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
ops = [x for x in dir(bpy.ops.export_scene) if "vrm" in x.lower()]
props = []
try:
    op = bpy.ops.export_scene.vrm
    rna = op.get_rna_type()
    for p in rna.properties:
        if p.identifier == "rna_type":
            continue
        default = None
        try:
            default = p.default
        except Exception:
            pass
        props.append({"id": p.identifier, "type": p.type, "default": str(default)})
except Exception as e:
    props = [{"error": str(e)}]
vrm_ops = [x for x in dir(bpy.ops.vrm) if not x.startswith("_")] if hasattr(bpy.ops, "vrm") else []
result = {"export_ops": ops, "props": props, "vrm_ops": vrm_ops}
'''
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False))
