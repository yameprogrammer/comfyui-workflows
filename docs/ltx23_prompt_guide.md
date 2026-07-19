# LTX 2.3 비디오 프롬프트 최적화 가이드

- **작성:** 2026-07-19  
- **범위:** 에이전트가 LTX 2.3 모델을 사용하여 일관성 있고 움직임이 부드러운 고품질 비디오 클립(I2V/SI2V)을 생성하기 위한 실전 가이드  
- **관련:** [skills/generation-prompt/references/ltx23_video.md](../skills/generation-prompt/references/ltx23_video.md) · [ltx23_clip_extend_guide.md](ltx23_clip_extend_guide.md) · [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md)

---

## 목차

1. [왜 LTX 2.3인가](#1-왜-ltx-23인가)
2. [핵심 프롬프트 문법과 공식](#2-핵심-프롬프트-문법과-공식)
3. [카메라 & 미세 동작 어휘 사전 (Lexicon)](#3-카메라--미세-동작-어휘-사전-lexicon)
4. [매개변수(Parameter) 및 시스템 연동 규칙](#4-매개변수parameter-및-시스템-연동-규칙)
5. [안티 패턴 및 피해야 할 실수](#5-안티-패턴-및-피해야-할-실수)
6. [LTX 2.3 실패 사례 ➜ 교정 레시피 (6대 Case)](#6-ltx-23-실패-사례-➜-교정-레시피-6대-case)
7. [생성 전 체크리스트](#7-생성-전-체크리스트)

---

## 1. 왜 LTX 2.3인가

### 디퓨전 트랜스포머(DiT) 영상 모델의 특성
LTX 2.3은 Flow Matching 기반의 강력한 로컬 오픈소스 비디오 모델입니다.

| 항목 | 상세 |
|:---|:---|
| **강점** | 필름 질감(시네마틱 그레인), 입체적인 카메라 무빙, 물리적 모션의 높은 설득력 |
| **약점** | 100프레임 이상 생성 시 급격한 VRAM 누수 및 얼굴 형태 붕괴(Drift) 현상 |
| **해결책** | **97프레임(≈4초) 하드 캡** 제한 준수 + 선행 클립 마지막 프레임 기반 **Extend 체인 생성** |
| **CFG 범위** | **2.0 ~ 4.0** (기본 **3.0**이 모션의 자연스러움과 프롬프트 준수율의 최적 스윗스팟) |
| **성능 프로필** | `draft` (러프 540p) ➜ `work` (기본 720p) ➜ `hero` (최고화질 1080p) |

---

## 2. 핵심 프롬프트 문법과 공식

LTX 2.3 I2V(Image-to-Video)의 핵심 철학은 다음과 같습니다:
> **"이미지(Image)는 외모와 스타일을 정의하고, 프롬프트(Prompt)는 시간 축 위의 움직임(Temporal Behavior)만 서술한다."**

### 2.1 3대 기본 서술 공식

1. **Simple (단일 카메라 무브 - 가장 권장)**
   - 하나의 명확한 카메라 무브와 미세한 대상의 움직임만 서술합니다.
   - *공식*: `[카메라 무브], [인물/소품 미세 동작], continuous motion throughout, no warp`
   - *예시*: `slow push-in toward face, subtle breathing and hair drift, continuous, no warp`

2. **Chronological (시간순 서술 - 복합 연출)**
   - LTX는 시간에 따른 사건의 전개를 잘 이해합니다. 문장의 순서대로 시간차 액션을 지시합니다.
   - *공식*: `[0-2초 액션]. [2-4초 액션]. [전체 카메라 무빙] throughout. [환경 소리(선택)]`
   - *예시*: `She sits quietly with a neutral expression, then slowly turns her head to look at the camera. Slow dolly forward throughout.`

3. **Extend (클립 연장 - 100프레임+ 장테이크)**
   - 선행 클립의 마지막 프레임을 받아 이어붙일 때 사용합니다.
   - *공식*: `continuing [이전 카메라 무브], [동작의 다음 단계 전개], no jump cut, identity preserved`
   - *예시*: `continuing the slow push-in, she now closes her eyes slowly as rain continues, no jump cut, identity preserved`

---

## 3. 카메라 & 미세 동작 어휘 사전 (Lexicon)

비디오 생성 시 형태 왜곡(Warp)을 방지하고 자연스러운 움직임을 유도하는 최적의 시네마틱 어휘 목록입니다.

### 3.1 카메라 무브먼트 (Camera Movement)
* **줌인/접근**: `slow push-in`, `gentle dolly forward`, `gradual camera approach`
* **줌아웃/멀어짐**: `slow pull-back`, `gentle dolly back`
* **패닝/평행 이동**: `slow pan left/right`, `lateral track`, `horizontal camera glide`
* **틸트/수직 이동**: `slow tilt up/down`
* **고정 샷 (무빙 최소화)**: `static frame`, `locked shot, no camera movement`
* **다이내믹 무빙 (사용 주의)**: `subtle handheld drift` (*whip pan, fast zoom 등은 형태 붕괴 유발로 사용 금지*)

### 3.2 인물 및 환경 미세 동작 (Micro-action)
* **호흡**: `subtle breathing`, `chest micro-rise`
* **눈**: `slow blink`, `eyes glance aside`, `gaze holds lens`
* **헤어/의상**: `hair drift in breeze`, `coat gently sways`
* **소품/물리 현상**: `rain bead slides down glass`, `steam rises from the cup`

---

## 4. 매개변수(Parameter) 및 시스템 연동 규칙

에이전트는 프롬프트를 작성할 때 백엔드 엔진(`lib/ltx_aio_workflow_runner.py`)의 자동 보정 메커니즘을 이해하고 있어야 중복 입력을 막을 수 있습니다.

### 4.1 시스템 자동 인입 내역 (에이전트가 직접 쓸 필요 없음)
* **안면 안정화 접미사**: 엔진에서 자동으로 `"keep facial identity stable, natural micro expression only, no face morph, continuous motion"`을 프롬프트 끝에 덧붙입니다.
* **부정 프롬프트 (Negative)**: 얼굴이 흘러내리거나 붉은 반점이 생기는 현상을 방지하는 강력한 안면 안정화 부정 프롬프트(`FACE_STABILITY_NEGATIVE`)가 백엔드에서 강제 주입됩니다.
  - *주입 내용*: `morphing face, identity shift, face melt, deformed face, red spots on skin, bloody rain...`

### 4.2 생성 해상도 매칭
* **work 프로필**: 반드시 `1280x720` (가로형) 혹은 `720x1280` (세로형) 등 720p를 기준으로 생성합니다.
* **마감 마스터**: 생성 단계에서 1080p/4K를 바로 굽지 않고, 720p 생성 완료 후 별도 `upscale_video.py`로 마감 처리하여 GPU 메모리 OOM과 모션 왜곡을 예방합니다.

---

## 5. 안티 패턴 및 피해야 할 실수

| 금지 패턴 (Anti-pattern) | 이유 | 올바른 방법 |
|:---|:---|:---|
| **의상 및 얼굴 생김새 재서술** | I2V 생성 시 인물 생김새를 또 쓰면 AI가 이미지를 무시하고 얼굴을 새로 그려 왜곡 발생 | 얼굴/의상 묘사는 전면 배제하고, 오직 동작과 카메라 무브만 적음 |
| **추상적 형용사 사용** | `beautiful lighting`, `photorealistic` 등은 모션 모델에 아무 의미가 없음 | `neon spill`, `overcast soft light` 등 실제 물리 조명 용어 사용 |
| **격렬하고 상반된 모션 지시** | `A girl runs forward, then jumps and dances`와 같은 급격한 연출은 신체 붕괴를 유발 | 한 클립(4초) 안에는 오직 하나의 주동작만 서술 |
| **97프레임 초과 일시 생성** | 100프레임이 넘어가는 순간 프레임 간 누적으로 얼굴이 괴물처럼 변함 | 97프레임 단위로 생성 후 `chain_si2v_last_frame.py`로 연장 |

---

## 6. LTX 2.3 실패 사례 ➜ 교정 레시피 (6대 Case)

### Case 1: 인물 이미지를 입력하고 비디오를 뽑았는데, 첫 프레임과 다르게 얼굴이 완전히 다른 사람으로 변할 때
* **증상**: Identity Shift (인물 정보 손실). 프롬프트에 불필요한 얼굴 묘사가 들어가 충돌이 일어남.
* **해결책**: 프롬프트에서 얼굴, 나이, 머리색 묘사를 모두 지우고 모션만 남깁니다.
  * *나쁜 예*: `A Korean girl with brown hair blinks her eyes...`
  * *좋은 예*: `slow blink, subtle breathing, continuous, no warp`

### Case 2: 영상 중간에 갑자기 다른 카메라 앵글로 컷이 튀거나 화면이 순간이동할 때
* **증상**: Teleport / Unwanted Jump Cut. 순차 서술어(`and then`, `after that`)가 오작동함.
* **해결책**: 하나의 카메라 이동 지시만 남깁니다.
  * *교정*: `slow push-in, subtle breathing`으로 단순화하고 뒤쪽 컷 연출은 Extend 체인으로 분리.

### Case 3: 화면 전체가 부글부글 끓거나(Jitter) 자글자글한 노이즈가 발생할 때
* **증상**: Temporal Noise / Jittering. 해상도 규격 불일치 또는 너무 낮은 스텝 수.
* **해결책**:
  - `video_backends.json`에 정의된 `work` 프로필 규격으로 가로/세로 길이를 Divisible by 32 형태로 스냅하여 세팅.
  - 단계 수(Steps)를 25~30으로 유지하고 sampler를 `Euler a`로 고정.

### Case 4: 비디오가 움직이지 않고 멈춘 사진(Slideshow)처럼 끝날 때
* **증상**: Motion Freezing. 모션 에너지가 너무 낮거나 동사(Verb) 부재.
* **해결책**: 프롬프트에 `continuous motion throughout`과 같은 지속성 문구를 수동 기입하고, `hair drift`, `rain falling` 등 환경 애니메이션 요소를 강하게 서술.

### Case 5: 비디오 시작부(1~5프레임)에 급격한 화질 저하나 사각형 깨짐 현상이 보일 때
* **증상**: First Frame Artifact. 입력 이미지 해상도와 비디오 종횡비 불일치로 인한 크롭 오류.
* **해결책**: 입력 키프레임 이미지를 비디오 생성 규격(예: 1280x720)으로 사전에 크기 조정(Resize) 및 크롭하여 입력.

### Case 6: 비 내리는 씬을 생성할 때 빗물이 피처럼 붉게 나오거나 얼굴에 붉은 반점이 돋아날 때
* **증상**: Red Spots Artifact (LTX 고유 색상 튀는 버그).
* **해결책**: 백엔드 부정 프롬프트에 `red spots, bloody rain` 등이 주입되었는지 확인하고, 입력 이미지 자체의 붉은 채도를 다소 낮춰 대비.

---

## 7. 생성 전 체크리스트

- [ ] 단일 생성 프레임 수가 97프레임(≈4초) 이하로 설정되어 있는가?
- [ ] 100프레임 이상의 장컷인 경우, 선행 세그먼트의 last frame extend 분할 계획이 서 있는가?
- [ ] 비디오 프롬프트에 의상, 머리색, 얼굴 생김새를 재설명하는 구절이 전면 배제되었는가?
- [ ] 지시한 카메라 무브먼트가 1개 이하인가? (`push-in`과 `pan` 중복 금지)
- [ ] 프롬프트에 `continuous motion throughout`, `no warp` 등의 예방 키워드가 들어가 있는가?
- [ ] 생성 해상도가 720p(`work` 레벨) 규격으로 올바르게 세팅되었는가?
