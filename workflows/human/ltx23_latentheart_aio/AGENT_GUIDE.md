# LatentHeart LTX2.3 AIO (Director) — Agent 가이드

**출처:** [LTX2.3 All in one SFW/NSFW — LTX Director + ID LoRA + ControlNet + Detailer + Upscaler + Interpolator](https://civitai.red/models/2553704/ltx23-all-in-one-sfw-nsfw-ltx-director-id-lora-controlnet-detailer-upscaler-interpolator)  
**제작:** LatentHeart · base **LTXV 2.3** · v4.0 zip `LTX23_v4.zip`  
**로컬 SSOT:**

| 파일 | Director 노드 |
|------|----------------|
| `LTX23LTXDirector2.json` | **v2** (기본) |
| `LTX23LTXDirector13.json` | v1.3 (구 노드 호환) |

**CLI:** `python scripts/generate_ltx23_latentheart.py`  
**원칙:** 실 UI 유지 · 스위치/그룹 mode · **GGUF 우선** · 미니그래프 금지 · 카탈로그 자유 선택 (본선 강제 없음)

---

## 1. 출처 목적

모듈형 **T/I/A2V** 시스템 (ComfyUI):

- LTX Director 타임라인 (텍스트/이미지/오디오 세그먼트)
- 모델 3종 **독립 그룹** (안 쓰는 그룹 꺼도 됨)
- ID LoRA (보이스 클로닝) · ControlNet · Half-res + 2× upscaler · Detailer · Nvidia VSR · RIFE
- SFW / NSFW (10Eros 권장 NSFW, standard distilled 권장 SFW)

**지원 모델 (카드):** Standard distilled · distilled **GGUF** · 10Eros  

**에이전트 기본:** `gguf_distilled` — 로컬  
`LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf`  
(팩 기본 STANDARD fp8은 메모리 부담 큼)

---

## 2. 두 워크플로 차이

| | Director13 | Director2 |
|--|------------|-----------|
| LTX Director 노드 | v1.3 | **v2** |
| 기능 세트 | 동일 계열 | 동일 계열 + v2 타임라인 필드 |
| 핫픽스 노트 | 구 환경 | v2 일부 신기능(편집/retake 등) 미검증 가능 |

기본 호출: `--director-version 2`  
구 노드만 있으면: `--director-version 13`

---

## 3. 스위치 맵 (세심)

### 3.1 QUICK MODEL SELECTOR (`matchTitle=LTX2.3 MODEL`, **max one**)

| 그룹 | 출하 | 에이전트 GGUF 프로필 |
|------|------|----------------------|
| `LTX2.3 MODEL [STANDARD]` | ON (fp8 UNET) | OFF |
| `LTX2.3 MODEL [GGUF]` | OFF (mode 4) | **ON** |
| `LTX2.3 MODEL [10EROS]` | OFF | OFF (또는 별도 프로필) |

카드: 안 쓰는 모델 그룹은 꺼도 나머지 독립 동작.

**에이전트 GGUF 로딩:** 팩은 `GGUFLoaderKJ`(unet_gguf 폴더).  
로컬 가중치는 `diffusion_models` → expand 후 **`UnetLoaderGGUF` 스왑** (그래프 구조 유지, 로더 클래스만).

### 3.2 기능 그룹 (Bypasser titles)

| feature_id | 그룹 제목 | 출하 | 메모 |
|------------|-----------|------|------|
| `half_resolution` | Half resolution | 혼합 | 카드: 2-pass 품질 권장 (480p 이하는 1-pass) |
| `controlnet` | Controlnet conditioning | OFF | IC-LoRA track 무시, 전용 CN 그룹 사용 |
| `id_lora` | ID LoRA conditioning (voice) | OFF | 보이스 샘플 + ID LoRA |
| `ltx_2x_upscaler` | LTX 2x Upscaler | OFF | half-res와 세트 권장 |
| `ltx_detailer` | LTX Detailer | OFF | 아마추어 룩에는 비권장 (카드) |
| `nvidia_vsr` | Nvidia VSR upscaler | OFF | |
| `interpolation` | Interpolation (RIFE) | OFF | |
| `image_reference` | Image reference | OFF | 프롬프트 인핸서 레퍼 |
| `lipsync_enhancer` | Lipsync enhancer | OFF | MelBand 등 — 미설치 시 자동 NEVER |
| `prompt_enhancer` | Prompt enhancer | 혼합 | Heretic NSFW 이슈 카드에 언급 |

색 힌트: brown = sampling (half/upscaler/detailer), cyan = optional, red = extra, black = VRAM opts.

### 3.3 공통 셋업 (카드 → 에이전트)

| 셋업 | 요약 |
|------|------|
| T2V | Director 타임라인 text segment |
| I2V | image segment + duration + segment prompt |
| Lipsync | image segment + audio + custom audio |
| A2V | text segment + audio |
| Char LoRA + voice | Power LoRA + ID LoRA ON |
| CN animation | image segment + ControlNet ON |
| FFLF | image segment ×2 (끝 세그먼트 prompt `.`) |

---

## 4. 프로필

```bash
python scripts/generate_ltx23_latentheart.py --list-profiles
```

| profile | 내용 |
|---------|------|
| **`gguf_distilled`** | GGUF distilled Q4 · 헤비 후처리 OFF · **기본** |
| `gguf_10eros` | 같은 GGUF 그룹 + 10Eros Q4 파일 |
| `gguf_half_upscale` | half-res + LTX 2× upscaler ON |
| `as_saved` | 모드 유지 |

```bash
python scripts/generate_ltx23_latentheart.py --list-features
python scripts/generate_ltx23_latentheart.py -p "..." -o out.mp4 --profile gguf_distilled
python scripts/generate_ltx23_latentheart.py -p "..." -o out.mp4 --profile gguf_half_upscale
python scripts/generate_ltx23_latentheart.py -p "..." --director-version 13 -o out.mp4
```

---

## 5. 로컬 모델 (GGUF 위주)

| 역할 | 경로 (`models/`) |
|------|------------------|
| Distilled GGUF | `diffusion_models/LTX2.3/LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf` |
| 10Eros GGUF | `diffusion_models/LTX2.3/10Eros_v1-Q4_K_M.gguf` |
| TE | `text_encoders/gemma_3_12B_it_fp8_e4m3fn.safetensors` + `ltx-2.3_text_projection_bf16.safetensors` |
| VAE | 팩: `LTX23_video_vae_bf16` / audio vae (로컬 파일명 확인) |

ID LoRA / IC-LoRA 파일이 없으면 러너가 해당 **LoraLoader 소비자를 업스트림 모델로 재배선** (노드 삭제 아님).

---

## 6. 호스트 주의

- `enable_fp16_accumulation` → **False** (torch &lt; 2.7.1)
- MelBand / ChatterBox 등 **미설치 노드** → lipsync 관련 mode NEVER
- Director 타임라인 풀 편집(API)은 복잡 — 1차 포트는 **global/base prompt + seed + GGUF 프로필**
- 풀 스모크는 해상도·Director 세그먼트 준비 후 권장

---

## 7. Kenpechi `ltx23_nsfw` 와의 관계

| | LatentHeart AIO (이 도구) | Kenpechi NSFW (`ltx23_nsfw`) |
|--|---------------------------|------------------------------|
| 출처 | LatentHeart 2553704 | Kenpechi v2.0 packs |
| 범위 | SFW+NSFW 모듈 AIO | NSFW I2V/Director 특화 |
| CLI | `generate_ltx23_latentheart` | `generate_ltx_nsfw_*` |

둘 다 카탈로그 도구 — 에이전트가 목적에 맞게 고름.

---

## 8. 커스텀 노드 (카드 목록 요약)

ComfyUI-LTXVideo · WhatDreamsCost LTX Director · rgthree · KJNodes · Impact · VHS · controlnet_aux · Frame-Interpolation · Nvidia RTX nodes · Easy-Use · LayerStyle · cg-use-everywhere · CRT-Nodes · (TTS-Audio-Suite for director voice)
