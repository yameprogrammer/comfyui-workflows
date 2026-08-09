#!/usr/bin/env python3
"""Generate sleek mecha_yame_v2 mesh via native Hunyuan3D 2.1 ComfyUI workflow."""

from __future__ import annotations

import json
import random
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
INPUT_IMAGE = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\single_front.png")
ALT_4K = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\single_front_4k.png")
EXPORTS = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")
COMFY_OUT_3D = Path(r"F:\ComfyUI_data\output\3d")
PREFIX = "3d/mecha_yame_v2"


def upload_image(image_path: Path) -> str:
    url = f"http://{SERVER}/upload/image"
    boundary = "----WebKitFormBoundaryMechaYameV2"
    data = image_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    name = res.get("name") or image_path.name
    print(f"[upload] {name}")
    return name


def build_prompt(image_filename: str, seed: int) -> dict:
    # Tuned for cleaner character mesh (not max latent which can mush details)
    return {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": "hunyuan3d\\hunyuan_3d_v2.1.safetensors"},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
        "3": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 1.0},
        },
        "4": {
            "class_type": "EmptyLatentHunyuan3Dv2",
            "inputs": {"resolution": 512, "batch_size": 1},
        },
        "13": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["1", 1],
                "image": ["2", 0],
                "crop": "center",
            },
        },
        "6": {
            "class_type": "Hunyuan3Dv2Conditioning",
            "inputs": {"clip_vision_output": ["13", 0]},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": 40,
                "cfg": 6.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecodeHunyuan3D",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["1", 2],
                "num_chunks": 8000,
                "octree_resolution": 384,
            },
        },
        "9": {
            "class_type": "VoxelToMesh",
            "inputs": {
                "voxel": ["8", 0],
                "algorithm": "surface net",
                "threshold": 0.55,
            },
        },
        "10": {
            "class_type": "SaveGLB",
            "inputs": {
                "mesh": ["9", 0],
                "filename_prefix": PREFIX,
            },
        },
    }


def queue_prompt(prompt: dict) -> str:
    url = f"http://{SERVER}/prompt"
    data = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    pid = res["prompt_id"]
    print(f"[queued] {pid}")
    return pid


def wait_history(prompt_id: str, timeout_sec: int = 600) -> dict:
    url = f"http://{SERVER}/history/{prompt_id}"
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
            if prompt_id in hist:
                item = hist[prompt_id]
                status = item.get("status") or {}
                outs = item.get("outputs") or {}
                if status.get("completed") or outs:
                    print("[done] comfy history ready")
                    return item
                if status.get("status_str") == "error":
                    raise RuntimeError(json.dumps(status, ensure_ascii=False))
        except Exception as e:
            print(f"[poll] {e}")
        time.sleep(4)
    raise TimeoutError("Hunyuan3D timed out")


def find_latest_glb() -> Path:
    # SaveGLB may write under output/3d or output/mesh depending on prefix
    candidates: list[Path] = []
    for root in (COMFY_OUT_3D, Path(r"F:\ComfyUI_data\output\mesh"), Path(r"F:\ComfyUI_data\output")):
        if not root.exists():
            continue
        for p in root.rglob("mecha_yame_v2*.glb"):
            candidates.append(p)
        for p in root.rglob("*mecha_yame_v2*.glb"):
            candidates.append(p)
    if not candidates:
        # fallback newest glb in 3d
        if COMFY_OUT_3D.exists():
            candidates = list(COMFY_OUT_3D.glob("*.glb"))
    if not candidates:
        raise FileNotFoundError("No GLB output found for mecha_yame_v2")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"[glb] {latest} ({latest.stat().st_size} bytes)")
    return latest


def main() -> int:
    img = ALT_4K if ALT_4K.is_file() else INPUT_IMAGE
    if not img.is_file():
        print(f"[ERROR] missing input image: {img}", file=sys.stderr)
        return 1

    EXPORTS.mkdir(parents=True, exist_ok=True)
    seed = random.randint(100_000_000, 999_999_999)
    print(f"[seed] {seed}")
    print(f"[image] {img}")

    filename = upload_image(img)
    prompt = build_prompt(filename, seed)
    pid = queue_prompt(prompt)
    result = wait_history(pid, timeout_sec=900)
    print(json.dumps({"outputs": result.get("outputs"), "status": result.get("status")}, indent=2)[:2000])

    time.sleep(2)
    src = find_latest_glb()
    dst = EXPORTS / "mecha_yame_v2_raw.glb"
    shutil.copyfile(src, dst)
    print(f"[export] {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
