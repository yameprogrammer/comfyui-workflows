#!/usr/bin/env python3
"""Export VRM only (no reimport). Then postprocess structure to match v2."""

from __future__ import annotations

import json
import shutil
import struct
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


def postprocess(src: Path, dst: Path) -> dict:
    gltf, bin_chunk = load_glb(src)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    joints = skin["joints"]
    want = [
        "Hips", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
        "RightUpperLeg", "RightLowerLeg", "RightFoot",
        "Spine", "Chest", "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
        "Neck", "Head", "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
    ]
    # Keep original joint order for first 19 if they match want order-ish
    name_to_node = {}
    for j in joints:
        nm = nodes[j].get("name")
        if nm and nm not in name_to_node:
            name_to_node[nm] = j
    real = [name_to_node[n] for n in want if n in name_to_node]
    if len(real) < 19:
        real = joints[:19]
    # Only truncate if first N joints equal real (weight indices safe)
    if joints[: len(real)] == real:
        skin["joints"] = real
        ibm = skin.get("inverseBindMatrices")
        if ibm is not None:
            gltf["accessors"][ibm]["count"] = len(real)
    else:
        # weights reference skin joint indices by position in joints array.
        # If order of first 19 is already correct PascalCase, truncate.
        first_names = [nodes[j].get("name") for j in joints[:19]]
        if set(first_names) >= set(want) and all(n[0].isupper() for n in first_names if n):
            skin["joints"] = joints[:19]
            ibm = skin.get("inverseBindMatrices")
            if ibm is not None:
                gltf["accessors"][ibm]["count"] = 19

    mesh_i = next(i for i, n in enumerate(nodes) if "mesh" in n)
    hips_i = name_to_node.get("Hips") or next(i for i, n in enumerate(nodes) if n.get("name") == "Hips")
    for n in nodes:
        if n.get("children"):
            n["children"] = [c for c in n["children"] if c != mesh_i]
    gltf["scenes"] = [{"name": "Scene", "nodes": [mesh_i, hips_i]}]
    gltf["scene"] = 0

    # rebuild name map preferring first occurrence
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
    if "VRMC_vrm" in gltf.get("extensions", {}):
        hb = {k: {"node": name_to_idx[b]} for k, b in remap.items() if b in name_to_idx}
        gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
        meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = "0.3.5"
        meta["authors"] = ["yameprogrammer"]

    save_glb(dst, gltf, bin_chunk)
    g2, _ = load_glb(dst)
    return {
        "scene": [[i, g2["nodes"][i].get("name")] for i in g2["scenes"][0]["nodes"]],
        "joints": len(g2["skins"][0]["joints"]),
        "joint_names": [g2["nodes"][j].get("name") for j in g2["skins"][0]["joints"]],
        "head": g2["nodes"][g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"]["node"]].get("name"),
        "leftUpperArm": g2["nodes"][
            g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["leftUpperArm"]["node"]
        ].get("name"),
        "size": dst.stat().st_size,
    }


def main() -> int:
    TEMP_VRM.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP_VRM).replace("\\", "/"),
        "glb": str(TEMP_GLB).replace("\\", "/"),
    }

    code = f'''
import bpy, addon_utils
from mathutils import Quaternion
from pathlib import Path

paths = {repr(paths)}
log = []
addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
main = next(o for o in bpy.data.objects if o.type=="MESH")

for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)

# parent mesh to armature preserving world matrix
for m in list(main.modifiers):
    if m.type == "ARMATURE":
        main.modifiers.remove(m)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
_mw = main.matrix_world.copy()
main.parent = arm
main.matrix_world = _mw

for o in bpy.data.objects:
    if o.type in {{"LIGHT","CAMERA"}}:
        o.hide_render = True
        o.hide_viewport = True

ext = arm.data.vrm_addon_extension
# Try VRM1 (same as working v2 file)
try:
    ext.spec_version = "1.0"
    log.append("spec=1.0")
except Exception as e:
    log.append(f"spec {{e}}")

v1 = {{
    "hips":"Hips","spine":"Spine","chest":"Chest","neck":"Neck","head":"Head",
    "left_shoulder":"LeftShoulder","left_upper_arm":"LeftUpperArm","left_lower_arm":"LeftLowerArm","left_hand":"LeftHand",
    "right_shoulder":"RightShoulder","right_upper_arm":"RightUpperArm","right_lower_arm":"RightLowerArm","right_hand":"RightHand",
    "left_upper_leg":"LeftUpperLeg","left_lower_leg":"LeftLowerLeg","left_foot":"LeftFoot",
    "right_upper_leg":"RightUpperLeg","right_lower_leg":"RightLowerLeg","right_foot":"RightFoot",
}}
try:
    hb = ext.vrm1.humanoid.human_bones
    hb.filter_by_human_bone_hierarchy = False
    for prop, bone in v1.items():
        slot = getattr(hb, prop, None)
        if slot and slot.node and bone in arm.data.bones:
            slot.node.bone_name = bone
except Exception as e:
    log.append(f"v1 {{e}}")

try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.5"
except Exception:
    pass

win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type=="VIEW_3D")
region = next(r for r in area.regions if r.type=="WINDOW")
for o in bpy.data.objects:
    o.select_set(o in (arm, main))
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(window=win, area=area, region=region, scene=bpy.context.scene, active_object=arm, selected_objects=[arm,main]):
    bpy.ops.export_scene.gltf(filepath=paths["glb"], export_format="GLB", use_selection=True, export_apply=False, export_skins=True, export_morph=True)
    Path(paths["vrm"]).unlink(missing_ok=True)
    r = bpy.ops.export_scene.vrm(filepath=paths["vrm"], ignore_warning=True, check_existing=False, armature_object_name=arm.name, export_all_influences=True)
    log.append(f"export={{list(r)}}")

sz = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
result = {{"status":"ok" if sz>1000 else "error", "size": sz, "log": log}}
'''

    res = exec_blender_code(code)
    print("export", json.dumps(res, indent=2, ensure_ascii=False)[:2500])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "ok":
        return 1

    info = postprocess(TEMP_VRM, OUT_VRM)
    shutil.copyfile(OUT_VRM, OUT_VRM2)
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, OUT_GLB)
    print("post", json.dumps(info, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
