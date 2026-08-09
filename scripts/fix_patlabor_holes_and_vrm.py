#!/usr/bin/env python3
"""
Fill small mesh holes (neck / left arm / left torso) and re-export Warudo VRM
with verified skin + humanoid mapping. Preserve current arm bone layout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
BLEND = EXPORTS / "mecha_patlabor_v3.blend"


def main() -> int:
    paths = {
        "blend": str(BLEND).replace("\\", "/"),
        "blend_rigged": str(EXPORTS / "mecha_patlabor_v3_rigged.blend").replace("\\", "/"),
        "vrm": str(EXPORTS / "mecha_patlabor_v3.vrm").replace("\\", "/"),
        "vrm_warudo": str(EXPORTS / "mecha_patlabor_v3_warudo.vrm").replace("\\", "/"),
        "glb": str(EXPORTS / "mecha_patlabor_v3_warudo.glb").replace("\\", "/"),
        "r_front": str(EXPORTS / "viewport_fixed_front.png").replace("\\", "/"),
        "r_raise": str(EXPORTS / "viewport_fixed_raise.png").replace("\\", "/"),
        "r_close": str(EXPORTS / "viewport_fixed_neck_arm.png").replace("\\", "/"),
    }

    code = f'''
import bpy
import bmesh
import math
import addon_utils
import shutil
from mathutils import Vector, Quaternion, Matrix, Euler
from pathlib import Path
from collections import defaultdict

paths = {repr(paths)}
log = []

addon_utils.enable("bl_ext.user_default.vrm", default_set=True, persistent=True)
bpy.ops.wm.open_mainfile(filepath=paths["blend"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
main = next(o for o in bpy.data.objects if o.type == "MESH")

# rest pose
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
    pb.location = (0,0,0)
    pb.scale = (1,1,1)
bpy.context.view_layer.update()

# ========== 1) HOLE FILL ==========
# Work on mesh data in object mode via bmesh
bm = bmesh.new()
bm.from_mesh(main.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

before_boundary = sum(1 for e in bm.edges if e.is_boundary)
before_faces = len(bm.faces)

# remove doubles first
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0006)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

# Fill holes: try holes_fill on all boundary edges, multiple passes with increasing sides
for sides in (8, 16, 32, 64, 128, 256, 512, 0):
    boundary = [e for e in bm.edges if e.is_boundary]
    if not boundary:
        break
    try:
        if sides == 0:
            # 0 = no limit in some versions; use large
            bmesh.ops.holes_fill(bm, edges=boundary, sides=1000)
        else:
            bmesh.ops.holes_fill(bm, edges=boundary, sides=sides)
    except Exception as e:
        log.append(f"holes_fill sides={{sides}} err={{e}}")
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

# edgenet_fill remaining small boundary clusters
boundary = [e for e in bm.edges if e.is_boundary]
if boundary:
    try:
        bmesh.ops.edgenet_fill(bm, edges=boundary)
        log.append("edgenet_fill")
    except Exception as e:
        log.append(f"edgenet_fill err={{e}}")
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

# dissolve degenerate + recalc normals
try:
    bmesh.ops.dissolve_degenerate(bm, dist=0.0004, edges=list(bm.edges))
except Exception as e:
    log.append(f"dissolve {{e}}")
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

# Targeted: if still open boundary near neck/left torso/left arm, fill loop by loop
def boundary_loops(bm):
    adj = defaultdict(set)
    bedges = [e for e in bm.edges if e.is_boundary]
    for e in bedges:
        a, b = e.verts
        adj[a.index].add(b.index)
        adj[b.index].add(a.index)
    vis = set()
    loops = []
    for vid in list(adj.keys()):
        if vid in vis:
            continue
        stack = [vid]
        vis.add(vid)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in vis:
                    vis.add(v)
                    stack.append(v)
        loops.append(comp)
    return loops

coords = {{v.index: v.co.copy() for v in bm.verts}}
minz = min(c.z for c in coords.values())
maxz = max(c.z for c in coords.values())
H = max(maxz - minz, 1e-6)
cx = sum(c.x for c in coords.values()) / len(coords)

def is_target_loop(comp):
    pts = [coords[i] for i in comp if i in coords]
    if not pts or len(comp) < 4:
        return False
    z = sum(p.z for p in pts) / len(pts)
    x = sum(p.x for p in pts) / len(pts)
    t = (z - minz) / H
    # neck
    if t > 0.68 and abs(x - cx) < 0.22 and len(comp) <= 400:
        return True
    # left arm
    if x > cx + 0.12 and t > 0.48 and t < 0.78 and len(comp) <= 500:
        return True
    # left torso
    if x > cx and x < cx + 0.35 and t > 0.42 and t < 0.72 and len(comp) <= 500:
        return True
    # small loops anywhere on upper body
    if t > 0.40 and len(comp) <= 80:
        return True
    return False

# refresh coords after fills
bm.verts.ensure_lookup_table()
coords = {{v.index: v.co.copy() for v in bm.verts}}
filled_loops = 0
for comp in boundary_loops(bm):
    if not is_target_loop(comp):
        continue
    # gather edges in this loop
    vset = set(comp)
    edges = [e for e in bm.edges if e.is_boundary and e.verts[0].index in vset and e.verts[1].index in vset]
    if len(edges) < 3:
        continue
    try:
        bmesh.ops.edgeloop_fill(bm, edges=edges)
        filled_loops += 1
    except Exception:
        try:
            bmesh.ops.holes_fill(bm, edges=edges, sides=len(edges) + 2)
            filled_loops += 1
        except Exception as e:
            log.append(f"loop fill fail n={{len(comp)}} {{e}}")
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    coords = {{v.index: v.co.copy() for v in bm.verts}}

log.append(f"filled_loops={{filled_loops}}")

# one more global holes_fill
boundary = [e for e in bm.edges if e.is_boundary]
if boundary:
    try:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=200)
    except Exception:
        pass

bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
after_boundary = sum(1 for e in bm.edges if e.is_boundary)
after_faces = len(bm.faces)
log.append(f"boundary {{before_boundary}}->{{after_boundary}} faces {{before_faces}}->{{after_faces}}")

bm.to_mesh(main.data)
bm.free()
main.data.update()
for p in main.data.polygons:
    p.use_smooth = True

# ========== 2) RE-SKIN critical areas (head/arms must deform) ==========
# Keep existing groups but ensure Head owns helmet, arms own limbs, blend shoulders
# Rebuild weights similar to anatomy rig but softer blends

# clear and rebuild weights carefully
main.vertex_groups.clear()
for b in arm.data.bones:
    main.vertex_groups.new(name=b.name)

mw = main.matrix_world
vs = [mw @ v.co for v in main.data.vertices]
xs=[p.x for p in vs]; ys=[p.y for p in vs]; zs=[p.z for p in vs]
minx,maxx=min(xs),max(xs); miny,maxy=min(ys),max(ys); minz,maxz=min(zs),max(zs)
H=maxz-minz; W=maxx-minx; cx=0.5*(minx+maxx); cy=0.5*(miny+maxy)

# bone samples (world)
samples = []
for b in arm.data.bones:
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    samples.append((b.name, h, (h+t)*0.5, t))

def dist_seg(p, a, b):
    ab = b - a
    L2 = ab.length_squared
    if L2 < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / L2))
    return (p - (a + ab * t)).length

def nearest(names, p):
    best, bd = None, 1e18
    for n, h, m, t in samples:
        if n not in names:
            continue
        d = min(dist_seg(p, h, t), (p - m).length)
        if d < bd:
            bd, best = d, n
    return best, bd

# head sphere from Head bone
hb = arm.data.bones["Head"]
head_c = arm.matrix_world @ ((hb.head_local + hb.tail_local) * 0.5)
head_r = (arm.matrix_world @ hb.tail_local - arm.matrix_world @ hb.head_local).length * 0.55
# expand using high verts
high = [p for p in vs if p.z >= minz + H * 0.72]
if high:
    hc = sum(high, Vector()) / len(high)
    head_c = Vector((hc.x, hc.y, head_c.z))
    head_r = max((p - head_c).length for p in high) * 1.02

ARM_L = {{"LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand"}}
ARM_R = {{"RightShoulder","RightUpperArm","RightLowerArm","RightHand"}}
LEG_L = {{"LeftUpperLeg","LeftLowerLeg","LeftFoot"}}
LEG_R = {{"RightUpperLeg","RightLowerLeg","RightFoot"}}
TORSO = {{"Hips","Spine","Chest","Neck"}}

def assign(vi, pairs):
    s = sum(w for _, w in pairs) or 1.0
    for g, w in pairs:
        if w <= 0:
            continue
        main.vertex_groups[g].add([vi], w / s, "REPLACE")

counts = defaultdict(int)
for vi, p in enumerate(vs):
    lat = abs(p.x - cx) / max(W * 0.5, 1e-6)
    th = (p.z - minz) / max(H, 1e-6)
    side_L = p.x >= cx
    d_head = (p - head_c).length

    # HEAD — exclusive for helmet (critical for Warudo head tracking)
    if d_head <= head_r and p.z >= minz + H * 0.68:
        main.vertex_groups["Head"].add([vi], 1.0, "REPLACE")
        counts["head"] += 1
        continue

    # neck blend ring
    if d_head <= head_r * 1.15 and p.z >= minz + H * 0.64:
        assign(vi, [("Head", 0.55), ("Neck", 0.45)])
        counts["neck"] += 1
        continue

    # LEGS
    if th < 0.50:
        n0, d0 = nearest(LEG_L if side_L else LEG_R, p)
        n_t, dt = nearest(TORSO, p)
        if n0 and (th < 0.48 or d0 < dt * 1.05):
            if th > 0.42 and n_t:
                assign(vi, [(n0, 0.8), (n_t, 0.2)])
            else:
                main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
            counts["leg"] += 1
            continue

    # ARMS — exclusive for outer limb (critical for arm motion)
    n_a, da = nearest(ARM_L if side_L else ARM_R, p)
    n_t, dt = nearest(TORSO, p)
    if n_a and (lat > 0.22 or da < dt * 0.9) and th > 0.32 and p.z < head_c.z - H * 0.02:
        if lat > 0.32 or da < 0.05:
            # pure arm
            main.vertex_groups[n_a].add([vi], 1.0, "REPLACE")
        else:
            assign(vi, [(n_a, 0.75), ("Chest", 0.25)])
        counts["arm"] += 1
        continue

    # TORSO
    n0, _ = nearest(TORSO, p)
    if not n0:
        n0 = "Chest" if th > 0.55 else ("Spine" if th > 0.48 else "Hips")
    main.vertex_groups[n0].add([vi], 1.0, "REPLACE")
    counts["torso"] += 1

log.append(f"weights {{dict(counts)}}")

# armature modifier
for m in list(main.modifiers):
    if m.type == "ARMATURE":
        main.modifiers.remove(m)
am = main.modifiers.new("Armature", "ARMATURE")
am.object = arm
am.use_vertex_groups = True
am.use_deform_preserve_volume = False
main.parent = arm

# ========== 3) Bone rolls / rest for VRM ==========
# Apply rest pose as is; set VRM1 humanoid mapping
ext = arm.data.vrm_addon_extension
try:
    for val in ("1.0", getattr(ext, "SPEC_VERSION_VRM1", "1.0")):
        try:
            ext.spec_version = val
            break
        except Exception:
            pass
except Exception as e:
    log.append(f"spec {{e}}")

vrm1_map = {{
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
    "left_shoulder": "LeftShoulder", "left_upper_arm": "LeftUpperArm", "left_lower_arm": "LeftLowerArm", "left_hand": "LeftHand",
    "right_shoulder": "RightShoulder", "right_upper_arm": "RightUpperArm", "right_lower_arm": "RightLowerArm", "right_hand": "RightHand",
    "left_upper_leg": "LeftUpperLeg", "left_lower_leg": "LeftLowerLeg", "left_foot": "LeftFoot",
    "right_upper_leg": "RightUpperLeg", "right_lower_leg": "RightLowerLeg", "right_foot": "RightFoot",
}}
try:
    hb = ext.vrm1.humanoid.human_bones
    hb.filter_by_human_bone_hierarchy = False
    if hasattr(hb, "allow_non_humanoid_rig"):
        hb.allow_non_humanoid_rig = True
    for prop, bone in vrm1_map.items():
        slot = getattr(hb, prop, None)
        if slot and slot.node and bone in arm.data.bones:
            slot.node.bone_name = bone
except Exception as e:
    log.append(f"vrm1 {{e}}")
try:
    ext.vrm0.meta.title = "Mecha Patlabor VTuber v3"
    ext.vrm0.meta.author = "yameprogrammer"
    ext.vrm0.meta.version = "0.3.2"
except Exception:
    pass

# pose deformation verify after reskin
coords0 = [v.co.copy() for v in main.data.vertices]
arm.pose.bones["Head"].rotation_mode = "XYZ"
arm.pose.bones["Head"].rotation_euler = (0.35, 0, 0.25)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
me = main.evaluated_get(deps).to_mesh()
max_head = max((me.vertices[i].co - coords0[i]).length for i in range(len(me.vertices)))
main.evaluated_get(deps).to_mesh_clear()
arm.pose.bones["Head"].rotation_euler = (0,0,0)
arm.pose.bones["LeftUpperArm"].rotation_mode = "XYZ"
arm.pose.bones["LeftUpperArm"].rotation_euler = (0, -0.9, 0)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
me = main.evaluated_get(deps).to_mesh()
max_arm = max((me.vertices[i].co - coords0[i]).length for i in range(len(me.vertices)))
main.evaluated_get(deps).to_mesh_clear()
arm.pose.bones["LeftUpperArm"].rotation_euler = (0,0,0)
bpy.context.view_layer.update()
log.append(f"deform head={{max_head:.4f}} arm={{max_arm:.4f}}")

# boundary after fill
bm2 = bmesh.new(); bm2.from_mesh(main.data)
bnd = sum(1 for e in bm2.edges if e.is_boundary)
bm2.free()
log.append(f"final_boundary={{bnd}}")

# renders
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.hide_render = False
        o.hide_viewport = False
cam = bpy.context.scene.camera
if not cam:
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

def frame(az=15, elev=6, dist=3.0, focus_z=None):
    bpy.context.view_layer.update()
    bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
    center = sum(bb, Vector()) / 8
    if focus_z is not None:
        center.z = focus_z
    azr, el = math.radians(az), math.radians(elev)
    loc = Vector((
        center.x + dist * math.cos(el) * math.sin(azr),
        center.y - dist * math.cos(el) * math.cos(azr),
        center.z + dist * math.sin(el),
    ))
    cam.location = loc
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.resolution_x = 1024
scene.render.resolution_y = 1280
scene.render.film_transparent = True
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass

frame(15)
scene.render.filepath = paths["r_front"]
bpy.ops.render.render(write_still=True)

# close-up neck/left arm
frame(25, elev=10, dist=1.6, focus_z=1.05)
scene.render.filepath = paths["r_close"]
bpy.ops.render.render(write_still=True)

# raise arms
def world_rot(pb, axis, deg):
    pb.rotation_mode = "QUATERNION"
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest = pb.matrix.copy()
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    head = rest.translation
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ rest
    bpy.context.view_layer.update()

world_rot(arm.pose.bones["LeftUpperArm"], "Y", -80)
world_rot(arm.pose.bones["RightUpperArm"], "Y", 80)
frame(15, dist=3.0)
scene.render.filepath = paths["r_raise"]
bpy.ops.render.render(write_still=True)
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion((1,0,0,0))
bpy.context.view_layer.update()

# save blend BEFORE export
bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
shutil.copyfile(paths["blend"], paths["blend_rigged"])

# export GLB + VRM from current scene (no reload)
win = bpy.context.window_manager.windows[0]
area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
for o in bpy.data.objects:
    o.select_set(o in (arm, main))
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(window=win, area=area, region=region, scene=scene, active_object=arm, selected_objects=[arm, main]):
    bpy.ops.export_scene.gltf(
        filepath=paths["glb"], export_format="GLB", use_selection=True,
        export_apply=False, export_skins=True, export_morph=True,
    )
    r = bpy.ops.export_scene.vrm(
        filepath=paths["vrm"], ignore_warning=True, check_existing=False,
        armature_object_name=arm.name, export_all_influences=True,
    )
    log.append(f"vrm={{list(r) if r else None}}")

vrm_size = Path(paths["vrm"]).stat().st_size if Path(paths["vrm"]).is_file() else 0
if vrm_size > 1000:
    shutil.copyfile(paths["vrm"], paths["vrm_warudo"])
# save again
bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])
shutil.copyfile(paths["blend"], paths["blend_rigged"])

result = {{
    "status": "ok" if vrm_size > 1000 else "error",
    "log": log,
    "boundary_after": bnd,
    "deform_head": round(max_head, 4),
    "deform_arm": round(max_arm, 4),
    "weight_counts": dict(counts),
    "vrm_size": vrm_size,
}}
'''

    res = exec_blender_code(code)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:8000])
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    return 0 if isinstance(payload, dict) and payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
