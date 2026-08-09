"""Blender-side mesh ops driven via MCP — clean / light auto-rig / VRM export.

Requires running Blender with VRM addon for export_mesh_vrm.
Auto-rig is **basic** (ARMATURE_AUTO) — good enough for prototype avatars,
not production game humanoid retarget quality.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from lib.blender_mcp import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    exec_blender_code,
    probe_blender,
    unwrap_result,
)


def _py_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")


def process_mesh_glb(
    *,
    input_glb: str,
    output_glb: str,
    clean: bool = True,
    auto_rig: bool = False,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 180.0,
) -> dict[str, Any]:
    """Import GLB → optional clean → optional ARMATURE_AUTO → export GLB."""
    src = Path(input_glb).expanduser().resolve()
    dst = Path(output_glb).expanduser().resolve()
    if not src.is_file():
        return {"ok": False, "error": "MISSING_INPUT", "message": str(src)}
    if dst.suffix.lower() != ".glb":
        dst = dst.with_suffix(".glb")
    dst.parent.mkdir(parents=True, exist_ok=True)

    probe = probe_blender(host=host, port=port)
    if not probe.get("ok"):
        return {
            "ok": False,
            "error": "BLENDER_OFFLINE",
            "message": probe.get("message")
            or "Start Blender with MCP server (default port 9876)",
        }

    tmp = Path(tempfile.gettempdir()) / f"agent_mesh_{int(time.time())}.glb"
    code = f'''
import bpy
import bmesh
from mathutils import Vector

src = r"{_py_path(src)}"
tmp = r"{_py_path(tmp)}"
do_clean = {str(bool(clean))}
do_rig = {str(bool(auto_rig))}

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.armatures):
    bpy.data.armatures.remove(block)

bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    result = {{"status": "error", "message": "no mesh after import"}}
else:
    # join multi-mesh imports
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    main = bpy.context.view_layer.objects.active
    main.name = "Body"
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    main.location = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if do_clean:
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(main.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(main.data)
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            bpy.ops.mesh.dissolve_degenerate(threshold=1e-4)
        except Exception:
            pass
        try:
            bpy.ops.mesh.fill_holes(sides=0)
        except Exception:
            pass
        bpy.ops.object.mode_set(mode="OBJECT")
        for poly in main.data.polygons:
            poly.use_smooth = True

    arm_name = None
    if do_rig:
        bpy.ops.object.armature_add(enter_editmode=False, location=(0, 0, 0))
        arm = bpy.context.active_object
        arm.name = "Armature"
        arm_name = arm.name
        bpy.ops.object.select_all(action="DESELECT")
        main.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        if not main.data.shape_keys:
            main.shape_key_add(name="Basis", from_mix=False)
        for key_name in ("A", "I", "U", "E", "O", "Blink", "Joy", "Angry", "Sorrow", "Fun"):
            if key_name not in main.data.shape_keys.key_blocks:
                main.shape_key_add(name=key_name, from_mix=False)

    bpy.ops.object.select_all(action="DESELECT")
    main.select_set(True)
    if arm_name:
        arm = bpy.data.objects.get(arm_name)
        if arm:
            arm.select_set(True)
            bpy.context.view_layer.objects.active = arm
        else:
            bpy.context.view_layer.objects.active = main
    else:
        bpy.context.view_layer.objects.active = main

    bpy.ops.export_scene.gltf(
        filepath=tmp,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_skins=True,
        export_morph=True,
    )
    result = {{
        "status": "ok",
        "mesh": main.name,
        "verts": len(main.data.vertices),
        "faces": len(main.data.polygons),
        "armature": arm_name,
        "tmp": tmp,
    }}
'''
    try:
        raw = exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
    except Exception as e:
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)}

    payload = unwrap_result(raw)
    if payload.get("status") != "ok":
        return {
            "ok": False,
            "error": "PROCESS_FAIL",
            "message": payload.get("message") or str(payload)[:500],
            "detail": payload,
        }
    if not tmp.is_file():
        return {"ok": False, "error": "NO_TMP", "message": f"missing {tmp}"}
    shutil.copy2(tmp, dst)
    try:
        tmp.unlink(missing_ok=True)  # type: ignore[arg-type]
    except Exception:
        pass
    return {
        "ok": True,
        "output_path": str(dst),
        "mesh": payload.get("mesh"),
        "verts": payload.get("verts"),
        "faces": payload.get("faces"),
        "armature": payload.get("armature"),
        "bytes": dst.stat().st_size,
    }


def export_mesh_vrm(
    *,
    input_path: str,
    output_vrm: str,
    auto_rig_if_missing: bool = True,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 240.0,
) -> dict[str, Any]:
    """GLB/blend → VRM via Blender VRM addon (export_scene.vrm)."""
    src = Path(input_path).expanduser().resolve()
    dst = Path(output_vrm).expanduser().resolve()
    if not src.is_file():
        return {"ok": False, "error": "MISSING_INPUT", "message": str(src)}
    if dst.suffix.lower() != ".vrm":
        dst = dst.with_suffix(".vrm")
    dst.parent.mkdir(parents=True, exist_ok=True)

    probe = probe_blender(host=host, port=port)
    if not probe.get("ok"):
        return {
            "ok": False,
            "error": "BLENDER_OFFLINE",
            "message": probe.get("message")
            or "Start Blender with MCP server (default port 9876)",
        }

    tmp_vrm = Path(tempfile.gettempdir()) / f"agent_export_{int(time.time())}.vrm"
    tmp_glb = Path(tempfile.gettempdir()) / f"agent_export_{int(time.time())}.glb"
    ext = src.suffix.lower()

    code = f'''
import bpy
import addon_utils

src = r"{_py_path(src)}"
tmp_vrm = r"{_py_path(tmp_vrm)}"
tmp_glb = r"{_py_path(tmp_glb)}"
auto_rig = {str(bool(auto_rig_if_missing))}
ext = "{ext}"

for name in ["bl_ext.user_default.vrm", "vrm", "VRM_Addon_for_Blender"]:
    try:
        addon_utils.enable(name, default_set=True, persistent=True)
    except Exception:
        pass

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

if ext == ".blend":
    bpy.ops.wm.open_mainfile(filepath=src)
else:
    bpy.ops.import_scene.gltf(filepath=src)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not meshes:
    result = {{"status": "error", "message": "no mesh"}}
else:
    main = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        main = bpy.context.view_layer.objects.active
        main.name = "Body"

    arm = arms[0] if arms else None
    if arm is None and auto_rig:
        bpy.ops.object.armature_add(enter_editmode=False, location=(0, 0, 0))
        arm = bpy.context.active_object
        arm.name = "Armature"
        bpy.ops.object.select_all(action="DESELECT")
        main.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    bpy.ops.object.select_all(action="DESELECT")
    main.select_set(True)
    selected = [main]
    if arm:
        arm.hide_set(False)
        arm.select_set(True)
        selected.append(arm)
        bpy.context.view_layer.objects.active = arm
    else:
        bpy.context.view_layer.objects.active = main

    window = bpy.context.window_manager.windows[0]
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), window.screen.areas[0])
    region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

    glb_ok = False
    glb_err = ""
    with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=bpy.context.view_layer.objects.active, selected_objects=selected):
        try:
            bpy.ops.export_scene.gltf(filepath=tmp_glb, export_format="GLB", use_selection=True, export_apply=True, export_skins=True)
            glb_ok = True
        except Exception as e:
            glb_err = str(e)

    vrm_ok = False
    vrm_err = ""
    if hasattr(bpy.ops.export_scene, "vrm"):
        with bpy.context.temp_override(window=window, area=area, region=region, scene=bpy.context.scene, active_object=bpy.context.view_layer.objects.active, selected_objects=selected):
            try:
                bpy.ops.export_scene.vrm(filepath=tmp_vrm)
                vrm_ok = True
            except Exception as e:
                vrm_err = str(e)
    else:
        vrm_err = "export_scene.vrm missing — enable VRM addon for Blender"

    result = {{
        "status": "ok" if vrm_ok else "error",
        "mesh": main.name,
        "armature": arm.name if arm else None,
        "verts": len(main.data.vertices),
        "faces": len(main.data.polygons),
        "glb_ok": glb_ok,
        "glb_err": glb_err,
        "vrm_ok": vrm_ok,
        "vrm_err": vrm_err,
    }}
'''
    try:
        raw = exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
    except Exception as e:
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)}

    payload = unwrap_result(raw)
    if payload.get("status") != "ok" or not tmp_vrm.is_file():
        return {
            "ok": False,
            "error": "VRM_FAIL",
            "message": payload.get("vrm_err")
            or payload.get("message")
            or "VRM export failed",
            "detail": payload,
        }
    shutil.copy2(tmp_vrm, dst)
    sidecar_glb = None
    if tmp_glb.is_file():
        sidecar_glb = dst.with_suffix(".glb")
        shutil.copy2(tmp_glb, sidecar_glb)
    for p in (tmp_vrm, tmp_glb):
        try:
            p.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
    return {
        "ok": True,
        "output_path": str(dst),
        "sidecar_glb": str(sidecar_glb) if sidecar_glb else None,
        "mesh": payload.get("mesh"),
        "armature": payload.get("armature"),
        "verts": payload.get("verts"),
        "faces": payload.get("faces"),
        "bytes": dst.stat().st_size,
        "note": "Auto-rig is basic ARMATURE_AUTO — fine for prototype, not final Warudo humanoid QA.",
    }
