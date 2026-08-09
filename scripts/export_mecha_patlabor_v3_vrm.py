#!/usr/bin/env python3
"""Export mecha_patlabor_v3 as real VRM for Warudo (VRM1 snake_case humanoid map)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3.blend"
VRM_OUT = EXPORTS / "mecha_patlabor_v3.vrm"
VRM_WARUDO = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
GLB_OUT = EXPORTS / "mecha_patlabor_v3_warudo.glb"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_patlabor_v3_export.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_patlabor_v3_export.glb")


def main() -> int:
    if not BLEND.is_file():
        print("[ERROR] missing", BLEND)
        return 1
    TEMP_VRM.parent.mkdir(parents=True, exist_ok=True)

    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP_VRM).replace("\\", "/"),
        "glb": str(TEMP_GLB).replace("\\", "/"),
        "vrm_final": str(VRM_OUT).replace("\\", "/"),
        "vrm_warudo": str(VRM_WARUDO).replace("\\", "/"),
        "glb_final": str(GLB_OUT).replace("\\", "/"),
        "blend_rigged": str(EXPORTS / "mecha_patlabor_v3_rigged.blend").replace("\\", "/"),
    }

    code = f'''
import bpy
import addon_utils
import shutil
from mathutils import Quaternion
from pathlib import Path

paths = {repr(paths)}
log = []

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

for o in bpy.data.objects:
    if o.type in {{"LIGHT", "CAMERA"}}:
        o.hide_render = True

window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

def with_ctx(active=None, selected=None):
    active = active or arm
    selected = selected or [arm, main]
    for o in bpy.data.objects:
        o.select_set(o in selected)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(
        window=window, area=area, region=region, scene=bpy.context.scene,
        view_layer=bpy.context.view_layer, active_object=active, object=active,
        selected_objects=selected, selected_editable_objects=selected,
    )

# VRM1 uses snake_case property names on human_bones
vrm1_map = {{
    "hips": "Hips",
    "spine": "Spine",
    "chest": "Chest",
    "neck": "Neck",
    "head": "Head",
    "left_shoulder": "LeftShoulder",
    "left_upper_arm": "LeftUpperArm",
    "left_lower_arm": "LeftLowerArm",
    "left_hand": "LeftHand",
    "right_shoulder": "RightShoulder",
    "right_upper_arm": "RightUpperArm",
    "right_lower_arm": "RightLowerArm",
    "right_hand": "RightHand",
    "left_upper_leg": "LeftUpperLeg",
    "left_lower_leg": "LeftLowerLeg",
    "left_foot": "LeftFoot",
    "right_upper_leg": "RightUpperLeg",
    "right_lower_leg": "RightLowerLeg",
    "right_foot": "RightFoot",
}}

ext = arm.data.vrm_addon_extension
# Prefer VRM 1.0
try:
    # enum values depend on addon version
    for val in ("1.0", "VRM1", "SPEC_VERSION_VRM1", ext.SPEC_VERSION_VRM1):
        try:
            ext.spec_version = val
            log.append(f"spec_version={{val}}")
            break
        except Exception:
            continue
except Exception as e:
    log.append(f"spec set err={{e}}")

mapped = []
# VRM1 assignment
try:
    hb = ext.vrm1.humanoid.human_bones
    # allow assignment even if hierarchy filter is picky
    if hasattr(hb, "filter_by_human_bone_hierarchy"):
        hb.filter_by_human_bone_hierarchy = False
        log.append("filter_by_human_bone_hierarchy=False")
    if hasattr(hb, "allow_non_humanoid_rig"):
        hb.allow_non_humanoid_rig = True
        log.append("allow_non_humanoid_rig=True")
    if hasattr(hb, "initial_automatic_bone_assignment"):
        hb.initial_automatic_bone_assignment = False
    for prop, bone in vrm1_map.items():
        slot = getattr(hb, prop, None)
        if slot is None:
            mapped.append(f"missing_slot:{{prop}}")
            continue
        node = getattr(slot, "node", None)
        if node is None:
            mapped.append(f"missing_node:{{prop}}")
            continue
        if bone in arm.data.bones:
            node.bone_name = bone
            mapped.append(f"vrm1.{{prop}}={{bone}}")
        else:
            mapped.append(f"missing_bone:{{bone}}")
except Exception as e:
    log.append(f"vrm1 map err={{e}}")

# VRM0 collection assignment (backup)
try:
    humanoid0 = ext.vrm0.humanoid
    if hasattr(humanoid0, "filter_by_human_bone_hierarchy"):
        humanoid0.filter_by_human_bone_hierarchy = False
    # VRM0 human_bones is a collection of items with .bone / .node
    hb0 = humanoid0.human_bones
    # ensure list populated
    if hasattr(humanoid0, "fixup_human_bones"):
        try:
            humanoid0.fixup_human_bones(arm)
            log.append("fixup_human_bones")
        except TypeError:
            try:
                humanoid0.fixup_human_bones()
                log.append("fixup_human_bones()")
            except Exception as e:
                log.append(f"fixup err={{e}}")
    # map by item.bone property name if present
    vrm0_name_map = {{
        "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
        "leftShoulder": "LeftShoulder", "leftUpperArm": "LeftUpperArm", "leftLowerArm": "LeftLowerArm", "leftHand": "LeftHand",
        "rightShoulder": "RightShoulder", "rightUpperArm": "RightUpperArm", "rightLowerArm": "RightLowerArm", "rightHand": "RightHand",
        "leftUpperLeg": "LeftUpperLeg", "leftLowerLeg": "LeftLowerLeg", "leftFoot": "LeftFoot",
        "rightUpperLeg": "RightUpperLeg", "rightLowerLeg": "RightLowerLeg", "rightFoot": "RightFoot",
    }}
    for item in hb0:
        # try common fields
        key = None
        for attr in ("bone", "specification", "human_bone", "name"):
            if hasattr(item, attr):
                try:
                    key = str(getattr(item, attr))
                    break
                except Exception:
                    pass
        # node.bone_name
        node = getattr(item, "node", None)
        bone_name = None
        # match key to map
        for k, v in vrm0_name_map.items():
            if key and (k.lower() in key.lower() or key.lower() in k.lower()):
                bone_name = v
                break
        # also try item.bone as enum identifier
        if bone_name is None and hasattr(item, "bone"):
            b = str(item.bone)
            bone_name = vrm0_name_map.get(b) or vrm0_name_map.get(b[0].lower() + b[1:] if b else "")
        if bone_name and node is not None and bone_name in arm.data.bones:
            node.bone_name = bone_name
            mapped.append(f"vrm0.{{key}}={{bone_name}}")
except Exception as e:
    log.append(f"vrm0 map err={{e}}")

# meta
try:
    if hasattr(ext, "vrm1") and hasattr(ext.vrm1, "meta"):
        # vrm1 meta authors etc may be collections; set title-like if available
        meta = ext.vrm1.meta
        if hasattr(meta, "name"):
            meta.name = "Mecha Patlabor VTuber v3"
    if hasattr(ext.vrm0, "meta"):
        ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
        ext.vrm0.meta.author = "yameprogrammer"
        ext.vrm0.meta.version = "0.3.0"
except Exception as e:
    log.append(f"meta err={{e}}")

# verify assignment snapshot
verify = {{}}
try:
    hb = ext.vrm1.humanoid.human_bones
    for prop in vrm1_map:
        slot = getattr(hb, prop, None)
        bn = slot.node.bone_name if slot and slot.node else None
        verify[prop] = bn
except Exception as e:
    verify = {{"err": str(e)}}

# export GLB
glb_ok = False
with with_ctx(selected=[arm, main]):
    r = bpy.ops.export_scene.gltf(
        filepath=paths["glb"], export_format="GLB", use_selection=True,
        export_apply=False, export_skins=True, export_morph=True,
    )
    glb_ok = Path(paths["glb"]).is_file()
    log.append(f"glb={{r}}")

# export VRM
Path(paths["vrm"]).unlink(missing_ok=True)
export_result = None
with with_ctx(active=arm, selected=[arm, main]):
    try:
        export_result = bpy.ops.export_scene.vrm(
            filepath=paths["vrm"],
            ignore_warning=True,
            check_existing=False,
            armature_object_name=arm.name,
            export_all_influences=True,
        )
    except Exception as e:
        log.append(f"export exception={{e}}")
        try:
            export_result = bpy.ops.export_scene.vrm(filepath=paths["vrm"], ignore_warning=True)
        except Exception as e2:
            log.append(f"export2={{e2}}")

size = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
head = b""
if size > 0:
    with open(paths["vrm"], "rb") as f:
        head = f.read(8)

copied = []
if size > 1000 and head[:4] == b"glTF":
    for dst in (paths["vrm_final"], paths["vrm_warudo"]):
        shutil.copyfile(paths["vrm"], dst)
        copied.append(dst)
if glb_ok:
    shutil.copyfile(paths["glb"], paths["glb_final"])
    copied.append(paths["glb_final"])

try:
    bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
    bpy.ops.wm.save_as_mainfile(filepath=paths["blend_rigged"])
    log.append("blend saved")
except Exception as e:
    log.append(f"save {{e}}")

result = {{
    "status": "ok" if size > 1000 and head[:4] == b"glTF" else "error",
    "log": log,
    "mapped": mapped,
    "verify_vrm1": verify,
    "export_result": list(export_result) if export_result else None,
    "vrm_size": size,
    "is_glb_magic": head[:4] == b"glTF" if head else False,
    "glb_ok": glb_ok,
    "copied": copied,
    "spec_version": getattr(ext, "spec_version", None),
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:8000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] VRM export failed")
        # print verify for debug
        if isinstance(payload, dict):
            print("verify", payload.get("verify_vrm1"))
        return 1

    for p in (VRM_OUT, VRM_WARUDO):
        print("[OK]", p, p.stat().st_size)
    if GLB_OUT.is_file():
        print("[OK GLB]", GLB_OUT, GLB_OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
