#!/usr/bin/env python3
"""Generate a BRAND NEW high-quality 3D Model in ComfyUI from scratch with new seed and parameters."""

import json
import random
import time
import urllib.request
import shutil
from pathlib import Path

def queue_brand_new_hunyuan3d():
    single_img_path = Path(r"D:\캐릭터\drafts\mecha_yame_v1\approved\single_front.png")
    
    # 1. Upload image to ComfyUI
    url_upload = "http://127.0.0.1:8188/upload/image"
    with open(single_img_path, "rb") as f:
        data = f.read()
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="brand_new_mecha_input.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        url_upload,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as resp:
        up_res = json.loads(resp.read().decode("utf-8"))
        img_filename = up_res.get("name", "brand_new_mecha_input.png")
    print(f"[1/4] Uploaded brand new input image to ComfyUI: {img_filename}")

    # 2. Build brand new workflow prompt
    new_seed = random.randint(100000000, 999999999)
    print(f"[2/4] Generating BRAND NEW 3D Model with seed={new_seed}...")

    wf_path = r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\3d_hunyuan3d-v2.1.json"
    with open(wf_path, "r", encoding="utf-8") as f:
        wf = json.load(f)

    prompt = {}
    for n in wf["nodes"]:
        node_id = str(n["id"])
        class_type = n["type"]
        inputs = {}
        
        if class_type == "ImageOnlyCheckpointLoader":
            inputs["ckpt_name"] = n["widgets_values"][0]
        elif class_type == "LoadImage":
            inputs["image"] = img_filename
        elif class_type == "ModelSamplingAuraFlow":
            inputs["model"] = ["1", 0]
            inputs["shift"] = n["widgets_values"][0]
        elif class_type == "EmptyLatentHunyuan3Dv2":
            inputs["resolution"] = 384
            inputs["batch_size"] = 1
        elif class_type == "CLIPVisionEncode":
            inputs["clip_vision"] = ["1", 1]
            inputs["image"] = ["2", 0]
            inputs["crop"] = "center"
        elif class_type == "Hunyuan3Dv2Conditioning":
            inputs["clip_vision_output"] = ["13", 0]
        elif class_type == "KSampler":
            inputs["model"] = ["3", 0]
            inputs["positive"] = ["6", 0]
            inputs["negative"] = ["6", 1]
            inputs["latent_image"] = ["4", 0]
            inputs["seed"] = new_seed
            inputs["steps"] = 50
            inputs["cfg"] = 7.5
            inputs["sampler_name"] = "euler"
            inputs["scheduler"] = "normal"
            inputs["denoise"] = 1.0
        elif class_type == "VAEDecodeHunyuan3D":
            inputs["samples"] = ["7", 0]
            inputs["vae"] = ["1", 2]
            inputs["num_chunks"] = 1000
            inputs["octree_resolution"] = 384
        elif class_type == "VoxelToMesh":
            inputs["voxel"] = ["8", 0]
            inputs["algorithm"] = "surface net"
            inputs["threshold"] = 0.50
        elif class_type == "SaveGLB":
            inputs["mesh"] = ["9", 0]
            inputs["filename_prefix"] = "3d/brand_new_mecha"
        elif class_type == "MarkdownNote":
            continue

        prompt[node_id] = {
            "class_type": class_type,
            "inputs": inputs
        }

    # 3. Submit to ComfyUI
    url_prompt = "http://127.0.0.1:8188/prompt"
    data = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(url_prompt, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        prompt_id = res.get("prompt_id")
        print(f"[3/4] Queued ComfyUI Prompt ID: {prompt_id}")

    # 4. Wait for completion
    url_hist = f"http://127.0.0.1:8188/history/{prompt_id}"
    print("[4/4] Waiting for ComfyUI 3D Generation to complete (approx 30s)...")
    for _ in range(90):
        time.sleep(3)
        try:
            h_resp = urllib.request.urlopen(url_hist)
            h_data = json.loads(h_resp.read())
            if prompt_id in h_data:
                st = h_data[prompt_id].get("status", {})
                out = h_data[prompt_id].get("outputs", {})
                if st.get("completed", False) or out:
                    print("[SUCCESS] Brand New 3D Generation Completed!")
                    print("Outputs:", json.dumps(out, indent=2))
                    return True
        except Exception as e:
            print("Polling status...", e)

    return False

if __name__ == "__main__":
    success = queue_brand_new_hunyuan3d()
    if not success:
        sys.exit(1)
