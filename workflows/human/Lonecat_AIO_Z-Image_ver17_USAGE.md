# Lonecat's AIO Z-Image ver 17 — 사용 방법 (스위치·분기 분석)

> 올인원 워크플로우: **그룹(색/제목) + Fast Groups Bypasser/Muter + Any/Boolean Switch** 로 기능을 켜고 끕니다.  
> 이 문서는 워크플로우 JSON(420 노드 / 45 그룹)을 기준으로 정리했습니다.

**에이전트용 기능 선택 SSOT**

| 문서 | 용도 |
|------|------|
| [Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md](Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md) | feature_id · 의사결정 트리 · 강제 규칙 |
| [Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json](Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json) | bypasser↔그룹↔feature 전체 맵 |
| [../agent/presets/lonecat_feature_presets.json](../agent/presets/lonecat_feature_presets.json) | 프리셋 ready/planned |
| CLI | `python scripts/run_workflow_api.py --list-features` |

| 항목 | 경로 |
|------|------|
| **UI 원본** | `F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\Lonecat's AIO Z-Image ver 17.json` |
| **API export** | `F:\ComfyUI_workflows\agent_custom\workflows\agent\Lonecat_AIO_Z-Image_ver17.api.json` |
| **그룹 덤프** | `F:\ComfyUI_workflows\agent_custom\workflows\human\Lonecat_AIO_Z-Image_ver17_GROUPS.json` |
| **스모크 결과** | `D:\뮤직비디오 작업\소나기_v2\03_키프레임\v3_smoke_lonecat_v17\` |

---

## 0. 조작 철학 (먼저 읽을 것)

1. **큰 기능 on/off** → 화면의 **Fast Groups Bypasser** (제목이 `psst...over here 🤫` 인 것이 많음).  
   - 내부 `matchTitle` 문자열로 **그룹 제목에 그 글자가 들어간 그룹**을 통째로 bypass/mute.
2. **모델 하나만 선택** → `Model selector` (**always one** 제한).
3. **값 분기** → `Any Switch (rgthree)` (입력 여러 개 중 하나 통과).  
   - 보통 **위에 연결된 입력 = any_01**, 아래 = any_02 (연결 순·슬롯 확인).
4. **본 생성 엔진** → `🧠 Brains` 그룹 + Clownshark 2-pass 샘플러.
5. **사용자 손대는 구역** → 대부분 **`⚙️ User Settings`** (흰 배경 그룹).

rgthree 규칙 요약:

| 컨트롤 | 하는 일 |
|--------|---------|
| **Fast Groups Bypasser** | 매칭 그룹 전체를 bypass (실행 스킵, 링크 유지) |
| **Fast Groups Muter** | 매칭 그룹 mute |
| **Fast Bypasser** | 직접 연결된 개별 노드 bypass (그룹 매칭 아님) |
| **toggleRestriction: always one** | 해당 바이패서 묶음 중 하나만 활성 |
| **toggleRestriction: max one** | 최대 하나만 (전부 off 가능) |

---

## 1. 기능 스위치 보드 (Bypasser → 영향 그룹)

`matchTitle` 은 **그룹 제목 부분 문자열 매칭**입니다.

| Bypasser id | UI에서 보이는 이름 | matchTitle | 켜면/끄면 영향 받는 그룹 | 용도 |
|-------------|-------------------|------------|---------------------------|------|
| **1329** | **Model selector** | `Model` | `Diffusion Model`, `GGUF Model`, `Checkpoint Model` (+ Loaders 쪽 모델 관련) | **모델 계열 선택 (always one)** |
| **1318** | **Bypasser** | `#` | 제목에 `#` 가 있는 **옵션 기능 그룹 다수** | 해시 옵션 묶음 마스터 토글 |
| **2028** | psst… 🤫 | `!` | `# …!` 로 끝나는 강조 옵션 (`🖼️Load Image!`, `I2I 🖼️!`, `Remove Background!` 등) | 이미지 입력·I2I·배경제거 계열 |
| **2029** | psst… 🤫 | `📝 Img Prompt` | `# 📝 Img Prompt` | 이미지 기반 캡션/프롬프트 보조 |
| **1867** | psst… 🤫 | `Prompt` | `# Qwen Prompt Enhancer`, `# 📝 Img Prompt` 등 Prompt 포함 그룹 | **LLM/프롬프트 강화 전체** |
| **1863** | psst… 🤫 | `#  Seed` | `# Seed Variance`, `# Seed VR2 Upscale` | 시드 분산 / SeedVR2 업스케일 |
| **2046** | psst… 🤫 | `Hi Rez Fix/ Upscale` | `# Hi Rez Fix/ Upscale`, `Hi Rez fix & Upscale` | **Ultimate 등 Hi-res 업스케일** |
| **2034** | psst… 🤫 | `🥅` | `# 🥅Controlnet` | **ControlNet** |
| **1866** | psst… 🤫 | `Klein Inpaint 🖌️` | `# Klein Inpaint 🖌️` (+ Inpaint 연계) | **인페인트** |
| **2094** | pssst… 🤫 | `::` | `# ::Face 🙂` `# ::Eyes 👀` `# ::Hands ✋` `# ::Spare 🛞` | **디테일러 부위별** |
| **1872** | **Group switches** | `📷` | `Optical Realism 📷`, `✂️Crop 📷` | 광학 보정·크롭 후처리 |
| **2031** | **Picture or Mask?** | `'` | `Create Mask'`, `Load Mask'` | 마스크 생성 vs 로드 |
| **1874** | **Post processing selector** | (개별 Fast Bypasser) | Post 계열 개별 노드 | 후처리 세부 |
| **1708** | **Meta 📂📅+** | (개별) | 저장 메타/날짜/서브폴더 관련 | 저장 옵션 |
| **2100** | **LLM Prompt Instructions** | (개별, max one) | Instruct (Beta) 쪽 | LLM 시스템 지시문 |
| **1068** | **Options** | Fast Muter | 옵션 노드 mute | 잡옵션 |

