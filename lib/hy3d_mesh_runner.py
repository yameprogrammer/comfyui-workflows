"""Hunyuan3D / Kijai Hy3D mesh generation for the agent toolbox.

Requires ComfyUI with **ComfyUI-Hunyuan3DWrapper** (Kijai) and weights under
extra_model_paths, typically:

  F:\\model\\...\\hy3dgen\\hunyuan3d-dit-v2-0-fp16.safetensors

Profiles:
  draft — fast scout mesh
  work  — default agent quality (geo + postprocess)
  hero  — higher octree / faces; optional --texture paint path (VRAM heavy)

Not episode default. Opt-in 3D asset tool (shelf MESH).
"""

from __future__ import annotations

import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    free_comfy_memory,
    get_comfy_input_dir,
    get_comfy_output_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import FAMILY_HY3D, ensure_engine

DEFAULT_DIT_MODEL = r"hy3dgen\hunyuan3d-dit-v2-0-fp16.safetensors"

PROFILES: dict[str, dict[str, Any]] = {
    "draft": {
        "steps": 25,
        "guidance": 5.5,
        "octree": 256,
        "max_faces": 40000,
        "notes": "scout mesh; faster, coarser",
    },
    "work": {
        "steps": 45,
        "guidance": 6.5,
        "octree": 384,
        "max_faces": 80000,
        "notes": "DEFAULT agent geometry + postprocess",
    },
    "hero": {
        "steps": 50,
        "guidance": 7.0,
        "octree": 512,
        "max_faces": 120000,
        "notes": "heavier geo; pair with --texture only when VRAM allows",
    },
}


def list_profiles() -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in PROFILES.items()}


def _stage_image(path: str, server: str) -> str:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"image not found: {src}")
    dest_dir = Path(get_comfy_input_dir(server))
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem[:40]
    name = f"hy3d_{stem}_{int(time.time() * 1000) % 10_000_000}{src.suffix.lower() or '.png'}"
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return name


def build_geometry_prompt(
    image_name: str,
    *,
    seed: int,
    steps: int,
    guidance: float,
    octree: int,
    max_faces: int,
    remesh: bool,
    prefix: str,
    dit_model: str = DEFAULT_DIT_MODEL,
) -> dict[str, Any]:
    prompt: dict[str, Any] = {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": dit_model,
                "attention_mode": "sdpa",
                "cublas_ops": False,
            },
        },
        "141": {
            "class_type": "Hy3DGenerateMesh",
            "inputs": {
                "pipeline": ["10", 0],
                "image": ["1", 0],
                "guidance_scale": guidance,
                "steps": steps,
                "seed": seed,
                "scheduler": "FlowMatchEulerDiscreteScheduler",
                "force_offload": True,
            },
        },
        "140": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "latents": ["141", 0],
                "vae": ["10", 1],
                "box_v": 1.01,
                "octree_resolution": octree,
                "num_chunks": 32000,
                "mc_level": 0.0,
                "mc_algo": "dmc",
            },
        },
        "59": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["140", 0],
                "remove_floaters": True,
                "remove_degenerate_faces": True,
                "reduce_faces": True,
                "max_facenum": max_faces,
                "smooth_normals": True,
            },
        },
    }
    mesh_src: list[Any] = ["59", 0]
    next_id = 200
    if remesh:
        prompt[str(next_id)] = {
            "class_type": "Hy3DIMRemesh",
            "inputs": {
                "trimesh": mesh_src,
                "merge_vertices": True,
                "vertex_count": min(max_faces, 60000),
                "smooth_iter": 3,
                "align_to_boundaries": True,
                "triangulate_result": True,
                "max_facenum": max_faces,
            },
        }
        mesh_src = [str(next_id), 0]
        next_id += 1

    prompt[str(next_id)] = {
        "class_type": "Hy3DExportMesh",
        "inputs": {
            "trimesh": mesh_src,
            "filename_prefix": prefix,
            "file_format": "glb",
            "save_file": True,
        },
    }
    return prompt


