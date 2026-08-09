#!/usr/bin/env python3
"""Install/enable VRM addon if needed, assign humanoid bones, export real VRM for Warudo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.blend")
VRM_OUT = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.vrm")
# also a clearly named warudo target
VRM_WARUDO = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2_warudo.vrm")


def main() -> int:
    blend = str(BLEND).replace("\\", "/")
    vrm_out = str(VRM_OUT).replace("\\", "/")
    vrm_warudo = str(VRM_WARUDO).replace("\\", "/")

    code = f"""
import bpy
import addon_utils
from pathlib import Path

blend_path = r"{blend}"
vrm_out = r"{vrm_out}"
vrm_warudo = r"{vrm_warudo}"

# --- enable VRM extension ---
enable_log = []
candidates = [
    "bl_ext.user_default.vrm",
    "vrm",
    "bl_ext.blender_org.vrm",
]
for name in candidates:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
        enable_log.append({{"name": name, "ok": True}})
    except Exception as e:
        enable_log.append({{"name": name, "ok": False, "err": str(e)}})

# also try preferences
try:
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.vrm")
    enable_log.append({{"name": "prefs_enable", "ok": True}})
except Exception as e:
    enable_log.append({{"name": "prefs_enable", "ok": False, "err": str(e)}})

has_export = hasattr(bpy.ops.export_scene, "vrm")
export_ops = [x for x in dir(bpy.ops.export_scene) if not x.startswith("_")]
wm_ops = [x for x in dir(bpy.ops.wm) if "vrm" in x.lower()]

if not has_export:
    result = {{
        "status": "error",
        "message": "export_scene.vrm not available after enable",
        "enable_log": enable_log,
        "export_ops": export_ops,
        "wm_ops": wm_ops,
        "addons": [a.module for a in bpy.context.preferences.addons],
    }}
