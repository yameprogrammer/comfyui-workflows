#!/usr/bin/env python3
"""Regenerate mecha_yame_v2 with proven Hunyuan3D settings from user workflow."""
import json, time, shutil, urllib.request
from pathlib import Path

SERVER = "127.0.0.1:8188"
img = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\single_front_4k.png")
if not img.is_file():
    img = Path(r"D:\캐릭터\drafts\mecha_yame_v2\approved\single_front.png")
exports = Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports")

def upload(path: Path) -> str:
    boundary = "----WebKitFormBoundaryRegen"
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
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["name"]

def queue(prompt):
    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["prompt_id"]

def wait(pid, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h:
            item = h[pid]
            if item.get("status", {}).get("completed") or item.get("outputs"):
                return item
            if item.get("status", {}).get("status_str") == "error":
                raise RuntimeError(item["status"])
        time.sleep(4)
    raise TimeoutError("timeout")

name = upload(img)
print("uploaded", name)
seed = 77221401
# Match user workflow defaults that produced solid 7-8MB meshes
prompt = {
    "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {"ckpt_name": "hunyuan3d\\hunyuan_3d_v2.1.safetensors"}},
    "2": {"class_type": "LoadImage", "inputs": {"image": name}},
    "3": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 1.0}},
    "4": {"class_type": "EmptyLatentHunyuan3Dv2", "inputs": {"resolution": 4096, "batch_size": 1}},
    "13": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["1", 1], "image": ["2", 0], "crop": "center"}},
    "6": {"class_type": "Hunyuan3Dv2Conditioning", "inputs": {"clip_vision_output": ["13", 0]}},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["3", 0], "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["4", 0],
        "seed": seed, "steps": 40, "cfg": 5.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0
    }},
    "8": {"class_type": "VAEDecodeHunyuan3D", "inputs": {
        "samples": ["7", 0], "vae": ["1", 2], "num_chunks": 8000, "octree_resolution": 256
    }},
    "9": {"class_type": "VoxelToMesh", "inputs": {"voxel": ["8", 0], "algorithm": "surface net", "threshold": 0.6}},
    "10": {"class_type": "SaveGLB", "inputs": {"mesh": ["9", 0], "filename_prefix": "3d/mecha_yame_v2_hq"}},
}
pid = queue(prompt)
print("queued", pid, "seed", seed)
item = wait(pid)
print("status", item.get("status", {}).get("status_str"), "outputs", item.get("outputs"))

# find newest matching glb
out_dir = Path(r"F:\ComfyUI_data\output\3d")
cands = sorted(out_dir.glob("mecha_yame_v2_hq*.glb"), key=lambda p: p.stat().st_mtime)
if not cands:
    cands = sorted(out_dir.glob("*.glb"), key=lambda p: p.stat().st_mtime)
src = cands[-1]
dst = exports / "mecha_yame_v2_raw.glb"
shutil.copyfile(src, dst)
print("copied", src, "->", dst, "size", dst.stat().st_size)
