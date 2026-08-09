#!/usr/bin/env python3
"""Full rebuild: Hunyuan3D (head+arm-clear ref) → Blender clean/rig → real VRM."""

from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

SERVER = "127.0.0.1:8188"
PACK = Path(r"D:\캐릭터\drafts\mecha_yame_v2")
EXPORTS = PACK / "exports"
IMG = PACK / "approved" / "single_front_4k.png"
if not IMG.is_file():
    IMG = PACK / "approved" / "single_front.png"
RAW_GLB = EXPORTS / "mecha_yame_v2_raw.glb"
BLEND = EXPORTS / "mecha_yame_v2.blend"
VRM_OUT = EXPORTS / "mecha_yame_v2.vrm"
VRM_COPY = EXPORTS / "mecha_yame_v2_warudo.vrm"
GLB_OUT = EXPORTS / "mecha_yame_v2_warudo.glb"
FBX_OUT = EXPORTS / "mecha_yame_v2.fbx"
RENDER = EXPORTS / "viewport_render.png"
OGL = EXPORTS / "viewport_opengl.png"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")
COMFY_3D = Path(r"F:\ComfyUI_data\output\3d")


def upload(path: Path) -> str:
    boundary = "----WebKitFormBoundaryRebuildV2"
    data = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"http://{SERVER}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["name"]


def queue_hunyuan(name: str, seed: int) -> str:
    prompt = {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": "hunyuan3d\\hunyuan_3d_v2.1.safetensors"},
        },
        "2": {"class_type": "LoadImage", "inputs": {"image": name}},
        "3": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 1.0},
        },
        "4": {
            "class_type": "EmptyLatentHunyuan3Dv2",
            "inputs": {"resolution": 4096, "batch_size": 1},
        },
        "13": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["1", 1],
                "image": ["2", 0],
                "crop": "center",
            },
        },
        "6": {
            "class_type": "Hunyuan3Dv2Conditioning",
            "inputs": {"clip_vision_output": ["13", 0]},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": 45,
                "cfg": 5.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecodeHunyuan3D",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["1", 2],
                "num_chunks": 10000,
                "octree_resolution": 320,
            },
        },
        "9": {
            "class_type": "VoxelToMesh",
            "inputs": {
                "voxel": ["8", 0],
                "algorithm": "surface net",
                "threshold": 0.55,
            },
        },
        "10": {
            "class_type": "SaveGLB",
            "inputs": {
                "mesh": ["9", 0],
                "filename_prefix": "3d/mecha_yame_v2_rebuild",
            },
        },
    }
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["prompt_id"]


def wait(pid: str, timeout: int = 900) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h:
            item = h[pid]
            st = item.get("status") or {}
            if st.get("completed") or item.get("outputs"):
                return item
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st))
        time.sleep(4)
    raise TimeoutError("hunyuan timeout")


