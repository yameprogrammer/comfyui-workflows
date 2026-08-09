#!/usr/bin/env python3
"""Check VRM export capabilities and addons in Blender via MCP."""

import json
from blender_mcp_client import exec_blender_code

code = """
import bpy, addon_utils

modules = [mod.__name__ for mod in addon_utils.modules()]
vrm_modules = [m for m in modules if 'vrm' in m.lower()]
enabled_vrm = [m for m in vrm_modules if addon_utils.check(m)[0]]

result = {
    "all_vrm_addons": vrm_modules,
    "enabled_vrm_addons": enabled_vrm,
    "has_vrm_export_op": hasattr(bpy.ops.export_scene, 'vrm')
}
"""

res = exec_blender_code(code)
print("Blender VRM Check:", json.dumps(res, indent=2))
