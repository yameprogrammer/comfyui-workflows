#!/usr/bin/env python3
"""Run a Brand New ComfyUI 3D Generation with 100% Valid API Prompt Mapping."""

import json
import random
import time
import urllib.request
import shutil
from pathlib import Path

def run_comfy_generation():
    input_img = Path(r"D:\캐릭터\drafts\mecha_yame_v1\approved\single_front.png")
    
    # 1. Upload Image
    url_upload = "http://127.0.0.1:8188/upload/image"
    with open(input_img, "rb") as f:
        img_bytes = f.read()
        
    boundary = "----WebKitFormBoundaryComfy3DUpload"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="mecha_front_new.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + img_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        url_upload,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as resp:
        up_res = json.loads(resp.read().decode("utf-8"))
        img_filename = up_res.get("name", "mecha_front_new.png")
        
    print(f"[1/4] Image uploaded to ComfyUI: {img_filename}")

    # 2. Build 100% Valid API Prompt Dict
    new_seed = random.randint(1000000000, 9999999999)
    prefix = f"3d/brand_new_mecha_{new_seed}"
    print(f"[2/4] Triggering BRAND NEW 3D generation with seed={new_seed}...")

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
                "image": img_filename
            }
        },
        "3": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {
                "model": ["1", 0],
                "shift": 1
            }
        },
        "4": {
            "class_type": "EmptyLatentHunyuan3Dv2",
            "inputs": {
                "resolution": 4096,
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
                "seed": new_seed,
                "steps": 40,
                "cfg": 6.0,
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
                "octree_resolution": 384
            }
        },
        "9": {
            "class_type": "VoxelToMesh",
            "inputs": {
                "voxel": ["8", 0],
                "algorithm": "surface net",
                "threshold": 0.50
            }
        },
        "10": {
            "class_type": "SaveGLB",
            "inputs": {
                "mesh": ["9", 0],
                "filename_prefix": prefix
            }
        }
    }

    # 3. Post to ComfyUI API
    url_prompt = "http://127.0.0.1:8188/prompt"
    data = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(url_prompt, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        prompt_id = res.get("prompt_id")
        print(f"[3/4] Successfully submitted ComfyUI Prompt ID: {prompt_id}")

    # 4. Monitor execution until completion
    url_hist = f"http://127.0.0.1:8188/history/{prompt_id}"
    print("[4/4] Monitoring ComfyUI 3D Generation execution...")
    for step in range(90):
        time.sleep(3)
        try:
            h_resp = urllib.request.urlopen(url_hist)
            h_data = json.loads(h_resp.read())
            if prompt_id in h_data:
                st = h_data[prompt_id].get("status", {})
                out = h_data[prompt_id].get("outputs", {})
                if st.get("completed", False) or out:
                    print("[SUCCESS] Brand New ComfyUI 3D Generation Finished!")
                    print("Outputs:", json.dumps(out, indent=2))
                    return True, prefix
        except Exception as e:
            print(f"Waiting... ({step*3}s)", e)

    return False, prefix

if __name__ == "__main__":
    success, prefix = run_comfy_generation()
    if not success:
        print("[ERROR] ComfyUI generation failed or timed out.")
