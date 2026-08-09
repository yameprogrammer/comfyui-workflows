#!/usr/bin/env python3
"""
Import hy3d_example_01 textured GLB → light clean → humanoid rig → VRM/GLB/blend.

Keeps baked texture (no frankenstein sphere head, no front-project override).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

PACK = Path(r"D:\캐릭터\drafts\mecha_yame_v2")
EXPORTS = PACK / "exports"

BLEND_OUT = EXPORTS / "mecha_yame_v2.blend"
GLB_OUT = EXPORTS / "mecha_yame_v2_warudo.glb"
VRM_OUT = EXPORTS / "mecha_yame_v2.vrm"
VRM_WARUDO = EXPORTS / "mecha_yame_v2_warudo.vrm"
FBX_OUT = EXPORTS / "mecha_yame_v2.fbx"
RENDER_OUT = EXPORTS / "viewport_render.png"
OGL_OUT = EXPORTS / "viewport_opengl.png"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_example01_export.glb")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--glb",
        default="",
        help="Input textured GLB (default: simple_mv_tex then example01_tex)",
    )
    args = ap.parse_args()
    if args.glb:
        raw_glb_path = Path(args.glb)
    else:
        candidates = [
            EXPORTS / "mecha_yame_v2_simple_mv_tex.glb",
            EXPORTS / "mecha_yame_v2_example01_tex.glb",
            EXPORTS / "mecha_yame_v2_example01_geo.glb",
        ]
        raw_glb_path = next((p for p in candidates if p.is_file()), candidates[0])
    if not raw_glb_path.is_file():
        print("[ERROR] missing glb", raw_glb_path, file=sys.stderr)
        return 1
    print("[input]", raw_glb_path)

    raw_glb = str(raw_glb_path).replace("\\", "/")
    temp_glb = str(TEMP_GLB).replace("\\", "/")
    blend_path = str(BLEND_OUT).replace("\\", "/")
    fbx_path = str(FBX_OUT).replace("\\", "/")
    render_path = str(RENDER_OUT).replace("\\", "/")
    ogl_path = str(OGL_OUT).replace("\\", "/")
    vrm_out = str(VRM_OUT).replace("\\", "/")
    vrm_warudo = str(VRM_WARUDO).replace("\\", "/")

    code = f"""
import bpy
import addon_utils
from mathutils import Vector

raw_glb = r"{raw_glb}"
temp_glb = r"{temp_glb}"
blend_path = r"{blend_path}"
fbx_path = r"{fbx_path}"
render_path = r"{render_path}"
ogl_path = r"{ogl_path}"
vrm_out = r"{vrm_out}"
vrm_warudo = r"{vrm_warudo}"

# clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
    for b in list(coll):
        try:
            coll.remove(b)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=raw_glb)
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

    # normalize height ~1.70m, feet on ground
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main.location = (0, 0, 0)
    main.rotation_euler = (0, 0, 0)
    dims = main.dimensions.copy()
    if dims.z > 1e-6:
        s = 1.70 / float(dims.z)
        main.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_z = min(v.z for v in bbox)
    main.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # light clean only — keep topology + baked UVs/textures
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00015)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.reveal()
    bpy.ops.object.mode_set(mode='OBJECT')
    for p in main.data.polygons:
        p.use_smooth = True

    # ensure materials not backface culled
    for mat in main.data.materials:
        if mat:
            mat.use_backface_culling = False

    n_verts = len(main.data.vertices)
    n_faces = len(main.data.polygons)
    n_mats = len(main.data.materials)
    has_uv = len(main.data.uv_layers) > 0
    has_img = any(
        (mat and mat.use_nodes and any(n.type == 'TEX_IMAGE' and n.image for n in mat.node_tree.nodes))
        for mat in main.data.materials if mat
    )

    # humanoid armature from bbox proportions
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    height = max_v.z - min_v.z
    mid_x = (min_v.x + max_v.x) * 0.5
    mid_y = (min_v.y + max_v.y) * 0.5
    width = max(max_v.x - min_v.x, 0.3)

    def z(t):
        return min_v.z + height * t

    # slightly wider arms for chubby toy proportions
    bones_def = [
        ("Hips", (mid_x, mid_y, z(0.50)), (mid_x, mid_y, z(0.56)), None),
        ("Spine", (mid_x, mid_y, z(0.56)), (mid_x, mid_y, z(0.64)), "Hips"),
        ("Chest", (mid_x, mid_y, z(0.64)), (mid_x, mid_y, z(0.76)), "Spine"),
        ("Neck", (mid_x, mid_y, z(0.76)), (mid_x, mid_y, z(0.82)), "Chest"),
        ("Head", (mid_x, mid_y, z(0.82)), (mid_x, mid_y, z(0.98)), "Neck"),
        ("LeftShoulder", (mid_x, mid_y, z(0.75)), (mid_x + width*0.14, mid_y, z(0.74)), "Chest"),
        ("LeftUpperArm", (mid_x + width*0.14, mid_y, z(0.74)), (mid_x + width*0.30, mid_y, z(0.58)), "LeftShoulder"),
        ("LeftLowerArm", (mid_x + width*0.30, mid_y, z(0.58)), (mid_x + width*0.38, mid_y, z(0.44)), "LeftUpperArm"),
        ("LeftHand", (mid_x + width*0.38, mid_y, z(0.44)), (mid_x + width*0.42, mid_y, z(0.40)), "LeftLowerArm"),
        ("RightShoulder", (mid_x, mid_y, z(0.75)), (mid_x - width*0.14, mid_y, z(0.74)), "Chest"),
        ("RightUpperArm", (mid_x - width*0.14, mid_y, z(0.74)), (mid_x - width*0.30, mid_y, z(0.58)), "RightShoulder"),
        ("RightLowerArm", (mid_x - width*0.30, mid_y, z(0.58)), (mid_x - width*0.38, mid_y, z(0.44)), "RightUpperArm"),
        ("RightHand", (mid_x - width*0.38, mid_y, z(0.44)), (mid_x - width*0.42, mid_y, z(0.40)), "RightLowerArm"),
        ("LeftUpperLeg", (mid_x + width*0.10, mid_y, z(0.50)), (mid_x + width*0.11, mid_y, z(0.28)), "Hips"),
        ("LeftLowerLeg", (mid_x + width*0.11, mid_y, z(0.28)), (mid_x + width*0.11, mid_y, z(0.08)), "LeftUpperLeg"),
        ("LeftFoot", (mid_x + width*0.11, mid_y, z(0.08)), (mid_x + width*0.11, mid_y + width*0.06, z(0.02)), "LeftLowerLeg"),
        ("RightUpperLeg", (mid_x - width*0.10, mid_y, z(0.50)), (mid_x - width*0.11, mid_y, z(0.28)), "Hips"),
        ("RightLowerLeg", (mid_x - width*0.11, mid_y, z(0.28)), (mid_x - width*0.11, mid_y, z(0.08)), "RightUpperLeg"),
        ("RightFoot", (mid_x - width*0.11, mid_y, z(0.08)), (mid_x - width*0.11, mid_y + width*0.06, z(0.02)), "RightLowerLeg"),
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

    arm_obj.hide_render = True
    arm_obj.show_in_front = True

    # world + preview cam/lights
    world = bpy.context.scene.world or bpy.data.worlds.new("WorldLite")
    bpy.context.scene.world = world
    world.use_nodes = True
    wn = world.node_tree.nodes
    wl = world.node_tree.links
    wn.clear()
    bg = wn.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.85, 0.86, 0.88, 1.0)
    bg.inputs[1].default_value = 1.15
    wout = wn.new("ShaderNodeOutputWorld")
    wl.new(bg.outputs[0], wout.inputs[0])

    for o in list(bpy.data.objects):
        if o.type in {{'LIGHT', 'CAMERA'}}:
            bpy.data.objects.remove(o, do_unlink=True)

    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bbox, Vector()) / 8.0
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 55
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (center.x, center.y - max(height * 2.15, 3.3), center.z + 0.02)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    def add_light(name, loc, energy):
        ld = bpy.data.lights.new(name=name, type='AREA')
        ld.energy = energy
        ld.size = 1.7
        lo = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = loc

    add_light("Key", (center.x + 1.4, center.y - 2.1, center.z + 1.6), 480)
    add_light("Fill", (center.x - 1.7, center.y - 1.3, center.z + 0.9), 180)
    add_light("Rim", (center.x, center.y + 1.7, center.z + 1.3), 220)

    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except Exception:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 32
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1152
    scene.render.filepath = render_path
    scene.render.image_settings.file_format = 'PNG'
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
                    scene.render.filepath = ogl_path
                    bpy.ops.render.opengl(write_still=True)
                break
    arm_obj.hide_set(False)

    # export glb/fbx/blend
    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.export_scene.gltf(
        filepath=temp_glb,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
    )
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        add_leaf_bones=False,
    )
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    # VRM export
    vrm_log = []
    for name in ("bl_ext.user_default.vrm", "vrm", "bl_ext.blender_org.vrm"):
        try:
            addon_utils.enable(name, default_set=True, persistent=True)
            vrm_log.append({{"enable": name, "ok": True}})
        except Exception as e:
            vrm_log.append({{"enable": name, "ok": False, "err": str(e)}})
    try:
        bpy.ops.preferences.addon_enable(module="bl_ext.user_default.vrm")
    except Exception:
        pass

    has_export = hasattr(bpy.ops.export_scene, "vrm")
    vrm_status = "skipped"
    if has_export:
        try:
            # try assign humanoid if API present
            try:
                arm = arm_obj
                bpy.ops.object.select_all(action='DESELECT')
                arm.select_set(True)
                bpy.context.view_layer.objects.active = arm
                # VRM addon humanoid mapping often auto-detects English bone names
            except Exception as e:
                vrm_log.append({{"humanoid": str(e)}})
            bpy.ops.export_scene.vrm(filepath=vrm_out)
            vrm_status = "ok"
            try:
                import shutil as _sh
                _sh.copyfile(vrm_out, vrm_warudo)
            except Exception as e:
                vrm_log.append({{"copy_warudo": str(e)}})
        except Exception as e:
            vrm_status = "error:" + str(e)
            vrm_log.append({{"export_err": str(e)}})
    else:
        vrm_status = "no_export_op"

    result = {{
        "status": "ok",
        "source": raw_glb,
        "verts": n_verts,
        "faces": n_faces,
        "materials": n_mats,
        "has_uv": has_uv,
        "has_texture_image": has_img,
        "weight_mode": weight_mode,
        "dims": list(main.dimensions),
        "vrm_status": vrm_status,
        "vrm_log": vrm_log,
        "blend": blend_path,
        "temp_glb": temp_glb,
    }}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])

    # unwrap nested result
    payload = res
    if isinstance(res, dict) and "result" in res:
        payload = res["result"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print("[ERROR] blender step failed")
        return 1

    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
        print("[OK glb]", GLB_OUT, GLB_OUT.stat().st_size)
    print("[OK blend]", BLEND_OUT.exists(), BLEND_OUT)
    print("[OK vrm]", VRM_OUT.exists(), VRM_OUT if VRM_OUT.exists() else "")
    print("[OK render]", RENDER_OUT.exists(), RENDER_OUT)
    print("[OK ogl]", OGL_OUT.exists(), OGL_OUT)
    print("mesh verts", payload.get("verts"), "faces", payload.get("faces"),
          "uv", payload.get("has_uv"), "tex", payload.get("has_texture_image"),
          "vrm", payload.get("vrm_status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