### 실사용 예

| 하고 싶은 것 | 이렇게 |
|--------------|--------|
| 순수 T2I만 | Model=Turbo 유지 · **Prompt/Qwen off** · **Load Image / I2I off** · **ControlNet off** · Detailer·Upscale는 취향 |
| I2I | **`!` 바이패서로 Load Image·I2I on** · Latent Switch=encode · Denoise 낮춤 |
| 얼굴 디테일만 | **🔎 Detailers on** · `::` 바이패서에서 Face on, 나머지 off 가능 |
| 4K | **Hi Rez Fix/Upscale on** 또는 **Seed VR2 on** (동시 풀가동 주의) |
| 포즈 고정 | **🥅 ControlNet on** + 이미지 로드 |

---

## 2. 그룹 맵 (화면 박스 전체)

색은 대략적인 UI 구역 구분입니다.

### 2.1 입력·이미지 (`Image suite` 주변, 왼쪽)

| # | 그룹 | 색 | 역할 |
|---|------|-----|------|
| 44 | **Image suite** | 파랑 | 이미지 입력 구역 부모 |
| 31 | **# 🖼️Load Image!** | 보라 | 소스 이미지 로드 |
| 29 | **# I2I 🖼️!** | 보라 | I2I 활성 관련 |
| 30 | **# 📝 Img Prompt** | 연보라 | 이미지→캡션/프롬프트 |
| 28 | **# Remove Background!** | 파랑 | 배경 제거 |
| 32 | **# 🥅Controlnet** | 분홍 | ControlNet |
| 25 | **Create Mask'** | 파랑 | 마스크 생성 |
| 26 | **Load Mask'** | 파랑 | 마스크 로드 |

### 2.2 모델·로더 (금색)

| # | 그룹 | 역할 |
|---|------|------|
| 9 | **Loaders 💩** | 로더 모음 |
| 3 | **Diffusion Model** | ZIT UNET (예: `ZImageTurbo\…`) |
| 4 | **GGUF Model** | 저VRAM GGUF |
| 5 | **Checkpoint Model** | 병합 CKPT |
| 6 | **Sampler Select** | Base/ZIT 샘플러 프리셋·스위치 (초록) |

→ **Model selector (1329)** 로 3/4/5 중 하나 계열만 켜기.

### 2.3 사용자 설정·두뇌

| # | 그룹 | 역할 |
|---|------|------|
| 33 | **⚙️ User Settings** | 시드, 비율, denoise, 품질 프롬프트 등 **손대는 메인 패널** |
| 42 | **🧠 Brains** | 실제 샘플링·모델 패치·생성 코어 |
| 43 | **🥱 to 🤡 regexes** | Clownshark 샘플러명 regex 변환 (v17) |
| 17 | **Settings** | 보조 설정 |
| 2 | **# Seed Variance** | 시드 분산 강화 |
| 8 | **# Qwen Prompt Enhancer** | QwenVL GGUF 프롬프트 확장 (**llama_cpp 필요**) |
| 41 | **Instruct (Beta)** | LLM 시스템 지시 (Realistic/Photographic/NSFW 등) |

