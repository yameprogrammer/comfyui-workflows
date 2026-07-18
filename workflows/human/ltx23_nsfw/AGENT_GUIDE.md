# LTX 2.3 Kenpechi v2.0 NSFW (빨간맛 video) — Agent guide

> **Toolbox shelf:** MOTION · **18+ only**  
> **CLI:** `generate_ltx_nsfw_i2v` · `generate_ltx_nsfw_director`  
> **Alternatives:** SFW motion → `generate_i2v` / LTX AIO  
> **Catalog:** [docs/tool_catalog.md](../../docs/tool_catalog.md) §2.4

**Use the real UI workflows.** No mini graphs. No node deletion for “cleanup.”

| Role | UI SSOT |
|------|---------|
| I2V | `ltx23I2VWorkflow_v20.json` |
| Director | `ltx23DirectorWorkflow_directorV20.json` |

Source (Comfy user): `ComfyUI/user/default/workflows/ltx23* v20`  
Factory copy: `workflows/human/ltx23_nsfw/`

## How the agent runs it

```
real UI JSON
  → group switches (Fast Groups Bypasser equivalent)
  → expand_ui_workflow_to_api (bypass = passthrough, never = omit)
  → port inject (image / prompt / seed / size / length)
  → POST /prompt
```

| CLI | Script |
|-----|--------|
| I2V | `python scripts/generate_ltx_nsfw_i2v.py -i first.png -p "..." -o out.mp4` |
| Director | `python scripts/generate_ltx_nsfw_director.py -p "..." -o out.mp4` |
| Profiles | `python scripts/generate_ltx_nsfw_i2v.py --list-profiles` |

## Fast Groups Bypasser (switches)

| Bypasser title | Groups (matchTitle) | Notes |
|----------------|---------------------|--------|
| **GGUF Model** | GGUF model, CLIP GGUF | Default local path (10Eros GGUF) |
| **Safetensors Model & VAE** | Safetensors Model, Video-Audio VAE | Pack couples VAE with safetensors; agent can enable **Video-Audio VAE alone** for GGUF |
| **Include VAE Checkpoint** | Included VAE Checkpoint, Included Audio VAE | Merged ckpt+VAE |
| **Text Encoder** | CLIP Safetensors, Included CLIP | Heretic / ablit CLIP paths |
| **Distilled Lora** | Distilled Lora | ON for 10Eros v1.2 / Dasiwa; OFF for v1.4 + DMD in Power Lora |
| **Sigmas or Steps** | Sigmas **xor** Basic Scheduler | 10Eros packs use **Sigmas** |
| **Sage Attention & Torch Settings** | Sage Attention, Patch Torch Settings | Patch Torch OFF on torch&lt;2.7.1 |
| **RIFE Frame Interpolation** | RIFE **xor** Don't Use RIFE | Need `flownet.pkl` for RIFE |
| **Final Upscale** | RTX Super Resolution, Upscale Model | Optional deliver upscale |
| **IC Lora** (Director) | IC Lora | Only with Director IC feature |

Implementation: `lib/ltx23_nsfw_switches.py`  
Runner: `lib/ltx23_nsfw_workflow_runner.py`

## Default profile `gguf_10eros`

Matches models on this machine:

| ON | OFF (bypass passthrough) |
|----|---------------------------|
| GGUF model, CLIP GGUF, Video-Audio VAE | Safetensors Model, CLIP Safetensors |
| Sigmas, Sage Attention, Ltx Upscale | Checkpoint / Included CLIP+VAE |
| | Distilled Lora, Basic Scheduler |
| | Final Upscale (RTX + Upscale Model) |
| | Patch Torch Settings (torch 2.6 host) |
| Don't Use RIFE (default) | RIFE |

`--profile as_saved` = honor UI modes only (no re-pick).  
`--rife` / `--no-rife` = RIFE switch pair.

## Ports only (no graph surgery)

- `LoadImage` first frame  
- `CLIPTextEncode` positive / negative  
- mxSliders: Base Width/Height, Length (Seconds), FPS  
- `SamplerCustom` seed inside First/Upscale pass  
- `LTXDirector` global_prompt / motion (Director)

## Models (local inventory notes)

| Need | Example path |
|------|----------------|
| GGUF UNet | `diffusion_models/LTX2.3/10Eros_v1-Q4_K_M.gguf` |
| CLIP GGUF | `text_encoders/gemma-3-12b-it-IQ4_XS.gguf` |
| Projection | `text_encoders/ltx-2.3_text_projection_bf16.safetensors` |
| Video/Audio VAE | `vae/LTX23_*_bf16.safetensors` |
| Power Lora slots | Pack may list DMD / bodyphysics / SexGod — **install or turn OFF in UI Power Lora** |

Missing optional Power Lora files will fail load until present or toggled off **in the UI pack** (agent does not rewrite LoRA quality stack).

## Policy

- **Adult 18+ only** (same guard as `generate_krea_nsfw`)  
- SFW motion defaults: `generate_i2v` / `ltx23_aio_*`  
- Single-image erotic clips → **I2V**. Multi-shot camera timeline → **Director**

## Examples

```bash
# Smoke (short)
python scripts/generate_ltx_nsfw_i2v.py \
  -i "F:/generated_images/krea2_nsfw_smoke/krea2_nsfw_smoke.png" \
  -p "adult woman, soft motion..." \
  -o "F:/generated_videos/ltx23_nsfw_smoke/i2v.mp4" \
  --length 2 --width 576 --height 1024 --seed 42 --no-rife

# Production length at pack base size
python scripts/generate_ltx_nsfw_i2v.py -i first.png -p "..." -o out.mp4 --length 7

# Dry-run (expand + switches only)
python scripts/generate_ltx_nsfw_i2v.py -i first.png -p "..." --dry-run
```

## Hard rules

1. Do **not** strip samplers / upscale pass / NAG / Power Lora nodes to “simplify.”  
2. Do **not** rebuild a mini I2V graph.  
3. Turn quality features with **group switches**, same as the UI bypassers.  
4. Bypass (mode 4) = pass-through; Never (mode 2) = omit. Expand must respect both.
