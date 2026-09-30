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

## Clip Duration Limit & Guidelines

- **기준 규격:** 24프레임(fps) 기준, 768P 해상도 기준
- **단일 클립 권장 상한:** **최대 10초** (240프레임)
- **초과 시 처리:** CLI(`generate_ltx25_aio.py`)에서 10.0초를 초과하여 생성 요청 시 경고([WARNING]) 로그가 출력됩니다.
- **장편 연출 가이드:** 10초를 초과하는 긴 컷의 경우 시간축 드리프트 및 모션 뭉개짐 방지를 위해 `flf` (First-Last Frame) 연결이나 `last-frame` 체이닝 방식으로 씬을 분할 생성하십시오.

## Supported CLI Modes

```bash
# 1. Text to Video (Smoke Test)
python scripts/generate_ltx25_aio.py --smoke -p "a glowing jellyfish floating in dark ocean, bioluminescent"

# 2. Text + Audio to Video (S2V)
python scripts/generate_ltx25_aio.py --mode t2v_audio -a voice.wav -p "character speaking with emotion" -o out.mp4 --clip-length 5.0

# 3. Image to Video (I2V, 권장 최대 10초)
python scripts/generate_ltx25_aio.py --mode i2v -i hero.png -p "cinematic camera push-in" -o out.mp4 --clip-length 8.0

# 4. Image + Audio to Video (IA2V / S2V)
python scripts/generate_ltx25_aio.py --mode i2v_audio -i hero.png -a voice.wav -p "character talking naturally" -o out.mp4

# 5. First/Last Frame Interpolation (FLF)
python scripts/generate_ltx25_aio.py --mode flf -i start.png --last end.png -p "smooth motion between poses" -o out.mp4
```
