"""Blender MCP previz plates — block geometry + camera path → MP4.

Requires Blender 5.x with MCP addon listening (default 127.0.0.1:9876).
Does not call Comfy. H3 consumes the MP4 via generate_minimax_h3 --ref-video.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from lib.blender_mcp import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    exec_blender_code,
    probe_blender,
    unwrap_result,
)

FPS = 24
DEFAULT_SECONDS = 5.0
MAX_SECONDS = 15.0
CLIP_START = 0.1
CLIP_START_MAX = 0.15
COLOR_TOL = 0.18

# Proxy color = role. H3 maps hero orange (or prop green) to <Picture 1>.
ROLE_COLORS: dict[str, tuple[float, float, float]] = {
    "hero": (1.0, 0.38, 0.05),
    "extra": (0.12, 0.42, 0.95),
    "prop": (0.08, 0.72, 0.42),
    "set": (0.55, 0.55, 0.58),
    "floor": (0.22, 0.22, 0.24),
    "mark": (0.85, 0.78, 0.22),
}

SET_NAME_PREFIXES = ("wall", "floor", "ceil", "mark", "ground", "set")
HERO_NAME_PREFIXES = ("hero",)
PROP_NAME_PREFIXES = ("prop", "ball", "vehicle", "bike", "car", "object")
EXTRA_NAME_PREFIXES = ("extra", "crowd", "npc")

# Camera x must stay inside corridor walls at ±2.3.
PRESETS: dict[str, dict[str, Any]] = {
    "corridor_follow": {
        "summary": "Gray corridor; orange block walks +Y; camera behind → 3/4 (inside walls) → closer",
        "scene": "corridor",
        "hero_walk": True,
        "cam_fracs": [
            (0.0, (0.0, -11.8, 1.9)),
            (0.33, (1.05, -5.5, 1.95)),
            (0.67, (1.10, 1.2, 1.90)),
            (1.0, (0.25, 5.0, 1.70)),
        ],
    },
    "push_in": {
        "summary": "Open pad; static block; camera dollies in",
        "scene": "pad",
        "hero_walk": False,
        "cam_fracs": [
            (0.0, (0.0, -8.0, 1.7)),
            (1.0, (0.0, -2.8, 1.55)),
        ],
    },
    "orbit": {
        "summary": "Open pad; static block; camera 90° orbit at safe radius",
        "scene": "pad",
        "hero_walk": False,
        "cam_fracs": [
            (0.0, (0.0, -6.0, 1.8)),
            (0.5, (6.0, 0.0, 1.9)),
            (1.0, (0.0, 6.0, 1.8)),
        ],
    },
    "side_track": {
        "summary": "Corridor; block walks +Y; camera tracks from left, stays inside walls",
        "scene": "corridor",
        "hero_walk": True,
        "cam_fracs": [
            (0.0, (1.05, -11.0, 1.8)),
            (1.0, (1.05, 5.0, 1.8)),
        ],
    },
}


def list_presets() -> dict[str, str]:
    return {k: str(v["summary"]) for k, v in PRESETS.items()}


def nearest_role(rgb: tuple[float, float, float] | list[float] | None) -> str | None:
    if rgb is None or len(rgb) < 3:
        return None
    best: str | None = None
    best_d = 1e9
    r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
    for name, col in ROLE_COLORS.items():
        d = ((r - col[0]) ** 2 + (g - col[1]) ** 2 + (b - col[2]) ** 2) ** 0.5
        if d < best_d:
            best, best_d = name, d
    if best_d > COLOR_TOL:
        return None
    return best


def evaluate_plate_qa(
    report: dict[str, Any],
    *,
    required_camera: str | None = None,
    hero: str = "character",
) -> dict[str, Any]:
    """Judge a Blender inspect payload. No Blender needed."""
    qa = report.get("qa") if isinstance(report.get("qa"), dict) else report
    errors: list[str] = []
    cameras = list(qa.get("cameras") or [])
    cam_names = [str(c.get("name")) for c in cameras if c.get("name")]
    if not cam_names:
        errors.append("NO_CAMERA: scene has no camera")
    elif not qa.get("active_camera"):
        errors.append("NO_CAMERA: scene.camera is unset")
    if required_camera and required_camera not in cam_names:
        errors.append(f"CAMERA_MISSING: {required_camera!r} not in {cam_names}")
    active = qa.get("active_camera")
    if required_camera and active and active != required_camera:
        errors.append(
            f"CAMERA_NOT_ACTIVE: active={active!r} required={required_camera!r}"
        )

    for cam in cameras:
        name = cam.get("name") or "?"
        clip = cam.get("clip_start")
        if clip is not None and float(clip) > CLIP_START_MAX:
            errors.append(
                f"CLIP_START: {name} clip_start={clip} (need <= {CLIP_START_MAX})"
            )
        cons = list(cam.get("constraints") or [])
        if cons:
            errors.append(f"CAMERA_CONSTRAINED: {name} still has {cons}")
        inside = list(cam.get("inside_meshes") or [])
        if inside:
            errors.append(f"CAMERA_INSIDE_GEO: {name} inside {inside}")
        if cam.get("outside_corridor"):
            errors.append(f"CAMERA_OUTSIDE_SET: {name} x is not between walls")

    meshes = list(qa.get("meshes") or [])
    for mesh in meshes:
        if mesh.get("role") is None and mesh.get("color"):
            mesh["role"] = nearest_role(mesh.get("color"))
    heroes = [m for m in meshes if m.get("role") == "hero"]
    props = [m for m in meshes if m.get("role") == "prop"]
    want_object = hero == "object"
    if want_object:
        if len(heroes) > 1:
            errors.append(
                f"HERO_COLOR: object plate expected 0–1 hero mesh, got {len(heroes)}"
            )
        if len(heroes) == 0 and len(props) < 1:
            errors.append("HERO_COLOR: object plate needs one prop-green proxy")
    elif len(heroes) != 1:
        names = [m.get("name") for m in heroes]
        errors.append(
            f"HERO_COLOR: expected 1 hero-orange mesh, got {len(heroes)} {names}"
        )

    for mesh in meshes:
        name = str(mesh.get("name") or "")
        role = mesh.get("role")
        lower = name.lower()
        if role == "hero" and not lower.startswith(HERO_NAME_PREFIXES):
            errors.append(f"COLOR_COLLISION: {name} wears hero orange but is not Hero*")
        if role == "extra" and not lower.startswith(EXTRA_NAME_PREFIXES):
            errors.append(
                f"COLOR_COLLISION: {name} wears extra blue; extras Extra*/Crowd*/Npc*"
            )
        if role in ("hero", "extra", "prop") and lower.startswith(SET_NAME_PREFIXES):
            errors.append(f"COLOR_COLLISION: set mesh {name} wears {role} color")

    return {"ok": not errors, "errors": errors, "report": qa}


def _py_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")


def _frame_count(seconds: float) -> int:
    sec = max(1.0, min(float(seconds), MAX_SECONDS))
    return max(24, int(round(sec * FPS)))


def _blender_exec(
    code: str,
    *,
    host: str,
    port: int,
    timeout_sec: float,
) -> dict[str, Any]:
    try:
        payload = unwrap_result(
            exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
        )
    except Exception as e:
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)[:800]}
    if isinstance(payload, dict) and payload.get("status") == "error":
        return {
            "ok": False,
            "error": str(payload.get("error") or "RENDER_FAIL"),
            "message": str(payload.get("message") or payload)[:800],
            "payload": payload,
        }
    return {"ok": True, "payload": payload if isinstance(payload, dict) else {"raw": payload}}


def _qa_fail(
    payload: dict[str, Any],
    *,
    required_camera: str | None,
    hero: str,
) -> dict[str, Any] | None:
    qa = evaluate_plate_qa(payload, required_camera=required_camera, hero=hero)
    if qa["ok"]:
        return None
    return {
        "ok": False,
        "error": "PLATE_QA",
        "message": "; ".join(qa["errors"]),
        "qa": qa,
    }


def _prepare_inspect_bpy(
    *,
    camera_name: str | None,
) -> str:
    cam_lit = repr(camera_name)
    colors_lit = repr({k: tuple(v) for k, v in ROLE_COLORS.items()})
    return f'''
ROLE_COLORS = {colors_lit}
CLIP_START = {CLIP_START}
_req_cam = {cam_lit}

def _base_color(obj):
    mats = getattr(obj.data, "materials", None)
    if not mats or mats[0] is None:
        return None
    mat = mats[0]
    if not mat.use_nodes or mat.node_tree is None:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return None
    c = bsdf.inputs["Base Color"].default_value
    return (float(c[0]), float(c[1]), float(c[2]))

def _nearest_role(rgb):
    best, best_d = None, 1e9
    for name, col in ROLE_COLORS.items():
        d = ((rgb[0]-col[0])**2 + (rgb[1]-col[1])**2 + (rgb[2]-col[2])**2) ** 0.5
        if d < best_d:
            best, best_d = name, d
    if best_d > {COLOR_TOL}:
        return None
    return best

def _world_aabb(obj):
    from mathutils import Vector
    matw = obj.matrix_world
    pts = [matw @ Vector(c) for c in obj.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def _inside_aabb(pt, aabb, inset=0.05):
    return (aabb[0]+inset < pt.x < aabb[1]-inset and
            aabb[2]+inset < pt.y < aabb[3]-inset and
            aabb[4]+inset < pt.z < aabb[5]-inset)

_prep_error = None
if _req_cam:
    obj = bpy.data.objects.get(_req_cam)
    if obj is None or obj.type != "CAMERA":
        _prep_error = {{
            "status": "error",
            "error": "CAMERA_MISSING",
            "message": "no camera named " + repr(_req_cam),
        }}
    else:
        scn.camera = obj

if _prep_error is not None:
    result = _prep_error
else:
    start, end = int(scn.frame_start), int(scn.frame_end)
    for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        if cam.constraints:
            for f in range(start, end + 1):
                scn.frame_set(f)
                bpy.context.view_layer.update()
                mw = cam.matrix_world.copy()
                cam.location = mw.to_translation()
                cam.rotation_euler = mw.to_euler(cam.rotation_mode)
                cam.keyframe_insert("location", frame=f)
                cam.keyframe_insert("rotation_euler", frame=f)
            for cnst in list(cam.constraints):
                cam.constraints.remove(cnst)
        if cam.data:
            cam.data.clip_start = CLIP_START
            if cam.data.clip_end < 250.0:
                cam.data.clip_end = 1000.0
    scn.frame_set(start)
    wall_xs = [o.matrix_world.translation.x for o in bpy.data.objects if o.name.startswith("Wall_")]
    qa_cameras = []
    for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        loc = cam.matrix_world.translation
        inside = []
        for mesh in [o for o in bpy.data.objects if o.type == "MESH"]:
            if _inside_aabb(loc, _world_aabb(mesh)):
                inside.append(mesh.name)
        outside = False
        if len(wall_xs) >= 2:
            lo, hi = min(wall_xs), max(wall_xs)
            if not (lo + 0.2 < loc.x < hi - 0.2):
                outside = True
        qa_cameras.append({{
            "name": cam.name,
            "clip_start": float(cam.data.clip_start) if cam.data else None,
            "constraints": [c.type for c in cam.constraints],
            "location": [float(loc.x), float(loc.y), float(loc.z)],
            "inside_meshes": inside,
            "outside_corridor": outside,
        }})
    meshes_info = []
    for mesh in [o for o in bpy.data.objects if o.type == "MESH"]:
        rgb = _base_color(mesh)
        meshes_info.append({{
            "name": mesh.name,
            "role": _nearest_role(rgb) if rgb else None,
            "color": list(rgb) if rgb else None,
        }})
    qa_report = {{
        "cameras": qa_cameras,
        "active_camera": scn.camera.name if scn.camera else None,
        "meshes": meshes_info,
    }}
    result = {{
        "status": "ok",
        "qa": qa_report,
        "nframes": int(scn.frame_end) - int(scn.frame_start) + 1,
        "camera": scn.camera.name if scn.camera else None,
        "cameras": [c["name"] for c in qa_cameras],
        "objects": len(bpy.data.objects),
        "blend": None,
    }}
'''


def list_scene_cameras(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    offline = _blender_offline(host, port)
    if offline:
        return offline
    code = """
