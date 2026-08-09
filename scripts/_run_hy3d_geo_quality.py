#!/usr/bin/env python3
import json
import shutil
import time
import urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
IMG = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\master_front.png")
OUT = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2_quality_raw.glb")


def post(path: str, body: dict | None = None) -> bytes:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"http://{SERVER}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> int:
    for path, body in (
        ("/interrupt", {}),
        ("/queue", {"clear": True}),
        ("/free", {"unload_models": True, "free_memory": True}),
    ):
        try:
            post(path, body)
        except Exception as e:
            print("prep", path, e)
    time.sleep(2)

    boundary = "----B"
    raw = IMG.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="mecha_q.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + raw + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"http://{SERVER}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        name = json.loads(resp.read())["name"]
    print("uploaded", name)

    # Kijai example geometry path (research defaults)
    prompt = {
        "1": {"class_type": "LoadImage", "inputs": {"image": name}},
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
                "guidance_scale": 5.5,
                "steps": 50,
                "seed": 515151,
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
                "filename_prefix": "3D/mecha_quality_v2",
                "file_format": "glb",
                "save_file": True,
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
    print("queued", pid)

    t0 = time.time()
    while time.time() - t0 < 900:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as resp:
            hist = json.loads(resp.read())
        if pid in hist:
            item = hist[pid]
            st = item.get("status") or {}
            if st.get("status_str") == "error":
                print(json.dumps(st, ensure_ascii=False)[:3000])
                return 1
            if st.get("completed") or item.get("outputs"):
                print("outputs", item.get("outputs"))
                break
        time.sleep(4)
    else:
        print("timeout")
        return 2

    root = Path(r"F:\ComfyUI_data\output")
    cands = list(root.rglob("mecha_quality_v2*.glb"))
    if not cands:
        cands = list(root.rglob("*.glb"))
    src = max(cands, key=lambda p: p.stat().st_mtime)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, OUT)
    print("OK", src, "->", OUT, OUT.stat().st_size)
    try:
        post("/free", {"unload_models": True, "free_memory": True})
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
