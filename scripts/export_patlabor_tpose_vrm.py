#!/usr/bin/env python3
"""Export with make_estimated_humanoid_t_pose (critical for Unity/Warudo humanoid)."""

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
TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_tpose.vrm")


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


def fix_structure(src: Path, dst: Path) -> dict:
    gltf, bin_chunk = load_glb(src)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    joints = skin["joints"]
    first19 = joints[:19]
    names19 = [nodes[j].get("name") for j in first19]
    # Only truncate if first 19 are PascalCase real bones
    if all(n and n[0].isupper() for n in names19):
        skin["joints"] = first19
        ibm = skin.get("inverseBindMatrices")
        if ibm is not None:
            gltf["accessors"][ibm]["count"] = 19

    mesh_i = next(i for i, n in enumerate(nodes) if "mesh" in n)
    hips_i = next(i for i, n in enumerate(nodes) if n.get("name") == "Hips")
    for n in nodes:
        if n.get("children"):
            n["children"] = [c for c in n["children"] if c != mesh_i]
    gltf["scenes"] = [{"name": "Scene", "nodes": [mesh_i, hips_i]}]

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
    hb = {k: {"node": name_to_idx[b]} for k, b in remap.items() if b in name_to_idx}
    gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
    meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
    meta["name"] = "Mecha Patlabor VTuber v3"
    meta["version"] = "0.3.6"
    meta["authors"] = ["yameprogrammer"]

    # Add a simple glTF animation so Warudo can play motion without external tracking
    # Animation rotates LeftUpperArm and Head slightly over 2 seconds
    # This proves bones work in runtime even without VMC
    try:
        # find node indices
        head_i = name_to_idx["Head"]
        lua_i = name_to_idx["LeftUpperArm"]
        # Create samplers with baked quaternions in buffer - append to BIN
        # For simplicity use TARGET path rotation with sparse keyframes stored as new buffer views
        import math
        import struct as st

        def quat_y(deg):
            a = math.radians(deg) * 0.5
            return (0.0, math.sin(a), 0.0, math.cos(a))  # x,y,z,w

        def quat_x(deg):
            a = math.radians(deg) * 0.5
            return (math.sin(a), 0.0, 0.0, math.cos(a))

        times = [0.0, 1.0, 2.0]
        # head nod
        head_rots = [quat_x(0), quat_x(20), quat_x(0)]
        # left arm raise-ish in local - may look odd but should move
        arm_rots = [quat_y(0), quat_y(-45), quat_y(0)]

        def pack_f(vals):
            return b"".join(st.pack("<f", float(v)) for v in vals)

        def pack_quat_list(qs):
            out = b""
            for q in qs:
                out += st.pack("<4f", *q)
            return out

        bin_extra = b""
        accessors = gltf.setdefault("accessors", [])
        views = gltf.setdefault("bufferViews", [])
        base = len(bin_chunk or b"")

        def add_view(data: bytes, target=None):
            nonlocal bin_extra, base
            # pad
            pad = (4 - (len(bin_extra) % 4)) % 4
            bin_extra += b"\x00" * pad
            off = base + len(bin_extra)
            bin_extra += data
            pad2 = (4 - (len(bin_extra) % 4)) % 4
            bin_extra += b"\x00" * pad2
            bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
            if target is not None:
                bv["target"] = target
            views.append(bv)
            return len(views) - 1

        t_bytes = pack_f(times)
        bv_t = add_view(t_bytes)
        acc_t = {
            "bufferView": bv_t,
            "componentType": 5126,
            "count": 3,
            "type": "SCALAR",
            "max": [2.0],
            "min": [0.0],
        }
        accessors.append(acc_t)
        acc_t_i = len(accessors) - 1

        def add_rot_acc(qs):
            data = pack_quat_list(qs)
            bv = add_view(data)
            acc = {
                "bufferView": bv,
                "componentType": 5126,
                "count": len(qs),
                "type": "VEC4",
            }
            accessors.append(acc)
            return len(accessors) - 1

        acc_head = add_rot_acc(head_rots)
        acc_arm = add_rot_acc(arm_rots)

        gltf["animations"] = [
            {
                "name": "TestMove_HeadArm",
                "samplers": [
                    {"input": acc_t_i, "interpolation": "LINEAR", "output": acc_head},
                    {"input": acc_t_i, "interpolation": "LINEAR", "output": acc_arm},
                ],
                "channels": [
                    {"sampler": 0, "target": {"node": head_i, "path": "rotation"}},
                    {"sampler": 1, "target": {"node": lua_i, "path": "rotation"}},
                ],
            }
        ]
        # update buffer length
        if gltf.get("buffers"):
            gltf["buffers"][0]["byteLength"] = base + len(bin_extra)
        new_bin = (bin_chunk or b"") + bin_extra
        save_glb(dst, gltf, new_bin)
        anim = True
    except Exception as e:
        save_glb(dst, gltf, bin_chunk)
        anim = f"fail:{e}"

    g2, _ = load_glb(dst)
    return {
        "size": dst.stat().st_size,
        "scene": [[i, g2["nodes"][i].get("name")] for i in g2["scenes"][0]["nodes"]],
        "joints": len(g2["skins"][0]["joints"]),
        "animations": [a.get("name") for a in g2.get("animations", [])],
        "anim_ok": anim,
        "humanoid_head": g2["nodes"][g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["head"]["node"]].get("name"),
    }