### 2.4 인페인트·드래프트

| # | 그룹 | 역할 |
|---|------|------|
| 15 | **Inpaint** | 인페인트 본체 |
| 16 | **# Klein Inpaint 🖌️** | Klein 계열 인페인트 |
| 0 | **Final vs. Rough Draft** | 최종본 vs 러프 드래프트 비교/분기 |

### 2.5 디테일러 (연두 부모 + 파란 자식)

| # | 그룹 | 역할 |
|---|------|------|
| 36 | **🔎 Detailers** | 디테일러 스위트 전체 |
| 37 | **# ::Face 🙂** | 얼굴 |
| 38 | **# ::Eyes 👀** | 눈 |
| 39 | **# ::Hands ✋** | 손 |
| 40 | **# ::Spare 🛞** | 여분 슬롯 |

→ **`::` 바이패서(2094)** 로 부위 on/off.

### 2.6 업스케일

| # | 그룹 | 역할 |
|---|------|------|
| 1 / 34 | **Hi Rez Fix/Upscale** | Ultimate SD Upscale 등 |
| 18 | **Seed VR2 …** | SeedVR2 본체 |
| 20 | **# Seed VR2 Upscale** | SeedVR2 업스케일 토글 단위 |

### 2.7 후처리·저장

| # | 그룹 | 역할 |
|---|------|------|
| 21 | **🎨 Post Processing Suite** | 후처리 스위트 |
| 23 | **Optical Realism 📷** | 광학 리얼리즘 |
| 22 | **✂️Crop 📷** | 크롭 |
| 10 | **💾 Save Group** | 저장 부모 |
| 11 | **#Save Mask🎭** | 마스크 저장 |
| 12 | **#Save Draft 📐** | 드래프트 저장 |
| 13 | **#Save w/Metadata🗒️** | 메타 포함 저장 |
| 14 | **#Create Subfolder📂** | 날짜/이름 서브폴더 |

---

## 3. 값 분기 스위치 (Any Switch / Boolean)

실행 중 **어느 입력을 쓸지** 고르는 노드입니다. UI에서 스위치 노드를 클릭해 활성 입력을 확인하세요.

| id | 이름 | 기능 |
|----|------|------|
| **1330** | **Model switch** | Diffusion / GGUF / 기타 모델 출력 중 그래프에 물릴 것 |
| **1562** | **Modelname Switch** | 파일명·메타용 모델 표시 이름 |
| **1331** | **Clip switch** | CLIP/텍스트 인코더 경로 |
| **1391** | **VAE Switch** | VAE (`ae.safetensors` 등) |
| **1800** | **Latent Switch** | **any≈원본 VAEEncode(I2I)** vs **EmptyLatent(T2I)** |
| **1351** | **Step switch** | 스텝 수 (Base vs ZIT Config) |
| **1354** | **CFG Switch** | CFG |
| **1355** | **Sampler Switch** | 샘플러 이름 |
| **1356** | **Scheduler Switch** | 스케줄러 |
| **1353** | **Ref step switch** | 리파이너/레퍼런스 스텝 |
| **2120** | **Regex Switch** | Clownshark 정규화 전/후 샘플러명 |
| **1069** | **🛑 switch** | 이미지 파이프 안전 분기 (업스케일 전 등) |
| **1778** | **IMG pass \switch** | 이미지 패스 분기 |
| **1923 / 1925** | color match / bypass | 컬러 매치 on·off |
| **1893** | **Optical Real switch** | Optical Realism 적용 여부 |
| **1890** | **crop bypass Switch** | 크롭 적용 여부 |
| **1806 / 1807** | Height/Width Sw | 해상도 소스 분기 |
| **2010 / 2011** | **boolean width/height** | 크롭·리사이즈 시 가로/세로 우선 (기본 False) |
| **2098** | Any Switch | Instruct/시스템 프롬프트 선택 분기 |

### Latent Switch (1800) — 특히 중요

| 선택 | 의미 | denoise 가이드 |
|------|------|----------------|
| **EmptyLatent** (1808) | 순수 T2I | **1.0** |
| **VAEEncode** (2017←리사이즈된 LoadImage) | I2I | **0.35–0.75** (얼굴 유지면 낮게) |

---

## 4. User Settings에서 만질 핵심 위젯

