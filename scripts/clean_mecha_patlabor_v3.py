#!/usr/bin/env python3
"""
Conservative Blender cleanup for mecha_patlabor_v3.

Do NOT delete large connected components (arms can be weakly connected /
counted as separate islands in bad topology).

Safe ops only:
- tiny floaters (<80 faces AND small bbox)
- remove doubles
- consistent normals
- light hand tip smooth
- mild ear lateral shrink (small region only)
- scale 1.6m, ground feet
- export clean glb/blend + renders
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import exec_blender_code

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
GLB_IN = EXPORTS / "mecha_patlabor_v3_mv_tex.glb"
BLEND_OUT = EXPORTS / "mecha_patlabor_v3_clean.blend"
GLB_OUT = EXPORTS / "mecha_patlabor_v3_clean.glb"
BLEND_MAIN = EXPORTS / "mecha_patlabor_v3.blend"


def main() -> int:
    if not GLB_IN.is_file():
        print("missing", GLB_IN)
        return 1

    paths = {
        "glb_in": str(GLB_IN).replace("\\", "/"),
        "blend_out": str(BLEND_OUT).replace("\\", "/"),
        "glb_out": str(GLB_OUT).replace("\\", "/"),
        "r_front": str(EXPORTS / "viewport_clean_front.png").replace("\\", "/"),
        "r_side": str(EXPORTS / "viewport_clean_side.png").replace("\\", "/"),
        "r_back": str(EXPORTS / "viewport_clean_back.png").replace("\\", "/"),
        "r_3q": str(EXPORTS / "viewport_clean_3q.png").replace("\\", "/"),
    }

    code = f'''
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

paths = {repr(paths)}
report = {{"steps": []}}

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(coll):
        try:
            coll.remove(item)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=paths["glb_in"])
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objs:
    result = {{"status": "error", "message": "no mesh"}}
else:
    if len(mesh_objs) > 1:
        bm_all = bmesh.new()
        for o in mesh_objs:
            bm_tmp = bmesh.new()
            bm_tmp.from_mesh(o.data)
            bm_tmp.transform(o.matrix_world)
            mesh_tmp = bpy.data.meshes.new("_tmp")
            bm_tmp.to_mesh(mesh_tmp)
            bm_tmp.free()
            bm_all.from_mesh(mesh_tmp)
            bpy.data.meshes.remove(mesh_tmp)
        for o in mesh_objs:
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new("MechaPatlabor_V3")
        bm_all.to_mesh(me)
        bm_all.free()
        main = bpy.data.objects.new("MechaPatlabor_V3", me)
        bpy.context.scene.collection.objects.link(main)
    else:
        main = mesh_objs[0]
        main.name = "MechaPatlabor_V3"
        main.data.transform(main.matrix_world)
        main.matrix_world = Matrix.Identity(4)

    before = {{"verts": len(main.data.vertices), "faces": len(main.data.polygons)}}

    bm = bmesh.new()
    bm.from_mesh(main.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # components
    visited = set()
    components = []
    for f in bm.faces:
        if f.index in visited:
            continue
        stack = [f]
        visited.add(f.index)
        faces = []
        verts = set()
        while stack:
            cur = stack.pop()
            faces.append(cur)
            for v in cur.verts:
                verts.add(v)
            for e in cur.edges:
                for lf in e.link_faces:
                    if lf.index not in visited:
                        visited.add(lf.index)
                        stack.append(lf)
        components.append((faces, verts))
    components.sort(key=lambda t: len(t[0]), reverse=True)

    # whole mesh bbox
    all_co = [v.co for v in bm.verts]
    W = max(c.x for c in all_co) - min(c.x for c in all_co)
    H = max(c.z for c in all_co) - min(c.z for c in all_co)
    D = max(c.y for c in all_co) - min(c.y for c in all_co)

    del_faces = []
    removed_comps = 0
    removed_faces = 0
    for i, (faces, verts) in enumerate(components):
        if i == 0:
            continue
        n = len(faces)
        if n == 0:
            continue
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        zs = [v.co.z for v in verts]
        bw = max(xs) - min(xs)
        bd = max(ys) - min(ys)
        bh = max(zs) - min(zs)
        # ONLY tiny debris: few faces AND tiny volume
        tiny = n < 80 and max(bw, bd, bh) < max(W, H, D) * 0.08
        if tiny:
            del_faces.extend(faces)
            removed_faces += n
            removed_comps += 1
    if del_faces:
        bmesh.ops.delete(bm, geom=del_faces, context="FACES")
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
    report["steps"].append({{
        "floaters_removed_comps": removed_comps,
        "faces": removed_faces,
        "components_total": len(components),
        "body_faces": len(components[0][0]) if components else 0,
    }})

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0005)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    coords = [v.co.copy() for v in bm.verts]
    minx = min(c.x for c in coords); maxx = max(c.x for c in coords)
    miny = min(c.y for c in coords); maxy = max(c.y for c in coords)
    minz = min(c.z for c in coords); maxz = max(c.z for c in coords)
    W = maxx - minx; D = maxy - miny; H = maxz - minz
    cx = (minx + maxx) * 0.5
    cy = (miny + maxy) * 0.5

    # mild ear shrink: only very outer head side verts
    ear_moved = 0
    head_z0 = minz + H * 0.78
    for v in bm.verts:
        w = v.co
        if w.z < head_z0:
            continue
        side = abs(w.x - cx)
        if side < W * 0.28:
            continue
        # outer ear pad only
        if abs(w.y - cy) > D * 0.22:
            continue
        center = Vector((cx, w.y, w.z))
        offset = w - center
        offset.x *= 0.88
        v.co = center + offset
        ear_moved += 1
    report["steps"].append({{"ear_verts_adjusted": ear_moved}})

    # gentle hand tip smooth only on extreme tips
    hand_idxs = []
    for v in bm.verts:
        w = v.co
        if w.z < minz + H * 0.32 or w.z > minz + H * 0.52:
            continue
        if abs(w.x - cx) < W * 0.38:
            continue
        hand_idxs.append(v.index)
    bm.verts.ensure_lookup_table()
    for _ in range(1):
        new_co = {{}}
        for idx in hand_idxs:
            v = bm.verts[idx]
            nbrs = [e.other_vert(v) for e in v.link_edges]
            if not nbrs:
                continue
            avg = sum((n.co for n in nbrs), Vector()) / len(nbrs)
            new_co[idx] = v.co.lerp(avg, 0.25)
        for idx, co in new_co.items():
            bm.verts[idx].co = co
    report["steps"].append({{"hand_verts_smoothed": len(hand_idxs)}})

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    try:
        bmesh.ops.dissolve_degenerate(bm, dist=0.0002, edges=list(bm.edges))
    except Exception as e:
        report["steps"].append({{"dissolve_degenerate": str(e)}})

    # scale / ground / center
    minz = min(v.co.z for v in bm.verts)
    maxz = max(v.co.z for v in bm.verts)
    h = max(maxz - minz, 1e-6)
    s = 1.6 / h
    for v in bm.verts:
        v.co *= s
    minz = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= minz
    minx = min(v.co.x for v in bm.verts); maxx = max(v.co.x for v in bm.verts)
    miny = min(v.co.y for v in bm.verts); maxy = max(v.co.y for v in bm.verts)
    cx = (minx + maxx) * 0.5
    cy = (miny + maxy) * 0.5
    for v in bm.verts:
        v.co.x -= cx
        v.co.y -= cy

    bm.to_mesh(main.data)
    bm.free()
    main.data.update()
    main.location = (0, 0, 0)
    main.rotation_euler = (0, 0, 0)
    main.scale = (1, 1, 1)

    for p in main.data.polygons:
        p.use_smooth = True
    for mat in main.data.materials:
        if mat:
            mat.use_backface_culling = False

    after = {{"verts": len(main.data.vertices), "faces": len(main.data.polygons)}}
    report["before"] = before
    report["after"] = after
    # true mesh AABB after ops
    xs = [v.co.x for v in main.data.vertices]
    ys = [v.co.y for v in main.data.vertices]
    zs = [v.co.z for v in main.data.vertices]
    report["aabb"] = {{
        "x": max(xs) - min(xs),
        "y": max(ys) - min(ys),
        "z": max(zs) - min(zs),
    }}

    # studio setup
    for o in list(bpy.data.objects):
        if o.type in {{"CAMERA", "LIGHT"}}:
            bpy.data.objects.remove(o, do_unlink=True)

    def add_light(ltype, loc, energy, size=None):
        data = bpy.data.lights.new(name=ltype + str(loc[0]), type=ltype)
        data.energy = energy
        if size is not None and hasattr(data, "size"):
            data.size = size
        obj = bpy.data.objects.new(data.name, data)
        obj.location = loc
        bpy.context.scene.collection.objects.link(obj)

    add_light("AREA", (2.5, -2.0, 3.0), 400, 3.0)
    add_light("AREA", (-2.5, 2.0, 2.0), 150, 4.0)
    add_light("SUN", (0, 0, 5), 2.0)

    cam_data = bpy.data.cameras.new("ReviewCam")
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.95, 0.95, 0.97, 1.0)
        bg.inputs[1].default_value = 1.0

    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except Exception:
            continue
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1280
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"

    def frame_cam(az_deg, elev=8.0, dist=3.0):
        bpy.context.view_layer.update()
        bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
        center = sum(bb, Vector()) / 8.0
        center.z = max(0.75, center.z)
        az = math.radians(az_deg)
        el = math.radians(elev)
        loc = Vector((
            center.x + dist * math.cos(el) * math.sin(az),
            center.y - dist * math.cos(el) * math.cos(az),
            center.z + dist * math.sin(el),
        ))
        cam.location = loc
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def render_to(path, az):
        frame_cam(az)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)

    render_to(paths["r_front"], 0)
    render_to(paths["r_side"], 90)
    render_to(paths["r_back"], 180)
    render_to(paths["r_3q"], 35)
    frame_cam(35)

    for o in bpy.data.objects:
        o.select_set(o == main)
    try:
        bpy.context.view_layer.objects.active = main
    except Exception:
        pass
    bpy.ops.export_scene.gltf(
        filepath=paths["glb_out"],
        use_selection=True,
        export_format="GLB",
        export_apply=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=paths["blend_out"])

    report["status"] = "ok"
    report["object"] = main.name
    report["glb_out"] = paths["glb_out"]
    report["blend_out"] = paths["blend_out"]
    result = report
'''

    res = exec_blender_code(code)
    print(res if isinstance(res, str) else __import__("json").dumps(res, indent=2, ensure_ascii=False))
    payload = res.get("result") if isinstance(res.get("result"), dict) else res
    if payload.get("status") != "ok":
        return 2

    if BLEND_OUT.is_file():
        shutil.copyfile(BLEND_OUT, BLEND_MAIN)

    for p in (
        BLEND_OUT,
        GLB_OUT,
        EXPORTS / "viewport_clean_front.png",
        EXPORTS / "viewport_clean_side.png",
        EXPORTS / "viewport_clean_back.png",
        EXPORTS / "viewport_clean_3q.png",
    ):
        print(("OK" if p.is_file() else "MISS"), p.name, p.stat().st_size if p.is_file() else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
