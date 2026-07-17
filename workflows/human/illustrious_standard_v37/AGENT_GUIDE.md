# Standard_V37 — Agent 선택 가이드

**출처(필수 읽기):** [ComfyUI Image Workflows — Legendaer · Civitai](https://civitai.red/models/1386234/comfyui-image-workflows)  
**공식 가이드 아티클:** [articles/17339](https://civitai.red/articles/17339) (로그인 필요할 수 있음)  
**SSOT UI:** `Standard_V37.json` (팩 그대로)  
**CLI:** `python scripts/generate_illustrious_standard.py`  
**기계 메뉴:** `CAPABILITIES.json` · `GROUPS.json`

> 도구 편입·호출 전에 **출처 페이지의 목적·팩 구성**을 먼저 이해한다.  
> JSON 스위치만 나열하고 용도를 비우면 안 된다.

---

## 1. 이 워크플로가 무엇을 위해 만들어졌는가 (출처)

Civitai 모델 카드 한 줄:

> **Workflow for XL / Illustrious / NoobAI Models**

| 항목 | 출처 기준 |
|------|-----------|
| **대상 모델** | SDXL 계열 **Illustrious / NoobAI** (애니·일러스트 체크포인트·LoRA) |
| **역할** | 생성 + 디테일 + 업스케일을 **한 UI에서 스위치로** 다루는 이미지 워크플로 툴 |
| **제작** | Legendaer · 타입 **Workflows** · 베이스 **Illustrious** |
| **Usage Tips** | **Clip Skip: 2** (카드에 명시) |
| **권장 체크포인트 예** | Suggested Resources: **Fabricated XL** (UI 기본 `fabricatedXL_v70`과 동일 계열) |
| **라이선스** | Illustrious License |
| **V37 환경** | ComfyUI **v0.27.0** 기준 제작 |

### 1.1 팩 전체 Key Features (카드 목록)

팩 마케팅에 올라간 기능 묶음:

LoRA · TIPO · Detail Enhancers · ControlNet Upscale · IPAdapter · HiresFix · OpenPose · Wildcards · ControlNET · Color Match · FBCNN · Regional Prompting · Inpaint · Outpaint

→ 이건 **팩 전체(Advanced 중심)** 카탈로그다.  
→ **Standard 한 장에 전부 들어 있지 않다** (아래 §2).

### 1.2 팩 안 워크플로 4종 (카드 정의 — 선택 기준)

| 색 | 이름 | 카드 설명 | 언제 고르나 |
|----|------|-----------|-------------|
| 🟥 | **Advanced** | comprehensive text to image | TIPO / IPA / OpenPose / Regional / 풀 CN 등 **풀 키친** |
| 🟦 | **Standard** | more basic version of the **Advanced** | **일상 생성 기본 드라이버** — 디테일러·하이레스·업스케일까지 포함, Advanced 없이 대부분 컷 |
| 🟨 | **Basic** | more basic version of the **Standard** | 더 가벼운 최소 경로 |
| 🟩 | **Detailer** | detailing **previously generated or existing** images | 이미 있는 이미지 **후처리·인페/아웃페 중심** (V37: Inpaint/Outpaint 갱신) |

**이 레포 도구는 지금 🟦 Standard_V37만 편입.**  
사용자가 “Standard만으로 대부분 되지 않나?” → **카드 정의상 Standard = Advanced의 축소판 = 일상 T2I 메인** 이 맞다.  
TIPO·IPA·OpenPose·Regional이 필요하면 **Advanced를 별도 도구로** 편입한다 (Standard에 가짜로 넣지 말 것).

### 1.3 V37 변경 포인트 (카드 About this version)

- General: 개선·버그픽스, 기본값 변경  
- Advanced: NegPip 추가  
- **Detailer:** Inpainting / Outpainting 업데이트  

→ “인페·아웃페 전문”은 카드상 **Detailer 워크플로** 쪽 강조.  
Standard에도 디테일러·업스케일은 있지만, **기존 이미지 전용 인/아웃페 작업**은 Detailer JSON이 더 맞다.

---

## 2. Standard가 담당하는 범위 (팩 키워드 ∩ 실제 JSON)

| 팩 키워드 | Standard_V37 | 에이전트 의미 |
|-----------|--------------|---------------|
| LoRA | ✅ LoraManager | `--lora-text` |
| Wildcards | ✅ ImpactWildcard | `-p` / `-n` |
| Detail Enhancers | ✅ Face/Hand/Eyes/NSFW ADetailer + generic | `--face` `--hand` `--eyes` … |
| HiresFix | ✅ Pre/Post | `--hires-pre` `--hires-post` |
| ControlNet Upscale | ✅ Ultimate SD Upscale + Canny | `--ultimate-upscale` |
| Color Match | ✅ | `--color-match` |
| ControlNET (일반) | △ 업스케일 경로 위주 | 포즈 CN 풀스택은 Advanced |
| TIPO | ❌ | Advanced (`Z-TIPO`) |
| IPAdapter | ❌ | Advanced |
| OpenPose | ❌ | Advanced |
| Regional Prompting | ❌ | Advanced |
| FBCNN / Compression Removal | ❌ | Advanced |
| Inpaint / Outpaint (전용) | △ 디테일러 인페 성격 / 전용 아웃페 없음 | **Detailer** 워크플로 권장 |

로컬 Advanced_V35 대조: IPA·OpenPose·TIPO·Regional·Body ADetailer 등은 Advanced 전용 그룹.

---

## 3. 어떻게 쓰면 좋은가 (출처 + UI Notes 실무)

### 3.1 기본 사용 루프 (제작자 의도)

```text
1) Illustrious / NoobAI 체크포인트 선택 (Clip Skip 2 유지)
2) Danbooru 스타일 태그 프롬프트 + quality tags
3) Standard로 1차 생성 (기본: Face ADetailer ON)
4) 손/눈 문제 → Hand / Eyes 스위치
5) 해상도·선명도 → Hires post 또는 Ultimate SD Upscale
6) 이미 있는 컷만 손보기 → (이상적) Detailer 워크플로
   또는 Standard I2I (-i + denoise)
7) TIPO/얼굴 레퍼/포즈 강제 → Advanced 필요
```

### 3.2 프롬프트 (워크플로 안 Notes = 제작자 힌트)

**Quality (Illustrious 관례 + NoobAI Note)**

- 자주: `masterpiece, best quality, amazing quality, absurdres`
- NoobAI percentile (UI Note):  
  `very awa` / masterpiece / best quality / good quality / normal / worst quality  
  year: `old` `early` `mid` `recent` `newest`

**조명·스타일·구도 태그 표** — UI Notes 그룹에 표로 있음. 예:

| 의도 | 태그 예 |
|------|---------|
| 시네마틱 광 | `cinematic lighting` |
| 애니 | `anime` / `anime key visual` |
| 샷 | `portrait` `cowboy shot` `full body` `from above` … |
| 팔레트 | `vibrant` `pastel colors` `warm colors` … |

**네거티브 기본(출하):** bad quality, worst detail, bad hands/anatomy, watermark, signature …

### 3.3 해상도 (UI Note 표)

| Low-Res | High-Res (Hires 목표) |
|---------|------------------------|
| 1024×1024 | 1536×1536 |
| 896×1152 | 1152×1536 |
| 832×1216 | 1024×1536 |
| 1344×768 | 1536×864 |

출하 기본 캔버스: **1024×1536** (세로 포트레이트).  
에이전트: 1차는 low-res 표 안에서 생성 → 필요 시 `--hires-post` / ultimate.

### 3.4 샘플러 출하 기본 (Control Center)

steps **28** · cfg **6** · `euler_ancestral` / `normal` · denoise **1.0** (T2I)

### 3.5 추천 시나리오 → preset / 플래그

| 목적 (출처 관점) | 추천 |
|------------------|------|
| 일일 애니 캐릭 생성 | `--preset t2i_face` (기본에 가장 가까움) |
| 빠른 초안·구성 탐색 | `--preset t2i_clean` (디테일러 끔) |
| 손·눈 정리 | `--hand` `--eyes` |
| 선명도·해상도 | `--hires-post` 또는 `--ultimate-upscale` (무거움·CN 필요) |
| 기존 이미지 변형 | `-i` + `-d 0.45~0.65` (`i2i_face`) |
| 기존 이미지 인페/아웃페 중심 | Standard 아님 → **Detailer** 팩 (미편입) |
| 레퍼 얼굴·스타일·포즈·TIPO | Standard 아님 → **Advanced** |

---

## 4. 편입 원칙

| 한다 | 하지 않는다 |
|------|-------------|
| 출처 목적(XL/Illustrious/NoobAI) 유지 | 실사 Z-Image 대용으로 남용 |
| 실 UI JSON + 그룹 스위치 | 미니 T2I 그래프 재작성 |
| Standard 스위치 메뉴를 도구의 가치로 문서화 | “한 경로만”으로 축소 |
| Advanced 키워드는 Advanced 도구로 | Standard에 TIPO/IPA 가짜 구현 |

---

## 5. UI 스위치 구조 (구현 SSOT)

### 5.1 Fast Groups Bypasser

| UI id | matchColors | 대상 |
|-------|-------------|------|
| **2** | pale_blue `#3f789e` | 옵션 기능 대부분 |
| **87** | cyan `#8AA` | Post FX 4종 |

에이전트: `GROUPS.json` node_ids에 `mode=0`(ON) / `mode=4`(BYPASS).

### 5.2 항상 켜짐 (`#444`)

Control Center · Detailer Settings · Image Saver · Notes · Post Processing(bypasser 본체)

### 5.3 ImpactSwitch

| Switch | select=1 | select=2 |
|--------|----------|----------|
| **38** latent | EmptyLatent (T2I) | VAEEncode (I2I) |
| **40** VAE | Checkpoint VAE | Separate VAE |
| **75** →Saver | post 체인 | Signature composite |

---

## 6. 기능 메뉴 (에이전트 선택 목록)

전체: `CAPABILITIES.json` ·  
`python scripts/generate_illustrious_standard.py --list-features`

### Core / Prompt

| feature_id | 기본 | CLI |
|------------|------|-----|
| core_t2i | ON | `-p` `-n` `--seed` size/steps/cfg |
| wildcards | ON | `-p`/`-n` |
| lora_manager | ON(빈) | `--lora-text` |

### Detail Enhancers (카드 “Detail Enhancers”)

| feature_id | 기본 | CLI |
|------------|------|-----|
| face_adetailer | **ON** | `--face` / `--no-face` |
| hand_adetailer | OFF | `--hand` |
| eyes_adetailer | OFF | `--eyes` |
| nsfw_adetailer | OFF | `--nsfw-detailer` (18+, segm 모델) |
| generic_detailer | OFF | `--generic-detailer` |
| use_sam | **ON** | `--no-sam` |

### Model / I2I

| feature_id | 기본 | CLI |
|------------|------|-----|
| clip_skip | **ON** (카드 Clip Skip 2) | `--no-clip-skip` |
| load_image_i2i | OFF | `-i` · `-d` |
| separate_vae | OFF | `--separate-vae` |
| vpred | OFF | `--vpred` (VPred ckpt만) |
| epsilon_scaling / cfg_zero_star | OFF | 해당 플래그 |

### Upscale / Color (카드 HiresFix · ControlNet Upscale · Color Match)

| feature_id | CLI |
|------------|-----|
| hires_pre / hires_post | `--hires-pre` `--hires-post` |
| ultimate_sd_upscale | `--ultimate-upscale` |
| color_match | `--color-match` |

### Signature / Post FX

`--signature` · `--fx-morphology` · `--fx-quantize` · `--fx-sharpen` · `--fx-contrast`

### Presets

| preset | 출처 관점 용도 |
|--------|----------------|
| `t2i_face` | Standard **일상 생성** (출하에 가장 가까움) |
| `t2i_clean` | 빠른 초안 |
| `t2i_face_hand_eyes` | 인물 디테일 풀 |
| `i2i_face` | 기존 이미지 변형 |
| `t2i_hires_face` | 생성 + hires post |

---

## 7. CLI 예제

```bash
# 기능 메뉴
python scripts/generate_illustrious_standard.py --list-features

# 일상 Illustrious 포트레이트 (출처: XL/Illustrious 워크플로)
python scripts/generate_illustrious_standard.py \
  -p "masterpiece, best quality, amazing quality, absurdres, 1girl, solo, portrait, soft lighting" \
  -o out.png --seed 42

# 빠른 탐색
python scripts/generate_illustrious_standard.py --preset t2i_clean -p "1girl, outdoors" -o draft.png

# 디테일 + 하이레스 (카드 Detail Enhancers + HiresFix)
python scripts/generate_illustrious_standard.py -p "1girl, holding cup" --hand --eyes --hires-post -o out.png

# I2I
python scripts/generate_illustrious_standard.py -i ref.png -d 0.55 -p "winter coat, same character" -o i2i.png
```

---

## 8. 포트 (Control Center)

| 포트 | 노드 | 키 |
|------|------|-----|
| positive/negative | 3/4 Wildcard | text |
| seed | 32 | seed |
| width/height | 1/12 | value |
| steps/cfg/sampler/scheduler/denoise | 18 | widgets |
| ckpt | 30 | ckpt_name |
| lora | 5 | text |
| image | 50 | image |

---

## 9. 모델·커스텀 노드

**커스텀:** impact-pack/subpack · rgthree · easy-use · lora-manager · image-saver  

**가중치 체크리스트:** Fabricated XL 등 Illustrious ckpt · face_yolov9c · SAM · Remacri · (ultimate 시) SDXL canny CN · (hand/eyes/nsfw 시) 해당 detector  

---

## 10. 실패 시

1. 출처 카드: **Illustrious 계열 ckpt + Clip Skip 2** 인지 확인  
2. `--preset t2i_clean` 최소 스모크  
3. Ultimate/NSFW는 모델 없으면 켜지 말 것  
4. TIPO/IPA/OpenPose 요구 → Standard가 아니라 Advanced  
5. 미니그래프 응급처치 금지  

---

## 11. 출처 링크

| 문서 | URL |
|------|-----|
| 모델 (V37) | https://civitai.red/models/1386234/comfyui-image-workflows |
| 가이드 아티클 | https://civitai.red/articles/17339 |
| 제작자 | https://civitai.com/user/Legendaer |