| 항목 | 노드 힌트 | 권장 |
|------|-----------|------|
| **장면 프롬프트** | `easy positive` (빈 슬롯 / id≈1342) | 샷 action 영문 |
| **품질 태그** | `Quality Prompt` easy positive | `photorealistic, detailed skin…` 유지 가능 |
| **네거티브** | `easy negative` | Turbo에선 약함 (노트: Not used for Turbo) |
| **시드** | `Seed (rgthree)` | 재현 시 fixed |
| **시드 분산** | Seed Variance 그룹 | 다양성 필요 시 on |
| **비율·해상도** | `CR Aspect Ratio Social Media` (≈1305) | 시네마 **1024×576** 등 |
| **Denoise** | mxSlider 제목 `Denoise` (≈2041/2056) | T2I=1.0, I2I=0.4–0.65 |
| **Base 샘플러 프리셋** | `KSampler Base` Config | steps~30, cfg~4, res_multistep… |
| **ZIT 샘플러 프리셋** | `KSampler ZIT` Config | steps~8–11, cfg~1, euler/simple |
| **LoRA** | Power Lora Loader (rgthree) | 필요 슬롯만 on |
| **파일 접두사** | DF_Text `Filename Prefix` | 기본 `Lonecats Z-Image Ver 17` |

### 모델별 권장 (워크플로우 노트 id≈1258)

**Z-Image Turbo**

- steps **9–11**
- cfg **1.0–2.0**
- clip last layer **-2**

**Z-Image Base**

- steps **25–30**
- cfg **4.0**
- sampler **res_multistep**, scheduler **simple/sgm 계열**
- clip last layer **-1**

---

## 5. 기능별 레시피 (버튼 순서)

### 5.1 빠른 T2I (스모크·컨셉)

1. **Model selector** → Diffusion/Turbo UNET  
2. **Prompt / Qwen / Img Prompt** → **OFF** (의존성·시간 절약)  
3. **Load Image / I2I (`!`)** → **OFF**  
4. **ControlNet** → OFF  
5. **Latent Switch** → EmptyLatent  
6. **Denoise** → 1.0  
7. User Settings에 프롬프트·시드·비율  
8. Detailer/Upscale → 선택 (처음엔 OFF 권장)  
9. Queue  

### 5.2 캐릭터 I2I (키프레임 유지)

1. **`!` 바이패서** → Load Image·I2I **ON**  
2. LoadImage에 마스터/포즈 플레이트  
3. **Latent Switch** → **VAEEncode(원본)**  
4. **Denoise** → **0.40–0.55** (얼굴), 장면 많이 바꾸면 0.55–0.70  
5. 프롬프트는 **변경점 위주**  
6. Qwen enhancer → 끄거나, 켜면 원본 캡션이 덮일 수 있음  
7. ControlNet은 포즈 고정 시에만  

### 5.3 ControlNet

1. Load Image ON  
2. **🥅 ControlNet** 바이패서 ON  
3. Union ControlNet 패치/strength 조절  
4. 비율 맞춘 뒤 Queue  
5. 끌 때: 그룹 bypass (중간 스위치만 어중간하게 두지 말 것)

### 5.4 Detailer (얼굴/눈/손)

1. 1차 생성 또는 I2I 후  
2. **🔎 Detailers** 영역 활성  
3. **`::` 바이패서**로 Face/Eyes/Hands 선택  
4. Detailer Prompt (`realistic eyes` 등) 확인  
5. VRAM 부족 시 부위 하나씩  

### 5.5 Upscale

| 목표 | 조작 |
|------|------|
| 일반 Hi-res | **Hi Rez Fix/Upscale** ON, SeedVR2 OFF |
| 최대 해상도 | **Seed VR2 Upscale** ON (VRAM·시간 큼) |
| 둘 다 | 단계적 권장 (한 번에 풀가동 비권장) |

### 5.6 Inpaint

1. **Klein Inpaint / Inpaint** ON  
2. 마스크: **Picture or Mask?** 로 Create vs Load  
3. **Inpainting prompt** easy positive에 수정 지시  
4. 나머지 전역 denoise와 혼동하지 말 것  

### 5.7 Post / Color / Crop

1. **Post processing selector** / **📷 Group switches**  
2. Optical Realism, Color match(레퍼 LoadImage), Crop 슬라이더  
3. 최종 저장 전 토글  

### 5.8 저장

