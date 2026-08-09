#!/usr/bin/env python3
"""
Rebuild mecha_patlabor_v3 VRM for Warudo using official/community requirements:

Official docs (docs.warudo.app):
- Place .vrm in Warudo data/Characters
- Humanoid required for body tracking
- Bone normalization: T-pose with (0,0,0) rotation preferred for mods;
  VRM path is the "tried-and-tested" way to guarantee normalized bones
- Setup via Onboarding / Character → Setup Motion Capture

Community (Kana Fuyuko, OrendCross):
- Model must be true T-pose before humanoid setup
- A-pose causes locked/twisted arms
- VRM 0 Freeze T-Pose helps normalization when going through Unity SDK

This script:
1. Loads current blend (keeps joint positions as much as possible)
2. Straightens arm chains to true T-pose (horizontal world X)
3. Aligns spine/neck/head up (+Z Blender)
4. Aligns legs down
5. Applies as rest (pose clear + armature modifier keep)
6. Exports VRM 1.0 like working mecha_yame_v2
7. Post-processes humanoid to match yame structure (no upperChest dup)
8. Writes to exports + Warudo Characters folder
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
EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
TEMP_VRM = Path(r"C:\Users\parkp\AppData\Local\Temp\patlabor_warudo_rebuild.vrm")
OUT_READY = EXPORTS / "mecha_patlabor_v3_WARUDO_READY.vrm"
OUT_STD = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
OUT_ALT = EXPORTS / "mecha_patlabor_v3.vrm"
WARUDO_CHARS = Path(
    r"G:\SteamLibrary\steamapps\common\Warudo\Warudo_Data\StreamingAssets\Characters"
)
VERSION = "0.4.0"


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


def postprocess_vrm(path: Path) -> dict:
    """Match working yame humanoid: PascalCase skinned joints only, no upperChest."""
    gltf, bin_chunk = load_glb(path)
    nodes = gltf["nodes"]
    name_to_idx = {}
    for i, n in enumerate(nodes):
        nm = n.get("name")
        if nm and nm not in name_to_idx:
            name_to_idx[nm] = i

    remap = {
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
    }

    changes = []
    if "VRMC_vrm" in gltf.get("extensions", {}):
        vrm = gltf["extensions"]["VRMC_vrm"]
        hb = vrm.setdefault("humanoid", {}).setdefault("humanBones", {})
        # drop upperChest / eyes / fingers if present
        for drop in list(hb.keys()):
            if drop not in remap:
                del hb[drop]
                changes.append(f"drop {drop}")
        for k, bone in remap.items():
            if bone not in name_to_idx:
                continue
            new_i = name_to_idx[bone]
            old = hb.get(k, {}).get("node")
            old_n = nodes[old].get("name") if old is not None else None
            hb[k] = {"node": new_i}
            if old != new_i:
                changes.append(f"{k}: {old_n}->{bone}")
        meta = vrm.setdefault("meta", {})
        meta["name"] = "Mecha Patlabor VTuber v3"
        meta["version"] = VERSION
        meta["authors"] = ["yameprogrammer"]
        if gltf.get("skins"):
            gltf["skins"][0].pop("skeleton", None)
        gltf.pop("animations", None)

    save_glb(path, gltf, bin_chunk)
    g2, _ = load_glb(path)
    skin = g2["skins"][0]
    nodes2 = g2["nodes"]
    hb2 = g2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    return {
        "changes": changes,
        "joints": [nodes2[j].get("name") for j in skin["joints"]],
        "joint_count": len(skin["joints"]),
        "scene": [nodes2[i].get("name") for i in g2["scenes"][0]["nodes"]],
        "humanoid": {k: nodes2[v["node"]].get("name") for k, v in sorted(hb2.items())},
        "humanoid_count": len(hb2),
        "size": path.stat().st_size,
    }


def main() -> int:
    blend = str(BLEND).replace("\\", "/")
    vrm_out = str(TEMP_VRM).replace("\\", "/")
    TEMP_VRM.parent.mkdir(parents=True, exist_ok=True)

    code = f'''
import bpy
import addon_utils
from mathutils import Vector, Quaternion, Matrix
from pathlib import Path

blend_path = r"{blend}"
vrm_out = r"{vrm_out}"
log = []

for name in ["bl_ext.user_default.vrm", "vrm", "bl_ext.blender_org.vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
        log.append(f"enable {{name}} ok")
    except Exception as e:
        log.append(f"enable {{name}} {{e}}")

if not hasattr(bpy.ops.export_scene, "vrm"):
    result = {{"status": "error", "message": "no export_scene.vrm", "log": log}}
else:
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    # ensure valid context after file load
    window = bpy.context.window_manager.windows[0]
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
    region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    mesh = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if arm is None or mesh is None:
        result = {{"status": "error", "message": "missing arm/mesh", "log": log}}
    else:
        def set_mode(mode):
            bpy.context.view_layer.objects.active = arm
            arm.select_set(True)
            with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
                bpy.ops.object.mode_set(mode=mode)

        # --- clear pose ---
        set_mode("POSE")
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        set_mode("OBJECT")

        def set_bone_world(name, head_w, tail_w, roll=0.0):
            b = arm.data.edit_bones[name]
            mw = arm.matrix_world
            imw = mw.inverted()
            b.use_connect = False
            b.head = imw @ Vector(head_w)
            b.tail = imw @ Vector(tail_w)
            b.roll = roll

        # Capture current joint positions in world space (keep landmarks)
        set_mode("EDIT")
        eb = arm.data.edit_bones
        world = {{}}
        for b in eb:
            world[b.name] = {{
                "head": (arm.matrix_world @ b.head).copy(),
                "tail": (arm.matrix_world @ b.tail).copy(),
                "len": b.length,
            }}

        # Height / center from mesh
        bb = [arm.matrix_world @ Vector(c) for c in mesh.bound_box] if False else None
        # mesh world bbox
        mat = mesh.matrix_world
        corners = [mat @ Vector(c) for c in mesh.bound_box]
        min_z = min(c.z for c in corners)
        max_z = max(c.z for c in corners)
        mid_x = (min(c.x for c in corners) + max(c.x for c in corners)) * 0.5
        mid_y = (min(c.y for c in corners) + max(c.y for c in corners)) * 0.5
        height = max_z - min_z
        log.append(f"mesh z={{min_z:.3f}}..{{max_z:.3f}} h={{height:.3f}}")

        # Use existing heads for joint placement; straighten directions for T-pose
        # Spine chain: vertical +Z
        hips_h = world["Hips"]["head"]
        spine_h = world["Spine"]["head"]
        chest_h = world["Chest"]["head"]
        neck_h = world["Neck"]["head"]
        head_h = world["Head"]["head"]

        # keep X=mid, Y=mid for spine
        def v(x, y, z):
            return Vector((x, y, z))

        cx, cy = mid_x, mid_y
        # Hips slightly above min leg roots
        hips_z = hips_h.z
        spine_z = spine_h.z
        chest_z = chest_h.z
        neck_z = neck_h.z
        head_z = head_h.z
        head_top = max(head_z + 0.18, max_z - 0.02)

        set_bone_world("Hips", v(cx, cy, hips_z), v(cx, cy, spine_z))
        set_bone_world("Spine", v(cx, cy, spine_z), v(cx, cy, chest_z))
        set_bone_world("Chest", v(cx, cy, chest_z), v(cx, cy, neck_z))
        set_bone_world("Neck", v(cx, cy, neck_z), v(cx, cy, head_z))
        set_bone_world("Head", v(cx, cy, head_z), v(cx, cy, head_top))

        # Arms: TRUE T-pose horizontal along +X / -X (critical for Unity/Warudo)
        # keep shoulder height from chest, use existing lateral positions for lengths
        sh_l = world["LeftShoulder"]["head"]
        ua_l = world["LeftUpperArm"]["head"]
        la_l = world["LeftLowerArm"]["head"]
        hd_l = world["LeftHand"]["head"]
        sh_r = world["RightShoulder"]["head"]
        ua_r = world["RightUpperArm"]["head"]
        la_r = world["RightLowerArm"]["head"]
        hd_r = world["RightHand"]["head"]

        arm_z = (sh_l.z + sh_r.z) * 0.5
        # shoulder from chest side
        chest_side = 0.12
        l_sh_x = max(abs(sh_l.x), chest_side)
        r_sh_x = -max(abs(sh_r.x), chest_side)

        # segment lengths from original
        len_sh_l = max(0.08, (ua_l - sh_l).length)
        len_ua_l = max(0.12, (la_l - ua_l).length)
        len_la_l = max(0.12, (hd_l - la_l).length)
        len_hd_l = max(0.04, world["LeftHand"]["len"])
        len_sh_r = max(0.08, (ua_r - sh_r).length)
        len_ua_r = max(0.12, (la_r - ua_r).length)
        len_la_r = max(0.12, (hd_r - la_r).length)
        len_hd_r = max(0.04, world["RightHand"]["len"])

        # Left arm straight +X at arm_z
        l0 = v(l_sh_x, cy, arm_z)
        l1 = l0 + Vector((len_sh_l, 0, 0))
        l2 = l1 + Vector((len_ua_l, 0, 0))
        l3 = l2 + Vector((len_la_l, 0, 0))
        l4 = l3 + Vector((len_hd_l, 0, 0))
        set_bone_world("LeftShoulder", l0, l1)
        set_bone_world("LeftUpperArm", l1, l2)
        set_bone_world("LeftLowerArm", l2, l3)
        set_bone_world("LeftHand", l3, l4)

        r0 = v(r_sh_x, cy, arm_z)
        r1 = r0 + Vector((-len_sh_r, 0, 0))
        r2 = r1 + Vector((-len_ua_r, 0, 0))
        r3 = r2 + Vector((-len_la_r, 0, 0))
        r4 = r3 + Vector((-len_hd_r, 0, 0))
        set_bone_world("RightShoulder", r0, r1)
        set_bone_world("RightUpperArm", r1, r2)
        set_bone_world("RightLowerArm", r2, r3)
        set_bone_world("RightHand", r3, r4)

        # Legs: down -Z, slight outward X
        for side, sign in (("Left", 1.0), ("Right", -1.0)):
            ul = world[f"{{side}}UpperLeg"]["head"]
            ll = world[f"{{side}}LowerLeg"]["head"]
            ft = world[f"{{side}}Foot"]["head"]
            ft_t = world[f"{{side}}Foot"]["tail"]
            len_ul = max(0.2, (ll - ul).length)
            len_ll = max(0.2, (ft - ll).length)
            len_ft = max(0.08, world[f"{{side}}Foot"]["len"])
            hx = sign * abs(ul.x)
            # upper leg head
            u0 = v(hx, cy, hips_z - 0.02)
            u1 = u0 + Vector((0, 0, -len_ul))
            u2 = u1 + Vector((0, 0, -len_ll))
            # foot pointing +Y forward (Blender)
            u3 = u2 + Vector((0, -len_ft * 0.7, -len_ft * 0.3))
            set_bone_world(f"{{side}}UpperLeg", u0, u1)
            set_bone_world(f"{{side}}LowerLeg", u1, u2)
            set_bone_world(f"{{side}}Foot", u2, u3)

        set_mode("OBJECT")

        # ensure armature modifier
        for m in list(mesh.modifiers):
            if m.type == "ARMATURE":
                mesh.modifiers.remove(m)
        am = mesh.modifiers.new("Armature", "ARMATURE")
        am.object = arm
        am.use_vertex_groups = True
        mw = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_world = mw

        # delete lights/cameras
        for o in list(bpy.data.objects):
            if o.type in {{"LIGHT", "CAMERA"}}:
                bpy.data.objects.remove(o, do_unlink=True)

        # VRM humanoid assignment
        with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
            bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = arm

        ext = arm.data.vrm_addon_extension
        try:
            ext.spec_version = "1.0"
            log.append("spec 1.0")
        except Exception as e:
            log.append(f"spec {{e}}")

        try:
            hb = ext.vrm1.humanoid.human_bones
            hb.filter_by_human_bone_hierarchy = False
            mapping = {{
                "hips": "Hips", "spine": "Spine", "chest": "Chest",
                "neck": "Neck", "head": "Head",
                "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm",
                "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
                "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm",
                "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
                "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg",
                "left_foot": "LeftFoot",
                "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg",
                "right_foot": "RightFoot",
            }}
            for k, v in mapping.items():
                slot = getattr(hb, k, None)
                if slot and slot.node and v in arm.data.bones:
                    slot.node.bone_name = v
            # clear upper_chest if present
            try:
                if getattr(hb, "upper_chest", None) and hb.upper_chest.node:
                    hb.upper_chest.node.bone_name = ""
            except Exception:
                pass
            log.append("vrm1 humanoid assigned")
        except Exception as e:
            log.append(f"vrm1 assign {{e}}")

        for op_name in [
            "assign_vrm1_humanoid_human_bones_automatically",
            "assign_vrm0_humanoid_human_bones_automatically",
        ]:
            try:
                op = getattr(bpy.ops.vrm, op_name, None)
                if op:
                    op()
                    log.append(f"auto {{op_name}}")
                    break
            except Exception as e:
                log.append(f"auto {{op_name}} {{e}}")

        try:
            ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
            ext.vrm0.meta.author = "yameprogrammer"
            ext.vrm0.meta.version = "{VERSION}"
        except Exception:
            pass
        try:
            ext.vrm1.meta.vrm_name = "Mecha Patlabor VTuber v3"
            ext.vrm1.meta.version = "{VERSION}"
        except Exception:
            pass

        # optional estimated T-pose (may CANCEL — ignore)
        try:
            with bpy.context.temp_override(window=window, area=area, region=region, active_object=arm, object=arm):
                r = bpy.ops.vrm.make_estimated_humanoid_t_pose()
            log.append(f"est_tpose {{list(r)}}")
        except Exception as e:
            log.append(f"est_tpose {{e}}")

        # re-clear pose after est
        set_mode("POSE")
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        set_mode("OBJECT")

        Path(vrm_out).unlink(missing_ok=True)
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
                try:
                    export_result = bpy.ops.export_scene.vrm(filepath=vrm_out, ignore_warning=True)
                except Exception as e2:
                    export_err = f"{{export_err}} | {{e2}}"

        size = Path(vrm_out).stat().st_size if Path(vrm_out).is_file() else 0
        head = open(vrm_out, "rb").read(4) if size else b""

        # save blend copy for warudo rebuild (do NOT overwrite user's main blend carelessly —
        # write a dedicated rebuild blend)
        rebuild_blend = r"D:/캐릭터/drafts/mecha_patlabor_v3/exports/mecha_patlabor_v3_warudo_rebuild.blend"
        try:
            bpy.ops.wm.save_as_mainfile(filepath=rebuild_blend, copy=True)
            log.append(f"saved {{rebuild_blend}}")
        except Exception as e:
            log.append(f"save blend {{e}}")

        # bone dirs after edit
        arm_dirs = {{}}
        for nm in ["LeftUpperArm", "LeftLowerArm", "Head", "Hips"]:
            b = arm.data.bones[nm]
            h = arm.matrix_world @ b.head_local
            t = arm.matrix_world @ b.tail_local
            d = (t - h)
            arm_dirs[nm] = {{
                "head": [round(x, 4) for x in h],
                "tail": [round(x, 4) for x in t],
                "dir": [round(x, 4) for x in d.normalized()] if d.length > 1e-8 else [0,0,0],
            }}

        result = {{
            "status": "success" if size > 1000 and head == b"glTF" else "error",
            "log": log,
            "export_result": list(export_result) if export_result else None,
            "export_err": export_err,
            "size": size,
            "arm_dirs": arm_dirs,
            "bones": [b.name for b in arm.data.bones],
            "vgroups": [vg.name for vg in mesh.vertex_groups],
        }}
'''

    print("=== Blender rebuild + export ===")
    res = exec_blender_code(code)
    # result may be nested
    payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:6000])
    if not isinstance(payload, dict) or payload.get("status") != "success":
        print("EXPORT FAILED")
        return 1

    print("=== Postprocess humanoid ===")
    info = postprocess_vrm(TEMP_VRM)
    print(json.dumps(info, indent=2, ensure_ascii=False))

    for dest in [OUT_READY, OUT_STD, OUT_ALT]:
        shutil.copyfile(TEMP_VRM, dest)
        print("wrote", dest, dest.stat().st_size)

    if WARUDO_CHARS.is_dir():
        for name in [
            "mecha_patlabor_v3_WARUDO_READY.vrm",
            "mecha_patlabor_v3_warudo.vrm",
        ]:
            dest = WARUDO_CHARS / name
            shutil.copyfile(TEMP_VRM, dest)
            print("Warudo Characters <-", dest, dest.stat().st_size)
    else:
        print("WARN: Warudo Characters folder not found:", WARUDO_CHARS)

    # write load instructions
    readme = EXPORTS / "WARUDO_LOAD.md"
    readme.write_text(
        f"""# Warudo 로드 가이드 — mecha_patlabor_v3

