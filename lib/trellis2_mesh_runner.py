"""Microsoft TRELLIS 2 image → GLB for the agent toolbox.

Requires ComfyUI + ComfyUI-TRELLIS2 (PozzettiAndrea) and weights:

  ComfyUI/models/trellis2/ckpts/*.safetensors
  ComfyUI/models/dinov3/model.safetensors

Agent MESH default. Hunyuan3D (`generate_hy3d_mesh`) is KR Community License
blocked — do not call it unless the user names it.

Profiles:
  draft — 512, geometry only (no PBR)
  work  — 1024_cascade + PBR (DEFAULT)
  hero  — 1024_cascade + PBR, more steps / faces
"""

from __future__ import annotations

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
from lib.comfy_engine_session import FAMILY_TRELLIS2, ensure_engine

FAMILY_TRELLIS2_MESH = FAMILY_TRELLIS2

RESOLUTION_MODES = ("512", "1024", "1024_cascade", "1536_cascade")

PROFILES: dict[str, dict[str, Any]] = {
    "draft": {
        "resolution": "512",
        "ss_steps": 8,
        "shape_steps": 8,
        "tex_steps": 0,
        "texture": False,
        "max_tokens": 32768,
        "target_faces": 40000,
        "texture_size": 1024,
        "notes": "scout geometry only; 512, no PBR",
    },
    "work": {
        "resolution": "1024_cascade",
        "ss_steps": 12,
        "shape_steps": 12,
        "tex_steps": 12,
        "texture": True,
        "max_tokens": 49152,
        "target_faces": 80000,
        "texture_size": 2048,
        "notes": "DEFAULT agent PBR GLB; 1024_cascade",
    },
    "hero": {
        "resolution": "1024_cascade",
        "ss_steps": 16,
        "shape_steps": 16,
        "tex_steps": 16,
        "texture": True,
        "max_tokens": 65536,
        "target_faces": 200000,
        "texture_size": 2048,
        "notes": "heavier geo + PBR; still not a hero character rig",
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
    name = f"trellis2_{stem}_{int(time.time() * 1000) % 10_000_000}{src.suffix.lower() or '.png'}"
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return name


def build_trellis2_prompt(
    image_name: str,
    *,
    seed: int,
    resolution: str,
    ss_steps: int,
    shape_steps: int,
    tex_steps: int,
    texture: bool,
    max_tokens: int,
    target_faces: int,
    texture_size: int,
    prefix: str,
    ss_guidance: float = 6.5,
    shape_guidance: float = 6.5,
    tex_guidance: float = 3.0,
    remesh: bool = False,
) -> dict[str, Any]:
    """Minimal API graph: LoadImage → rembg → cond → shape → (PBR) → export."""
    if resolution not in RESOLUTION_MODES:
        raise ValueError(f"unknown resolution {resolution!r}; use {RESOLUTION_MODES}")
    prompt: dict[str, Any] = {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "2": {
            "class_type": "Trellis2RemoveBackground",
            "inputs": {"image": ["1", 0], "low_vram": True},
        },
        "3": {
            "class_type": "LoadTrellis2Models",
            "inputs": {
                "resolution": resolution,
                "precision": "auto",
                "attn_backend": "auto",
            },
        },
        "4": {
            "class_type": "Trellis2GetConditioning",
            "inputs": {
                "model_config": ["3", 0],
                "image": ["2", 0],
                "mask": ["2", 1],
                "background_color": "black",
            },
        },
        "5": {
            "class_type": "Trellis2ImageToShape",
            "inputs": {
                "model_config": ["3", 0],
                "conditioning": ["4", 0],
                "seed": int(seed),
                "ss_guidance_strength": float(ss_guidance),
                "ss_guidance_rescale": 0.05,
                "ss_sampling_steps": int(ss_steps),
                "shape_guidance_strength": float(shape_guidance),
                "shape_guidance_rescale": 0.05,
                "shape_sampling_steps": int(shape_steps),
                "max_tokens": int(max_tokens),
            },
        },
    }
    if not texture:
        prompt["9"] = {
            "class_type": "Trellis2ExportTrimesh",
            "inputs": {
                "trimesh": ["5", 0],
                "filename_prefix": prefix,
                "file_format": "glb",
            },
        }
        return prompt

    remesh_payload: dict[str, Any] = {
        "remesh": "on" if remesh else "off",
        "remesh_band": 1.0,
        "remove_inner_faces": True,
        "fill_holes": True,
        "fill_holes_perimeter": 0.03,
    }
    prompt["6"] = {
        "class_type": "Trellis2ShapeToTexturedMesh",
        "inputs": {
            "model_config": ["3", 0],
            "conditioning": ["4", 0],
            "shape_slat": ["5", 1],
            "subs": ["5", 2],
            "seed": int(seed),
            "tex_guidance_strength": float(tex_guidance),
            "tex_guidance_rescale": 0.20,
            "tex_sampling_steps": int(tex_steps),
        },
    }
    prompt["7"] = {
        "class_type": "Trellis2ProcessMesh",
        "inputs": {
            "trimesh": ["5", 0],
            "remesh": remesh_payload,
            "floater_threshold": 0.001,
            "target_face_count": int(target_faces),
            "weld_vertices": True,
            "weld_digits": 4,
            "chart_cone_angle": 90.0,
            "chart_refine_iterations": 1,
            "chart_global_iterations": 1,
            "chart_smooth_strength": 1,
        },
    }
    prompt["8"] = {
        "class_type": "Trellis2RasterizePBR",
        "inputs": {
            "trimesh": ["7", 0],
            "voxelgrid": ["6", 0],
            "original_mesh": ["5", 0],
            "texture_size": int(texture_size),
        },
    }
    prompt["9"] = {
        "class_type": "Trellis2ExportTrimesh",
        "inputs": {
            "trimesh": ["8", 0],
            "filename_prefix": prefix,
            "file_format": "glb",
        },
    }
    return prompt


def _find_latest_glb(prefix: str, server: str, *, after_mtime: float) -> Path | None:
    out_root = Path(get_comfy_output_dir(server))
    leaf = prefix.replace("\\", "/").split("/")[-1]
    cands: list[Path] = []
    search_roots = [out_root / "3D", out_root / "3d", out_root / "trellis2", out_root]
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
                elif "trellis" in name.lower():
                    cands.append(p)
        except OSError:
            continue
    if not cands:
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


def generate_trellis_mesh(
    *,
    image_path: str,
    output_path: str,
    seed: int | None = None,
    profile: str = "work",
    resolution: str | None = None,
    texture: bool | None = None,
    remesh: bool = False,
    ss_steps: int | None = None,
    shape_steps: int | None = None,
    tex_steps: int | None = None,
    max_tokens: int | None = None,
    target_faces: int | None = None,
    texture_size: int | None = None,
    prefix: str | None = None,
    timeout_sec: float = 1800.0,
    server_address: str = DEFAULT_SERVER,
    free_policy: str | None = None,
    free_after: bool = True,
) -> dict[str, Any]:
    """Image → GLB via TRELLIS 2. Returns ok_result / fail_result dict."""
    t0 = time.time()
    prof_name = (profile or "work").strip().lower()
    if prof_name not in PROFILES:
        return fail_result(
            error="BAD_PROFILE",
            message=f"unknown profile {profile!r}; use draft|work|hero",
        )
    prof = PROFILES[prof_name]
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    res = (resolution or prof["resolution"]).strip()
    if res not in RESOLUTION_MODES:
        return fail_result(
            error="BAD_RESOLUTION",
            message=f"unknown resolution {res!r}; use {RESOLUTION_MODES}",
        )
    do_tex = bool(prof["texture"] if texture is None else texture)
    ss_i = int(ss_steps if ss_steps is not None else prof["ss_steps"])
    shape_i = int(shape_steps if shape_steps is not None else prof["shape_steps"])
    tex_i = int(tex_steps if tex_steps is not None else prof["tex_steps"] or 12)
    tokens_i = int(max_tokens if max_tokens is not None else prof["max_tokens"])
    faces_i = int(target_faces if target_faces is not None else prof["target_faces"])
    tex_size_i = int(texture_size if texture_size is not None else prof["texture_size"])
    out = Path(output_path).expanduser().resolve()
    if out.suffix.lower() != ".glb":
        out = out.with_suffix(".glb")
    ensure_parent_dir(str(out))

    # Export node does mkdir(exist_ok=True) without parents — no slashes.
    prefix_s = (prefix or f"agent_trellis2_{seed_i % 1_000_000}").replace("\\", "/").strip("/")
    if "/" in prefix_s:
        prefix_s = prefix_s.split("/")[-1]

    server = (server_address or DEFAULT_SERVER).strip()
    try:
        ensure_engine(
            FAMILY_TRELLIS2,
            server_address=server,
            policy=free_policy,
            caller="generate_trellis_mesh",
        )
    except Exception as e:
        return fail_result(error="ENGINE", message=str(e))

    try:
        image_name = _stage_image(image_path, server)
    except Exception as e:
        return fail_result(error="STAGE_IMAGE", message=str(e))

    try:
        api = build_trellis2_prompt(
            image_name,
            seed=seed_i,
            resolution=res,
            ss_steps=ss_i,
            shape_steps=shape_i,
            tex_steps=tex_i,
            texture=do_tex,
            max_tokens=tokens_i,
            target_faces=faces_i,
            texture_size=tex_size_i,
            prefix=prefix_s,
            remesh=bool(remesh),
        )
    except ValueError as e:
        return fail_result(error="GRAPH", message=str(e))

    mode = "pbr" if do_tex else "geometry"
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
                f"(prefix={prefix_s!r}). Check ComfyUI-TRELLIS2 / trellis2 weights."
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
        "tool": "generate_trellis_mesh",
        "mode": mode,
        "profile": prof_name,
        "seed": seed_i,
        "resolution": res,
        "ss_steps": ss_i,
        "shape_steps": shape_i,
        "tex_steps": tex_i if do_tex else 0,
        "texture": do_tex,
        "remesh": bool(remesh),
        "max_tokens": tokens_i,
        "target_faces": faces_i,
        "texture_size": tex_size_i if do_tex else None,
        "prefix": prefix_s,
        "comfy_glb": str(glb),
        "output_path": str(out),
        "prompt_id": prompt_id,
        "elapsed_sec": round(time.time() - t0, 2),
        "created_at": utc_now_iso(),
        "bytes": out.stat().st_size if out.is_file() else 0,
        "license": "TRELLIS 2 weights MIT; commercial GLB: confirm pack did not use nvdiffrast",
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
