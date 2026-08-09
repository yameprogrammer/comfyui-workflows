#!/usr/bin/env python3
"""Blender MCP: solid mesh process + front texture project + humanoid rig + exports."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

PACK = Path(r"D:\캐릭터\drafts\mecha_yame_v2")
EXPORTS = PACK / "exports"
RAW_GLB = EXPORTS / "mecha_yame_v2_raw.glb"
FRONT_TEX = PACK / "approved" / "single_front.png"
if not FRONT_TEX.is_file():
    FRONT_TEX = PACK / "approved" / "master_front.png"
BLEND_OUT = EXPORTS / "mecha_yame_v2.blend"
GLB_OUT = EXPORTS / "mecha_yame_v2_warudo.glb"
VRM_OUT = EXPORTS / "mecha_yame_v2.vrm"
FBX_OUT = EXPORTS / "mecha_yame_v2.fbx"
RENDER_OUT = EXPORTS / "viewport_render.png"
OGL_OUT = EXPORTS / "viewport_opengl.png"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")


def main() -> int:
    if not RAW_GLB.is_file() or not FRONT_TEX.is_file():
        print("[ERROR] missing raw glb or front texture", file=sys.stderr)
        return 1
    EXPORTS.mkdir(parents=True, exist_ok=True)

    raw_glb = str(RAW_GLB).replace("\\", "/")
    tex_path = str(FRONT_TEX).replace("\\", "/")
    temp_glb = str(TEMP_GLB).replace("\\", "/")
    blend_path = str(BLEND_OUT).replace("\\", "/")
    fbx_path = str(FBX_OUT).replace("\\", "/")
    render_path = str(RENDER_OUT).replace("\\", "/")
    ogl_path = str(OGL_OUT).replace("\\", "/")

    code = f"""
import bpy
import math
from mathutils import Vector, Matrix

raw_glb = r"{raw_glb}"
tex_path = r"{tex_path}"
temp_glb = r"{temp_glb}"
blend_path = r"{blend_path}"
fbx_path = r"{fbx_path}"
render_path = r"{render_path}"
ogl_path = r"{ogl_path}"