버전: {VERSION}

## 이 파일이 Warudo용인 이유

공식 문서 (docs.warudo.app):

1. Warudo는 **`.vrm`** 과 **`.warudo`** 캐릭터 포맷을 지원
2. VRM은 **data 폴더 → Characters** 에 넣음
3. 바디 트래킹은 **Humanoid 스켈레톤** 필요
4. Character Mod 경로에서는 **본 정규화(T-pose에서 rotation 0)** 가 핵심  
   → “가장 검증된 방법 = VRM으로 만든 뒤 로드” (VRM은 정규화된 본을 보장)

커뮤니티 (Kana Fuyuko / OrendCross):

- T-pose가 아니면 팔이 뒤로 고정되거나 트위스트됨
- 로드 후 **Setup Motion Capture** 다시 할 것
- (선택) Unity SDK → Setup Character → `.warudo` 는 커스텀 셰이더/다이나믹본용

## 이 빌드에서 한 일

- 팔 체인을 **완전 수평 T-pose** 로 재정렬 (A-pose 잔여 제거)
- 척추/목/머리 수직 정렬
- VRM 1.0 humanoid 19본 (yame_v2와 동일 구조)
- upperChest 중복 매핑 제거
- Warudo Characters 폴더에 복사

## 로드 절차 (중요)

