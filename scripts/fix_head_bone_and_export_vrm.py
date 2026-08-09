#!/usr/bin/env python3
"""
Shorten Head/Neck bones to humanoid-friendly lengths (Warudo/Unity),
keep arm bones, re-export VRM without scene-graph hacks.
"""

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
OUT = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
OUT2 = EXPORTS / "mecha_patlabor_v3.vrm"
OUT3 = EXPORTS / "mecha_patlabor_v3_warudo_v038.vrm"
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_headfix.vrm")


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


def humanoid_only(path: Path) -> dict:
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i
    skin = gltf["skins"][0]
    jn = [nodes[j].get("name") for j in skin["joints"]]
    if len(skin["joints"]) > 19 and all((n or "x")[0].isupper() for n in jn[:19]):
        skin["joints"] = skin["joints"][:19]
        if skin.get("inverseBindMatrices") is not None:
            gltf["accessors"][skin["inverseBindMatrices"]]["count"] = 19
    skin.pop("skeleton", None)
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
    hb = {k: {"node": name_to_idx[b]} for k, b in remap.items() if b in name_to_idx}
    gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
    meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
    meta["name"] = "Mecha Patlabor VTuber v3"
    meta["version"] = "0.3.9"
    meta["authors"] = ["yameprogrammer"]
    gltf.pop("animations", None)
    save_glb(path, gltf, bin_chunk)
    return {
        "joints": len(gltf["skins"][0]["joints"]),
        "scene": [[i, nodes[i].get("name")] for i in gltf["scenes"][0]["nodes"]],
        "head": nodes[hb["head"]["node"]].get("name"),
        "size": path.stat().st_size,
    }


def main() -> int:
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP).replace("\\", "/"),
        "blend_save": str(BLEND).replace("\\", "/"),
        "blend_rigged": str(EXPORTS / "mecha_patlabor_v3_rigged.blend").replace("\\", "/"),
    }

    code = f'''
import bpy, addon_utils, math
from mathutils import Vector, Quaternion
from pathlib import Path

paths = {repr(paths)}
log = []
bone_info = {{}}
addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)

# parent mesh
for m in list(main.modifiers):
    if m.type == "ARMATURE":
        main.modifiers.remove(m)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
mw = main.matrix_world.copy()
main.parent = arm
main.matrix_world = mw

win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")

def ov(active, selected):
    for o in bpy.data.objects:
        o.select_set(o in selected)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(window=win, area=area, region=region, scene=bpy.context.scene, view_layer=bpy.context.view_layer, active_object=active, object=active, selected_objects=selected, selected_editable_objects=selected)

# --- shorten Neck / Head for Unity humanoid ---
with ov(arm, [arm]):
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    chest = eb["Chest"]
    neck = eb["Neck"]
    head = eb["Head"]
    neck_len = 0.07
    head_len = 0.12  # humanoid-friendly (was ~0.45 covering whole helmet)
    neck.head = chest.tail.copy()
    neck.tail = neck.head + Vector((0, 0, neck_len))
    head.head = neck.tail.copy()
    head.tail = head.head + Vector((0, 0, head_len))
    neck.parent = chest
    head.parent = neck
    eb["LeftShoulder"].parent = chest
    eb["RightShoulder"].parent = chest
    bone_info = {{
        "Neck": {{"len": round((neck.tail-neck.head).length, 3)}},
        "Head": {{"len": round((head.tail-head.head).length, 3)}},
    }}
    bpy.ops.object.mode_set(mode="OBJECT")

# Re-weight HEAD more tightly around head bone center (helmet still deforms with Head)
# Keep simple: any vert above neck head.z - small margin -> Head dominant
mw = main.matrix_world
neck_z = (arm.matrix_world @ arm.data.bones["Neck"].head_local).z
head_c = arm.matrix_world @ ((arm.data.bones["Head"].head_local + arm.data.bones["Head"].tail_local) * 0.5)
# clear Head/Neck groups and reassign upper verts
for name in ("Head", "Neck"):
    if name in main.vertex_groups:
        main.vertex_groups.remove(main.vertex_groups[name])
main.vertex_groups.new(name="Head")
main.vertex_groups.new(name="Neck")

for v in main.data.vertices:
    p = mw @ v.co
    # remove old head/neck weights from other groups? keep and overwrite head/neck
    if p.z >= neck_z - 0.02:
        # blend neck band
        if p.z < neck_z + 0.05:
            main.vertex_groups["Neck"].add([v.index], 0.55, "REPLACE")
            main.vertex_groups["Head"].add([v.index], 0.45, "REPLACE")
            # zero torso influence on these verts
            for gn in ("Chest", "Spine", "Hips"):
                if gn in main.vertex_groups:
                    try:
                        main.vertex_groups[gn].add([v.index], 0.0, "REPLACE")
                    except Exception:
                        pass
        else:
            main.vertex_groups["Head"].add([v.index], 1.0, "REPLACE")
            for gn in ("Neck", "Chest", "Spine", "Hips"):
                if gn in main.vertex_groups:
                    try:
                        main.vertex_groups[gn].add([v.index], 0.0, "REPLACE")
                    except Exception:
                        pass

# normalize all weights
for v in main.data.vertices:
    total = sum(g.weight for g in v.groups)
    if total <= 1e-8:
        main.vertex_groups["Hips"].add([v.index], 1.0, "REPLACE")
    elif abs(total - 1.0) > 0.02:
        for g in v.groups:
            g.weight /= total

# VRM map + export
ext = arm.data.vrm_addon_extension
try:
    ext.spec_version = "1.0"
except Exception:
    pass
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
    for p,b in v1.items():
        slot = getattr(hb, p, None)
        if slot and slot.node and b in arm.data.bones:
            slot.node.bone_name = b
except Exception as e:
    log.append(str(e))
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.9"
except Exception:
    pass

for o in bpy.data.objects:
    if o.type in {{"LIGHT","CAMERA"}}:
        o.hide_render = True
with ov(arm, [arm, main]):
    Path(paths["vrm"]).unlink(missing_ok=True)
    r = bpy.ops.export_scene.vrm(filepath=paths["vrm"], ignore_warning=True, check_existing=False, armature_object_name=arm.name, export_all_influences=True)
    log.append(f"export={{list(r)}}")

# save blend with shortened head bones
bpy.ops.wm.save_as_mainfile(filepath=paths["blend_save"])
import shutil
shutil.copyfile(paths["blend_save"], paths["blend_rigged"])

sz = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
result = {{"status": "ok" if sz>1000 else "error", "size": sz, "log": log, "bones": bone_info}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "ok":
        return 1

    info = humanoid_only(TEMP)
    for dst in (OUT, OUT2, OUT3):
        shutil.copyfile(TEMP, dst)
    print("final", json.dumps(info, indent=2, ensure_ascii=False))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
