#!/usr/bin/env python3
"""
Export patlabor VRM using the EXACT same method as mecha_yame_v2 (export_mecha_yame_v2_vrm.py).
No scene-graph postprocess. Only optional humanoid node remap if ghost bones appear.
"""

from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

BLEND = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3.blend")
VRM_OUT = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3_warudo.vrm")
VRM_ALT = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3.vrm")
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_exact_v2.vrm")


def load_glb(path: Path):
    data = path.read_bytes()
    off = 12
    gltf = bin_chunk = None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off : off + clen]
        off += clen
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            bin_chunk = chunk
    return gltf, bin_chunk


def save_glb(path: Path, gltf, bin_chunk):
    jb = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    chunks = struct.pack("<I4s", len(jb), b"JSON") + jb
    if bin_chunk is not None:
        bb = bin_chunk + b"\x00" * ((4 - len(bin_chunk) % 4) % 4)
        chunks += struct.pack("<I4s", len(bb), b"BIN\x00") + bb
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks)


def remap_humanoid_only(path: Path) -> dict:
    """Only fix humanBones to PascalCase skinned nodes. Do NOT change hierarchy/skin/IBM."""
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
    # Prefer first occurrence of each name (skinned chain comes first)
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i

    remap = {
        "hips": "Hips",
        "spine": "Spine",
        "chest": "Chest",
        "upperChest": "Chest",
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
    }

    changes = []
    if "VRMC_vrm" in gltf.get("extensions", {}):
        hb = gltf["extensions"]["VRMC_vrm"].setdefault("humanoid", {}).setdefault("humanBones", {})
        for k, bone in remap.items():
            if bone not in name_to_idx:
                continue
            new_i = name_to_idx[bone]
            old = hb.get(k, {}).get("node")
            old_n = nodes[old].get("name") if old is not None else None
            hb[k] = {"node": new_i}
            if old != new_i:
                changes.append(f"{k}: {old_n}->{bone}")
        meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = "0.3.7"
        meta["authors"] = ["yameprogrammer"]
        # remove skeleton field if present (v2 has null)
        if gltf.get("skins"):
            gltf["skins"][0].pop("skeleton", None)
        # remove animations that might confuse
        gltf.pop("animations", None)

    save_glb(path, gltf, bin_chunk)
    g2, _ = load_glb(path)
    skin = g2["skins"][0]
    return {
        "changes": changes,
        "joints": len(skin["joints"]),
        "joint_names": [g2["nodes"][j].get("name") for j in skin["joints"]],
        "scene": [[i, g2["nodes"][i].get("name")] for i in g2["scenes"][0]["nodes"]],
        "humanoid_head": g2["nodes"][
            g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"]["node"]
        ].get("name"),
        "humanoid_arm": g2["nodes"][
            g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["leftUpperArm"]["node"]
        ].get("name"),
        "size": path.stat().st_size,
    }


def main() -> int:
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    blend = str(BLEND).replace("\\", "/")
    vrm_out = str(TEMP).replace("\\", "/")

    # Nearly identical to export_mecha_yame_v2_vrm.py
    code = f'''
import bpy
import addon_utils
from pathlib import Path
from mathutils import Quaternion

blend_path = r"{blend}"
vrm_out = r"{vrm_out}"

enable_log = []
for name in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
        enable_log.append({{"name": name, "ok": True}})
    except Exception as e:
        enable_log.append({{"name": name, "ok": False, "err": str(e)}})

has_export = hasattr(bpy.ops.export_scene, "vrm")
if not has_export:
    result = {{"status": "error", "message": "no export_scene.vrm", "enable_log": enable_log}}
else:
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    mesh = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if arm is None or mesh is None:
        result = {{"status": "error", "message": "missing arm/mesh"}}
    else:
        # rest pose
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1,0,0,0))
            pb.location = (0,0,0)
            pb.scale = (1,1,1)

        # ensure armature modifier + parent (like a normal rigged character)
        for m in list(mesh.modifiers):
            if m.type == "ARMATURE":
                mesh.modifiers.remove(m)
        am = mesh.modifiers.new("Armature", "ARMATURE")
        am.object = arm
        am.use_vertex_groups = True
        mw = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_world = mw

        # delete lights/cameras to avoid export junk
        for o in list(bpy.data.objects):
            if o.type in {{"LIGHT", "CAMERA"}}:
                bpy.data.objects.remove(o, do_unlink=True)

        bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = arm

        ext = arm.data.vrm_addon_extension
        try:
            ext.spec_version = "1.0"
        except Exception:
            pass

        # VRM1 snake_case assignment (this is what actually works on this addon)
        try:
            hb = ext.vrm1.humanoid.human_bones
            hb.filter_by_human_bone_hierarchy = False
            mapping = {{
                "hips":"Hips","spine":"Spine","chest":"Chest","neck":"Neck","head":"Head",
                "left_shoulder":"LeftShoulder","left_upper_arm":"LeftUpperArm","left_lower_arm":"LeftLowerArm","left_hand":"LeftHand",
                "right_shoulder":"RightShoulder","right_upper_arm":"RightUpperArm","right_lower_arm":"RightLowerArm","right_hand":"RightHand",
                "left_upper_leg":"LeftUpperLeg","left_lower_leg":"LeftLowerLeg","left_foot":"LeftFoot",
                "right_upper_leg":"RightUpperLeg","right_lower_leg":"RightLowerLeg","right_foot":"RightFoot",
            }}
            for k,v in mapping.items():
                slot = getattr(hb, k, None)
                if slot and slot.node and v in arm.data.bones:
                    slot.node.bone_name = v
        except Exception as e:
            enable_log.append({{"vrm1": str(e)}})

        # auto assign ops like v2
        auto_ok = None
        for op_name in [
            "assign_vrm0_humanoid_human_bones_automatically",
            "assign_vrm1_humanoid_human_bones_automatically",
        ]:
            try:
                op = getattr(bpy.ops.vrm, op_name, None)
                if op:
                    op()
                    auto_ok = op_name
                    break
            except Exception as e:
                enable_log.append({{"auto": str(e)}})

        try:
            ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
            ext.vrm0.meta.author = "yameprogrammer"
            ext.vrm0.meta.version = "0.3.7"
        except Exception:
            pass

        window = bpy.context.window_manager.windows[0]
        area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
        region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
        bpy.context.view_layer.objects.active = arm
        export_result = None
        export_err = None
        Path(vrm_out).unlink(missing_ok=True)
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
                try:
                    export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)
                except Exception as e2:
                    export_err = f"{{export_err}} | {{e2}}"

        size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
        head = b""
        if size > 0:
            with open(vrm_out, "rb") as f:
                head = f.read(4)
        result = {{
            "status": "success" if size > 1000 and head == b"glTF" else "error",
            "enable_log": enable_log,
            "auto_ok": auto_ok,
            "export_result": list(export_result) if export_result else None,
            "export_err": export_err,
            "size": size,
            "bones": [b.name for b in arm.data.bones],
            "vgroups": len(mesh.vertex_groups),
        }}
'''

    res = exec_blender_code(code)
    print("blender:", json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "success":
        return 1

    # minimal humanoid remap only
    info = remap_humanoid_only(TEMP)
    shutil.copyfile(TEMP, VRM_OUT)
    shutil.copyfile(TEMP, VRM_ALT)
    print("remap:", json.dumps(info, indent=2, ensure_ascii=False))
    print("OUT", VRM_OUT, VRM_OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
