#!/usr/bin/env python3
"""
Research-backed Hunyuan3D quality pipeline via Kijai ComfyUI-Hunyuan3DWrapper.

Stages:
  1) Geometry: Hy3D_2_1SimpleMeshGen (or DiT path)
  2) Postprocess: remove floaters/degenerate + face reduce
  3) Optional IM remesh
  4) Optional texture: delight → UV → multiview paint → bake → apply
  5) Export GLB

See drafts/mecha_yame_v2/docs/3d_quality_research.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
COMFY_OUT = Path(r"F:\ComfyUI_data\output")


def free_memory() -> None:
    try:
        req = urllib.request.Request(
            f"http://{SERVER}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=60).read()
        print("[mem] free requested")
    except Exception as e:
        print(f"[mem] free skip: {e}")


def interrupt_and_clear() -> None:
    for path, body in (
        ("/interrupt", b"{}"),
        ("/queue", json.dumps({"clear": True}).encode()),
    ):
        try:
            req = urllib.request.Request(
                f"http://{SERVER}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=30).read()
        except Exception:
            pass
    time.sleep(1)


def upload_image(image_path: Path) -> str:
    boundary = "----WebKitFormBoundaryHy3DQuality"
    data = image_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"http://{SERVER}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        name = json.loads(resp.read())["name"]
    print(f"[upload] {name}")
    return name


def queue_prompt(prompt: dict) -> str:
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["prompt_id"]
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] queue failed: {err[:2000]}", file=sys.stderr)
        raise


def wait_history(prompt_id: str, timeout_sec: int = 1200) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        with urllib.request.urlopen(f"http://{SERVER}/history/{prompt_id}", timeout=30) as resp:
            hist = json.loads(resp.read())
        if prompt_id in hist:
            item = hist[prompt_id]
            st = item.get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st, ensure_ascii=False)[:3000])
            if st.get("completed") or item.get("outputs"):
                return item
        time.sleep(4)
    raise TimeoutError(f"timeout after {timeout_sec}s")


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
) -> dict:
    """
    Research path (Kijai wrapper, community standard):
      LoadImage → Hy3DModelLoader → GenerateMesh → VAEDecode(dmc, high octree)
      → Postprocess(floaters/degenerate/reduce) → [IMRemesh] → Export

    Note: Hy3D_2_1SimpleMeshGen can KeyError on some ckpt configs; DiT v2-0 path is reliable.
    """
    prompt: dict = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": "hy3dgen\\hunyuan3d-dit-v2-0-fp16.safetensors",
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
    mesh_src = ["59", 0]
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
) -> dict:
    """
    Full Kijai-style path (heavier VRAM):
      geometry → post → UV → delight → render MV → paint sample → bake → apply → export
    """
    # Geometry with classic DiT loader for texture pipeline compatibility
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": "hy3dgen\\hunyuan3d-dit-v2-0-fp16.safetensors",
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
        # VAE often bundled — Hy3DGenerateMesh may need VAE from loader output index 1
        # Check: many graphs use separate VAE loader. Use SimpleMeshGen path if this fails.
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
        "83": {
            "class_type": "Hy3DMeshUVWrap",
            "inputs": {"trimesh": ["59", 0]},
        },
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
                "renderer": ["129", 1] if False else ["92", 2],
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


def find_latest_glb(prefix_leaf: str) -> Path:
    cands: list[Path] = []
    for root in (COMFY_OUT / "3D", COMFY_OUT / "3d", COMFY_OUT / "mesh", COMFY_OUT):
        if not root.exists():
            continue
        for p in root.rglob("*.glb"):
            if prefix_leaf.replace("/", "_") in p.name or prefix_leaf.split("/")[-1] in p.name:
                cands.append(p)
            elif "Hy3D" in p.name or "mecha" in p.name.lower() or "quality" in p.name.lower():
                cands.append(p)
    if not cands:
        # newest any glb under output
        for root in (COMFY_OUT / "3D", COMFY_OUT / "3d", COMFY_OUT):
            if root.exists():
                cands.extend(root.rglob("*.glb"))
    if not cands:
        raise FileNotFoundError("no glb found in Comfy output")
    latest = max(cands, key=lambda p: p.stat().st_mtime)
    print(f"[glb] {latest} ({latest.stat().st_size} bytes)")
    return latest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True, help="destination glb path")
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--steps", type=int, default=45)
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--octree", type=int, default=384)
    ap.add_argument("--max-faces", type=int, default=80000)
    ap.add_argument("--remesh", action="store_true")
    ap.add_argument("--texture", action="store_true", help="full paint path (high VRAM)")
    ap.add_argument("--view-size", type=int, default=768)
    ap.add_argument("--paint-steps", type=int, default=25)
    ap.add_argument("--prefix", default="3D/mecha_yame_quality")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    image = Path(args.image)
    out = Path(args.out)
    if not image.is_file():
        print(f"[ERROR] missing image {image}", file=sys.stderr)
        return 1

    interrupt_and_clear()
    free_memory()
    time.sleep(2)

    name = upload_image(image)
    if args.texture:
        print("[mode] textured full pipeline (research path)")
        prompt = build_textured_prompt(
            name,
            seed=args.seed,
            steps=args.steps,
            guidance=args.guidance,
            octree=args.octree,
            max_faces=args.max_faces,
            view_size=args.view_size,
            paint_steps=args.paint_steps,
            prefix=args.prefix + "_tex",
        )
    else:
        print("[mode] geometry + postprocess (+ optional remesh)")
        prompt = build_geometry_prompt(
            name,
            seed=args.seed,
            steps=args.steps,
            guidance=args.guidance,
            octree=args.octree,
            max_faces=args.max_faces,
            remesh=args.remesh,
            prefix=args.prefix,
        )

    pid = queue_prompt(prompt)
    print(f"[queued] {pid}")
    item = wait_history(pid, timeout_sec=args.timeout)
    print("[status]", (item.get("status") or {}).get("status_str"))
    print("[outputs]", json.dumps(item.get("outputs"), ensure_ascii=False)[:1500])

    time.sleep(1)
    # Prefer path from export node if present
    src = None
    for _nid, outp in (item.get("outputs") or {}).items():
        # Hy3DExportMesh returns string path sometimes in UI meta; file on disk is reliable
        pass
    try:
        src = find_latest_glb(args.prefix.split("/")[-1])
    except FileNotFoundError:
        src = find_latest_glb("Hy3D")

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    print(f"[OK] {out} ({out.stat().st_size} bytes)")
    free_memory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
