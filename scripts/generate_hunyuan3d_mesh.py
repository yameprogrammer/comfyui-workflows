#!/usr/bin/env python3
"""Generate 3D Mesh using user's exact 3d_hunyuan3d-v2.1.json workflow via ComfyUI API."""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

DEFAULT_SERVER = "127.0.0.1:8188"

def upload_image(server: str, image_path: Path) -> str:
    url = f"http://{server}/upload/image"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    
    filename = image_path.name
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    
    parts = []
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode("utf-8"))
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(img_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, headers=headers)
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[INFO] Uploaded image: {res.get('name')}")
        return res.get("name")

def build_hunyuan3d_api_prompt(image_filename: str, seed: int = 42, resolution: int = 4096, steps: int = 30, cfg: float = 5.0):
    """Build API format JSON for Hunyuan3D 2.1 matching user's exact ImageOnlyCheckpointLoader workflow."""
    prompt = {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {
                "ckpt_name": "hunyuan3d\\hunyuan_3d_v2.1.safetensors"
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_filename
            }
        },
        "3": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {
                "model": ["1", 0],
                "shift": 1.0
            }
        },
        "4": {
            "class_type": "EmptyLatentHunyuan3Dv2",
            "inputs": {
                "resolution": resolution,
                "batch_size": 1
            }
        },
        "13": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["1", 1],
                "image": ["2", 0],
                "crop": "center"
            }
        },
        "6": {
            "class_type": "Hunyuan3Dv2Conditioning",
            "inputs": {
                "clip_vision_output": ["13", 0]
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecodeHunyuan3D",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["1", 2],
                "num_chunks": 8000,
                "octree_resolution": 256
            }
        },
        "9": {
            "class_type": "VoxelToMesh",
            "inputs": {
                "voxel": ["8", 0],
                "algorithm": "surface net",
                "threshold": 0.6
            }
        },
        "10": {
            "class_type": "SaveGLB",
            "inputs": {
                "mesh": ["9", 0],
                "filename_prefix": "3d/mecha_yame_v1"
            }
        }
    }
    return prompt

def queue_prompt(server: str, prompt_dict: dict) -> str:
    url = f"http://{server}/prompt"
    data = json.dumps({"prompt": prompt_dict}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        prompt_id = res.get("prompt_id")
        print(f"[INFO] Queued prompt ID: {prompt_id}")
        return prompt_id

def track_progress(server: str, prompt_id: str, timeout_sec: int = 300) -> dict:
    url = f"http://{server}/history/{prompt_id}"
    start_time = time.time()
    
    while time.time() - start_time < timeout_sec:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if prompt_id in data:
                    status = data[prompt_id].get("status", {})
                    outputs = data[prompt_id].get("outputs", {})
                    completed = status.get("completed", False)
                    print(f"[INFO] Task status: completed={completed}")
                    if completed or outputs:
                        return data[prompt_id]
        except Exception as e:
            print(f"[WARN] Error polling history: {e}")
        
        time.sleep(3)
    
    raise TimeoutError(f"Hunyuan3D task timed out after {timeout_sec}s")

def main():
    parser = argparse.ArgumentParser(description="Generate 3D mesh using user's exact 3d_hunyuan3d-v2.1 workflow")
    parser.add_argument("--image", required=True, help="Path to input 2D image")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="ComfyUI host:port")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    image_path = Path(args.image).resolve()
    if not image_path.is_file():
        print(f"[ERROR] Image file not found: {image_path}", file=sys.stderr)
        return 1

    print(f"=== Starting Hunyuan3D 2.1 (ImageOnlyCheckpointLoader) ===")
    uploaded_name = upload_image(args.server, image_path)
    prompt_dict = build_hunyuan3d_api_prompt(uploaded_name, seed=args.seed)
    prompt_id = queue_prompt(args.server, prompt_dict)
    result = track_progress(args.server, prompt_id)
    print(f"[SUCCESS] 3D Generation complete!")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0

if __name__ == "__main__":
    sys.exit(main())
