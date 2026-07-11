# 🤖 Moody ComfyUI 워크플로우 & 파이썬 API 자동화 스크립트

이 저장소는 **Z-Image-Turbo (Flow Matching)** 아키텍처 기반의 Moody 모델 3종(`RealMix`, `ProMix`, `WildMix`)을 연동하여, **신규 이미지 생성(T2I)** 및 **인물 일관성을 유지한 부분 편집/장면 변환(I2I)**을 완전 자동으로 제어하는 워크플로우 및 자동화 스크립트 모음입니다.

---

## 📁 파일 구조

```
agent_custom/
├── T2I-moody.json            # T2I ComfyUI 기본 워크플로우 (Real/Pro/Wild)
├── I2I-moody.json            # I2I ComfyUI 인물 일관성 편집 워크플로우
├── generate_moody.py         # T2I 자동 제어 스크립트
├── generate_moody_i2i.py     # I2I 자동 제어 스크립트 (sampler/CFG 조절 포함)
├── process.md                # 워크플로우 업데이트 및 개발 히스토리 이력서
└── agent_rules.md            # 에이전트 협업 규칙 및 개발 가이드
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

## 📜 개발 및 협업 지침
* 새로운 작업을 진행할 때에는 [process.md](process.md) 최상단에 이력을 추가하십시오.
* 작업 규칙 및 핸드북에 대한 세부 사항은 [agent_rules.md](agent_rules.md)를 참고해 주십시오.

---
> [!NOTE]
> * 본 워크플로우는 로컬 PC에서 ComfyUI 서버가 구동 중인 환경(`127.0.0.1:8188`)을 전제로 동작합니다.
