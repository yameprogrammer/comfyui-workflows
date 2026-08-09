#!/usr/bin/env python3
"""Crop front ref to subject, re-UV project, apply sleek dual materials, re-export."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

try:
    from PIL import Image
except ImportError:
    Image = None

PACK = Path(r"D:\캐릭터\drafts\mecha_yame_v2")
EXPORTS = PACK / "exports"
BLEND = EXPORTS / "mecha_yame_v2.blend"
FRONT = PACK / "approved" / "single_front.png"
CROPPED = PACK / "approved" / "single_front_cropped.png"
TEMP_GLB = Path(r"C:\Users\parkp\AppData\Local\Temp\mecha_yame_v2_export.glb")
GLB_OUT = EXPORTS / "mecha_yame_v2_warudo.glb"
VRM_OUT = EXPORTS / "mecha_yame_v2.vrm"
FBX_OUT = EXPORTS / "mecha_yame_v2.fbx"
RENDER_OUT = EXPORTS / "viewport_render.png"
OGL_OUT = EXPORTS / "viewport_opengl.png"


def crop_subject(src: Path, dst: Path) -> Path:
    if Image is None:
        return src
    im = Image.open(src).convert("RGBA")
    # assume near-white background; find non-white bbox
    px = im.load()
    w, h = im.size
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 10:
                continue
            # non-near-white
            if r < 245 or g < 245 or b < 245:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x <= min_x or max_y <= min_y:
        im.save(dst)
        return dst
    pad = int(0.02 * max(w, h))
    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(w - 1, max_x + pad)
    max_y = min(h - 1, max_y + pad)
    crop = im.crop((min_x, min_y, max_x + 1, max_y + 1))
    # put on pure white
    bg = Image.new("RGBA", crop.size, (255, 255, 255, 255))
    bg.paste(crop, mask=crop.split()[-1])
    bg.convert("RGB").save(dst)
    print(f"[crop] {src.name} -> {dst.name} size={bg.size}")
    return dst


def main() -> int:
    tex = crop_subject(FRONT, CROPPED) if FRONT.is_file() else FRONT
    blend = str(BLEND).replace("\\", "/")
    tex_path = str(tex).replace("\\", "/")
    temp_glb = str(TEMP_GLB).replace("\\", "/")
    fbx_path = str(FBX_OUT).replace("\\", "/")
    render_path = str(RENDER_OUT).replace("\\", "/")
    ogl_path = str(OGL_OUT).replace("\\", "/")
    blend_path = blend

    code = f"""
import bpy
import bmesh
from mathutils import Vector

blend_path = r"{blend_path}"
tex_path = r"{tex_path}"
temp_glb = r"{temp_glb}"
fbx_path = r"{fbx_path}"
render_path = r"{render_path}"
ogl_path = r"{ogl_path}"

bpy.ops.wm.open_mainfile(filepath=blend_path)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
main = meshes[0]
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

# ---- rebuild materials: hybrid textured + elegant PBR ----
# 1) body fabric matte charcoal with optional texture mix
# 2) head more metallic black with cyan emission on upper faces

for m in list(bpy.data.materials):
    if m.users == 0:
        bpy.data.materials.remove(m)