1. Warudo **완전 종료** 후 재실행 (파일 캐시 갱신)
2. Menu → **Open Data Folder** → `Characters` 확인  
   경로: `G:\\SteamLibrary\\steamapps\\common\\Warudo\\Warudo_Data\\StreamingAssets\\Characters`
3. 파일: **`mecha_patlabor_v3_WARUDO_READY.vrm`**
4. **Onboarding Assistant → Basic Setup → Get Started**  
   또는 Character 에셋 Source 선택 후:
   - **Setup Motion Capture** (캐릭터 바꿀 때마다 다시)
   - (표정 있으면) Import VRM Expressions
5. 움직임 확인 순서:
   - Idle Animation 을 앉기/호흡 등으로 바꿔 **애니메이션이 붙는지** 먼저 확인
   - 그다음 MediaPipe/페이스 트래킹 캘리브레이션

## 안 움직일 때 체크

- Source 가 새 파일명(`WARUDO_READY`)인지 (옛 캐시 파일 아님)
- Setup Motion Capture 를 **이 캐릭터로 다시** 돌렸는지
- Idle Animation 이 None 이 아닌지
- 로그에 `All humanoid bones are normalized` 가 뜨는지  
  (`LocalLow/HakuyaLabs/Warudo/Logs`)
- VRIK finger 경고는 손가락 없는 메카에서 정상 (yame도 동일)

## 로컬 복사본

- `{OUT_READY}`
- `{OUT_STD}`
""",
        encoding="utf-8",
    )
    print("README", readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
