# 🤖 Moody ComfyUI 워크플로우 & 파이썬 API 자동화 스크립트

이 저장소는 **Z-Image-Turbo (Flow Matching)** 아키텍처 기반의 Moody 모델 3종(`RealMix`, `ProMix`, `WildMix`)을 연동하여, **신규 이미지 생성(T2I)** 및 **인물 일관성을 유지한 부분 편집/장면 변환(I2I)**을 완전 자동으로 제어하는 워크플로우 및 자동화 스크립트 모음입니다.

---

## 📁 파일 구조

```
agent_custom/
├── T2I-moody.json              # T2I ComfyUI 기본 워크플로우 (Real/Pro/Wild)
├── I2I-moody.json              # I2I ComfyUI 인물 일관성 편집 워크플로우
├── I2I-ControlNet-moody.json   # I2I + 공식 ControlNet (Union 2.1) 연동 워크플로우
├── T2I-krea.json               # Krea 2 Turbo T2I ComfyUI 기본 워크플로우
├── generate_moody.py           # T2I 자동 제어 스크립트
├── generate_moody_i2i.py       # I2I 자동 제어 스크립트 (sampler/CFG 조절 포함)
├── generate_moody_controlnet.py # I2I + 컨트롤넷 자동 제어 스크립트 (강도 조절 포함)
├── generate_krea.py            # Krea 2 Turbo T2I 자동 제어 스크립트 (8-steps 고속)
├── video_pipeline_roadmap.md          # 영상 제작 파이프라인 로드맵 (1차 목표/MVP)
├── character_sheet_system_design.md   # 캐릭터 시트 기획·리서치·장기 설계
├── character_impl_spec.md             # 캐릭터 시트 구현 착수 스펙 (코딩 SSOT)
├── characters/                        # 패키지 템플릿·스키마·프리셋·파일럿
│   ├── _template/
│   ├── schemas/
│   ├── sheet_presets.json
│   └── pilots/
├── process.md                         # 워크플로우 업데이트 및 개발 히스토리 이력서
└── agent_rules.md                     # 에이전트 협업 규칙 및 개발 가이드
```

---

## 🚀 파이썬 스크립트 사용법 (CLI)

### 1. 신규 이미지 생성 (T2I)
```bash
# 기본 생성 (ProMix 모델 사용)
python generate_moody.py --model pro --prompt "Cinematic photo of a Korean woman in a cozy coffee shop..."
```

### 2. 이미지 입력 편집 및 일관성 변환 (I2I)
```bash
# 입력 이미지를 활용하여 텀블러로 사물 교체
python generate_moody_i2i.py -i "input.png" -p "holding a sleek modern insulated tumbler" -d 0.70 -c 3.5 -m pro -o "output.png"
```

### 3. 컨트롤넷 연동 자세/구조 제어 (I2I + ControlNet)
```bash
# 인물 원본(-i)의 정체성을 유지하며, 다른 자세 가이드 이미지(-c_img)의 포즈를 강제 추종
python generate_moody_controlnet.py -i "character.png" -c_img "pose_guide.png" -p "Cinematic photo of a Korean woman riding a bicycle..." -d 0.70 -c 3.5 -s 0.80 -m pro -o "output.png"
```

### 4. Krea 2 Turbo 모델을 활용한 고속 이미지 생성 (T2I)
```bash
# euler_ancestral, simple 스케줄러, 8-steps 고속 생성 (F:\generated_images\ 에 저장)
python generate_krea.py --prompt "Futuristic glass sphere floating over a desert landscape, sunset, 8k"
```

---

## 🎛️ I2I 상황별 Denoise 스위트 스팟 가이드
Flow Matching 모델은 원본 이미지의 결합력이 매우 강하므로, 변환 목적에 따라 **디노이즈(Denoise) 값**을 조절해 주어야 합니다. (모든 I2I 연산 시 **CFG는 3.5 이상**을 권장합니다.)