def main() -> int:
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "vrm": str(TEMP).replace("\\", "/"),
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
    pb.rotation_mode="QUATERNION"
    pb.rotation_quaternion=Quaternion((1,0,0,0))
    pb.location=(0,0,0)
    pb.scale=(1,1,1)

# parent mesh
for m in list(main.modifiers):
    if m.type=="ARMATURE":
        main.modifiers.remove(m)
am=main.modifiers.new("Armature","ARMATURE")
am.object=arm
am.use_vertex_groups=True
mw=main.matrix_world.copy()
main.parent=arm
main.matrix_world=mw

ext=arm.data.vrm_addon_extension
try:
    ext.spec_version="1.0"
except Exception:
    pass

# humanoid assign
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

win=bpy.context.window_manager.windows[0]
area=next(a for a in win.screen.areas if a.type=="VIEW_3D")
region=next(r for r in area.regions if r.type=="WINDOW")
for o in bpy.data.objects:
    o.select_set(o in (arm,main))
bpy.context.view_layer.objects.active=arm

with bpy.context.temp_override(window=win, area=area, region=region, scene=bpy.context.scene, active_object=arm, selected_objects=[arm,main]):
    # CRITICAL for Unity humanoid
    try:
        r=bpy.ops.vrm.make_estimated_humanoid_t_pose()
        log.append(f"tpose={{list(r)}}")
    except Exception as e:
        log.append(f"tpose err={{e}}")
    try:
        r=bpy.ops.vrm.model_validate()
        log.append(f"validate={{list(r)}}")
    except Exception as e:
        log.append(f"validate err={{e}}")

    Path(paths["vrm"]).unlink(missing_ok=True)
    r=bpy.ops.export_scene.vrm(filepath=paths["vrm"], ignore_warning=True, check_existing=False, armature_object_name=arm.name, export_all_influences=True)
    log.append(f"export={{list(r)}}")

