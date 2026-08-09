#!/usr/bin/env python3
"""
High-quality multiview geometry for simple mecha_yame_v2.

Uses matched refs in drafts/.../refs/simple_mv (front/side/back).
Geometry: hunyuan3d-dit-v2-0-mv-fast, steps50, cfg5.5, VAE octree384, post 60k
Texture: example_01 style delight+paint with SchedulerConfig (Euler A)
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
DEFAULT_TURN = Path(r"D:\캐릭터\drafts\mecha_yame_v2\refs\simple_mv")
EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
COMFY_OUT = Path(r"F:\ComfyUI_data\output")


def post(path: str, body: dict) -> None:
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
    boundary = "----SMV"
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
    print(f"[upload] {path.name} -> {name}")
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
        print(e.read().decode("utf-8", errors="replace")[:3000], file=sys.stderr)
        raise


def wait(pid: str, timeout: int = 2400) -> dict:
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


def build_mv_geo(front: str, left: str, back: str, seed: int, right: str | None = None) -> dict:
    p = {
        "1f": {"class_type": "LoadImage", "inputs": {"image": front}},
        "1l": {"class_type": "LoadImage", "inputs": {"image": left}},
        "1b": {"class_type": "LoadImage", "inputs": {"image": back}},
        # controlled 518 resize for consistency with example notes (optional but good)
        "52f": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["1f", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        "52l": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["1l", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        "52b": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["1b", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": "hy3dgen\\hunyuan3d-dit-v2-0-mv-fast-fp16.safetensors",
                "attention_mode": "sdpa",
                "cublas_ops": False,
            },
        },
        "166": {
            "class_type": "Hy3DGenerateMeshMultiView",
            "inputs": {
                "pipeline": ["10", 0],
                "guidance_scale": 5.5,
                "steps": 50,
                "seed": seed,
                "front": ["52f", 0],
                "left": ["52l", 0],
                "back": ["52b", 0],
                "scheduler": "FlowMatchEulerDiscreteScheduler",
            },
        },
        "140": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "vae": ["10", 1],
                "latents": ["166", 0],
                "box_v": 1.01,
                "octree_resolution": 384,
                "num_chunks": 32000,
                "mc_level": 0.0,
                "mc_algo": "mc",
                "enable_flash_vdm": True,
                "force_offload": True,
            },
        },
        "203": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["140", 0],
                "remove_floaters": True,
                "remove_degenerate_faces": True,
                "reduce_faces": True,
                "max_facenum": 60000,
                "smooth_normals": False,
            },
        },
        "17": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["203", 0],
                "filename_prefix": "3D/mecha_simple_mv_geo",
                "file_format": "glb",
                "save_file": True,
            },
        },
    }
    if right:
        p["1r"] = {"class_type": "LoadImage", "inputs": {"image": right}}
        p["52r"] = {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["1r", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        }
        p["166"]["inputs"]["right"] = ["52r", 0]
    return p


def build_mv_geo_and_paint(front: str, left: str, back: str, seed: int) -> dict:
    """MV geo + example_01 style texture (SchedulerConfig Euler A)."""
    p = build_mv_geo(front, left, back, seed)
    # keep geo export; add texture branch from 203
    p.update(
        {
            "83": {"class_type": "Hy3DMeshUVWrap", "inputs": {"trimesh": ["203", 0]}},
            "28": {
                "class_type": "DownloadAndLoadHy3DDelightModel",
                "inputs": {"model": "hunyuan3d-delight-v2-0"},
            },
            "148": {
                "class_type": "Hy3DDiffusersSchedulerConfig",
                "inputs": {
                    "pipeline": ["28", 0],
                    "scheduler": "Euler A",
                    "sigmas": "default",
                },
            },
            # mid-gray plate for delight
            "132": {
                "class_type": "SolidMask",
                "inputs": {"value": 0.8, "width": 512, "height": 512},
            },
            "133": {"class_type": "MaskToImage", "inputs": {"mask": ["132", 0]}},
            "55": {
                "class_type": "TransparentBGSession+",
                "inputs": {"mode": "base", "use_jit": True},
            },
            "56": {
                "class_type": "ImageRemoveBackground+",
                "inputs": {"rembg_session": ["55", 0], "image": ["52f", 0]},
            },
            "64": {
                "class_type": "ImageCompositeMasked",
                "inputs": {
                    "destination": ["133", 0],
                    "source": ["52f", 0],
                    "mask": ["56", 1],
                    "x": 0,
                    "y": 0,
                    "resize_source": False,
                },
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
                    "filename_prefix": "3D/mecha_simple_mv_tex",
                    "file_format": "glb",
                    "save_file": True,
                },
            },
        }
    )
    return p


def strip_optional(prompt: dict) -> dict:
    try:
        with urllib.request.urlopen(f"http://{SERVER}/object_info", timeout=60) as r:
            info = json.loads(r.read())
    except Exception:
        return prompt
    if "ImageResize+" not in info:
        for k in ("52f", "52l", "52b", "52r"):
            prompt.pop(k, None)
        if "166" in prompt:
            prompt["166"]["inputs"]["front"] = ["1f", 0]
            prompt["166"]["inputs"]["left"] = ["1l", 0]
            prompt["166"]["inputs"]["back"] = ["1b", 0]
        if "35" in prompt:
            prompt["35"]["inputs"]["image"] = ["1f", 0]
    if "CV2InpaintTexture" not in info and "98" in prompt:
        prompt["98"]["inputs"]["texture"] = ["129", 0]
        prompt.pop("104", None)
    if "ImageCompositeMasked" not in info and "35" in prompt:
        prompt["35"]["inputs"]["image"] = ["52f", 0] if "52f" in prompt else ["1f", 0]
        for k in ("132", "133", "55", "56", "64"):
            prompt.pop(k, None)
    return prompt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turn-dir", default=str(DEFAULT_TURN))
    ap.add_argument("--exports", default=str(EXPORTS), help="Output directory for GLBs")
    ap.add_argument("--name-prefix", default="mecha_yame_v2_simple_mv", help="Output basename prefix")
    ap.add_argument("--seed", type=int, default=777101)
    ap.add_argument("--geo-only", action="store_true")
    ap.add_argument("--timeout", type=int, default=2400)
    args = ap.parse_args()

    turn = Path(args.turn_dir)
    front_p = turn / "front.png"
    side_p = turn / "side.png"
    back_p = turn / "back.png"
    for p in (front_p, side_p, back_p):
        if not p.is_file():
            print("missing", p)
            return 1

    exports_dir = Path(args.exports)
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_geo = exports_dir / f"{args.name_prefix}_geo.glb"
    out_tex = exports_dir / f"{args.name_prefix}_tex.glb"

    post("/interrupt", {})
    post("/queue", {"clear": True})
    post("/free", {"unload_models": True, "free_memory": True})
    time.sleep(3)

    front = upload(front_p)
    # Multiview node "left" slot: use side profile (right-side photo is fine; volume cue matters)
    left = upload(side_p)
    back = upload(back_p)

    print("[1/2] Multiview geometry (steps=50, octree=384)...")
    prompt_geo = strip_optional(build_mv_geo(front, left, back, args.seed))
    pid = queue(prompt_geo)
    print("queued geo", pid)
    item = wait(pid, args.timeout)
    print("geo status", (item.get("status") or {}).get("status_str"))
    print("geo outputs", item.get("outputs"))
    geo = find_glb("mecha_simple_mv_geo")
    shutil.copyfile(geo, out_geo)
    print("[OK geo]", out_geo, out_geo.stat().st_size)

    if args.geo_only:
        post("/free", {"unload_models": True, "free_memory": True})
        return 0

    post("/free", {"unload_models": True, "free_memory": True})
    time.sleep(4)

    print("[2/2] Multiview geo + delight/paint texture...")
    try:
        prompt_tex = strip_optional(build_mv_geo_and_paint(front, left, back, args.seed + 1))
        pid2 = queue(prompt_tex)
        print("queued tex", pid2)
        item2 = wait(pid2, args.timeout)
        print("tex status", (item2.get("status") or {}).get("status_str"))
        print("tex outputs", item2.get("outputs"))
        tex = find_glb("mecha_simple_mv_tex")
        shutil.copyfile(tex, out_tex)
        print("[OK tex]", out_tex, out_tex.stat().st_size)
    except Exception as e:
        print("[tex failed]", e)
        return 2
    finally:
        post("/free", {"unload_models": True, "free_memory": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
