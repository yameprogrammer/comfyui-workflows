#!/usr/bin/env python3
"""
Run Kijai hy3d_example_01 quality path against a user image.

Geometry:
  LoadImage → Resize 518 → RemoveBG → GenerateMesh → VAEDecode → Postprocess → Export geo

Texture (same graph, research path):
  Composite on mid-gray BG → Delight(+SchedulerConfig) → UVWrap → RenderMV
  → Paint Sample(+SchedulerConfig) → optional upscale → Bake → VertInpaint
  → CV2Inpaint → ApplyTexture → Export textured

Analysis reference: hy3d_example_01.json links for scheduler → delight/paint.
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


def post_json(path: str, body: dict) -> None:
    req = urllib.request.Request(
        f"http://{SERVER}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print(f"[warn] {path}: {e}")


def upload(path: Path) -> str:
    boundary = "----Ex01"
    data = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"http://{SERVER}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        name = json.loads(resp.read())["name"]
    print("[upload]", name)
    return name


def queue(prompt: dict) -> str:
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace")[:2500], file=sys.stderr)
        raise


def wait(pid: str, timeout: int = 1800) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as resp:
            hist = json.loads(resp.read())
        if pid in hist:
            item = hist[pid]
            st = item.get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st, ensure_ascii=False)[:4000])
            if st.get("completed") or item.get("outputs"):
                return item
        time.sleep(4)
    raise TimeoutError(pid)


def find_glb(leaf: str) -> Path:
    cands: list[Path] = []
    for root in (COMFY_OUT / "3D", COMFY_OUT / "3d", COMFY_OUT):
        if root.exists():
            cands.extend(p for p in root.rglob("*.glb") if leaf in p.name)
    if not cands:
        cands = list(COMFY_OUT.rglob("*.glb"))
    latest = max(cands, key=lambda p: p.stat().st_mtime)
    print(f"[glb] {latest} ({latest.stat().st_size})")
    return latest


def build_example01_prompt(image_name: str, seed: int, textured: bool) -> dict:
    """
    Faithful subset of hy3d_example_01 wiring.

    Key fixes vs previous attempts:
    - Resize to 518 before generate (example note)
    - Rembg mask fed into GenerateMesh
    - Delight/Paint schedulers from Hy3DDiffusersSchedulerConfig nodes
    - Delight image is subject composited on mid-gray (SolidMask 0.8)
    """
    p: dict = {
        # --- input prep ---
        "13": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "52": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["13", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        "55": {
            "class_type": "TransparentBGSession+",
            "inputs": {"mode": "base", "use_jit": True},
        },
        "56": {
            "class_type": "ImageRemoveBackground+",
            "inputs": {
                "rembg_session": ["55", 0],
                "image": ["52", 0],
            },
        },
        # mid-gray plate for delight (example SolidMask 0.8 + composite)
        "132": {
            "class_type": "SolidMask",
            "inputs": {"value": 0.8, "width": 512, "height": 512},
        },
        "133": {
            "class_type": "MaskToImage",
            "inputs": {"mask": ["132", 0]},
        },
        # composite: destination gray, source = resized subject, mask = alpha from rembg
        # ImageRemoveBackground+ outputs: IMAGE, MASK typically
        "64": {
            "class_type": "ImageCompositeMasked",
            "inputs": {
                "destination": ["133", 0],
                "source": ["52", 0],
                "mask": ["56", 1],
                "x": 0,
                "y": 0,
                "resize_source": False,
            },
        },
        # --- geometry ---
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
                "image": ["52", 0],
                "mask": ["56", 1],
                "guidance_scale": 5.5,
                "steps": 50,
                "seed": seed,
                "scheduler": "FlowMatchEulerDiscreteScheduler",
                "force_offload": True,
            },
        },
        "140": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "vae": ["10", 1],
                "latents": ["141", 0],
                "box_v": 1.01,
                "octree_resolution": 384,
                "num_chunks": 32000,
                "mc_level": 0.0,
                "mc_algo": "mc",
                "enable_flash_vdm": True,
                "force_offload": True,
            },
        },
        "59": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["140", 0],
                "remove_floaters": True,
                "remove_degenerate_faces": True,
                "reduce_faces": True,
                "max_facenum": 50000,
                "smooth_normals": False,
            },
        },
        "17": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["59", 0],
                "filename_prefix": "3D/Hy3D_example01_geo",
                "file_format": "glb",
                "save_file": True,
            },
        },
    }

    if not textured:
        return p

    # --- texture branch (example_01) ---
    p.update(
        {
            "83": {
                "class_type": "Hy3DMeshUVWrap",
                "inputs": {"trimesh": ["59", 0]},
            },
            "28": {
                "class_type": "DownloadAndLoadHy3DDelightModel",
                "inputs": {"model": "hunyuan3d-delight-v2-0"},
            },
            # CRITICAL: scheduler object, not string
            "148": {
                "class_type": "Hy3DDiffusersSchedulerConfig",
                "inputs": {
                    "pipeline": ["28", 0],
                    "scheduler": "Euler A",
                    "sigmas": "default",
                },
            },
            "144": {
                "class_type": "PrimitiveInt",  # may not exist — use fixed in delight
                "inputs": {"value": 512},
            },
            "35": {
                "class_type": "Hy3DDelightImage",
                "inputs": {
                    "delight_pipe": ["28", 0],
                    "image": ["64", 0],
                    "scheduler": ["148", 0],
                    "steps": 50,
                    "width": 512,
                    "height": 512,
                    "cfg_image": 1.0,
                    "seed": seed,
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
                    "camera_config": ["61", 0],
                    "render_size": 1024,
                    "texture_size": 2048,
                    "normal_space": "world",
                },
            },
            "85": {
                "class_type": "DownloadAndLoadHy3DPaintModel",
                "inputs": {"model": "hunyuan3d-paint-v2-0"},
            },
            "149": {
                "class_type": "Hy3DDiffusersSchedulerConfig",
                "inputs": {
                    "pipeline": ["85", 0],
                    "scheduler": "Euler A",
                    "sigmas": "default",
                },
            },
            "88": {
                "class_type": "Hy3DSampleMultiView",
                "inputs": {
                    "pipeline": ["85", 0],
                    "ref_image": ["35", 0],
                    "normal_maps": ["79", 0],
                    "position_maps": ["79", 1],
                    "camera_config": ["61", 0],
                    "scheduler": ["149", 0],
                    "view_size": 512,
                    "steps": 25,
                    "seed": seed,
                    "denoise_strength": 1.0,
                },
            },
            "117": {
                "class_type": "ImageResize+",
                "inputs": {
                    "image": ["88", 0],
                    "width": 2048,
                    "height": 2048,
                    "interpolation": "lanczos",
                    "method": "stretch",
                    "condition": "always",
                    "multiple_of": 0,
                },
            },
            "92": {
                "class_type": "Hy3DBakeFromMultiview",
                "inputs": {
                    "images": ["117", 0],
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
            "104": {
                "class_type": "CV2InpaintTexture",
                "inputs": {
                    "texture": ["129", 0],
                    "mask": ["129", 1],
                    "inpaint_radius": 3,
                    "inpaint_method": "ns",
                },
            },
            "98": {
                "class_type": "Hy3DApplyTexture",
                "inputs": {
                    "texture": ["104", 0],
                    "renderer": ["129", 2],
                },
            },
            "99": {
                "class_type": "Hy3DExportMesh",
                "inputs": {
                    "trimesh": ["98", 0],
                    "filename_prefix": "3D/Hy3D_example01_tex",
                    "file_format": "glb",
                    "save_file": True,
                },
            },
        }
    )
    # remove PrimitiveInt if missing — use only width/height widgets
    # Check if PrimitiveInt exists; if not, strip node 144 and rely on defaults in 35/88
    return p


def strip_missing_nodes(prompt: dict) -> dict:
    """Drop PrimitiveInt if not registered."""
    try:
        with urllib.request.urlopen(f"http://{SERVER}/object_info/PrimitiveInt", timeout=10) as r:
            if r.status != 200:
                raise RuntimeError("no")
    except Exception:
        prompt.pop("144", None)
    # Validate CV2InpaintTexture exists
    try:
        with urllib.request.urlopen(f"http://{SERVER}/object_info", timeout=60) as r:
            info = json.loads(r.read())
    except Exception:
        return prompt
    if "CV2InpaintTexture" not in info:
        # skip cv2, apply vertex-inpainted texture directly
        if "98" in prompt:
            prompt["98"]["inputs"]["texture"] = ["129", 0]
        prompt.pop("104", None)
    if "ImageRemoveBackground+" not in info or "TransparentBGSession+" not in info:
        print("[warn] rembg nodes missing — using raw image")
        prompt["141"]["inputs"]["image"] = ["13", 0]
        prompt["141"]["inputs"].pop("mask", None)
        if "35" in prompt:
            prompt["35"]["inputs"]["image"] = ["13", 0]
    if "ImageResize+" not in info:
        prompt["141"]["inputs"]["image"] = ["13", 0]
        if "35" in prompt and "64" not in prompt:
            prompt["35"]["inputs"]["image"] = ["13", 0]
    if "ImageCompositeMasked" not in info and "35" in prompt:
        prompt["35"]["inputs"]["image"] = ["52", 0] if "52" in prompt else ["13", 0]
    return prompt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out-geo", required=True)
    ap.add_argument("--out-tex", default="")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--geo-only", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    image = Path(args.image)
    if not image.is_file():
        print("missing image", image)
        return 1

    post_json("/interrupt", {})
    post_json("/queue", {"clear": True})
    post_json("/free", {"unload_models": True, "free_memory": True})
    time.sleep(2)

    name = upload(image)

    # Stage 1 geo-only first (always)
    print("[stage1] example_01 geometry...")
    prompt_geo = strip_missing_nodes(build_example01_prompt(name, args.seed, textured=False))
    pid = queue(prompt_geo)
    print("queued", pid)
    item = wait(pid, args.timeout)
    print("status", (item.get("status") or {}).get("status_str"))
    print("outputs", item.get("outputs"))
    geo = find_glb("Hy3D_example01_geo")
    out_geo = Path(args.out_geo)
    out_geo.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(geo, out_geo)
    print("[OK geo]", out_geo, out_geo.stat().st_size)

    if args.geo_only:
        post_json("/free", {"unload_models": True, "free_memory": True})
        return 0

    post_json("/free", {"unload_models": True, "free_memory": True})
    time.sleep(3)

    print("[stage2] example_01 full texture...")
    prompt_tex = strip_missing_nodes(build_example01_prompt(name, args.seed + 1, textured=True))
    # remove broken primitive
    prompt_tex.pop("144", None)
    try:
        pid2 = queue(prompt_tex)
        print("queued tex", pid2)
        item2 = wait(pid2, args.timeout)
        print("tex status", (item2.get("status") or {}).get("status_str"))
        print("tex outputs", item2.get("outputs"))
        tex = find_glb("Hy3D_example01_tex")
        out_tex = Path(args.out_tex) if args.out_tex else out_geo.with_name(out_geo.stem + "_tex.glb")
        shutil.copyfile(tex, out_tex)
        print("[OK tex]", out_tex, out_tex.stat().st_size)
    except Exception as e:
        print("[tex failed]", e)
        return 2
    finally:
        post_json("/free", {"unload_models": True, "free_memory": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
