# 🤖 Moody T2I 및 I2I 이미지 생성/편집 자동화 가이드

이 문서는 **Z-Image-Turbo (Flow Matching)** 아키텍처 기반의 Moody 모델 3종(`RealMix`, `ProMix`, `WildMix`)을 연동하여, **신규 텍스트 이미지 생성(T2I)** 및 **일관성 유지 이미지 편집/상황 변환(I2I)**을 자동으로 실행하는 에이전트 스크립트 가이드입니다.

**프롬프트 작성 품질 (필수):** [generation_prompt_craft.md](generation_prompt_craft.md) · Rule **7.5**  
(Subject→Action→Setting→Light→Camera · insert/risk 제약 · 태그 수프 금지)

---

## 📁 파일 구조 및 위치
에이전트용 레이아웃 (`agent_custom` 루트 기준):
* **워크플로우 SSOT**: `workflows/agent/` (API 프리셋 우선)
* **I2I 본선 (권장)**: `workflows/agent/presets/lonecat_i2i_identity.api.json` + `.ports.json`
* **I2I 실행 스크립트**: [../scripts/generate_moody_i2i.py](../scripts/generate_moody_i2i.py) → `workflow_api_runner` (기본 프리셋 `lonecat_i2i_identity`)
* **lock / “ipadapter”**: 동일 경로 (`generate_moody_i2i_lock` · `generate_moody_i2i_ipadapter` — inject 없음)
* **T2I 실행 스크립트**: [../scripts/generate_moody.py](../scripts/generate_moody.py) (미니 T2I 잔존 — Phase 2에서 Lonecat T2I로 이전 예정)
* **레거시 미니 I2I**: `I2I-moody.json` — `--legacy-mini` 비상 전용
* 기능 목록: `python scripts/run_workflow_api.py --list-features`

---

## 🛠️ 핵심 최적화 및 디버깅 여정 (Flow Matching I2I 극복)
디버깅 과정에서 Flow Matching 모델 고유의 특성 및 불안정한 커스텀 노드 오작동을 해결하기 위해 아래의 설계 수정을 완료했습니다.
1. **LoRA 매니저 우회 (Direct Wiring)**: 빈 LoRA 입력 시 KSampler 모델 전송이 누락되는 현상을 방지하고자, `ModelSamplingAuraFlow` 및 `CLIPLoader`를 KSampler와 `CLIPTextEncode`에 다이렉트로 결합했습니다.
2. **표준 `CLIPTextEncode` 노드 결합**: 커스텀 프롬프트 인코더가 긍정 조건을 누락시키던 버그를 제거하고 ComfyUI 표준 인코더로 교체하여 프롬프트 가이드 강도가 온전히 수치화되도록 복원했습니다.
3. **타임스텝 시프터 우회**: I2I 과정에서 텐서 시프트 왜곡이 노이즈 융합을 누락시키던 문제를 우회하여 KSampler가 타임스텝 연산을 끝까지 완수하도록 정비했습니다.

---

## 🚀 파이썬 스크립트 사용법 (CLI)

### 1. 신규 이미지 생성 (T2I)
```bash
# 기본 생성 (ProMix 모델 사용)
python scripts/generate_moody.py --model pro --prompt "Cinematic photo of a Korean woman in a cozy coffee shop..."
```

### 2. 이미지 입력 편집 및 일관성 변환 (I2I)
```bash
# Lonecat AIO I2I 프리셋 (기본). 인물 ID 유지 시 denoise ~0.42–0.58
python scripts/generate_moody_i2i.py -i "입력이미지경로.png" -p "holding a sleek modern insulated tumbler" -d 0.55 -m pro -o "출력이미지경로.png"

# 동일 경로, 아이덴티티 문구 + denoise cap
python -c "from generate_moody_i2i_lock import generate_i2i_lock; ..."

# 직접 프리셋 호출
python scripts/run_workflow_api.py -p lonecat_i2i_identity --positive "..." --input-image "..." --denoise 0.55
```

---

## 🎛️ I2I 상황별 디노이즈(Denoise) 스위트 스팟 가이드
Flow Matching 모델은 원본 이미지 결합력(Attractor)이 매우 강하므로, 변환 목적에 따라 **디노이즈(Denoise) 값**을 정밀하게 처방해야 합니다. (모든 I2I 연산 시 **CFG는 3.5 이상**을 강력히 권장합니다.)

| 변환 모드 | 추천 Denoise 범위 | 실제 적용 사례 및 결과 | 설명 |
| :--- | :--- | :--- | :--- |
| **사물 교체 (Local Edit)** | **`0.70 ~ 0.73`** | `output_i2i_tumbler.png` (유리잔 ➡️ 텀블러) | 인물의 포즈, 의상, 조명, 표정, 배경을 100% 동일하게 박제한 채 쥐고 있는 사물 등 국소 부위만 미세 교체합니다. |
| **조명/분위기 변환 (Atmosphere)** | **`0.75 ~ 0.78`** | `output_i2i_night.png` (낮 시간 ➡️ 밤 감성/네온사인) | 전체 구도와 캐릭터는 유지하면서, 창밖의 시간대(낮 ➡️ 밤)와 그에 따른 안면부 음영(Rim Light)을 재배치합니다. |
| **상황/액션/의상 변환 (Consistent Pose)** | **`0.82 ~ 0.86`** | `output_i2i_action.png` (카페 착석 ➡️ 공원 자전거 라이딩) | 인물의 고유 이목구비와 얼굴형 정체성은 그대로 유지하면서, 의상(검은 티 ➡️ 흰 티)과 포즈(자전거 탑승), 배경을 전면 개조합니다. |
| **완전 재창조 (T2I)** | **`0.90 ~ 1.00`** | `output_apple_i2i_test_95.png` (여성 소멸 ➡️ 순수 사물) | 이전의 모든 힌트와 레이아웃을 90% 이상 휘발시키고 완전한 새 이미지를 창조합니다. |

---

> [!IMPORTANT]
> **성공적인 작동 전제 조건**
> * 로컬 PC에 ComfyUI 서버가 구동 중이어야 합니다 (`127.0.0.1:8188`).
> * 스크립트 실행 전 입력 이미지 절대 경로가 올바른지 확인하십시오.
