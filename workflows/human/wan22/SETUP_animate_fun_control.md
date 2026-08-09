# Wan 2.2 Animate + Fun Control — ComfyUI basic setup

- **Date**: 2026-08-02  
- **Scope**: local ComfyUI portable (`F:\ComfyUI_windows_portable`) + shared models (`F:\model`)  
- **Not in scope**: agent CLI wiring (`generate_*`) — human UI / manual smoke first  

---

## Status checklist

| Piece | Path / node | Status |
|-------|-------------|--------|
| ComfyUI running | `:8188` · v0.28.0 | required |
| Shared models | `extra_model_paths.yaml` → `F:\model` | ✅ |
| **Animate** UNet GGUF | `F:\model\diffusion_models\Wan2.2\Wan2.2-Animate-14B-Q4_K.gguf` | ✅ |
| Animate relight LoRA | `F:\model\loras\Wan2.2\WanAnimate_relight_lora_fp16.safetensors` | ✅ |
| lightx2v speed LoRA | `F:\model\loras\Wan2.2\Wan_2_2_I2V_A14B_*_lightx2v_*` (or T2V lightx2v) | ✅ present |
| Text encoder | `F:\model\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors` (or bf16 enc) | ✅ |
| VAE | `F:\model\vae\wan_2.1_vae.safetensors` | ✅ |
| CLIP Vision | `F:\model\clip_vision\clip_vision_h.safetensors` | ✅ |
| YOLO (Animate preprocess) | `F:\model\detection\yolov10m.onnx` (+ mirror under portable `models/detection`) | ✅ |
| ViTPose Large | `F:\model\detection\vitpose-l-wholebody.onnx` | ✅ |
| **WanAnimatePreprocess** nodes | `custom_nodes/ComfyUI-WanAnimatePreprocess` | ✅ installed 2026-08-02 |
| Human Animate WF | `workflows/human/wan22/wan22_animate.json` | ✅ (planned → human-ready) |
| **Fun Control** High | `F:\model\diffusion_models\Wan2.2\wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors` (~14.3 GB) | ✅ 2026-08-02 |
| **Fun Control** Low | `F:\model\diffusion_models\Wan2.2\wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors` (~14.3 GB) | ✅ 2026-08-02 |
| Native Fun Control WF | `workflows/human/wan22/wan22_fun_control_native.json` | ✅ (Comfy-Org template) |
| Sample assets | `workflows/human/wan22/_fun_control_assets/` | ✅ |
| Depth/Pose preprocess | `comfyui_controlnet_aux` (DepthAnythingV2, OpenPose, DWPose) | ✅ nodes; annotator ckpts auto-download on first use |
| Agent CLI | `wan22_animate` / fun_control backends | ❌ not wired yet |
| **Smoke 2026-08-02** | `scripts/_smoke_wan22_animate_fun_control.py` | ✅ preprocess 17.6s · Fun Control 512²×33f×12step ~231s |

Smoke outputs: `stories/_tool_smoke/wan22_animate_fun_control/`

After **any** new custom_node install or large model add: **restart ComfyUI**.

---

## A. Wan 2.2 Animate (pose retarget / dance)

### Role
Reference video pose → character still → motion clip (`WanVideoAnimateEmbeds` + Animate UNet).

### Custom node
```text
F:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-WanAnimatePreprocess
```
Repo: https://github.com/kijai/ComfyUI-WanAnimatePreprocess  

Embedded Python already has `onnx`, `onnxruntime-gpu` (CUDA), `opencv`.

### Models layout
```text
F:\model\
  diffusion_models\Wan2.2\Wan2.2-Animate-14B-Q4_K.gguf
  loras\Wan2.2\WanAnimate_relight_lora_fp16.safetensors
  loras\Wan2.2\...lightx2v...
  text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors
  vae\wan_2.1_vae.safetensors
  clip_vision\clip_vision_h.safetensors
  detection\yolov10m.onnx
  detection\vitpose-l-wholebody.onnx
```

