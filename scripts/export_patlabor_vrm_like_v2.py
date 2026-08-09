#!/usr/bin/env python3
"""
Re-export mecha_patlabor_v3 VRM matching mecha_yame_v2 structure:
- scene roots: mesh + Hips (no Armature empty wrapper)
- single 19-joint skin (no ghost hips/head/leftUpperArm skeleton)
- humanoid -> skinned PascalCase bones
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3.blend"
VRM_OUT = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
VRM_ALT = EXPORTS / "mecha_patlabor_v3.vrm"
GLB_OUT = EXPORTS / "mecha_patlabor_v3_warudo.glb"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_vrm_like_v2.vrm")
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_vrm_like_v2.glb")


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


def save_glb(path: Path, gltf: dict, bin_chunk: bytes | None):
    jb = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    chunks = struct.pack("<I4s", len(jb), b"JSON") + jb
    if bin_chunk is not None:
        bb = bin_chunk + (b"\x00" * ((4 - len(bin_chunk) % 4) % 4))
        chunks += struct.pack("<I4s", len(bb), b"BIN\x00") + bb
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks)


def postprocess_like_v2(src: Path, dst: Path) -> dict:
    """Strip ghost skeleton + Armature wrapper; remap humanoid; scene=[mesh,Hips]."""
    gltf, bin_chunk = load_glb(src)
    nodes = gltf["nodes"]
    name_to_idx = {n.get("name"): i for i, n in enumerate(nodes) if n.get("name")}

    # Identify skinned joint nodes by primary skin joint list names (PascalCase first 19)
    skin = gltf["skins"][0]
    joints = skin["joints"]
    joint_names = [nodes[j].get("name") for j in joints]
    # keep only first occurrence of each bone that matches real armature names
    real_names = {
        "Hips", "Spine", "Chest", "Neck", "Head",
        "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
        "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
        "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
        "RightUpperLeg", "RightLowerLeg", "RightFoot",
    }
    real_joint_nodes = []
    for j, nm in zip(joints, joint_names):
        if nm in real_names and nm not in [nodes[x].get("name") for x in real_joint_nodes]:
            real_joint_nodes.append(j)

    if len(real_joint_nodes) != 19:
        # fallback: first 19 joints
        real_joint_nodes = joints[:19]

    mesh_node = next(i for i, n in enumerate(nodes) if "mesh" in n)
    hips_node = next(i for i, n in enumerate(nodes) if n.get("name") == "Hips")

    # Clear mesh parent by ensuring scene roots
    # Remove mesh from any children lists
    for n in nodes:
        if n.get("children"):
            n["children"] = [c for c in n["children"] if c != mesh_node]

    # Scene like v2: mesh + Hips as roots
    gltf["scenes"] = [{"name": "Scene", "nodes": [mesh_node, hips_node]}]
    gltf["scene"] = 0

    # Truncate skin to real joints only (first 19 match weights max index 18)
    # IBM accessor count must match - truncate count if same order
    skin["joints"] = real_joint_nodes
    ibm = skin.get("inverseBindMatrices")
    if ibm is not None:
        acc = gltf["accessors"][ibm]
        # only safe if original joints order started with real 19
        if acc.get("count", 0) >= 19 and joints[:19] == real_joint_nodes:
            acc["count"] = 19
        # else leave full IBM; extra matrices unused if joints truncated carefully
        # If joints list shorter than IBM, glTF invalid — force count=len(joints)
        acc["count"] = len(real_joint_nodes)

    # Humanoid map to PascalCase nodes
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
    vrm = gltf["extensions"]["VRMC_vrm"]
    hb = {}
    for k, bone in remap.items():
        if bone in name_to_idx:
            hb[k] = {"node": name_to_idx[bone]}
    vrm["humanoid"] = {"humanBones": hb}

    # meta names like a real avatar
    meta = vrm.setdefault("meta", {})
    meta["name"] = "Mecha Patlabor VTuber v3"
    meta["version"] = "0.3.3"
    if "authors" in meta:
        meta["authors"] = ["yameprogrammer"]

    save_glb(dst, gltf, bin_chunk)

    # verify
    g2, _ = load_glb(dst)
    return {
        "dst": str(dst),
        "size": dst.stat().st_size,
        "scene_nodes": g2["scenes"][0]["nodes"],
        "scene_names": [g2["nodes"][i].get("name") for i in g2["scenes"][0]["nodes"]],
        "joint_count": len(g2["skins"][0]["joints"]),
        "joint_names": [g2["nodes"][j].get("name") for j in g2["skins"][0]["joints"]],
        "humanoid": {
            k: g2["nodes"][v["node"]].get("name")
            for k, v in g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"].items()
        },
        "mesh_node": next(
            (i, n.get("name"), n.get("skin"))
            for i, n in enumerate(g2["nodes"])
            if "mesh" in n
        ),
    }


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "temp_vrm": str(TEMP).replace("\\", "/"),
        "temp_glb": str(TEMP_GLB).replace("\\", "/"),
    }
    TEMP.parent.mkdir(parents=True, exist_ok=True)

    code = f'''
import bpy
import addon_utils
from mathutils import Quaternion
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

# CRITICAL: unparent mesh from Armature object (keep modifier) — matches v2 export layout
for m in main.modifiers:
    if m.type == "ARMATURE":
        m.object = arm
        m.use_vertex_groups = True
main.parent = None
main.matrix_parent_inverse.identity()
# put mesh at origin
main.location = (0,0,0)
main.rotation_euler = (0,0,0)
main.scale = (1,1,1)

# hide lights/cameras
for o in list(bpy.data.objects):
    if o.type in {{"LIGHT", "CAMERA", "EMPTY"}} and o != arm:
        o.hide_render = True
        o.hide_viewport = True

# VRM1 mapping only on real bones
ext = arm.data.vrm_addon_extension
try:
    ext.spec_version = "1.0"
except Exception:
    pass
vrm1_map = {{
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
    "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm",
    "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
    "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm",
    "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
    "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg", "left_foot": "LeftFoot",
    "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg", "right_foot": "RightFoot",
}}
try:
    hb = ext.vrm1.humanoid.human_bones
    hb.filter_by_human_bone_hierarchy = False
    if hasattr(hb, "allow_non_humanoid_rig"):
        hb.allow_non_humanoid_rig = True
    for prop, bone in vrm1_map.items():
        slot = getattr(hb, prop, None)
        if slot and slot.node and bone in arm.data.bones:
            slot.node.bone_name = bone
except Exception as e:
    log.append(str(e))
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.3"
except Exception:
    pass

# select only mesh + armature
for o in bpy.data.objects:
    o.select_set(o in (arm, main))
win = bpy.context.window_manager.windows[0]
area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(window=win, area=area, region=region, scene=bpy.context.scene, active_object=arm, selected_objects=[arm, main]):
    bpy.ops.export_scene.gltf(
        filepath=paths["temp_glb"], export_format="GLB", use_selection=True,
        export_apply=False, export_skins=True, export_morph=True,
    )
    r = bpy.ops.export_scene.vrm(
        filepath=paths["temp_vrm"],
        ignore_warning=True,
        check_existing=False,
        armature_object_name=arm.name,
        export_all_influences=True,
        export_only_selections=False,
    )
    log.append(f"export={{list(r) if r else None}}")

# restore parent for blender workfile convenience? keep unparented like export
bpy.ops.wm.save_as_mainfile(filepath=r"{str(BLEND).replace(chr(92), '/')}")

size = Path(paths["temp_vrm"]).stat().st_size if Path(paths["temp_vrm"]).is_file() else 0
result = {{"status": "ok" if size > 1000 else "error", "log": log, "size": size, "temp": paths["temp_vrm"]}}
'''

    res = exec_blender_code(code)
    print("blender:", json.dumps(res, indent=2, ensure_ascii=False)[:3000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("export failed")
        return 1

    raw = TEMP
    if not raw.is_file():
        print("temp missing")
        return 1

    # postprocess structure
    info = postprocess_like_v2(raw, VRM_OUT)
    # copy alt
    import shutil

    shutil.copyfile(VRM_OUT, VRM_ALT)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
    print("post:", json.dumps(info, indent=2, ensure_ascii=False))

    # final hist quick
    g, b = load_glb(VRM_OUT)
    print("final joints", len(g["skins"][0]["joints"]), [g["nodes"][j]["name"] for j in g["skins"][0]["joints"]])
    print("final scene", g["scenes"])
    print("humanoid head", g["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