* **사물 교체 (Local Edit)**: `--denoise 0.70`
  * 인물의 포즈, 조명, 의상을 완전히 박제한 채 쥐고 있는 사물(유리잔 ➡️ 텀블러)만 미세 교체합니다.
* **조명/분위기 변환 (Atmosphere)**: `--denoise 0.78`
  * 인물 정체성은 유지하면서 창밖의 시간대(낮 ➡️ 밤)와 실내 조명 톤을 바꿉니다.
* **상황/포즈/의상 변환 (Consistent Pose)**: `--denoise 0.85`
  * 인물의 이목구비 정체성은 그대로 유지하면서, 의상(검은 티 ➡️ 흰 티)과 포즈(자전거 탑승), 배경을 전면 개조합니다.

---

## 🎬 영상 제작 로드맵 (1차 목표)
에이전트가 멋진 영상물을 만들기 위해 필요한 워크플로우 구성·우선순위·MVP 세트는 [video_pipeline_roadmap.md](video_pipeline_roadmap.md)를 참고하십시오.  
현재 T2I/I2I는 완료 상태이며, 다음 핵심은 **I2V + 마감/조립 층**입니다.

## 🎭 캐릭터 시트 시스템 (L2 Soft Factory)
* **기획/리서치**: [character_sheet_system_design.md](character_sheet_system_design.md)
* **구현 스펙**: [character_impl_spec.md](character_impl_spec.md)
* **프리셋·템플릿·프로필**: [characters/](characters/) (`sheet_presets.json`, **`profiles.json`**)
* **용도 프로필** (`--profile`): 기본 `video_ref`(영상 레퍼) · `artbook`(고해상·풀시트) — [profiles.json](characters/profiles.json)

```bash
python character_create.py --id hero --name "Hero" --profile video_ref --from-brief-samples
python character_expand_sheets.py --id hero --profile video_ref --sheets all_mvp
# artbook: 더 큰 해상도 + full-body master + 넓은 MVP
python character_create.py --id hero --name "Hero" --profile artbook --force ...
```

### CLI (ComfyUI `127.0.0.1:8188` 필요)
```bash
# 1) 패키지 + 마스터 후보 (파일럿 샘플 프롬프트)
python character_create.py --id mina_park_v1 --name "Mina Park" --model pro --candidates 4 --from-brief-samples --seed-base 10001

# 2) 마스터 승격
python character_approve.py --id mina_park_v1 --from refs/master/<chosen>.png --as master_front --set-primary

# 3) 시트 확장 (turnaround/expression/costume)
python character_expand_sheets.py --id mina_park_v1 --sheets all_mvp --model pro --candidates 2

# 4) 컷별 승격 예
python character_approve.py --id mina_park_v1 --from refs/turnaround/<chosen>.png --as turn_side

# 5) ControlNet turnaround (auto for turnaround presets; quality still WIP)
python character_expand_sheets.py --id mina_park_v1 --sheets turnaround --engine controlnet --candidates 1

# 6) Story keyframe from approved character pack
python shot_with_character.py --id mina_park_v1 --shot "medium shot in a coffee shop, holding a cup" --template medium_dialogue --expression neutral -d 0.75

# 7) Image-to-Video (Wan2.2 I2V A14B GGUF — requires models already installed)
python generate_i2v.py -i path/to/keyframe.png -p "gentle camera push-in, subtle motion" -o F:\generated_videos\clip.mp4 --width 640 --height 640 --frames 33
```

P1 개선: `generate_moody.py` / `generate_moody_i2i.py` 에 `--seed`, `--prompt-file`, `--meta-out`, I2I `--core-prefix-file` 지원.

## 📜 개발 및 협업 지침
* 새로운 작업을 진행할 때에는 [process.md](process.md) 최상단에 이력을 추가하십시오.
* 작업 규칙 및 핸드북에 대한 세부 사항은 [agent_rules.md](agent_rules.md)를 참고해 주십시오.

---
> [!NOTE]
> * 본 워크플로우는 로컬 PC에서 ComfyUI 서버가 구동 중인 환경(`127.0.0.1:8188`)을 전제로 동작합니다.