def build_textured_prompt(
    image_name: str,
    *,
    seed: int,
    steps: int,
    guidance: float,
    octree: int,
    max_faces: int,
    view_size: int,
    paint_steps: int,
    prefix: str,
    dit_model: str = DEFAULT_DIT_MODEL,
) -> dict[str, Any]:
    """Full paint path — high VRAM; agent should treat as hero opt-in."""
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": dit_model,
                "attention_mode": "sdpa",
                "cublas_ops": False,
            },
        },
        "141": {
            "class_type": "Hy3DGenerateMesh",
            "inputs": {
                "pipeline": ["10", 0],
                "image": ["1", 0],
                "guidance_scale": guidance,
                "steps": steps,
                "seed": seed,
                "scheduler": "FlowMatchEulerDiscreteScheduler",
            },
        },
        "140": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "latents": ["141", 0],
                "vae": ["10", 1],
                "box_v": 1.01,
                "octree_resolution": octree,
                "num_chunks": 20000,
                "mc_level": 0.0,
                "mc_algo": "dmc",
            },
        },
        "59": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["140", 0],
                "remove_floaters": True,
                "remove_degenerate_faces": True,
                "reduce_faces": True,
                "max_facenum": max_faces,
                "smooth_normals": True,
            },
        },
        "83": {"class_type": "Hy3DMeshUVWrap", "inputs": {"trimesh": ["59", 0]}},
        "28": {
            "class_type": "DownloadAndLoadHy3DDelightModel",
            "inputs": {"model": "hunyuan3d-delight-v2-0"},
        },
        "35": {
            "class_type": "Hy3DDelightImage",
            "inputs": {
                "delight_pipe": ["28", 0],
                "image": ["1", 0],
                "steps": 30,
                "width": 512,
                "height": 512,
                "cfg_image": 1.0,
                "seed": seed,
                "scheduler": "fixed",
            },
        },
        "61": {
            "class_type": "Hy3DCameraConfig",
            "inputs": {
                "camera_azimuths": "0, 90, 180, 270, 0, 180",
                "camera_elevations": "0, 0, 0, 0, 90, -90",
                "view_weights": "1, 0.1, 0.5, 0.1, 0.05, 0.05",
                "camera_distance": 1.45,
                "ortho_scale": 1.2,
            },
        },
        "79": {
            "class_type": "Hy3DRenderMultiView",
            "inputs": {
                "trimesh": ["83", 0],
                "render_size": 1024,
                "texture_size": 2048,
                "normal_space": "world",
                "camera_config": ["61", 0],
            },
        },
        "85": {
            "class_type": "DownloadAndLoadHy3DPaintModel",
            "inputs": {"model": "hunyuan3d-paint-v2-0"},
        },
        "88": {
            "class_type": "Hy3DSampleMultiView",
            "inputs": {
                "pipeline": ["85", 0],
                "ref_image": ["35", 0],
                "normal_maps": ["79", 0],
                "position_maps": ["79", 1],
                "view_size": view_size,
                "steps": paint_steps,
                "seed": seed,
                "camera_config": ["61", 0],
                "denoise_strength": 1.0,
            },
        },
        "92": {
            "class_type": "Hy3DBakeFromMultiview",
            "inputs": {
                "images": ["88", 0],
                "renderer": ["79", 2],
                "camera_config": ["61", 0],
            },
        },
        "129": {
            "class_type": "Hy3DMeshVerticeInpaintTexture",
            "inputs": {
                "texture": ["92", 0],
                "mask": ["92", 1],
                "renderer": ["92", 2],
            },
        },
        "98": {
            "class_type": "Hy3DApplyTexture",
            "inputs": {
                "texture": ["129", 0],
                "renderer": ["92", 2],
            },
        },
        "99": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["98", 0],
                "filename_prefix": prefix,
                "file_format": "glb",
                "save_file": True,
            },
        },
    }