else:
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    mesh = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if arm is None:
        result = {{"status": "error", "message": "no armature", "enable_log": enable_log}}
    else:
        bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm

        # Assign VRM humanoid bones via addon API if present
        assign_log = []
        # Our bone names already match VRM-ish English names
        bone_map = {{
            "hips": "Hips",
            "spine": "Spine",
            "chest": "Chest",
            "neck": "Neck",
            "head": "Head",
            "leftShoulder": "LeftShoulder",
            "leftUpperArm": "LeftUpperArm",
            "leftLowerArm": "LeftLowerArm",
            "leftHand": "LeftHand",
            "rightShoulder": "RightShoulder",
            "rightUpperArm": "RightUpperArm",
            "rightLowerArm": "RightLowerArm",
            "rightHand": "RightHand",
            "leftUpperLeg": "LeftUpperLeg",
            "leftLowerLeg": "LeftLowerLeg",
            "leftFoot": "LeftFoot",
            "rightUpperLeg": "RightUpperLeg",
            "rightLowerLeg": "RightLowerLeg",
            "rightFoot": "RightFoot",
        }}

        # Prefer VRM 0.x meta for broadest Warudo compatibility
        try:
            # Create VRM model extensions on armature
            if hasattr(bpy.ops.vrm, "model_validate"):
                assign_log.append("has vrm.model_validate")
        except Exception:
            pass

        # Use addon operator to assign human bones automatically by name
        auto_ok = None
        for op_path in [
            ("vrm", "assign_vrm0_humanoid_human_bones_automatically"),
            ("vrm", "assign_vrm1_humanoid_human_bones_automatically"),
            ("vrm", "load_human_bone_mappings"),
        ]:
            try:
                mod = getattr(bpy.ops, op_path[0], None)
                if mod and hasattr(mod, op_path[1]):
                    getattr(mod, op_path[1])()
                    auto_ok = op_path[1]
                    break
            except Exception as e:
                assign_log.append(f"{{op_path}}: {{e}}")

        # Manual VRM0 humanoid assignment via RNA if available
        ext = getattr(arm.data, "vrm_addon_extension", None)
        if ext is None:
            # Blender 4+ extension path
            ext = getattr(arm, "vrm_addon_extension", None)
        humanoid_info = None
        try:
            # typical path: arm.data.vrm_addon_extension.vrm0.humanoid
            vrm0 = ext.vrm0 if ext else None
            humanoid = vrm0.humanoid if vrm0 else None
            if humanoid is not None:
                # human_bones may be a collection
                hb = getattr(humanoid, "human_bones", None)
                if hb is not None:
                    for vrm_name, bone_name in bone_map.items():
                        # try attribute style: humanoid.human_bones.hips.node.bone_name
                        slot = getattr(hb, vrm_name, None)
                        if slot is not None and hasattr(slot, "node"):
                            try:
                                slot.node.bone_name = bone_name if bone_name in arm.data.bones else ""
                            except Exception as e:
                                assign_log.append(f"set {{vrm_name}}: {{e}}")
                    humanoid_info = "vrm0_human_bones_set"
                else:
                    # older list style
                    for item in getattr(humanoid, "human_bone", []) or getattr(humanoid, "human_bones", []) or []:
                        pass
                    humanoid_info = "vrm0_present_unknown_structure"
        except Exception as e:
            assign_log.append(f"manual assign: {{e}}")

        # Meta title
        try:
            if ext and hasattr(ext, "vrm0") and hasattr(ext.vrm0, "meta"):
                ext.vrm0.meta.title = "Mecha Yameprogrammer v2"
                ext.vrm0.meta.author = "yameprogrammer"
                ext.vrm0.meta.version = "0.2.0"
        except Exception as e:
            assign_log.append(f"meta: {{e}}")

        # Export with ignore_warning if needed
        window = bpy.context.window_manager.windows[0]
        area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
        region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
        bpy.context.view_layer.objects.active = arm
        export_result = None
        export_err = None
        with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=arm):
            try:
                export_result = bpy.ops.export_scene.vrm(
                    filepath=vrm_out,
                    export_invisibles=False,
                    export_only_selections=False,
                    armature_object_name=arm.name,
                    ignore_warning=True,
                    check_existing=False,
                )
            except Exception as e:
                export_err = str(e)
                # second try minimal kwargs
                try:
                    export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)
                except Exception as e2:
                    export_err = f"{{export_err}} | {{e2}}"

        # copy to warudo-named path via blender? use pathlib outside
        size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
        # validate magic: VRM is glb with extensions - starts with glTF
        head = b""
        if size > 0:
            with open(vrm_out, "rb") as f:
                head = f.read(20)

        result = {{
            "status": "success" if size > 1000 else "error",
            "enable_log": enable_log,
            "has_export": has_export,
            "auto_ok": auto_ok,
            "assign_log": assign_log,
            "humanoid_info": humanoid_info,
            "export_result": list(export_result) if export_result else None,
            "export_err": export_err,
            "vrm_out": vrm_out,
            "size": size,
            "head_hex": head.hex() if head else "",
            "is_glb_magic": head[:4] == b"glTF" if head else False,
            "armature": arm.name,
            "bones": [b.name for b in arm.data.bones],
        }}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:6000])

    # copy warudo-named file outside blender
    if VRM_OUT.is_file() and VRM_OUT.stat().st_size > 1000:
        import shutil
        shutil.copyfile(VRM_OUT, VRM_WARUDO)
        print(f"[OK] {VRM_OUT} ({VRM_OUT.stat().st_size} bytes)")
        print(f"[OK] {VRM_WARUDO}")
        # quick structural check: VRM should contain "VRM" or "VRMC" in json chunk
        data = VRM_OUT.read_bytes()
        has_vrm_ext = b"VRM" in data or b"VRMC" in data
        print(f"[check] contains VRM marker: {has_vrm_ext}")
        if not has_vrm_ext:
            print("[WARN] file may still be plain GLB without VRM extension")
            return 2
        return 0
    print("[ERROR] VRM export failed or too small", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
