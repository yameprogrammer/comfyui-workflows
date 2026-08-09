#!/usr/bin/env python3
"""Unified sleek dark materials — no height-band artifacts."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
BLEND = EXPORTS / "mecha_yame_v2.blend"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")
GLB_OUT = EXPORTS / "mecha_yame_v2_warudo.glb"
VRM_OUT = EXPORTS / "mecha_yame_v2.vrm"
FBX_OUT = EXPORTS / "mecha_yame_v2.fbx"
RENDER_OUT = EXPORTS / "viewport_render.png"
OGL_OUT = EXPORTS / "viewport_opengl.png"


def main() -> int:
    code = f"""
import bpy
from mathutils import Vector

blend_path = r"{str(BLEND).replace(chr(92), '/')}"
temp_glb = r"{str(TEMP_GLB).replace(chr(92), '/')}"
fbx_path = r"{str(FBX_OUT).replace(chr(92), '/')}"
render_path = r"{str(RENDER_OUT).replace(chr(92), '/')}"
ogl_path = r"{str(OGL_OUT).replace(chr(92), '/')}"

bpy.ops.wm.open_mainfile(filepath=blend_path)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

# single elegant body material: dark tech fabric with slight sheen
mat = bpy.data.materials.new('MechaYame_Sleek')
mat.use_nodes = True
mat.use_backface_culling = False
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()
out = nodes.new('ShaderNodeOutputMaterial')
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.045, 0.048, 0.052, 1.0)
if 'Metallic' in bsdf.inputs:
    bsdf.inputs['Metallic'].default_value = 0.18
if 'Roughness' in bsdf.inputs:
    bsdf.inputs['Roughness'].default_value = 0.48
if 'Specular IOR Level' in bsdf.inputs:
    bsdf.inputs['Specular IOR Level'].default_value = 0.4
# subtle cyan rim feel via very low emission
for k in ('Emission Color', 'Emission'):
    if k in bsdf.inputs:
        bsdf.inputs[k].default_value = (0.05, 0.35, 0.42, 1.0)
        break
if 'Emission Strength' in bsdf.inputs:
    bsdf.inputs['Emission Strength'].default_value = 0.04
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

main.data.materials.clear()
main.data.materials.append(mat)
# all faces slot 0
for p in main.data.polygons:
    p.material_index = 0

# cameras/lights
for o in list(bpy.data.objects):
    if o.type in {{'LIGHT', 'CAMERA'}}:
        bpy.data.objects.remove(o, do_unlink=True)

world = bpy.context.scene.world or bpy.data.worlds.new('World')
bpy.context.scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
bg = wn.new('ShaderNodeBackground')
bg.inputs[0].default_value = (0.82, 0.84, 0.87, 1.0)
bg.inputs[1].default_value = 1.05
wout = wn.new('ShaderNodeOutputWorld')
wl.new(bg.outputs[0], wout.inputs[0])

bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector()) / 8.0
height = max(v.z for v in bbox) - min(v.z for v in bbox)

cam_data = bpy.data.cameras.new('PreviewCam')
cam_data.lens = 55
cam = bpy.data.objects.new('PreviewCam', cam_data)
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

add_light('Key', (center.x + 1.4, center.y - 2.1, center.z + 1.6), 520)
add_light('Fill', (center.x - 1.7, center.y - 1.3, center.z + 0.9), 190)
add_light('Rim', (center.x, center.y + 1.7, center.z + 1.3), 240)

if arm:
    arm.hide_render = True

scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
scene.render.resolution_x = 768
scene.render.resolution_y = 1152
scene.render.filepath = render_path
bpy.ops.render.render(write_still=True)

if arm:
    arm.hide_set(True)
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
if arm:
    arm.hide_set(False)

window = bpy.context.window_manager.windows[0]
area = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), window.screen.areas[0])
region = next((r for r in area.regions if r.type == 'WINDOW'), area.regions[0])
bpy.ops.object.select_all(action='DESELECT')
main.select_set(True)
if arm:
    arm.select_set(True)
bpy.context.view_layer.objects.active = arm if arm else main
with bpy.context.temp_override(window=window, area=area, region=region, scene=scene, active_object=(arm or main), selected_objects=[main] + ([arm] if arm else [])):
    bpy.ops.export_scene.gltf(filepath=temp_glb, export_format='GLB', use_selection=True, export_skins=True, export_morph=True, export_materials='EXPORT', export_animations=False)
    try:
        bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_armature_deform_only=True, path_mode='COPY', embed_textures=True)
        fbx_ok = True
    except Exception as e:
        fbx_ok = str(e)

bpy.ops.wm.save_mainfile()
result = {{"status": "success", "poly": len(main.data.polygons), "fbx_ok": fbx_ok}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:2000])
    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
        shutil.copyfile(TEMP_GLB, VRM_OUT)
        print("glb", GLB_OUT.stat().st_size)
    for p in (RENDER_OUT, OGL_OUT, FBX_OUT):
        if p.is_file():
            print(p.name, p.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