### How to run (UI)
1. Open ComfyUI → Load `workflows/human/wan22/wan22_animate.json`  
2. After restart, confirm nodes exist: `OnnxDetectionModelLoader`, `PoseAndFaceDetection`, `DrawViTPose`, `WanVideoAnimateEmbeds`  
3. `WanVideoModelLoader` → select `Wan2.2\Wan2.2-Animate-14B-Q4_K.gguf`  
4. Detection loader → `vitpose-l-wholebody.onnx` + `yolov10m.onnx`  
5. Inputs: character still (`LoadImage`) + dance/ref video (`VHS_LoadVideo`)  
6. Start with short clip (≤81 frames @16fps), 640-wide if VRAM tight  

### First smoke expectation
- Pose skeleton overlay looks correct on ref video  
- Output follows large body motion; hands/feet may still wobble  

---

## B. Wan 2.2 Fun Control (pose/depth/canny control video)

### Role
Preprocessed **control video** (pose / depth / edge) + optional start image → structure-locked generation via **native** `Wan22FunControlToVideo`.

Official tutorial: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control  

### Models (Comfy-Org fp8, 4090-friendly)
```text
F:\model\diffusion_models\Wan2.2\
  wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors   ~14.3 GB
  wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors    ~14.3 GB
```

Sources:
- https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/tree/main/split_files/diffusion_models  

Shared deps (already on disk):
- VAE `wan_2.1_vae.safetensors`  
- CLIP `umt5_xxl_fp8_e4m3fn_scaled.safetensors`  
- Optional 4-step LoRA: existing lightx2v I2V high/low under `loras/Wan2.2/`  

### Workflow
- `workflows/human/wan22/wan22_fun_control_native.json` (Comfy-Org template)  
- Samples: `_fun_control_assets/input_start.jpg`, `control_video.mp4` (preprocessed pose plate)

### How to run (UI)
1. Restart ComfyUI after weights finish downloading  
2. Load `wan22_fun_control_native.json`  
3. Point High/Low UNET loaders at the two Fun Control fp8 files  
4. CLIP → umt5 fp8 · VAE → wan_2.1_vae  
5. Start image + control video (pose plate preferred for dance)  
6. Default template size is conservative (e.g. 640² · ~81 frames) — raise carefully on 4090  

### Control map tips
| Goal | Control plate |
|------|----------------|
| Dance / body | **OpenPose / DWPose** video |
| Camera / space | DepthAnythingV2 |
| Hard edges | Canny |

Use `comfyui_controlnet_aux` preprocessors if your control video is raw footage (not already a pose plate).

---

## C. Verify after restart

```powershell
# Node presence (Comfy must be up)
python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8188/object_info')); need=['Wan22FunControlToVideo','WanVideoAnimateEmbeds','OnnxDetectionModelLoader','PoseAndFaceDetection','DepthAnythingV2Preprocessor'];
print({k:('OK' if k in d else 'MISSING') for k in need})"
```

UNET dropdown should list Fun Control filenames under `Wan2.2\...` once files sit in `F:\model\diffusion_models`.

---

## D. Agent factory note

| Tool | Backend status |
|------|----------------|
| `generate_dance_ref` | LTX V2V — ready (draft dance) |
| `wan22_animate` | **planned** — Human WF ready; no agent API inject yet |
| Fun Control CLI | **none** — UI only for now |

Do not treat this setup as episode default I2V (still LTX work/hero).

---

## E. Re-download helpers

```powershell
# Fun Control pair (shared library)
python -c "from huggingface_hub import hf_hub_download; from pathlib import Path; import shutil; o=Path(r'F:/model/diffusion_models/Wan2.2');
for f in ['wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors','wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors']:
  p=hf_hub_download('Comfy-Org/Wan_2.2_ComfyUI_Repackaged', f'split_files/diffusion_models/{f}', local_dir=str(o/'_tmp'));
  src=next((o/'_tmp').rglob(f)); dest=o/f; 
  if not dest.exists() or dest.stat().st_size<1e9: shutil.move(str(src), str(dest)); print('OK', dest)"
```

Detection models (if missing):
- YOLO: https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/blob/main/process_checkpoint/det/yolov10m.onnx  
- ViTPose-L: https://huggingface.co/JunkyByte/easy_ViTPose/blob/main/onnx/wholebody/vitpose-l-wholebody.onnx  
→ place in `F:\model\detection\`