import bpy
cams = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
active = bpy.context.scene.camera.name if bpy.context.scene.camera else None
result = {"status": "ok", "cameras": cams, "active": active}
"""
    ran = _blender_exec(code, host=host, port=port, timeout_sec=timeout_sec)
    if not ran.get("ok"):
        return ran
    payload = ran["payload"]
    return {
        "ok": True,
        "cameras": list(payload.get("cameras") or []),
        "active": payload.get("active"),
    }


def render_previz(
    *,
    preset: str,
    output_mp4: str,
    seconds: float = DEFAULT_SECONDS,
    width: int = 1280,
    height: int = 720,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 300.0,
    camera: str | None = None,
    save_blend: str | None = None,
    hero: str = "character",
) -> dict[str, Any]:
    """Build a block previz in the live Blender session and mux an MP4."""
    spec = PRESETS.get(preset)
    if spec is None:
        return {
            "ok": False,
            "error": "UNKNOWN_PRESET",
            "message": f"unknown preset {preset!r}. --list-presets",
        }

    offline = _blender_offline(host, port)
    if offline:
        return offline

    nframes = _frame_count(seconds)

    cam_keys: list[tuple[int, tuple[float, float, float]]] = []
    for frac, loc in spec["cam_fracs"]:
        fr = 1 if frac <= 0 else nframes if frac >= 1 else 1 + int(round(frac * (nframes - 1)))
        cam_keys.append((fr, (float(loc[0]), float(loc[1]), float(loc[2]))))

    hero_walk = bool(spec["hero_walk"])
    scene = spec["scene"]
    cam_literal = repr(cam_keys)

    c_floor = ROLE_COLORS["floor"]
    c_set = ROLE_COLORS["set"]
    c_hero = ROLE_COLORS["hero"]
    c_mark = ROLE_COLORS["mark"]

    code = f'''
import bpy
from mathutils import Vector

nframes = {nframes}
hero_walk = {str(hero_walk)}
scene_kind = {scene!r}
cam_keys = {cam_literal}

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.actions):
    for block in list(coll):
        coll.remove(block)

scn = bpy.context.scene
scn.frame_start = 1
scn.frame_end = nframes
scn.render.fps = {FPS}


def new_mat(name, color, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def add_cube(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


mat_floor = new_mat("PrevizFloor", {c_floor!r})
mat_wall = new_mat("PrevizWall", {c_set!r})
mat_hero = new_mat("PrevizHero", {c_hero!r}, emission=0.35)
mat_mark = new_mat("PrevizMark", {c_mark!r}, emission=0.2)

if scene_kind == "corridor":
    add_cube("Floor", (0, 0, -0.1), (2.2, 12.0, 0.1), mat_floor)
    add_cube("Wall_L", (-2.3, 0, 1.6), (0.15, 12.0, 1.6), mat_wall)
    add_cube("Wall_R", (2.3, 0, 1.6), (0.15, 12.0, 1.6), mat_wall)
    add_cube("Ceil", (0, 0, 3.25), (2.4, 12.0, 0.08), mat_wall)
    add_cube("Mark_Start", (0, -8.0, 0.05), (0.4, 0.4, 0.05), mat_mark)
    add_cube("Mark_End", (0, 8.0, 0.05), (0.4, 0.4, 0.05), mat_mark)
else:
    add_cube("Floor", (0, 0, -0.1), (8.0, 8.0, 0.1), mat_floor)
    add_cube("Mark_Start", (0, 0, 0.05), (0.5, 0.5, 0.05), mat_mark)

hero = add_cube("Hero", (0, -8.0 if hero_walk else 0.0, 0.9), (0.35, 0.35, 0.9), mat_hero)
if hero_walk:
    hero.keyframe_insert("location", frame=1)
    hero.location = Vector((0, 8.0, 0.9))
    hero.keyframe_insert("location", frame=nframes)

bpy.ops.object.light_add(type="SUN", location=(4, -6, 8))
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.energy = 3.0
sun.rotation_euler = (0.6, 0.2, 0.4)

bpy.ops.object.camera_add(location=cam_keys[0][1])
cam = bpy.context.active_object
cam.name = "PrevizCam"
cam.data.lens = 35
cam.data.clip_start = {CLIP_START}
scn.camera = cam
track = cam.constraints.new("TRACK_TO")
track.target = hero
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
for fr, loc in cam_keys:
    cam.location = Vector(loc)
    cam.keyframe_insert("location", frame=fr)

result = {{"status": "ok", "built": True, "nframes": nframes}}
'''

    ran = _blender_exec(code, host=host, port=port, timeout_sec=timeout_sec)
    if not ran.get("ok"):
        return ran

    out = render_open_scene(
        output_mp4=output_mp4,
        seconds=seconds,
        width=width,
        height=height,
        host=host,
        port=port,
        timeout_sec=timeout_sec,
        camera=camera,
        save_blend=save_blend,
        hero=hero,
    )
    if out.get("ok"):
        out["preset"] = preset
    return out


def _blender_offline(host: str, port: int) -> dict[str, Any] | None:
    probe = probe_blender(host=host, port=port)
    if probe.get("ok"):
        return None
    return {
        "ok": False,
        "error": "BLENDER_OFFLINE",
        "message": probe.get("message")
        or "Start Blender with MCP addon (default port 9876, Allow Online Access)",
        "probe": probe,
    }


def _prepare_mp4(output_mp4: str) -> Path:
    dst = Path(output_mp4).expanduser().resolve()
    if dst.suffix.lower() != ".mp4":
        dst = dst.with_suffix(".mp4")
    dst.parent.mkdir(parents=True, exist_ok=True)
    return dst


def _mux_pngs_to_mp4(tmp: Path, dst: Path) -> dict[str, Any] | None:
    """FFmpeg mux. Return an error dict, or None if the mp4 is usable."""
    pattern = str(tmp / "frame_%04d.png")
    ff = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            str(dst),
        ],
        capture_output=True,
        text=True,
    )
    if ff.returncode != 0 or not dst.is_file() or dst.stat().st_size < 10_000:
        return {
            "ok": False,
            "error": "FFMPEG",
            "message": (ff.stderr or ff.stdout or "mux failed")[-1200:],
        }
    return None


def render_open_scene(
    *,
    output_mp4: str,
    seconds: float | None = None,
    width: int = 1280,
    height: int = 720,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 300.0,
    camera: str | None = None,
    save_blend: str | None = None,
    hero: str = "character",
) -> dict[str, Any]:
    """Playblast the live Blender scene. Does not wipe objects.

    Bakes camera constraints, sets clip_start, then plate-QA. Fail closed
    on color collision, camera-in-geo, or clip. Optional --camera / --save-blend.
    """
    offline = _blender_offline(host, port)
    if offline:
        return offline

    dst = _prepare_mp4(output_mp4)
    blend_path = None
    if save_blend:
        blend_path = Path(save_blend).expanduser().resolve()
        if blend_path.suffix.lower() != ".blend":
            blend_path = blend_path.with_suffix(".blend")
        blend_path.parent.mkdir(parents=True, exist_ok=True)

    nframes_lit = "None" if seconds is None else str(_frame_count(seconds))
    prep = f'''
import bpy
scn = bpy.context.scene
nframes = {nframes_lit}
if nframes is None:
    start = int(scn.frame_start)
    end = int(scn.frame_end)
    if end < start:
        end = start
    max_frames = {int(MAX_SECONDS * FPS)}
    if (end - start + 1) > max_frames:
        end = start + max_frames - 1
    scn.frame_start = start
    scn.frame_end = end
    nframes = end - start + 1
else:
    scn.frame_start = 1
    scn.frame_end = nframes
'''
    prep += _prepare_inspect_bpy(camera_name=camera)

    ran = _blender_exec(prep, host=host, port=port, timeout_sec=timeout_sec)
    if not ran.get("ok"):
        return ran
    payload = ran["payload"]
    qa_err = _qa_fail(payload, required_camera=camera, hero=hero)
    if qa_err:
        return qa_err

    if blend_path:
        save_code = f'''
import bpy
bpy.ops.wm.save_as_mainfile(filepath={_py_path(blend_path)!r}, copy=True)
result = {{"status": "ok", "blend": {_py_path(blend_path)!r}}}
'''
        saved = _blender_exec(save_code, host=host, port=port, timeout_sec=timeout_sec)
        if not saved.get("ok"):
            return saved
        payload["blend"] = _py_path(blend_path)

    tmp = Path(tempfile.mkdtemp(prefix="previz_"))
    prefix_s = _py_path(tmp / "frame_")
    render_code = f'''
import bpy
import glob

scn = bpy.context.scene
if scn.camera is None:
    result = {{"status": "error", "message": "no scene camera — set Camera or bpy.context.scene.camera"}}
else:
    nframes = int(scn.frame_end) - int(scn.frame_start) + 1
    scn.render.fps = {FPS}
    scn.render.resolution_x = {int(width)}
    scn.render.resolution_y = {int(height)}
    scn.render.resolution_percentage = 100
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.film_transparent = False
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.filepath = r"{prefix_s}"
    if hasattr(scn.view_settings, "view_transform"):
        scn.view_settings.view_transform = "Standard"
    bpy.ops.render.render(animation=True)
    pngs = sorted(glob.glob(r"{prefix_s}" + "*.png"))
    result = {{
        "status": "ok" if len(pngs) >= nframes else "error",
        "png_count": len(pngs),
        "nframes": nframes,
        "camera": scn.camera.name,
        "objects": len(bpy.data.objects),
    }}
'''

    ran2 = _blender_exec(render_code, host=host, port=port, timeout_sec=timeout_sec)
    if not ran2.get("ok"):
        shutil.rmtree(tmp, ignore_errors=True)
        return ran2
    payload2 = ran2["payload"]

    muxed = _mux_pngs_to_mp4(tmp, dst)
    shutil.rmtree(tmp, ignore_errors=True)
    if muxed is not None:
        return muxed

    nframes = int(payload2.get("nframes") or payload.get("nframes") or 0)
    return {
        "ok": True,
        "output": str(dst),
        "preset": "open_scene",
        "frames": nframes,
        "seconds": nframes / FPS if nframes else 0.0,
        "bytes": dst.stat().st_size,
        "camera": payload2.get("camera") or payload.get("camera"),
        "cameras": payload.get("cameras"),
        "objects": payload2.get("objects") or payload.get("objects"),
        "blend": payload.get("blend"),
        "qa": payload.get("qa"),
    }


def exec_then_render(
    *,
    code: str,
    output_mp4: str,
    seconds: float | None = DEFAULT_SECONDS,
    width: int = 1280,
    height: int = 720,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 300.0,
    camera: str | None = None,
    save_blend: str | None = None,
    hero: str = "character",
) -> dict[str, Any]:
    """Run agent bpy in the live session, then playblast. Does not wipe first."""
    offline = _blender_offline(host, port)
    if offline:
        return offline

    colors = {k: tuple(v) for k, v in ROLE_COLORS.items()}
    bootstrap = f"PREVIZ_COLORS = {colors!r}\nPREVIZ_CLIP_START = {CLIP_START}\n"
    wrapped = (
        bootstrap
        + code.rstrip()
        + "\n\nif 'result' not in globals():\n    result = {'status': 'ok'}\n"
    )
    ran = _blender_exec(wrapped, host=host, port=port, timeout_sec=timeout_sec)
    if not ran.get("ok"):
        ran["error"] = "BUILD_FAIL" if ran.get("error") != "BLENDER_EXEC" else ran["error"]
        return ran

    return render_open_scene(
        output_mp4=output_mp4,
        seconds=seconds,
        width=width,
        height=height,
        host=host,
        port=port,
        timeout_sec=timeout_sec,
        camera=camera,
        save_blend=save_blend,
        hero=hero,
    )


H3_R2V_PROMPT = """\
subject_definitions: <Subject 1> is the person in <Picture 1>; preserve face, hair, outfit.
summary: [video editing] Replace the orange block performer in <Video 1> with Subject 1; keep camera, pacing, and environment.
retention_analysis: <Video 1> fully_preserved - camera path, timing, environment. <Subject 1> fully_preserved - identity.
detailed_description: [Shot 1] Photoreal cinematic. Subject 1 performs the same action chain as <Video 1>. The orange block in <Video 1> is Subject 1. Camera follows the plate path, always tracking Subject 1. One continuous take, no cut.
overall_soundscape: quiet indoor ambience, footsteps on hard floor
non_diegetic_music: N/A
"""

H3_R2V_PROMPT_OBJECT = """\
subject_definitions: <Subject 1> is the object in <Picture 1>; preserve silhouette, materials, and scale.
summary: [video editing] Replace the previz proxy in <Video 1> with Subject 1; keep camera, pacing, and environment.
retention_analysis: <Video 1> fully_preserved - camera path, timing, environment. <Subject 1> fully_preserved - object identity.
detailed_description: [Shot 1] Photoreal cinematic. Subject 1 follows the same path and timing as the proxy in <Video 1>. Camera follows the plate path. One continuous take, no cut.
overall_soundscape: match the physical action sounds of <Video 1>
non_diegetic_music: N/A
"""


def h3_r2v_prompt(hero: str = "character") -> str:
    if hero == "object":
        return H3_R2V_PROMPT_OBJECT
    return H3_R2V_PROMPT