def _find_latest_glb(prefix: str, server: str, *, after_mtime: float) -> Path | None:
    out_root = Path(get_comfy_output_dir(server))
    leaf = prefix.replace("\\", "/").split("/")[-1]
    cands: list[Path] = []
    search_roots = [
        out_root / "3D",
        out_root / "3d",
        out_root / "mesh",
        out_root,
    ]
    for root in search_roots:
        if not root.is_dir():
            continue
        try:
            for p in root.rglob("*.glb"):
                try:
                    mt = p.stat().st_mtime
                except OSError:
                    continue
                if mt + 0.5 < after_mtime:
                    continue
                name = p.name
                if leaf and leaf in name:
                    cands.append(p)
                elif "Hy3D" in name or "hy3d" in name.lower():
                    cands.append(p)
        except OSError:
            continue
    if not cands:
        # fallback: newest glb under output modified after start
        for root in search_roots:
            if not root.is_dir():
                continue
            try:
                for p in root.rglob("*.glb"):
                    try:
                        if p.stat().st_mtime + 0.5 >= after_mtime:
                            cands.append(p)
                    except OSError:
                        continue
            except OSError:
                continue
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def generate_hy3d_mesh(
    *,
    image_path: str,
    output_path: str,
    seed: int | None = None,
    profile: str = "work",
    steps: int | None = None,
    guidance: float | None = None,
    octree: int | None = None,
    max_faces: int | None = None,
    remesh: bool = False,
    texture: bool = False,
    view_size: int = 768,
    paint_steps: int = 25,
    prefix: str | None = None,
    dit_model: str = DEFAULT_DIT_MODEL,
    timeout_sec: float = 1200.0,
    server_address: str = DEFAULT_SERVER,
    free_policy: str | None = None,
    free_after: bool = True,
) -> dict[str, Any]:
    """Image → GLB via Hy3D. Returns ok_result / fail_result dict."""
    t0 = time.time()
    prof_name = (profile or "work").strip().lower()
    if prof_name not in PROFILES:
        return fail_result(
            error="BAD_PROFILE",
            message=f"unknown profile {profile!r}; use draft|work|hero",
        )
    prof = PROFILES[prof_name]
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    steps_i = int(steps if steps is not None else prof["steps"])
    guidance_f = float(guidance if guidance is not None else prof["guidance"])
    octree_i = int(octree if octree is not None else prof["octree"])
    faces_i = int(max_faces if max_faces is not None else prof["max_faces"])
    out = Path(output_path).expanduser().resolve()
    if out.suffix.lower() != ".glb":
        out = out.with_suffix(".glb")
    ensure_parent_dir(str(out))

    prefix_s = (prefix or f"3D/agent_hy3d_{seed_i % 1_000_000}").replace("\\", "/")
    if texture:
        prefix_s = prefix_s.rstrip("/") + "_tex"

    server = (server_address or DEFAULT_SERVER).strip()
    try:
        ensure_engine(
            FAMILY_HY3D,
            server_address=server,
            policy=free_policy,
            caller="generate_hy3d_mesh",
        )
    except Exception as e:
        return fail_result(error="ENGINE", message=str(e))

    try:
        image_name = _stage_image(image_path, server)
    except Exception as e:
        return fail_result(error="STAGE_IMAGE", message=str(e))

    if texture:
        api = build_textured_prompt(
            image_name,
            seed=seed_i,
            steps=steps_i,
            guidance=guidance_f,
            octree=octree_i,
            max_faces=faces_i,
            view_size=int(view_size),
            paint_steps=int(paint_steps),
            prefix=prefix_s,
            dit_model=dit_model,
        )
        mode = "texture"
    else:
        api = build_geometry_prompt(
            image_name,
            seed=seed_i,
            steps=steps_i,
            guidance=guidance_f,
            octree=octree_i,
            max_faces=faces_i,
            remesh=bool(remesh),
            prefix=prefix_s,
            dit_model=dit_model,
        )
        mode = "geometry"

    started = time.time()
    try:
        prompt_id = queue_prompt(server, api)
    except Exception as e:
        return fail_result(error="QUEUE", message=str(e), seed=seed_i)

    try:
        hist = wait_for_history(server, prompt_id, timeout_sec=float(timeout_sec))
    except Exception as e:
        return fail_result(
            error="WAIT",
            message=str(e),
            seed=seed_i,
            prompt_id=prompt_id,
        )

    from lib.comfy_client import history_execution_error

    herr = history_execution_error(hist)
    if herr:
        return fail_result(
            error="EXEC",
            message=herr,
            seed=seed_i,
            prompt_id=prompt_id,
        )

    time.sleep(1.0)
    glb = _find_latest_glb(prefix_s, server, after_mtime=started - 2.0)
    if glb is None:
        return fail_result(
            error="NO_GLB",
            message=(
                f"no .glb found under Comfy output after run "
                f"(prefix={prefix_s!r}). Check Hy3D nodes / models."
            ),
            seed=seed_i,
            prompt_id=prompt_id,
        )

    try:
        shutil.copy2(glb, out)
    except Exception as e:
        return fail_result(
            error="COPY",
            message=f"{e} (src={glb})",
            seed=seed_i,
            prompt_id=prompt_id,
        )

    if free_after:
        try:
            free_comfy_memory(server, unload_models=True)
        except Exception:
            pass

    meta = {
        "tool": "generate_hy3d_mesh",
        "mode": mode,
        "profile": prof_name,
        "seed": seed_i,
        "steps": steps_i,
        "guidance": guidance_f,
        "octree": octree_i,
        "max_faces": faces_i,
        "remesh": bool(remesh),
        "texture": bool(texture),
        "prefix": prefix_s,
        "dit_model": dit_model,
        "comfy_glb": str(glb),
        "output_path": str(out),
        "prompt_id": prompt_id,
        "elapsed_sec": round(time.time() - t0, 2),
        "created_at": utc_now_iso(),
        "bytes": out.stat().st_size if out.is_file() else 0,
    }
    meta_path = str(out.with_suffix(out.suffix + ".meta.json"))
    try:
        write_meta(meta_path, meta)
    except Exception:
        meta_path = None
    return ok_result(
        output_path=str(out),
        seed=seed_i,
        prompt_id=prompt_id,
        meta_path=meta_path,
        elapsed_sec=meta["elapsed_sec"],
        mode=mode,
        profile=prof_name,
        comfy_glb=str(glb),
    )
