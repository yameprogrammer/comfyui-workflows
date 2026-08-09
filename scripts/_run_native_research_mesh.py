#!/usr/bin/env python3
import json
import shutil
import time
import urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
IMG = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\master_front.png")
OUT = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2_quality_raw.glb")


def main() -> int:
    for path, body in (
        ("/interrupt", {}),
        ("/queue", {"clear": True}),
        ("/free", {"unload_models": True, "free_memory": True}),
    ):
        try:
            req = urllib.request.Request(
                f"http://{SERVER}{path}",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=30)
        except Exception as e:
            print(path, e)
    time.sleep(2)

    boundary = "----X"
    data = IMG.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="mq.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"http://{SERVER}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        name = json.loads(resp.read())["name"]
    print("up", name)

    seed = 616161
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
                "steps": 50,
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
                "filename_prefix": "3d/mecha_research_native",
            },
        },
    }
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        pid = json.loads(resp.read())["prompt_id"]
    print("pid", pid)

    t0 = time.time()
    while time.time() - t0 < 600:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as resp:
            hist = json.loads(resp.read())
        if pid in hist:
            st = hist[pid].get("status") or {}
            if st.get("status_str") == "error":
                print(json.dumps(st, ensure_ascii=False)[:2500])
                return 1
            if st.get("completed") or hist[pid].get("outputs"):
                print("out", hist[pid].get("outputs"))
                break
        time.sleep(3)
    else:
        print("timeout")
        return 2

    cands = list(Path(r"F:\ComfyUI_data\output").rglob("mecha_research_native*.glb"))
    src = max(cands, key=lambda p: p.stat().st_mtime)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, OUT)
    print("OK", src, OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