def blender_build() -> dict:
    raw = str(RAW_GLB).replace("\\", "/")
    blend = str(BLEND).replace("\\", "/")
    temp = str(TEMP_GLB).replace("\\", "/")
    fbx = str(FBX_OUT).replace("\\", "/")
    render = str(RENDER).replace("\\", "/")
    ogl = str(OGL).replace("\\", "/")
    vrm = str(VRM_OUT).replace("\\", "/")

    code = f"""
import bpy
import bmesh
import addon_utils
from mathutils import Vector
from pathlib import Path

raw = r"{raw}"
blend = r"{blend}"
temp = r"{temp}"
fbx = r"{fbx}"
render = r"{render}"
ogl = r"{ogl}"
vrm = r"{vrm}"

# enable VRM
for name in ["bl_ext.user_default.vrm", "vrm"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

# clear
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights, bpy.data.images):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=raw)
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objs:
    result = {{"status": "error", "message": "no mesh"}}
else:
    for o in mesh_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    if len(mesh_objs) > 1:
        bpy.ops.object.join()
    main = bpy.context.view_layer.objects.active
    main.name = "MechaYame_V2"

    # normalize to 1.7m, feet on ground
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main.location = (0, 0, 0)
    dims = main.dimensions
    if dims.z > 1e-6:
        s = 1.70 / float(dims.z)
        main.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_z = min(v.z for v in bbox)
    main.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # cleanup: keep topology, fix normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00015)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    for p in main.data.polygons:
        p.use_smooth = True

    # optional light remesh only if very broken - skip, preserve detail

    # sleek multi-material by height/outer limbs
    def pbr(name, color, metallic, roughness, emit=None, emit_str=0.0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.use_backface_culling = False
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metallic
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = roughness
        if emit is not None:
            for k in ('Emission Color', 'Emission'):
                if k in bsdf.inputs:
                    bsdf.inputs[k].default_value = (*emit, 1.0)
                    break
            if 'Emission Strength' in bsdf.inputs:
                bsdf.inputs['Emission Strength'].default_value = emit_str
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        return mat

    mat_fabric = pbr('Fabric', (0.04, 0.042, 0.045), 0.05, 0.58)
    mat_head = pbr('Head', (0.012, 0.012, 0.014), 0.95, 0.12, emit=(0.1, 0.7, 0.85), emit_str=0.8)
    mat_hand = pbr('Hand', (0.02, 0.02, 0.022), 0.8, 0.25)
    mat_gold = pbr('Gold', (0.55, 0.45, 0.28), 0.95, 0.22)
    main.data.materials.clear()
    for m in (mat_fabric, mat_head, mat_hand, mat_gold):
        main.data.materials.append(m)

    bm = bmesh.new()
    bm.from_mesh(main.data)
    bm.faces.ensure_lookup_table()
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    h = max(max_v.z - min_v.z, 1e-6)
    max_x = max(abs(max_v.x), abs(min_v.x), 0.1)

    for f in bm.faces:
        cents = [main.matrix_world @ v.co for v in f.verts]
        cz = sum(v.z for v in cents) / len(cents)
        cx = abs(sum(v.x for v in cents) / len(cents))
        t = (cz - min_v.z) / h
        # head: top ~16% (clear exposed head in new ref)
        if t > 0.84:
            f.material_index = 1
        # hands/outer arms in A-pose: high lateral + mid height
        elif t > 0.35 and t < 0.75 and cx > max_x * 0.38:
            f.material_index = 2
        # gold ear band: near head sides
        elif t > 0.78 and t < 0.9 and cx > max_x * 0.12:
            f.material_index = 3
        else:
            f.material_index = 0
    bm.to_mesh(main.data)
    bm.free()
    main.data.update()

    # Humanoid armature sized for A-pose (arms out)
    mid_x = (min_v.x + max_v.x) * 0.5
    mid_y = (min_v.y + max_v.y) * 0.5
    width = max(max_v.x - min_v.x, 0.4)

    def z(t):
        return min_v.z + h * t

    # A-pose: arms extend more laterally than previous
    bones_def = [
        ("Hips", (mid_x, mid_y, z(0.52)), (mid_x, mid_y, z(0.58)), None),
        ("Spine", (mid_x, mid_y, z(0.58)), (mid_x, mid_y, z(0.66)), "Hips"),
        ("Chest", (mid_x, mid_y, z(0.66)), (mid_x, mid_y, z(0.78)), "Spine"),
        ("Neck", (mid_x, mid_y, z(0.78)), (mid_x, mid_y, z(0.85)), "Chest"),
        ("Head", (mid_x, mid_y, z(0.85)), (mid_x, mid_y, z(0.99)), "Neck"),
        ("LeftShoulder", (mid_x, mid_y, z(0.77)), (mid_x + width*0.14, mid_y, z(0.77)), "Chest"),
        ("LeftUpperArm", (mid_x + width*0.14, mid_y, z(0.77)), (mid_x + width*0.38, mid_y, z(0.68)), "LeftShoulder"),
        ("LeftLowerArm", (mid_x + width*0.38, mid_y, z(0.68)), (mid_x + width*0.48, mid_y, z(0.58)), "LeftUpperArm"),
        ("LeftHand", (mid_x + width*0.48, mid_y, z(0.58)), (mid_x + width*0.52, mid_y, z(0.55)), "LeftLowerArm"),
        ("RightShoulder", (mid_x, mid_y, z(0.77)), (mid_x - width*0.14, mid_y, z(0.77)), "Chest"),
        ("RightUpperArm", (mid_x - width*0.14, mid_y, z(0.77)), (mid_x - width*0.38, mid_y, z(0.68)), "RightShoulder"),
        ("RightLowerArm", (mid_x - width*0.38, mid_y, z(0.68)), (mid_x - width*0.48, mid_y, z(0.58)), "RightUpperArm"),
        ("RightHand", (mid_x - width*0.48, mid_y, z(0.58)), (mid_x - width*0.52, mid_y, z(0.55)), "RightLowerArm"),
        ("LeftUpperLeg", (mid_x + width*0.08, mid_y, z(0.52)), (mid_x + width*0.09, mid_y, z(0.30)), "Hips"),
        ("LeftLowerLeg", (mid_x + width*0.09, mid_y, z(0.30)), (mid_x + width*0.09, mid_y, z(0.08)), "LeftUpperLeg"),
        ("LeftFoot", (mid_x + width*0.09, mid_y, z(0.08)), (mid_x + width*0.09, mid_y + width*0.06, z(0.02)), "LeftLowerLeg"),
        ("RightUpperLeg", (mid_x - width*0.08, mid_y, z(0.52)), (mid_x - width*0.09, mid_y, z(0.30)), "Hips"),
        ("RightLowerLeg", (mid_x - width*0.09, mid_y, z(0.30)), (mid_x - width*0.09, mid_y, z(0.08)), "RightUpperLeg"),
        ("RightFoot", (mid_x - width*0.09, mid_y, z(0.08)), (mid_x - width*0.09, mid_y + width*0.06, z(0.02)), "RightLowerLeg"),
    ]

    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.view_layer.objects.active
    arm_obj.name = "Armature"
    arm = arm_obj.data
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)
    created = {{}}
    for name, head, tail, parent in bones_def:
        eb = arm.edit_bones.new(name)
        eb.head = head
        eb.tail = tail
        if parent and parent in created:
            eb.parent = created[parent]
            eb.use_connect = False
        created[name] = eb
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    weight_mode = "ARMATURE_AUTO"
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception as e:
        weight_mode = "FALLBACK:" + str(e)
        main.parent = arm_obj
        mod = main.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = arm_obj

    if main.data.shape_keys is None:
        main.shape_key_add(name="Basis", from_mix=False)
    for key in ["A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun",
                "EyeBlinkLeft", "EyeBlinkRight", "JawOpen", "MouthSmile"]:
        if key not in main.data.shape_keys.key_blocks:
            main.shape_key_add(name=key, from_mix=False)

    # VRM humanoid auto assign
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    auto_ok = None
    try:
        if hasattr(bpy.ops.vrm, "assign_vrm0_humanoid_human_bones_automatically"):
            bpy.ops.vrm.assign_vrm0_humanoid_human_bones_automatically()
            auto_ok = "vrm0_auto"
        elif hasattr(bpy.ops.vrm, "assign_vrm1_humanoid_human_bones_automatically"):
            bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically()
            auto_ok = "vrm1_auto"
    except Exception as e:
        auto_ok = str(e)

    # meta
    try:
        ext = getattr(arm_obj.data, "vrm_addon_extension", None)
        if ext and hasattr(ext, "vrm0") and hasattr(ext.vrm0, "meta"):
            ext.vrm0.meta.title = "Mecha Yameprogrammer v2"
            ext.vrm0.meta.author = "yameprogrammer"
            ext.vrm0.meta.version = "0.2.1"
    except Exception:
        pass

    # world + lights + camera
    for o in list(bpy.data.objects):
        if o.type in {{'LIGHT', 'CAMERA'}}:
            bpy.data.objects.remove(o, do_unlink=True)
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    wn = world.node_tree.nodes
    wl = world.node_tree.links
    wn.clear()
    bg = wn.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.82, 0.84, 0.87, 1.0)
    bg.inputs[1].default_value = 1.05
    wout = wn.new("ShaderNodeOutputWorld")
    wl.new(bg.outputs[0], wout.inputs[0])

    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bbox, Vector()) / 8.0
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    # pull back more for A-pose width
    cam.location = (center.x, center.y - max(height * 2.4, 3.8), center.z + 0.05)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    def add_light(name, loc, energy):
        ld = bpy.data.lights.new(name=name, type='AREA')
        ld.energy = energy
        ld.size = 1.8
        lo = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = loc
    add_light("Key", (center.x + 1.5, center.y - 2.2, center.z + 1.6), 520)
    add_light("Fill", (center.x - 1.8, center.y - 1.3, center.z + 0.9), 190)
    add_light("Rim", (center.x, center.y + 1.8, center.z + 1.3), 240)

    arm_obj.hide_render = True
    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except Exception:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 24
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1152
    scene.render.filepath = render
    bpy.ops.render.render(write_still=True)

    arm_obj.hide_set(True)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.region_3d.view_perspective = 'CAMERA'
                region = next(r for r in area.regions if r.type == 'WINDOW')
                with bpy.context.temp_override(window=window, area=area, region=region, scene=scene):
                    scene.render.filepath = ogl
                    bpy.ops.render.opengl(write_still=True)
                break
    arm_obj.hide_set(False)

    # export glb + fbx + vrm with context
    window = bpy.context.window_manager.windows[0]
    area = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), window.screen.areas[0])
    region = next((r for r in area.regions if r.type == 'WINDOW'), area.regions[0])
    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    export_notes = {{}}
    with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=arm_obj, selected_objects=[main, arm_obj]):
        bpy.ops.export_scene.gltf(
            filepath=temp,
            export_format='GLB',
            use_selection=True,
            export_skins=True,
            export_morph=True,
            export_materials='EXPORT',
            export_animations=False,
        )
        try:
            bpy.ops.export_scene.fbx(
                filepath=fbx,
                use_selection=True,
                add_leaf_bones=False,
                bake_anim=False,
                mesh_smooth_type='FACE',
                use_armature_deform_only=True,
                path_mode='COPY',
                embed_textures=True,
            )
            export_notes["fbx"] = True
        except Exception as e:
            export_notes["fbx"] = str(e)

        vrm_res = None
        if hasattr(bpy.ops.export_scene, "vrm"):
            try:
                vrm_res = bpy.ops.export_scene.vrm(
                    filepath=vrm,
                    export_invisibles=False,
                    export_only_selections=False,
                    armature_object_name=arm_obj.name,
                    ignore_warning=True,
                    check_existing=False,
                )
                export_notes["vrm"] = list(vrm_res) if vrm_res else True
            except Exception as e:
                export_notes["vrm"] = str(e)
        else:
            export_notes["vrm"] = "no_export_scene.vrm"

    bpy.ops.wm.save_as_mainfile(filepath=blend)

    # head volume check
    coords = [main.matrix_world @ v.co for v in main.data.vertices]
    zs = [c.z for c in coords]
    minz, maxz = min(zs), max(zs)
    hh = maxz - minz
    top = [c for c in coords if c.z > minz + hh * 0.84]
    mid_outer = [c for c in coords if (minz + hh*0.45 < c.z < minz + hh*0.7) and abs(c.x) > width*0.25]

    result = {{
        "status": "success",
        "poly": len(main.data.polygons),
        "verts": len(main.data.vertices),
        "height_m": float(main.dimensions.z),
        "width_m": float(main.dimensions.x),
        "weight_mode": weight_mode,
        "auto_ok": auto_ok,
        "export_notes": export_notes,
        "top_vert_count": len(top),
        "outer_arm_vert_count": len(mid_outer),
        "vrm_size": Path(vrm).stat().st_size if Path(vrm).is_file() else 0,
        "temp_glb_size": Path(temp).stat().st_size if Path(temp).is_file() else 0,
    }}
"""
    res = exec_blender_code(code)
    return res