1. **💾 Save Group** 하위: Draft / Metadata / Mask / Subfolder  
2. **Meta 📂📅+** 로 메타·날짜 폴더  
3. Filename Prefix 변경 시 에피소드명 넣기  

---

## 6. Set/Get 버스 (내부 허브 이름)

그래프 전역으로 값이 복사되는 이름입니다. API 패치 시 참고.

| Bus 이름 | 의미 |
|----------|------|
| Positive / Negative | 조건 임베딩 |
| postext / Negtext | 텍스트 프롬프트 문자열 |
| Seed | 시드 |
| Width / Height / W1 / H1 / W2 / H2 | 해상도 |
| Model / Clip / Lora Model / Model Patch | 모델 파이프 |
| Sampler / Scheduler / Steps / CFG | 샘플러 설정 |
| Upscale factor / Upscale Image | 업스케일 |
| Inpaint Image / Maskimg / OrgMask / Org pic | 인페인트·원본 |
| detail image / Detailer Steps | 디테일러 |
| Prompt Tag / Instruct / prefix / Metadata | 프롬프트·저장 메타 |
| Rough Draft / RD Post Stop / Pro Post / VR2 image | 드래프트·후처리·VR2 |

---

## 7. 에이전트·API 사용 시

1. UI에서 **원하는 기능 조합으로 바이패서 설정** (이 문서 레시피).  
2. **Save (API Format)** 또는 `graphToPrompt` 로 export → 기능 세트별 파일 분리 권장.  
   - 예: `Lonecat_v17_t2i_turbo.api.json`, `Lonecat_v17_i2i_face.api.json`  
3. API에서 바꿀 것: 프롬프트, seed, LoadImage 파일명, denoise, width/height.  
4. 주의:  
   - **Anything Everywhere / SetGet** 은 export 시 latent·VAE 링크 누락 가능 → T2I 시 EmptyLatent+VAE 확인.  
   - **QwenVL GGUF** 는 `llama_cpp` 없으면 Prompt 그룹 OFF 상태로 export.  
5. 소나기 스모크: Qwen OFF + Turbo + denoise 1.0 + 1024×576 로 검증 완료.

---

## 8. 빠른 치트시트

| 목적 | ON | OFF | 핵심 값 |
|------|----|-----|---------|
| 빠른 T2I | Turbo Model | Qwen, LoadImage, CN | denoise **1.0** |
| 캐릭터 I2I | LoadImage, I2I, Latent=encode | Qwen(선택) | denoise **0.4–0.55** |
| 포즈 고정 | ControlNet + LoadImage | — | strength 중~고 |
| 얼굴 보정 | Detailers ::Face | Spare 등 불필요 부위 | detailer prompt |
| 2K/4K | Hi Rez 또는 SeedVR2 | 동시 풀가동 | factor |
| 부분 수정 | Inpaint + mask | 전체 detailer 과다 | inpaint prompt |
| 색 맞추기 | Color match + ref | — | strength |
| 저장 정리 | Metadata + Subfolder | — | prefix |

---

## 9. 의존성 (풀 기능 시)

스모크 환경에서 추가로 필요했던 패키지 예:

- `DemonAlone-nodes-ComfyUI` → BooleanSwitchNode  
- `comfy-mtb` → String Replace (mtb) (Clownshark regex)  
- `ComfyUI-LevelPixel` → RemoveDuplicateTags\|LP  
- `SeedVarianceEnhancer`  
- `SAM3_SmartInpainter`  
- `ComfyUI-post-processing-nodes` → ChromaticAberration  
- Qwen 인핸서 사용 시: **llama_cpp / GGUF vision** + 해당 GGUF 가중치  

---

## 10. 관련 파일

| 파일 | 내용 |
|------|------|
| `Lonecat_AIO_Z-Image_ver17_USAGE.md` | **이 문서 (사용법 SSOT)** |
| `Lonecat_AIO_Z-Image_ver17_GROUPS.json` | 그룹 멤버·바이패서·스위치 기계 가독 덤프 |
| `Lonecat_AIO_Z-Image_ver17.api.json` | API 포맷 워크플로우 |
| `Lonecat_AIO_Z-Image_ver17.api.ports.json` | API 노드 중 텍스트/시드 포트 인덱스 |

---

*분석 기준: Lonecat's AIO Z-Image ver 17 UI JSON (groups/bypass matchTitle/switches/notes).*  
*Civitai: Z-Image Base & Turbo Pro Grade Workflow — V17.0 Sampler Options (lonecatone23).*
