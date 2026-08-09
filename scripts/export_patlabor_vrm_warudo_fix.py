#!/usr/bin/env python3
"""
Export patlabor VRM for Warudo by mirroring the successful mecha_yame_v2 path:
- mesh parented to armature
- VRM0 preferred (broader Warudo compat) + VRM1 fallback
- make_estimated_humanoid_t_pose when available
- no destructive postprocess that leaves ghost nodes
- verify import+pose after export
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3.blend"
OUT_VRM = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
OUT_VRM2 = EXPORTS / "mecha_patlabor_v3.vrm"
OUT_GLB = EXPORTS / "mecha_patlabor_v3_warudo.glb"
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_warudo_fix.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_warudo_fix.glb")


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP_VRM).replace("\\", "/"),
        "glb": str(TEMP_GLB).replace("\\", "/"),
        "out_vrm": str(OUT_VRM).replace("\\", "/"),
        "out_vrm2": str(OUT_VRM2).replace("\\", "/"),
        "out_glb": str(OUT_GLB).replace("\\", "/"),
        "blend_save": str(BLEND).replace("\\", "/"),
    }

    code = f'''
import bpy
import addon_utils
import shutil
from mathutils import Quaternion, Vector, Euler
from pathlib import Path

paths = {repr(paths)}
log = []

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# rest pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)

# Ensure armature modifier + parent (glTF/VRM exporter expects this; v2 import also parents)
for m in list(main.modifiers):
    if m.type == "ARMATURE":
        main.modifiers.remove(m)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
# parent while preserving world matrix (required by VRM exporter)
_mw = main.matrix_world.copy()
main.parent = arm
main.matrix_world = _mw

# hide extras
for o in bpy.data.objects:
    if o.type in {{"LIGHT", "CAMERA"}}:
        o.hide_render = True
        o.hide_viewport = True

ext = arm.data.vrm_addon_extension

# Prefer VRM 0.0 for maximum Warudo/Unity humanoid compatibility
spec_set = None
for cand in (
    getattr(ext, "SPEC_VERSION_VRM0", None),
    "0.0",
    "VRM0",
    "0",
):
    if cand is None:
        continue
    try:
        ext.spec_version = cand
        spec_set = str(cand)
        break
    except Exception as e:
        log.append(f"spec try {{cand}}: {{e}}")
if spec_set is None:
    try:
        ext.spec_version = "1.0"
        spec_set = "1.0-fallback"
    except Exception as e:
        log.append(f"spec1 {{e}}")
log.append(f"spec_version={{spec_set}} actual={{getattr(ext, 'spec_version', None)}}")

# Assign humanoid bones (VRM0 collection + VRM1 attrs)
bone_map_v1 = {{
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
    "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm",
    "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
    "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm",
    "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
    "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg", "left_foot": "LeftFoot",
    "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg", "right_foot": "RightFoot",
}}
bone_map_v0 = {{
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "upperChest": "Chest",
    "neck": "Neck", "head": "Head",
    "leftShoulder": "LeftShoulder", "leftUpperArm": "LeftUpperArm",
    "leftLowerArm": "LeftLowerArm", "leftHand": "LeftHand",
    "rightShoulder": "RightShoulder", "rightUpperArm": "RightUpperArm",
    "rightLowerArm": "RightLowerArm", "rightHand": "RightHand",
    "leftUpperLeg": "LeftUpperLeg", "leftLowerLeg": "LeftLowerLeg", "leftFoot": "LeftFoot",
    "rightUpperLeg": "RightUpperLeg", "rightLowerLeg": "RightLowerLeg", "rightFoot": "RightFoot",
}}

win = bpy.context.window_manager.windows[0]
area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

def ctx(active=None, selected=None):
    active = active or arm
    selected = selected or [arm, main]
    for o in bpy.data.objects:
        o.select_set(o in selected)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(
        window=win, area=area, region=region, scene=bpy.context.scene,
        view_layer=bpy.context.view_layer, active_object=active, object=active,
        selected_objects=selected, selected_editable_objects=selected,
    )

with ctx():
    for opn in (
        "assign_vrm0_humanoid_human_bones_automatically",
        "assign_vrm1_humanoid_human_bones_automatically",
    ):
        try:
            op = getattr(bpy.ops.vrm, opn, None)
            if op:
                log.append(f"{{opn}}={{list(op())}}")
        except Exception as e:
            log.append(f"{{opn}} err={{e}}")

# force VRM1 slots
try:
    hb = ext.vrm1.humanoid.human_bones
    if hasattr(hb, "filter_by_human_bone_hierarchy"):
        hb.filter_by_human_bone_hierarchy = False
    if hasattr(hb, "allow_non_humanoid_rig"):
        hb.allow_non_humanoid_rig = False  # require proper humanoid like v2
    for prop, bone in bone_map_v1.items():
        slot = getattr(hb, prop, None)
        if slot and slot.node and bone in arm.data.bones:
            slot.node.bone_name = bone
except Exception as e:
    log.append(f"vrm1 force {{e}}")

# force VRM0 collection
try:
    h0 = ext.vrm0.humanoid
    if hasattr(h0, "filter_by_human_bone_hierarchy"):
        h0.filter_by_human_bone_hierarchy = False
    if hasattr(h0, "fixup_human_bones"):
        try:
            h0.fixup_human_bones(arm)
        except TypeError:
            h0.fixup_human_bones()
    for item in h0.human_bones:
        # item.bone is enum like 'HEAD', 'LEFT_UPPER_ARM'
        key = str(getattr(item, "bone", ""))
        node = getattr(item, "node", None)
        if not node:
            continue
        # map enum to bone name
        enum_map = {{
            "HIPS": "Hips", "SPINE": "Spine", "CHEST": "Chest", "UPPER_CHEST": "Chest",
            "NECK": "Neck", "HEAD": "Head",
            "LEFT_SHOULDER": "LeftShoulder", "LEFT_UPPER_ARM": "LeftUpperArm",
            "LEFT_LOWER_ARM": "LeftLowerArm", "LEFT_HAND": "LeftHand",
            "RIGHT_SHOULDER": "RightShoulder", "RIGHT_UPPER_ARM": "RightUpperArm",
            "RIGHT_LOWER_ARM": "RightLowerArm", "RIGHT_HAND": "RightHand",
            "LEFT_UPPER_LEG": "LeftUpperLeg", "LEFT_LOWER_LEG": "LeftLowerLeg", "LEFT_FOOT": "LeftFoot",
            "RIGHT_UPPER_LEG": "RightUpperLeg", "RIGHT_LOWER_LEG": "RightLowerLeg", "RIGHT_FOOT": "RightFoot",
        }}
        # also try lower
        bname = enum_map.get(key) or enum_map.get(key.upper()) or bone_map_v0.get(key)
        if bname and bname in arm.data.bones:
            node.bone_name = bname
except Exception as e:
    log.append(f"vrm0 force {{e}}")

# T-pose estimate for humanoid (important for Unity/Warudo muscle mapping)
with ctx():
    try:
        r = bpy.ops.vrm.make_estimated_humanoid_t_pose()
        log.append(f"t_pose={{list(r)}}")
    except Exception as e:
        log.append(f"t_pose err={{e}}")
    try:
        r = bpy.ops.vrm.model_validate()
        log.append(f"validate={{list(r)}}")
    except Exception as e:
        log.append(f"validate err={{e}}")

# meta
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.4"
except Exception:
    pass
try:
    if hasattr(ext.vrm1, "meta") and hasattr(ext.vrm1.meta, "name"):
        ext.vrm1.meta.name = "Mecha Patlabor VTuber v3"
except Exception:
    pass

# Export — select arm+mesh, active arm
with ctx(selected=[arm, main]):
    try:
        bpy.ops.export_scene.gltf(
            filepath=paths["glb"], export_format="GLB", use_selection=True,
            export_apply=False, export_skins=True, export_morph=True,
        )
        log.append("glb ok")
    except Exception as e:
        log.append(f"glb {{e}}")

    export_result = None
    for kwargs in (
        dict(filepath=paths["vrm"], ignore_warning=True, check_existing=False, armature_object_name=arm.name),
        dict(filepath=paths["vrm"], ignore_warning=True, check_existing=False),
        dict(filepath=paths["vrm"], ignore_warning=True, export_all_influences=True, armature_object_name=arm.name),
    ):
        Path(paths["vrm"]).unlink(missing_ok=True)
        try:
            export_result = bpy.ops.export_scene.vrm(**kwargs)
            sz = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
            log.append(f"vrm try {{list(export_result)}} size={{sz}}")
            if sz > 1000:
                break
        except Exception as e:
            log.append(f"vrm err {{e}}")

size = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
if size > 1000:
    shutil.copyfile(paths["vrm"], paths["out_vrm"])
    shutil.copyfile(paths["vrm"], paths["out_vrm2"])
if Path(paths["glb"]).is_file():
    shutil.copyfile(paths["glb"], paths["out_glb"])

# save blend
bpy.ops.wm.save_as_mainfile(filepath=paths["blend_save"])

# Immediate re-import pose test of exported file
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.vrm(filepath=paths["out_vrm"])
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
pose_test = {{}}
if meshes and arms:
    main2, arm2 = meshes[0], arms[0]
    coords0 = [v.co.copy() for v in main2.data.vertices]
    pb = arm2.pose.bones.get("LeftUpperArm") or arm2.pose.bones.get("leftUpperArm")
    if pb:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, -1.0, 0)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        me = main2.evaluated_get(deps).to_mesh()
        maxd = max((me.vertices[i].co - coords0[i]).length for i in range(len(me.vertices)))
        moved = sum(1 for i in range(len(me.vertices)) if (me.vertices[i].co - coords0[i]).length > 0.001)
        main2.evaluated_get(deps).to_mesh_clear()
        pose_test = {{"arm_max_delta": round(maxd, 4), "arm_moved": moved, "bones": len(arm2.pose.bones)}}

result = {{
    "status": "ok" if size > 1000 else "error",
    "log": log,
    "size": size,
    "spec": spec_set,
    "pose_test_reimport": pose_test,
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:6000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "ok":
        return 1

    # Structural compare / cleanup ghost joints if any
    import struct

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

    gltf, bin_chunk = load_glb(OUT_VRM)
    nodes = gltf["nodes"]
    skins = gltf.get("skins") or []
    report = {
        "nodes": len(nodes),
        "joints": len(skins[0]["joints"]) if skins else 0,
        "joint_names": [nodes[j].get("name") for j in skins[0]["joints"]] if skins else [],
        "scene": [[i, nodes[i].get("name")] for i in gltf["scenes"][0]["nodes"]],
        "spec": (gltf.get("extensions") or {}).get("VRMC_vrm", {}).get("specVersion")
        or (gltf.get("extensions") or {}).get("VRM", {}).get("specVersion"),
        "ext_keys": list((gltf.get("extensions") or {}).keys()),
    }

    # If ghost joints present, strip like before + scene = mesh+Hips
    if skins and len(skins[0]["joints"]) > 19:
        real = []
        seen = set()
        want = {
            "Hips", "Spine", "Chest", "Neck", "Head",
            "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
            "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
            "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
            "RightUpperLeg", "RightLowerLeg", "RightFoot",
        }
        for j in skins[0]["joints"]:
            nm = nodes[j].get("name")
            if nm in want and nm not in seen:
                real.append(j)
                seen.add(nm)
        skins[0]["joints"] = real
        ibm = skins[0].get("inverseBindMatrices")
        if ibm is not None:
            gltf["accessors"][ibm]["count"] = len(real)
        report["stripped_joints_to"] = len(real)

    # force scene mesh+Hips
    mesh_i = next(i for i, n in enumerate(nodes) if "mesh" in n)
    hips_i = next(i for i, n in enumerate(nodes) if n.get("name") == "Hips")
    for n in nodes:
        if n.get("children"):
            n["children"] = [c for c in n["children"] if c != mesh_i]
    gltf["scenes"] = [{"name": "Scene", "nodes": [mesh_i, hips_i]}]

    # force humanoid to PascalCase
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i
    remap = {
        "hips": "Hips", "spine": "Spine", "chest": "Chest", "upperChest": "Chest",
        "neck": "Neck", "head": "Head",
        "leftShoulder": "LeftShoulder", "leftUpperArm": "LeftUpperArm",
        "leftLowerArm": "LeftLowerArm", "leftHand": "LeftHand",
        "rightShoulder": "RightShoulder", "rightUpperArm": "RightUpperArm",
        "rightLowerArm": "RightLowerArm", "rightHand": "RightHand",
        "leftUpperLeg": "LeftUpperLeg", "leftLowerLeg": "LeftLowerLeg", "leftFoot": "LeftFoot",
        "rightUpperLeg": "RightUpperLeg", "rightLowerLeg": "RightLowerLeg", "rightFoot": "RightFoot",
    }
    # ensure VRMC_vrm
    if "VRMC_vrm" in gltf.get("extensions", {}):
        hb = {}
        for k, b in remap.items():
            if b in name_to_idx:
                hb[k] = {"node": name_to_idx[b]}
        gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
        gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})["name"] = "Mecha Patlabor VTuber v3"
    # also VRM0 extension if present
    if "VRM" in gltf.get("extensions", {}):
        # VRM0 humanoid.humanBones is list of {{bone, node}}
        try:
            human_bones = []
            for k, b in remap.items():
                if b in name_to_idx:
                    # VRM0 bone enum is often same camelCase key
                    human_bones.append({"bone": k, "node": name_to_idx[b]})
            gltf["extensions"]["VRM"]["humanoid"]["humanBones"] = human_bones
        except Exception as e:
            report["vrm0_fix_err"] = str(e)

    save_glb(OUT_VRM, gltf, bin_chunk)
    shutil.copyfile(OUT_VRM, OUT_VRM2)
    report["final_scene"] = [[i, nodes[i].get("name")] for i in gltf["scenes"][0]["nodes"]]
    report["final_joints"] = len(gltf["skins"][0]["joints"])
    report["final_humanoid_head"] = gltf["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"]
    print("FINAL", json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
