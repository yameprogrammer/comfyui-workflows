# Qwen InstantX Inpainting ControlNet — Agent guide

**Use the real UI workflow.** No mini graph rebuild.

| Item | Path |
|------|------|
| **UI SSOT** | `workflows/human/image_qwen_image_instantx_inpainting_controlnet.json` |
| **Runner** | `lib/qwen_instantx_inpaint_runner.py` |
| **CLI** | `scripts/generate_qwen_inpaint.py` |
| **Catalog** | `qwen_instantx_inpaint` |

Comfy source: `user/default/workflows/image_qwen_image_instantx_inpainting_controlnet.json`

## What this pack is

Official-style **masked inpainting** for Qwen-Image using **InstantX ControlNet Inpainting** (`ControlNetInpaintingAliMamaApply`).

Useful when instruction-only edit (`generate_qwen_edit`) is too global — e.g. change only a hand/object/region while locking the rest via mask + composite.

## Graph structure (as shipped)

```
[Active — Inpainting, mode 0]
LoadImage (IMAGE + MASK)
  → ImageScaleToMaxDimension (≤1536)
  → VAEEncode
  → Grow+Blur Mask subgraph (GrowMask → MaskToImage → Blur → ImageToMask)
  → ControlNetInpaintingAliMamaApply (InstantX CN)
  → SetLatentNoiseMask
  → KSampler (default 20 / CFG 2.5 / euler / simple / denoise 1)
  → VAEDecode
  → ImageCompositeMasked  (paste original unmasked pixels back)
  → SaveImage ×2 (raw + composite)

[Bypassed — mode 4, not deleted]
  Outpainting branch (ImagePadForOutpaint + second loaders/sampler)
  Lightning 4-step LoraLoader (Ctrl-B in UI)
```

Expand omits mode-4 branches the same way Fast Groups / bypass works — **nodes stay in the JSON**.

## Models (this machine)

| Role | File | Status |
|------|------|--------|
| **UNet (agent default)** | `QwenImage/Qwen-Image-Edit-2509-Q5_K_M.gguf` via **LoaderGGUF** | present |
| UNet light | `QwenImage/qwen-image-edit-2511-Q4_K_M.gguf` (`--gguf-light`) | present |
| UNet pack fp8 | `qwen_image_edit_2509_fp8_e4m3fn` (`--fp8`, heavy ~20GB) | present |
| CLIP | `qwen_2.5_vl_7b_fp8_scaled.safetensors` | present |
| VAE | `qwen_image_vae.safetensors` | present |
| ControlNet | `controlnet/Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` | present |
| Lightning (optional) | Edit-2511 Lightning if `--lightning` | alternate present |

Agent keeps the pack graph; only node **37** is swapped `UNETLoader` → `LoaderGGUF` (same as `qwen_edit_2509`).

## Agent CLI

```bash
# Separate mask (recommended for agents): white/red = region to edit
python scripts/generate_qwen_inpaint.py \
  -i photo.png --mask mask.png \
  -p "replace the cup with a ceramic mug, same lighting" \
  -o out.png --seed 42

# Dry-run expand + ports
python scripts/generate_qwen_inpaint.py -i photo.png -p "..." --dry-run

# Optional faster Lightning path (rewires LoRA onto UNet; default stays 20-step)
python scripts/generate_qwen_inpaint.py -i photo.png -m mask.png -p "..." --lightning

# Lower VRAM GGUF
python scripts/generate_qwen_inpaint.py -i photo.png -m mask.png -p "..." --gguf-light

# Pack original fp8 (needs free VRAM)
python scripts/generate_qwen_inpaint.py -i photo.png -m mask.png -p "..." --fp8
```

### Ports (injected only)

| Port | Pack node | Notes |
|------|-----------|--------|
| image | LoadImage `71` | required |
| mask | optional external → GrowMask `121:199` | else LoadImage.MASK |
| prompt | CLIPTextEncode `6` | positive |
| negative | CLIPTextEncode `7` | default space |
| seed/steps/cfg/denoise | KSampler `3` | pack default 20 / 2.5 / 1.0 |
| cn_strength | ControlNet apply `108` | default 1.0 |
| max_dim | ImageScaleToMaxDimension `172` | default 1536 |
| grow_mask / blur | subgraph Grow/Blur | edge soft |

## When to use which Qwen tool

| Task | Tool |
|------|------|
| Global instruction edit | `generate_qwen_edit` (`qwen_edit_2509`) |
| Multi-view / angle | `generate_qwen_angle` |
| **Region inpaint / object replace** | **`generate_qwen_inpaint`** (this pack) |
| Soft denoise I2I identity | Lonecat `generate_moody_i2i` |

## Hard rules

1. Do **not** strip ControlNet / composite / mask subgraph to “simplify.”  
2. Do **not** invent a 5-node mini inpaint graph as mainline.  
3. Outpaint = enable that group in UI (or future profile); default agent path is **inpaint only**.  
4. Mask quality dominates results — prefer explicit `--mask` for agents.

## Reference KSampler table (from pack note)

| | Qwen Team | Comfy original | 4-step LoRA |
|--|-----------|----------------|-------------|
| Steps | 50 | **20** (default active) | 4 |
| CFG | 4.0 | **2.5** (default active) | 1.0 |
