# Qwen-Image 2.1 Low VRAM GGUF Image Edit — Agent Guide

> **Toolbox shelf:** TRANSFORM / EDIT  
> **CLI:** `python scripts/generate_qwen_edit.py --preset qwen_image_21_edit`  
> **Catalog:** `qwen_image_21_edit`  
> **Models:** `Qwen-Image-2.1-Q4.gguf` (UNet GGUF), `qwen3vl_8b_w4a8.safetensors` (Text/Vision Encoder), `qwen_image_2.1_vae_bf16.safetensors` (VAE)

---

## 1. 모델 개요 (What is Qwen-Image 2.1)

Qwen-Image 2.1은 고품질 다중 모달 이미지 생성 및 **정밀 이미지 지시어 편집(Instruction-based Image Editing)**에 특화된 모델입니다.
이 워크플로우는 **Low VRAM(8GB~16GB)** 환경에서도 원활하게 구동되도록 Q4_K GGUF 양자화 확산 모델과 w4a8 텍스트/비전 인코더를 결합하여 구성되었습니다.

### 주요 강점
1. **네이티브 2K (2048×2048) 지원**: 해상도 손실 없이 디테일한 출력 가능.
2. **TextEncodeQwenImage21 노드**: 단일/다중 입력 이미지(멀티 레퍼런스)와 지시어 프롬프트를 직관적으로 인코딩.
3. **QwenImage21Cache 노드**: 모델 캐싱을 통해 샘플링 속도 대폭 향상.
4. **Instruction Edit**: 마스크 없이도 자연어 문장 지시(예: "change the background to night", "the 2 women are taking a selfie at the park")만으로 원본 구도와 인물 특성을 유지하며 편집.

---

## 2. 파일 및 프리셋 위치 (SSOT)

| 역할 | 경로 / 파일명 |
|------|---------------|
| **UI Workflow** | `F:/Agent_media_tools/workflows/human/qwen_image_2.1_edit.json`<br>`F:/ComfyUI_windows_portable/ComfyUI/user/default/workflows/QWEN IMAGE 2.1 EDIT (WORKFLOW).json` |
| **API Workflow** | `workflows/agent/presets/qwen_image_21_edit.api.json` |
| **Ports Config** | `workflows/agent/presets/qwen_image_21_edit.ports.json` |
| **CLI Runner** | `scripts/generate_qwen_edit.py` |
| **Catalog ID** | `qwen_image_21_edit` |

---

## 3. 에이전트 CLI 사용법 (Agent CLI Usage)

### 기본 단일 이미지 편집
```bash
python scripts/generate_qwen_edit.py \
  --preset qwen_image_21_edit \
  -i "path/to/source.png" \
  -p "the person is wearing a red jacket and standing in the snow" \
  -o "path/to/output.png" \
  --seed 42
```

### 다중 레퍼런스(2장) 결합 편집
```bash
python scripts/generate_qwen_edit.py \
  --preset qwen_image_21_edit \
  -i "path/to/char1.png" \
  -i2 "path/to/char2.png" \
  -p "the 2 women are having coffee together in a bright cafe" \
  -o "path/to/output.png"
```

### 해상도 및 샘플러 옵션 조정
```bash
python scripts/generate_qwen_edit.py \
  --preset qwen_image_21_edit \
  -i "path/to/source.png" \
  -p "change background to futuristic cyberpunk neon city" \
  --steps 25 \
  --cfg 1.0 \
  -o "path/to/output.png"
```

---

## 4. 포트 및 기본값 (Ports Specification)

| 포트명 | 대상 노드 | 역할 | 기본값 |
|--------|-----------|------|--------|
| `input_image` | Node 470 (`LoadImage`) | 기본 편집 원본 이미지 (`-i`) | (필수) |
| `positive` | Node 484 (`TextEncodeQwenImage21`) | 편집 지시 텍스트 | (필수) |
| `negative` | Node 484 (`TextEncodeQwenImage21`) | 네거티브 텍스트 | `""` |
| `resolution` | Node 484 (`TextEncodeQwenImage21`) | 타겟 해상도 스케일 | `1024` (0=원본비율) |
| `seed` | Node 481 (`KSampler`) | 샘플링 시드 | 무작위 |
| `steps` | Node 481 (`KSampler`) | KSampler 스텝수 | `25` |
| `cfg` | Node 481 (`KSampler`) | CFG 스케일 | `1.0` |
| `denoise` | Node 481 (`KSampler`) | 디노이즈 강도 | `1.0` |
| `gguf_name` | Node 485 (`UnetLoaderGGUF`) | 확산 모델 GGUF | `Qwen-Image-2.1-Q4.gguf` |
| `clip_name` | Node 477 (`CLIPLoader`) | 텍스트/비전 인코더 | `qwen3vl_8b_w4a8.safetensors` |
| `vae_name` | Node 478 (`VAELoader`) | VAE 모델 | `qwen_image_2.1_vae_bf16.safetensors` |

추가 레퍼런스는 포트가 아니다. CLI `-i2` / `-i3`가 실행 중에 LoadImage를 만들어 노드 484의 `images.image_2` / `images.image_3`에 연결한다. 휴먼 UI의 노드 475는 API 그래프에 없다.

이 프리셋에는 Lightning / `enable_turbo`가 없다. 기본은 steps 25, cfg 1.0. 아이덴티티 접미사는 붙이지 않는다. 유지할 것은 프롬프트에 직접 쓴다.

`workflows/human/qwen_image_2.1_t2i.json`은 휴먼 UI 전용이다. 에이전트 CLI와 카탈로그 엔트리는 없다.

`-o`는 필수이며 이 레포 밖 경로여야 한다.

---

## 5. 도구 선택 가이드 (When to Use)

| 작업 목표 | 추천 도구 | 비고 |
|-----------|-----------|------|
| **최신 Qwen 2.1 네이티브 편집 (2K/GGUF)** | **`generate_qwen_edit --preset qwen_image_21_edit`** | **본 도구** (Low VRAM 4비트) |
| 이전 버전 Qwen Edit (2509/2511) | `generate_qwen_edit` (기본 프리셋) | 2511 Lightning 4스텝 지원 |
| 특정 부위만 마스킹하여 교체 (인페인트) | `generate_qwen_inpaint` | InstantX ControlNet Inpaint |
| 시점 / 각도 변경 (멀티앵글) | `generate_qwen_angle` | 360도 턴어라운드 |