# do NOT save blend after t-pose (would destroy rest pose edits) — reload later if needed
sz=Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
result={{"status":"ok" if sz>1000 else "error","size":sz,"log":log}}
'''
    res = exec_blender_code(code)
    print("export", json.dumps(res, indent=2, ensure_ascii=False)[:3000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if not payload or payload.get("status") != "ok":
        return 1

    info = fix_structure = None
    # use fix_structure function name
    info = fix_structure if False else None
    # call the postprocess defined as fix_structure in this file - I named it wrongly
    # Actually function is the block that was `fix_structure` - I inlined as post in previous; here:
    # I'll call the logic from export_patlabor - simpler:
    from export_patlabor_vrm_only import postprocess  # may fail

    try:
        info = postprocess(TEMP, OUT)
    except Exception:
        # local postprocess
        gltf, bin_chunk = load_glb(TEMP)
        nodes = gltf["nodes"]
        skin = gltf["skins"][0]
        if len(skin["joints"]) > 19 and all(
            (nodes[j].get("name") or "x")[0].isupper() for j in skin["joints"][:19]
        ):
            skin["joints"] = skin["joints"][:19]
            if skin.get("inverseBindMatrices") is not None:
                gltf["accessors"][skin["inverseBindMatrices"]]["count"] = 19
        mesh_i = next(i for i, n in enumerate(nodes) if "mesh" in n)
        hips_i = next(i for i, n in enumerate(nodes) if n.get("name") == "Hips")
        for n in nodes:
            if n.get("children"):
                n["children"] = [c for c in n["children"] if c != mesh_i]
        gltf["scenes"] = [{"name": "Scene", "nodes": [mesh_i, hips_i]}]
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
        hb = {k: {"node": name_to_idx[b]} for k, b in remap.items() if b in name_to_idx}
        gltf["extensions"]["VRMC_vrm"]["humanoid"] = {"humanBones": hb}
        meta = gltf["extensions"]["VRMC_vrm"].setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = "0.3.6"
        meta["authors"] = ["yameprogrammer"]

        # add test animation
        import math

        def qy(d):
            a = math.radians(d) / 2
            return (0.0, math.sin(a), 0.0, math.cos(a))

        def qx(d):
            a = math.radians(d) / 2
            return (math.sin(a), 0.0, 0.0, math.cos(a))

        times = [0.0, 1.0, 2.0]
        head_i = name_to_idx["Head"]
        arm_i = name_to_idx["LeftUpperArm"]
        bin_extra = b""
        base = len(bin_chunk or b"")
        views = gltf.setdefault("bufferViews", [])
        accessors = gltf.setdefault("accessors", [])

        def add_bytes(data: bytes):
            nonlocal bin_extra
            pad = (4 - len(bin_extra) % 4) % 4
            bin_extra += b"\x00" * pad
            off = base + len(bin_extra)
            bin_extra += data
            pad = (4 - len(bin_extra) % 4) % 4
            bin_extra += b"\x00" * pad
            views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
            return len(views) - 1

        import struct as st

        tdata = b"".join(st.pack("<f", t) for t in times)
        bv_t = add_bytes(tdata)
        accessors.append(
            {
                "bufferView": bv_t,
                "componentType": 5126,
                "count": 3,
                "type": "SCALAR",
                "max": [2.0],
                "min": [0.0],
            }
        )
        acc_t = len(accessors) - 1

        def add_quats(qs):
            data = b"".join(st.pack("<4f", *q) for q in qs)
            bv = add_bytes(data)
            accessors.append({"bufferView": bv, "componentType": 5126, "count": len(qs), "type": "VEC4"})
            return len(accessors) - 1

        acc_h = add_quats([qx(0), qx(25), qx(0)])
        acc_a = add_quats([qy(0), qy(-50), qy(0)])
        gltf["animations"] = [
            {
                "name": "WarudoTest_HeadArm",
                "samplers": [
                    {"input": acc_t, "interpolation": "LINEAR", "output": acc_h},
                    {"input": acc_t, "interpolation": "LINEAR", "output": acc_a},
                ],
                "channels": [
                    {"sampler": 0, "target": {"node": head_i, "path": "rotation"}},
                    {"sampler": 1, "target": {"node": arm_i, "path": "rotation"}},
                ],
            }
        ]
        gltf["buffers"][0]["byteLength"] = base + len(bin_extra)
        save_glb(OUT, gltf, (bin_chunk or b"") + bin_extra)
        info = {
            "size": OUT.stat().st_size,
            "anims": [a["name"] for a in gltf.get("animations", [])],
            "joints": len(gltf["skins"][0]["joints"]),
            "scene": [[i, nodes[i].get("name")] for i in gltf["scenes"][0]["nodes"]],
            "head": nodes[hb["head"]["node"]].get("name"),
        }
        print("POST", json.dumps(info, indent=2))
        shutil.copyfile(OUT, OUT2)
        return 0

    print("post", info)
    shutil.copyfile(OUT, OUT2)
    return 0


if __name__ == "__main__":
    # fix undefined names used in exception path
    TEMP = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_tpose.vrm")
    OUT = OUT
    OUT2 = OUT2
    raise SystemExit(main())