# clear
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

    # normalize
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

    # cleanup geometry carefully
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.reveal()
    bpy.ops.object.mode_set(mode='OBJECT')
    for p in main.data.polygons:
        p.use_smooth = True
    # ensure not backface-culled in materials later
    main.show_in_front = False

    # ---- camera-aligned front UV project for texture fidelity ----
    # place temporary camera in front (-Y) for project_from_view
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bbox, Vector()) / 8.0
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    cam_data = bpy.data.cameras.new("UVCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(main.dimensions.x, main.dimensions.z) * 1.15
    uv_cam = bpy.data.objects.new("UVCam", cam_data)
    bpy.context.scene.collection.objects.link(uv_cam)
    uv_cam.location = (center.x, center.y - max(height * 2.0, 3.0), center.z)
    direction = center - uv_cam.location
    uv_cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = uv_cam

    # set view to camera and project UV
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        space.shading.type = 'SOLID'
                region = next(r for r in area.regions if r.type == 'WINDOW')
                with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene):
                    bpy.context.view_layer.objects.active = main
                    main.select_set(True)
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    try:
                        bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=True, scale_to_bounds=True)
                        uv_mode = "project_from_view"
                    except Exception:
                        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
                        uv_mode = "smart_project_fallback"
                    bpy.ops.object.mode_set(mode='OBJECT')
                break

    # PBR material with front texture + solid fallback color
    mat = bpy.data.materials.new("MechaYame_V2_PBR")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.35
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.4
    # base dark charcoal so mesh is visible even if UV fails
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.13, 0.15, 1.0)
    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-300, 100)
    tex.image = bpy.data.images.load(tex_path)
    # mix: texture primary
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    main.data.materials.clear()
    main.data.materials.append(mat)

    # ---- humanoid armature ----
    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    height = max_v.z - min_v.z
    mid_x = (min_v.x + max_v.x) * 0.5
    mid_y = (min_v.y + max_v.y) * 0.5
    width = max(max_v.x - min_v.x, 0.3)

    def z(t):
        return min_v.z + height * t

    bones_def = [
        ("Hips", (mid_x, mid_y, z(0.52)), (mid_x, mid_y, z(0.58)), None),
        ("Spine", (mid_x, mid_y, z(0.58)), (mid_x, mid_y, z(0.66)), "Hips"),
        ("Chest", (mid_x, mid_y, z(0.66)), (mid_x, mid_y, z(0.78)), "Spine"),
        ("Neck", (mid_x, mid_y, z(0.78)), (mid_x, mid_y, z(0.84)), "Chest"),
        ("Head", (mid_x, mid_y, z(0.84)), (mid_x, mid_y, z(0.98)), "Neck"),
        ("LeftShoulder", (mid_x, mid_y, z(0.77)), (mid_x + width*0.12, mid_y, z(0.76)), "Chest"),
        ("LeftUpperArm", (mid_x + width*0.12, mid_y, z(0.76)), (mid_x + width*0.28, mid_y, z(0.62)), "LeftShoulder"),
        ("LeftLowerArm", (mid_x + width*0.28, mid_y, z(0.62)), (mid_x + width*0.36, mid_y, z(0.48)), "LeftUpperArm"),
        ("LeftHand", (mid_x + width*0.36, mid_y, z(0.48)), (mid_x + width*0.40, mid_y, z(0.44)), "LeftLowerArm"),
        ("RightShoulder", (mid_x, mid_y, z(0.77)), (mid_x - width*0.12, mid_y, z(0.76)), "Chest"),
        ("RightUpperArm", (mid_x - width*0.12, mid_y, z(0.76)), (mid_x - width*0.28, mid_y, z(0.62)), "RightShoulder"),
        ("RightLowerArm", (mid_x - width*0.28, mid_y, z(0.62)), (mid_x - width*0.36, mid_y, z(0.48)), "RightUpperArm"),
        ("RightHand", (mid_x - width*0.36, mid_y, z(0.48)), (mid_x - width*0.40, mid_y, z(0.44)), "RightLowerArm"),
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

    # hide armature in render
    arm_obj.hide_render = True
    arm_obj.show_in_front = True

    # preview camera + lights + world
    world = bpy.data.worlds.new("WorldLite") if bpy.context.scene.world is None else bpy.context.scene.world
    bpy.context.scene.world = world
    world.use_nodes = True
    wn = world.node_tree.nodes
    wl = world.node_tree.links
    wn.clear()
    bg = wn.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.82, 0.84, 0.87, 1.0)
    bg.inputs[1].default_value = 1.2
    wout = wn.new("ShaderNodeOutputWorld")
    wl.new(bg.outputs[0], wout.inputs[0])

    # remove UV cam, make render cam
    bpy.data.objects.remove(uv_cam, do_unlink=True)
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)

    bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bbox, Vector()) / 8.0
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 55
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (center.x, center.y - max(height * 2.1, 3.2), center.z + 0.05)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    def add_light(name, loc, energy):
        ld = bpy.data.lights.new(name=name, type='AREA')
        ld.energy = energy
        ld.size = 1.8
        lo = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = loc

    add_light("Key", (center.x + 1.4, center.y - 2.0, center.z + 1.6), 400)
    add_light("Fill", (center.x - 1.8, center.y - 1.2, center.z + 0.9), 180)
    add_light("Rim", (center.x, center.y + 1.8, center.z + 1.3), 220)

    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except Exception:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 24
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1152
    scene.render.filepath = render_path
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)

    # OpenGL solid preview of mesh (hide armature for clean shot)
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

    # export selected mesh+armature
    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.export_scene.gltf(
        filepath=temp_glb,
        export_format='GLB',
        use_selection=True,
        export_skins=True,
        export_morph=True,
        export_materials='EXPORT',
        export_animations=False,
    )
    fbx_ok = True
    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=True,
            add_leaf_bones=False,
            bake_anim=False,
            mesh_smooth_type='FACE',
            use_armature_deform_only=True,
            path_mode='COPY',
            embed_textures=True,
        )
    except Exception as e:
        fbx_ok = str(e)

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    result = {{
        "status": "success",
        "mesh": main.name,
        "poly_count": len(main.data.polygons),
        "vertex_count": len(main.data.vertices),
        "height_m": float(main.dimensions.z),
        "dims": [float(x) for x in main.dimensions],
        "bones": list(created.keys()),
        "blendshapes": len(main.data.shape_keys.key_blocks) if main.data.shape_keys else 0,
        "weight_mode": weight_mode,
        "uv_mode": uv_mode if 'uv_mode' in dir() else "unknown",
        "fbx_ok": fbx_ok,
    }}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:5000])

    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
        shutil.copyfile(TEMP_GLB, VRM_OUT)
        print(f"[OK] glb={GLB_OUT.stat().st_size} vrm_copy={VRM_OUT.stat().st_size}")
    else:
        print("[ERROR] no temp glb", file=sys.stderr)
        return 2
    for p in (FBX_OUT, RENDER_OUT, OGL_OUT, BLEND_OUT):
        if p.is_file():
            print(f"[OK] {p.name} {p.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