def make_pbr(name, base, metallic, roughness, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*base, 1.0)
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = metallic
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = roughness
    if emission is not None:
        for k in ('Emission Color', 'Emission'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = (*emission, 1.0)
                break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emission_strength
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

# textured body: mix texture with charcoal so white bg doesn't dominate
mat_body = bpy.data.materials.new('Mecha_Body')
mat_body.use_nodes = True
mat_body.use_backface_culling = False
n = mat_body.node_tree.nodes
l = mat_body.node_tree.links
n.clear()
out = n.new('ShaderNodeOutputMaterial'); out.location=(600,0)
bsdf = n.new('ShaderNodeBsdfPrincipled'); bsdf.location=(350,0)
if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = 0.08
if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = 0.55
tex = n.new('ShaderNodeTexImage'); tex.location=(-400,120)
tex.image = bpy.data.images.load(tex_path)
# RGB to BW for mask: dark clothing stays, white bg -> fabric color
rgb = n.new('ShaderNodeRGBToBW'); rgb.location=(-150,120)
mix = n.new('ShaderNodeMixRGB') if hasattr(bpy.types, 'ShaderNodeMixRGB') else n.new('ShaderNodeMix')
mix.location=(100,80)
# Blender 4+/5 Mix node
try:
    mix.data_type = 'RGBA'
    mix.blend_type = 'MIX'
    fabric = (0.10, 0.11, 0.12, 1.0)
    # Factor from luminance inverted: white bg high -> use fabric
    inv = n.new('ShaderNodeMath'); inv.location=(-20,200); inv.operation='SUBTRACT'
    inv.inputs[0].default_value = 1.0
    l.new(tex.outputs['Color'], rgb.inputs['Color'])
    l.new(rgb.outputs['Val'], inv.inputs[1])
    # threshold-ish
    gre = n.new('ShaderNodeMath'); gre.location=(100,200); gre.operation='GREATER_THAN'
    gre.inputs[1].default_value = 0.15
    l.new(inv.outputs[0], gre.inputs[0])
    if hasattr(mix, 'inputs') and 'Fac' in mix.inputs:
        l.new(gre.outputs[0], mix.inputs['Fac'])
        mix.inputs['Color1'].default_value = fabric
        l.new(tex.outputs['Color'], mix.inputs['Color2'])
        l.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        # ShaderNodeMix API
        mix.data_type = 'RGBA'
        l.new(gre.outputs[0], mix.inputs['Factor'])
        mix.inputs['A'].default_value = fabric
        l.new(tex.outputs['Color'], mix.inputs['B'])
        l.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
except Exception as e:
    # fallback solid fabric
    bsdf.inputs['Base Color'].default_value = (0.10, 0.11, 0.12, 1.0)
    mix_err = str(e)
l.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

mat_head = make_pbr('Mecha_Head', (0.02, 0.02, 0.03), 0.85, 0.22, emission=(0.05, 0.55, 0.65), emission_strength=0.35)
mat_hand = make_pbr('Mecha_Hand', (0.03, 0.03, 0.035), 0.7, 0.28)

main.data.materials.clear()
main.data.materials.append(mat_body)
main.data.materials.append(mat_head)
main.data.materials.append(mat_hand)

# assign materials by height/region using bmesh
bm = bmesh.new()
bm.from_mesh(main.data)
bm.faces.ensure_lookup_table()
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
min_z = min(v.z for v in bbox)
max_z = max(v.z for v in bbox)
h = max_z - min_z
max_x = max(abs((main.matrix_world @ Vector(c)).x) for c in main.bound_box)

for f in bm.faces:
    cents = [main.matrix_world @ v.co for v in f.verts]
    cz = sum(v.z for v in cents) / len(cents)
    cx = abs(sum(v.x for v in cents) / len(cents))
    t = (cz - min_z) / h if h > 1e-6 else 0.5
    # head region ~ top 18%
    if t > 0.82:
        f.material_index = 1
    # hands: outer lower-mid arms-ish
    elif t < 0.55 and t > 0.35 and cx > max_x * 0.28:
        f.material_index = 2
    else:
        f.material_index = 0
bm.to_mesh(main.data)
bm.free()
main.data.update()

# re-UV project from front with cropped texture
bbox = [main.matrix_world @ Vector(c) for c in main.bound_box]
center = sum(bbox, Vector()) / 8.0
height = max(v.z for v in bbox) - min(v.z for v in bbox)

# remove old cameras
for o in list(bpy.data.objects):
    if o.type == 'CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)

cam_data = bpy.data.cameras.new('UVCam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = max(main.dimensions.x, main.dimensions.z) * 1.05
cam = bpy.data.objects.new('UVCam', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (center.x, center.y - max(height*2.0, 3.0), center.z)
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam

for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
            region = next(r for r in area.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene):
                bpy.context.view_layer.objects.active = main
                main.select_set(True)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=True, scale_to_bounds=True)
                bpy.ops.object.mode_set(mode='OBJECT')
            break

# preview cam + lights
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)

world = bpy.context.scene.world or bpy.data.worlds.new('W')
bpy.context.scene.world = world
world.use_nodes = True
wn=world.node_tree.nodes; wl=world.node_tree.links; wn.clear()
bg=wn.new('ShaderNodeBackground'); bg.inputs[0].default_value=(0.78,0.80,0.83,1); bg.inputs[1].default_value=1.0
wout=wn.new('ShaderNodeOutputWorld'); wl.new(bg.outputs[0], wout.inputs[0])

cam_data2 = bpy.data.cameras.new('PreviewCam')
cam_data2.lens = 55
cam2 = bpy.data.objects.new('PreviewCam', cam_data2)
bpy.context.scene.collection.objects.link(cam2)
cam2.location = (center.x, center.y - max(height*2.15, 3.3), center.z + 0.02)
cam2.rotation_euler = (center - cam2.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam2
# remove UV cam from render confusion
bpy.data.objects.remove(cam, do_unlink=True)

def add_light(name, loc, energy):
    ld = bpy.data.lights.new(name=name, type='AREA'); ld.energy=energy; ld.size=1.6
    lo = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(lo); lo.location=loc
add_light('Key', (center.x+1.3, center.y-2.0, center.z+1.5), 450)
add_light('Fill', (center.x-1.6, center.y-1.2, center.z+0.8), 160)
add_light('Rim', (center.x, center.y+1.6, center.z+1.2), 200)

if arm:
    arm.hide_render = True

scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 24
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

# export
bpy.ops.object.select_all(action='DESELECT')
main.select_set(True)
if arm:
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
else:
    bpy.context.view_layer.objects.active = main
bpy.ops.export_scene.gltf(filepath=temp_glb, export_format='GLB', use_selection=True, export_skins=True, export_morph=True, export_materials='EXPORT', export_animations=False)
try:
    bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_armature_deform_only=True, path_mode='COPY', embed_textures=True)
    fbx_ok = True
except Exception as e:
    fbx_ok = str(e)

bpy.ops.wm.save_mainfile()
result = {{
    "status": "success",
    "materials": [m.name for m in main.data.materials],
    "poly": len(main.data.polygons),
    "fbx_ok": fbx_ok,
}}
"""
    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
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
