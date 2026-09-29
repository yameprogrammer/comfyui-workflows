# LTX 2.5 All-In-One Custom — Agent Guide

> **Toolbox shelf:** MOTION / S2V / VIDEO GENERATION  
> **CLI:** `python scripts/generate_ltx25_aio.py`  
> **Source UI:** `workflows/human/ltx25AllInOneWorkflowForRTX_custom.json`

## Overview

This workflow is the modernized LTX 2.5 upgrade of the proven RTX 3060/4090 All-In-One workflow. It preserves all 9 generation modes (T2V, TA2V, I2V, IA2V, FLF, FLFA, FML, FMLA, V2V) while utilizing:
- **Diffusion Model**: `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors`
- **Text Encoder**: `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors`
- **Video VAE**: `ltx-2.5-video-vae-bf16.safetensors`
- **Audio VAE**: `ltx-2.5-audio-vae-bf16.safetensors`
- **Spatial Upscaler**: `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`

## Supported CLI Modes

```bash
# 1. Text to Video (Smoke Test)
python scripts/generate_ltx25_aio.py --smoke -p "a glowing jellyfish floating in dark ocean, bioluminescent"

# 2. Text + Audio to Video (S2V)
python scripts/generate_ltx25_aio.py --mode t2v_audio -a voice.wav -p "character speaking with emotion" -o out.mp4

# 3. Image to Video (I2V)
python scripts/generate_ltx25_aio.py --mode i2v -i hero.png -p "cinematic camera push-in" -o out.mp4

# 4. Image + Audio to Video (IA2V / S2V)
python scripts/generate_ltx25_aio.py --mode i2v_audio -i hero.png -a voice.wav -p "character talking naturally" -o out.mp4

# 5. First/Last Frame Interpolation (FLF)
python scripts/generate_ltx25_aio.py --mode flf -i start.png --last end.png -p "smooth motion between poses" -o out.mp4
```
