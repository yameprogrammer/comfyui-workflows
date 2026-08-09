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
bpy.ops.wm.open_mainfile(filepath=r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3.blend")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

info = {"arm": arm.name, "bones": [b.name for b in arm.data.bones]}
ext = getattr(arm.data, "vrm_addon_extension", None)
info["has_ext_on_data"] = ext is not None
if ext is None:
    ext = getattr(arm, "vrm_addon_extension", None)
    info["has_ext_on_obj"] = ext is not None

def dump_hb(hb, label):
    out = {"label": label, "type": str(type(hb)), "attrs": []}
    # list interesting attrs
    for name in dir(hb):
        if name.startswith("_"):
            continue
        try:
            val = getattr(hb, name)
        except Exception:
            continue
        if callable(val):
            continue
        # node?
        node = getattr(val, "node", None)
        if node is not None:
            bn = getattr(node, "bone_name", None)
            out["attrs"].append({"name": name, "bone_name": bn, "node_type": str(type(node))})
        else:
            t = type(val).__name__
            if t in ("str", "int", "float", "bool") or val is None:
                out["attrs"].append({"name": name, "value": val})
    return out

if ext:
    info["ext_type"] = str(type(ext))
    info["ext_dir"] = [x for x in dir(ext) if not x.startswith("_")][:40]
    for root_name in ("vrm0", "vrm1"):
        root = getattr(ext, root_name, None)
        if root is None:
            info[root_name] = None
            continue
        humanoid = getattr(root, "humanoid", None)
        info[root_name] = {
            "humanoid_type": str(type(humanoid)) if humanoid else None,
            "humanoid_dir": [x for x in dir(humanoid) if not x.startswith("_")][:50] if humanoid else None,
        }
        if humanoid:
            hb = getattr(humanoid, "human_bones", None)
            if hb is not None:
                info[root_name]["human_bones"] = dump_hb(hb, root_name)
            # alternate collections
            for alt in ("human_bone", "humanBones", "human_bones"):
                if hasattr(humanoid, alt):
                    info[root_name][f"has_{alt}"] = True

result = info
'''
print(json.dumps(exec_blender_code(code), indent=2, ensure_ascii=False)[:12000])
