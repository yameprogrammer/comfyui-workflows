#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

code = """
import bpy
blend = r"D:/캐릭터/drafts/mecha_yame_v2/exports/mecha_yame_v2.blend"
bpy.ops.wm.open_mainfile(filepath=blend)
main = next(o for o in bpy.data.objects if o.type == "MESH")
info = {
    "mesh": main.name,
    "materials": [],
    "uv_layers": [uv.name for uv in main.data.uv_layers],
    "images": [],
}
for i, slot in enumerate(main.material_slots):
    mat = slot.material
    entry = {
        "slot": i,
        "name": mat.name if mat else None,
        "use_nodes": bool(mat and mat.use_nodes),
        "textures": [],
        "base_color": None,
    }
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                entry["textures"].append({
                    "node": n.name,
                    "image": n.image.name,
                    "size": list(n.image.size) if n.image.size else None,
                })
            if n.type == "BSDF_PRINCIPLED":
                bc = n.inputs.get("Base Color")
                if bc is not None:
                    entry["base_color"] = "linked" if bc.is_linked else [round(c, 3) for c in bc.default_value[:3]]
    info["materials"].append(entry)
for img in bpy.data.images:
    if img.size[0] > 0:
        info["images"].append({
            "name": img.name,
            "size": list(img.size),
            "filepath": img.filepath,
        })
result = info
"""
print(json.dumps(exec_blender_code(code), ensure_ascii=False, indent=2)[:4000])
