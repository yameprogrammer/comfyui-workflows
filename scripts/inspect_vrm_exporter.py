#!/usr/bin/env python3
"""Inspect VRM exporter parameters in Blender via MCP."""

import json
from blender_mcp_client import exec_blender_code

code = """
import bpy

vrm_op = getattr(bpy.ops.export_scene, 'vrm', None)
op_doc = vrm_op.__doc__ if vrm_op else None

result = {
    "vrm_export_available": vrm_op is not None,
    "doc": op_doc
}
"""

res = exec_blender_code(code)
print("VRM Exporter Info:", json.dumps(res, indent=2))
