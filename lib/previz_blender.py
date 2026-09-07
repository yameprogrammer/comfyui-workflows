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


def _py_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")


def _frame_count(seconds: float) -> int:
    sec = max(1.0, min(float(seconds), MAX_SECONDS))
    return max(24, int(round(sec * FPS)))


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
) -> dict[str, Any]:
    """Build a block previz in the live Blender session and mux an MP4."""
    spec = PRESETS.get(preset)
    if spec is None:
        return {
            "ok": False,
            "error": "UNKNOWN_PRESET",
            "message": f"unknown preset {preset!r}. --list-presets",
        }

    probe = probe_blender(host=host, port=port)
    if not probe.get("ok"):
        return {
            "ok": False,
            "error": "BLENDER_OFFLINE",
            "message": probe.get("message")
            or "Start Blender with MCP addon (default port 9876, Allow Online Access)",
        }

    dst = Path(output_mp4).expanduser().resolve()
    if dst.suffix.lower() != ".mp4":
        dst = dst.with_suffix(".mp4")
    dst.parent.mkdir(parents=True, exist_ok=True)

    nframes = _frame_count(seconds)
    tmp = Path(tempfile.mkdtemp(prefix="previz_"))
    prefix = tmp / "frame_"
    prefix_s = _py_path(prefix)

    cam_keys: list[tuple[int, tuple[float, float, float]]] = []
    for frac, loc in spec["cam_fracs"]:
        fr = 1 if frac <= 0 else nframes if frac >= 1 else 1 + int(round(frac * (nframes - 1)))
        cam_keys.append((fr, (float(loc[0]), float(loc[1]), float(loc[2]))))

    hero_walk = bool(spec["hero_walk"])
    scene = spec["scene"]
    cam_literal = repr(cam_keys)

    code = f'''
import bpy
from mathutils import Vector

out_prefix = r"{prefix_s}"
nframes = {nframes}
width = {int(width)}
height = {int(height)}
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
scn.render.resolution_x = width
scn.render.resolution_y = height
scn.render.resolution_percentage = 100
scn.render.engine = "BLENDER_EEVEE"
scn.render.film_transparent = False
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGB"
scn.render.filepath = out_prefix
if hasattr(scn.view_settings, "view_transform"):
    scn.view_settings.view_transform = "Standard"


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


mat_floor = new_mat("PrevizFloor", (0.22, 0.22, 0.24))
mat_wall = new_mat("PrevizWall", (0.55, 0.55, 0.58))
mat_hero = new_mat("PrevizHero", (1.0, 0.38, 0.05), emission=0.35)
mat_mark = new_mat("PrevizMark", (0.15, 0.45, 0.95), emission=0.2)

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
scn.camera = cam
track = cam.constraints.new("TRACK_TO")
track.target = hero
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
for fr, loc in cam_keys:
    cam.location = Vector(loc)
    cam.keyframe_insert("location", frame=fr)

bpy.ops.render.render(animation=True)

import glob, os
pngs = sorted(glob.glob(out_prefix + "*.png"))
result = {{
    "status": "ok" if len(pngs) >= nframes else "error",
    "png_count": len(pngs),
    "nframes": nframes,
    "prefix": out_prefix,
}}
'''

    try:
        payload = unwrap_result(
            exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
        )
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)[:800]}

    if payload.get("status") != "ok":
        shutil.rmtree(tmp, ignore_errors=True)
        return {
            "ok": False,
            "error": "RENDER_FAIL",
            "message": str(payload.get("message") or payload)[:800],
        }

    muxed = _mux_pngs_to_mp4(tmp, dst)
    shutil.rmtree(tmp, ignore_errors=True)
    if muxed is not None:
        return muxed

    return {
        "ok": True,
        "output": str(dst),
        "preset": preset,
        "frames": nframes,
        "seconds": nframes / FPS,
        "bytes": dst.stat().st_size,
        "blender": probe.get("blender_version"),
    }


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
) -> dict[str, Any]:
    """Playblast the live Blender scene. Does not wipe objects.

    Needs an active camera. If seconds is set, frame 1..N. Else current
    range, clamped to MAX_SECONDS.
    """
    offline = _blender_offline(host, port)
    if offline:
        return offline

    dst = _prepare_mp4(output_mp4)
    tmp = Path(tempfile.mkdtemp(prefix="previz_"))
    prefix_s = _py_path(tmp / "frame_")
    nframes_lit = "None" if seconds is None else str(_frame_count(seconds))

    code = f'''
import bpy
import glob

scn = bpy.context.scene
if scn.camera is None:
    result = {{"status": "error", "message": "no scene camera — set Camera or bpy.context.scene.camera"}}
else:
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

    try:
        payload = unwrap_result(
            exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
        )
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)[:800]}

    if payload.get("status") != "ok":
        shutil.rmtree(tmp, ignore_errors=True)
        return {
            "ok": False,
            "error": "RENDER_FAIL",
            "message": str(payload.get("message") or payload)[:800],
        }

    muxed = _mux_pngs_to_mp4(tmp, dst)
    shutil.rmtree(tmp, ignore_errors=True)
    if muxed is not None:
        return muxed

    nframes = int(payload.get("nframes") or 0)
    return {
        "ok": True,
        "output": str(dst),
        "preset": "open_scene",
        "frames": nframes,
        "seconds": nframes / FPS if nframes else 0.0,
        "bytes": dst.stat().st_size,
        "camera": payload.get("camera"),
        "objects": payload.get("objects"),
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
) -> dict[str, Any]:
    """Run agent bpy in the live session, then playblast. Does not wipe first."""
    offline = _blender_offline(host, port)
    if offline:
        return offline

    wrapped = code.rstrip() + "\n\nif 'result' not in globals():\n    result = {'status': 'ok'}\n"
    try:
        payload = unwrap_result(
            exec_blender_code(wrapped, host=host, port=port, timeout_sec=timeout_sec)
        )
    except Exception as e:
        return {"ok": False, "error": "BLENDER_EXEC", "message": str(e)[:800]}

    if isinstance(payload, dict) and payload.get("status") == "error":
        return {
            "ok": False,
            "error": "BUILD_FAIL",
            "message": str(payload.get("message") or payload)[:800],
        }

    return render_open_scene(
        output_mp4=output_mp4,
        seconds=seconds,
        width=width,
        height=height,
        host=host,
        port=port,
        timeout_sec=timeout_sec,
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
