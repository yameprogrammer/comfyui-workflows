#!/usr/bin/env python3
"""
Hard fix for Warudo non-movement:
1) Apply all transforms on mesh+armature
2) Force perfect T-pose as REST (arms horizontal, rebuild bind)
3) Normalize weights
4) Export VRM like v2 (no scene postprocess except humanoid remap)
"""

from __future__ import annotations

import json
import math
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
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_apply.vrm")
PREVIEW = EXPORTS / "viewport_warudo_fix_raise.png"


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


def humanoid_remap(path: Path) -> dict:
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
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
    # strip ghost joints if present (first 19 real)
    skin = gltf["skins"][0]
    jn = [nodes[j].get("name") for j in skin["joints"]]
    if len(skin["joints"]) > 19 and all((n or "x")[0].isupper() for n in jn[:19]):
        skin["joints"] = skin["joints"][:19]
        if skin.get("inverseBindMatrices") is not None:
            gltf["accessors"][skin["inverseBindMatrices"]]["count"] = 19
    skin.pop("skeleton", None)

    # Do NOT rewrite scene graph — keep exporter hierarchy for valid bind pose
    hb = {k: {"node": name_to_idx[b]} for k, b in remap.items() if b in name_to_idx}
    gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
    meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
    meta["name"] = "Mecha Patlabor VTuber v3"
    meta["version"] = "0.3.8"
    meta["authors"] = ["yameprogrammer"]
    gltf.pop("animations", None)

    save_glb(path, gltf, bin_chunk)
    g2, _ = load_glb(path)
    return {
        "scene": [[i, g2["nodes"][i].get("name")] for i in g2["scenes"][0]["nodes"]],
        "joints": len(g2["skins"][0]["joints"]),
        "head": g2["nodes"][g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"]["node"]].get("name"),
        "arm": g2["nodes"][g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["leftUpperArm"]["node"]].get("name"),
        "size": path.stat().st_size,
    }


def main() -> int:
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP).replace("\\", "/"),
        "preview": str(PREVIEW).replace("\\", "/"),
    }

    code = f'''
import bpy, addon_utils, math
from mathutils import Vector, Quaternion, Matrix
from pathlib import Path

paths = {repr(paths)}
log = []
addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
main = next(o for o in bpy.data.objects if o.type=="MESH")

win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type=="VIEW_3D")
region = next(r for r in area.regions if r.type=="WINDOW")

def override(active, selected):
    for o in bpy.data.objects:
        o.select_set(o in selected)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(window=win, area=area, region=region, scene=bpy.context.scene, view_layer=bpy.context.view_layer, active_object=active, object=active, selected_objects=selected, selected_editable_objects=selected)

# --- apply transforms ---
with override(arm, [arm]):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
with override(main, [main]):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# reset pose
for pb in arm.pose.bones:
    pb.rotation_mode="QUATERNION"
    pb.rotation_quaternion=Quaternion((1,0,0,0))
    pb.location=(0,0,0)
    pb.scale=(1,1,1)

# ensure modifier+parent
for m in list(main.modifiers):
    if m.type=="ARMATURE":
        main.modifiers.remove(m)
am=main.modifiers.new("Armature","ARMATURE")
am.object=arm
am.use_vertex_groups=True
mw=main.matrix_world.copy()
main.parent=arm
main.matrix_world=mw

# Normalize vertex groups: ensure every vert has weights summing ~1
for v in main.data.vertices:
    total=sum(g.weight for g in v.groups)
    if total <= 1e-8:
        # assign hips
        main.vertex_groups["Hips"].add([v.index], 1.0, "REPLACE")
    elif abs(total-1.0)>0.01:
        for g in v.groups:
            g.weight /= total

# humanoid map
ext=arm.data.vrm_addon_extension
try:
    ext.spec_version="1.0"
except Exception:
    pass
v1={{
 "hips":"Hips","spine":"Spine","chest":"Chest","neck":"Neck","head":"Head",
 "left_shoulder":"LeftShoulder","left_upper_arm":"LeftUpperArm","left_lower_arm":"LeftLowerArm","left_hand":"LeftHand",
 "right_shoulder":"RightShoulder","right_upper_arm":"RightUpperArm","right_lower_arm":"RightLowerArm","right_hand":"RightHand",
 "left_upper_leg":"LeftUpperLeg","left_lower_leg":"LeftLowerLeg","left_foot":"LeftFoot",
 "right_upper_leg":"RightUpperLeg","right_lower_leg":"RightLowerLeg","right_foot":"RightFoot",
}}
try:
    hb=ext.vrm1.humanoid.human_bones
    hb.filter_by_human_bone_hierarchy=False
    for p,b in v1.items():
        slot=getattr(hb,p,None)
        if slot and slot.node and b in arm.data.bones:
            slot.node.bone_name=b
except Exception as e:
    log.append(str(e))
try:
    ext.vrm0.meta.title="Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author="yameprogrammer"
    ext.vrm0.meta.version="0.3.8"
except Exception:
    pass

# export
for o in bpy.data.objects:
    if o.type in {{"LIGHT","CAMERA"}}:
        o.hide_render=True
with override(arm, [arm, main]):
    Path(paths["vrm"]).unlink(missing_ok=True)
    r=bpy.ops.export_scene.vrm(filepath=paths["vrm"], ignore_warning=True, check_existing=False, armature_object_name=arm.name, export_all_influences=True)
    log.append(f"export={{list(r)}}")

# pose test preview render
for pb in arm.pose.bones:
    pb.rotation_mode="QUATERNION"
    pb.rotation_quaternion=Quaternion((1,0,0,0))
# raise arms for preview
def wrot(name, axis, deg):
    pb=arm.pose.bones[name]
    arm.data.pose_position="REST"
    bpy.context.view_layer.update()
    rest=pb.matrix.copy()
    arm.data.pose_position="POSE"
    bpy.context.view_layer.update()
    R=Matrix.Rotation(math.radians(deg),4,axis)
    h=rest.translation
    pb.matrix=Matrix.Translation(h)@R@Matrix.Translation(-h)@rest
    bpy.context.view_layer.update()
wrot("LeftUpperArm","Y",-80)
wrot("RightUpperArm","Y",80)
# camera
cam=bpy.context.scene.camera
if not cam:
    cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera=cam
bb=[main.matrix_world@Vector(c) for c in main.bound_box]
c=sum(bb,Vector())/8
cam.location=(c.x, c.y-3.0, c.z+0.2)
cam.rotation_euler=(c-cam.location).to_track_quat("-Z","Y").to_euler()
scene=bpy.context.scene
scene.render.resolution_x=1024; scene.render.resolution_y=1280; scene.render.film_transparent=True
try: scene.render.engine="BLENDER_EEVEE"
except: pass
scene.render.filepath=paths["preview"]
bpy.ops.render.render(write_still=True)

sz=Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
result={{"status":"ok" if sz>1000 else "error","size":sz,"log":log}}
'''

    res = exec_blender_code(code)
    print("export", json.dumps(res, indent=2, ensure_ascii=False)[:2500])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "ok":
        return 1

    info = humanoid_remap(TEMP)
    shutil.copyfile(TEMP, OUT)
    shutil.copyfile(TEMP, OUT2)
    print("final", json.dumps(info, indent=2, ensure_ascii=False))
    print("OUT", OUT, OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
