#!/usr/bin/env python3
import json
import shutil
import time
import urllib.request
from pathlib import Path

from rebuild_mecha_yame_v2_pipeline import (
    COMFY_3D,
    GLB_OUT,
    IMG,
    RAW_GLB,
    SERVER,
    TEMP_GLB,
    VRM_COPY,
    VRM_OUT,
    blender_build,
    upload,
)


def queue_fast(name: str, seed: int) -> str:
    prompt = {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": "hunyuan3d\\hunyuan_3d_v2.1.safetensors"},
        },
        "2": {"class_type": "LoadImage", "inputs": {"image": name}},
        "3": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 1.0},
        },
        "4": {
            "class_type": "EmptyLatentHunyuan3Dv2",
            "inputs": {"resolution": 4096, "batch_size": 1},
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
                "cfg": 5.5,
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
                "octree_resolution": 256,
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
                "filename_prefix": "3d/mecha_yame_v2_bighead",
            },
        },
    }
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        try:
            return json.loads(body)["prompt_id"]
        except Exception:
            print(body[:500])
            raise


def wait(pid: str, timeout: int = 600) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h:
            item = h[pid]
            st = item.get("status") or {}
            if st.get("completed") or item.get("outputs"):
                return item
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st))
        time.sleep(3)
    raise TimeoutError("timeout")


def main() -> int:
    # clear queue first
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"http://{SERVER}/interrupt", method="POST", data=b"{}"
            ),
            timeout=10,
        )
    except Exception:
        pass
    time.sleep(1)

    print("img", IMG, IMG.is_file())
    name = upload(IMG)
    print("uploaded", name)
    pid = queue_fast(name, 99001122)
    print("queued", pid)
    item = wait(pid, 600)
    print("outputs", item.get("outputs"))

    cands = sorted(COMFY_3D.glob("mecha_yame_v2_bighead*.glb"), key=lambda p: p.stat().st_mtime)
    if not cands:
        cands = sorted(COMFY_3D.glob("*.glb"), key=lambda p: p.stat().st_mtime)
    src = cands[-1]
    shutil.copyfile(src, RAW_GLB)
    print("raw", src, RAW_GLB.stat().st_size)

    print("blender...")
    res = blender_build()
    payload = res.get("result") if isinstance(res, dict) else res
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:3500])

    if TEMP_GLB.is_file():
        shutil.copyfile(TEMP_GLB, GLB_OUT)
        print("glb", GLB_OUT.stat().st_size)
    if VRM_OUT.is_file() and VRM_OUT.stat().st_size > 10000:
        shutil.copyfile(VRM_OUT, VRM_COPY)
        print("VRM", VRM_OUT.stat().st_size, "has_VRM", b"VRM" in VRM_OUT.read_bytes())
        print("LOAD:", VRM_OUT)
        return 0
    print("VRM FAIL")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