def main() -> int:
    if not IMG.is_file():
        print(f"[ERROR] missing image {IMG}", file=sys.stderr)
        return 1
    EXPORTS.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Hunyuan3D from {IMG}")
    name = upload(IMG)
    seed = 99001122
    pid = queue_hunyuan(name, seed)
    print(f"queued {pid} seed={seed}")
    item = wait(pid)
    print("comfy status", (item.get("status") or {}).get("status_str"), item.get("outputs"))

    cands = sorted(COMFY_3D.glob("mecha_yame_v2_rebuild*.glb"), key=lambda p: p.stat().st_mtime)
    if not cands:
        cands = sorted(COMFY_3D.glob("*.glb"), key=lambda p: p.stat().st_mtime)
    src = cands[-1]
    shutil.copyfile(src, RAW_GLB)
    print(f"[raw] {src.name} -> {RAW_GLB} ({RAW_GLB.stat().st_size} bytes)")

    print("[2/3] Blender process + VRM export")
    res = blender_build()
    print(json.dumps(res, indent=2, ensure_ascii=False)[:5000])

    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
        print(f"[glb] {GLB_OUT.stat().st_size}")
    if VRM_OUT.is_file() and VRM_OUT.stat().st_size > 10000:
        shutil.copyfile(VRM_OUT, VRM_COPY)
        data = VRM_OUT.read_bytes()
        print(f"[vrm] {VRM_OUT.stat().st_size} has_VRM={b'VRM' in data}")
    else:
        print("[ERROR] VRM missing/small", file=sys.stderr)
        return 2

    payload = res.get("result") if isinstance(res, dict) else None
    if isinstance(payload, dict):
        top_n = payload.get("top_vert_count", 0)
        arm_n = payload.get("outer_arm_vert_count", 0)
        print(f"[qa] top_verts(head band)={top_n} outer_arm_verts={arm_n}")
        if top_n < 200:
            print("[WARN] head region still sparse — may need another ref seed")
        if arm_n < 200:
            print("[WARN] arm outer region sparse — arms may still merge")

    print("[3/3] done")
    print(f"LOAD THIS: {VRM_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
