#!/usr/bin/env python3
"""
Multiview Hunyuan3D (research path) → postprocess → optional paint texture → export GLB.

Uses Kijai Hy3DGenerateMeshMultiView + mv-fast model.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
TURN = Path(r"D:\캐릭터\drafts\mecha_yame_v2\refs\turnaround")
EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
OUT_GEO = EXPORTS / "mecha_yame_v2_mv_raw.glb"
OUT_TEX = EXPORTS / "mecha_yame_v2_mv_textured.glb"
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
    boundary = "----MV"
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["prompt_id"]


def wait(pid: str, timeout: int = 1200) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as resp:
            hist = json.loads(resp.read())
        if pid in hist:
            item = hist[pid]
            st = item.get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st, ensure_ascii=False)[:3500])
            if st.get("completed") or item.get("outputs"):
                return item
        time.sleep(4)
    raise TimeoutError(pid)


def find_glb(prefix: str) -> Path:
    leaf = prefix.split("/")[-1]
    cands: list[Path] = []
    for root in (COMFY_OUT / "3D", COMFY_OUT / "3d", COMFY_OUT):
        if root.exists():
            cands.extend(root.rglob(f"*{leaf}*.glb"))
    if not cands:
        cands = list(COMFY_OUT.rglob("*.glb"))
    latest = max(cands, key=lambda p: p.stat().st_mtime)
    print(f"[glb] {latest} ({latest.stat().st_size})")
    return latest


def build_mv_geo(front: str, left: str, back: str, right: str | None, seed: int) -> dict:
    """Multiview geometry + postprocess + export (example_02 style)."""
    prompt = {
        "1f": {"class_type": "LoadImage", "inputs": {"image": front}},
        "1l": {"class_type": "LoadImage", "inputs": {"image": left}},
        "1b": {"class_type": "LoadImage", "inputs": {"image": back}},
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
                "steps": 40,
                "seed": seed,
                "front": ["1f", 0],
                "left": ["1l", 0],
                "back": ["1b", 0],
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
                "filename_prefix": "3D/mecha_mv_geo",
                "file_format": "glb",
                "save_file": True,
            },
        },
    }
    if right:
        prompt["1r"] = {"class_type": "LoadImage", "inputs": {"image": right}}
        prompt["166"]["inputs"]["right"] = ["1r", 0]
    return prompt


def build_paint_on_mesh(front: str, seed: int) -> dict:
    """
    Load exported mesh isn't easy via API; instead re-run geo+paint in one graph
    by chaining from postprocess like example_01 texture branch.
    For simplicity we re-generate MV geo then paint in one prompt.
    """
    # Front/left/back already uploaded names must be re-passed — caller builds full graph.
    raise NotImplementedError


def build_mv_geo_and_paint(front: str, left: str, back: str, seed: int) -> dict:
    """Full multiview geo + delight + paint texture bake."""
    prompt = build_mv_geo(front, left, back, None, seed)
    # replace export 17 with texture chain from postprocess 203
    del prompt["17"]
    prompt.update(
        {
            "83": {
                "class_type": "Hy3DMeshUVWrap",
                "inputs": {"trimesh": ["203", 0]},
            },
            "28": {
                "class_type": "DownloadAndLoadHy3DDelightModel",
                "inputs": {"model": "hunyuan3d-delight-v2-0"},
            },
            "35": {
                "class_type": "Hy3DDelightImage",
                "inputs": {
                    "delight_pipe": ["28", 0],
                    "image": ["1f", 0],
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
            "88": {
                "class_type": "Hy3DSampleMultiView",
                "inputs": {
                    "pipeline": ["85", 0],
                    "ref_image": ["35", 0],
                    "normal_maps": ["79", 0],
                    "position_maps": ["79", 1],
                    "camera_config": ["61", 0],
                    "view_size": 768,
                    "steps": 25,
                    "seed": seed,
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
                    "renderer": ["129", 2],
                },
            },
            "99": {
                "class_type": "Hy3DExportMesh",
                "inputs": {
                    "trimesh": ["98", 0],
                    "filename_prefix": "3D/mecha_mv_tex",
                    "file_format": "glb",
                    "save_file": True,
                },
            },
            # also export untextured mid for safety
            "17": {
                "class_type": "Hy3DExportMesh",
                "inputs": {
                    "trimesh": ["203", 0],
                    "filename_prefix": "3D/mecha_mv_geo",
                    "file_format": "glb",
                    "save_file": True,
                },
            },
        }
    )
    return prompt


def main() -> int:
    front_p = TURN / "front_regen.png"
    if not front_p.is_file():
        front_p = TURN / "front.png"
    side_p = TURN / "side.png"
    back_p = TURN / "back.png"
    for p in (front_p, side_p, back_p):
        if not p.is_file():
            print("missing", p)
            return 1

    EXPORTS.mkdir(parents=True, exist_ok=True)
    post("/interrupt", {})
    post("/queue", {"clear": True})
    post("/free", {"unload_models": True, "free_memory": True})
    time.sleep(2)

    front = upload(front_p)
    left = upload(side_p)
    back = upload(back_p)
    seed = 777001

    # Stage 1: geometry multiview only (safer)
    print("[1/2] Multiview geometry...")
    pid = queue(build_mv_geo(front, left, back, None, seed))
    print("queued geo", pid)
    item = wait(pid, 1200)
    print("geo status", (item.get("status") or {}).get("status_str"))
    print("geo outputs", item.get("outputs"))
    geo = find_glb("mecha_mv_geo")
    shutil.copyfile(geo, OUT_GEO)
    print("saved", OUT_GEO, OUT_GEO.stat().st_size)

    post("/free", {"unload_models": True, "free_memory": True})
    time.sleep(3)

    # Stage 2: try paint full (may fail on VRAM / nodes)
    print("[2/2] Multiview + paint texture (best effort)...")
    try:
        pid2 = queue(build_mv_geo_and_paint(front, left, back, seed + 1))
        print("queued paint", pid2)
        item2 = wait(pid2, 1800)
        print("paint status", (item2.get("status") or {}).get("status_str"))
        print("paint outputs", item2.get("outputs"))
        tex = find_glb("mecha_mv_tex")
        shutil.copyfile(tex, OUT_TEX)
        print("saved", OUT_TEX, OUT_TEX.stat().st_size)
    except Exception as e:
        print(f"[paint failed] {e}")
        print("continuing with geometry-only mesh")

    post("/free", {"unload_models": True, "free_memory": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
