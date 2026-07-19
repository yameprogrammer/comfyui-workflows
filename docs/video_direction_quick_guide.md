# 🎬 디렉터 파이프라인 퀵 가이드 (기획에서 최종 영상까지)

- **작성**: 2026-07-19
- **대상**: 유저(기획 감독) 및 에이전트(공작소 제작자)
- **목적**: 기획력 부재로 인한 영상 퀄리티 저하를 막고, 내장된 `video-direction` 스킬을 활용하여 고품질 연출 영상을 제작하기 위한 단계별 가이드.
- **관련**: [video-direction/SKILL.md](../skills/video-direction/SKILL.md) · [krea2_prompt_guide.md](krea2_prompt_guide.md) · [ltx23_clip_extend_guide.md](ltx23_clip_extend_guide.md)

---

## 📌 핵심 연출 원칙 (3대 하드 룰)

1. **선 기획, 후 생성 (No Spine, No Pixels)**: `CREATIVE.md`와 `SHOT_DESIGN.md`가 유저에게 승인받기 전에는 단 한 장의 이미지도 생성하지 않는다.
2. **리듬감 있는 샷 배치 (Size Rhythm)**: 동일 크기의 샷을 3번 연속 쓰지 않는다. (와이드 → 미디엄 → 클로즈업 → 인서트 교차 배치)
3. **LTX 97프레임 상한 (4초 룰)**: 단일 모션 생성은 97프레임(≈4초)으로 제한하며, 더 긴 컷은 last-frame extend 방식으로 늘려간다.

---

## 🛠️ 1단계: 에이전트 기획 시동 걸기 (Copy-Paste 지시문)

영상을 시작할 때 유저가 에이전트에게 아래 지시문을 복사해서 전달합니다. 이 지시문을 받으면 에이전트는 기획 감독 페르소나를 장착하고 기획에만 집중합니다.

```text
[로그라인/소재]: "여기에 당신의 스토리나 로그라인을 입력하세요. (예: 비 오는 밤, 편의점 파라솔 아래 서 있는 슬픈 표정의 여자)"

[지시 사항]:
1. 바로 이미지를 생성하지 마라.
2. `video-direction` 스킬(skills/video-direction/SKILL.md)을 장착하라.
3. 위 로그라인을 바탕으로 1) 중심 패러독스, 2) 3대 비주얼 모티브, 3) 5대 안티 리스트(피해야 할 클리셰)가 포함된 CREATIVE.md 기획안 초안을 작성하여 보고하라.
4. 이어서 카메라 크기(Size Rhythm)와 무빙이 명시된 4~5컷의 SHOT_DESIGN.md를 작성하라.
5. 내가 확인하고 승인(Proceed)하기 전까지는 ComfyUI CLI 생성을 대기하라.
```

---

## 📝 2단계: 기획서 작성 템플릿 및 예시

에이전트는 위 지시를 받으면 `stories/<에피소드_ID>/` 폴더 아래에 다음 두 문서를 작성합니다.

### 1. `CREATIVE.md` (비주얼 컨셉)
* **중심 패러독스**: 따뜻한 실내 불빛 vs 차갑게 젖은 밤거리의 대비.
* **3대 비주얼 모티브**:
  1. 노란색 편의점 파라솔 (유일한 따뜻한 원색)
  2. 일회용 플라스틱 컵 표면의 물방울 (클로즈업 초점 포인트)
  3. 젖은 아스팔트 위의 네온사인 반사광 (배경 무드)
* **안티 리스트 (피해야 할 연출)**:
  - 노래 가사를 그대로 설명하는 슬라이드쇼 식 연출 금지.
  - 계속 얼굴 클로즈업만 반복되는 단조로운 편집 금지.
  - 마스터피스, 8k 등 무맥락한 프롬프트 태그 사용 금지.
  - 인물의 의상이나 얼굴이 프레임마다 갑자기 바뀌는 현상(teleport) 방지.

### 2. `SHOT_DESIGN.md` (샷 상세 설계)
* **사이즈 리듬**: `LS (넓게) ➜ MS (중간) ➜ Insert (소품 디테일) ➜ CU (인물 클로즈업) ➜ LS (아웃트로)`

| 샷 ID | 크기 | 카메라 앵글 & 무빙 | 연출 의도 (액션) | 모션 드라이버 |
|-------|------|-------------------|------------------|---------------|
| **S01** | **LS** | eye level, slow push-in | 비 내리는 편의점 전경, 노란 파라솔 아래 서 있는 인물 | `i2v` |
| **S02** | **MS** | slight low, static | 파라솔 아래 인물 상반신, 고개를 살짝 돌려 밤거리를 응시 | `i2v` |
| **S03** | **Insert** | macro close, tilt-down | 손에 들린 플라스틱 컵 표면을 타고 흘러내리는 빗물 | `i2v` (소품) |
| **S04** | **CU** | eye level, static | 인물의 얼굴 클로즈업, 천천히 눈을 감았다가 뜨는 미세 표정 | `si2v` or `i2v` |

---

## 🎨 3단계: Krea2 키프레임 생성 및 QA

기획안이 승인되면 에이전트는 **Krea2**를 사용하여 대표 이미지를 생성합니다.

```bash
# 에이전트가 실행할 Krea2 T2I 명령어
python scripts/generate_krea.py \
  -p "Photoreal cinematic film still, medium shot, slight low angle. A solitary mid-20s Korean woman stands under a yellow nylon parasol..." \
  -o keyframe.png --seed 42
```

### 🔍 이미지 검수 게이트
이미지가 나오면 에이전트와 유저는 다음 사항을 체크합니다.
- [ ] 손가락이 5개로 정상이고 해부학적 결함이 없는가?
- [ ] 노란 파라솔과 젖은 아스팔트 등 모티브가 적절히 묘사되었는가?
- [ ] 결함이 있다면 `generate_qwen_inpaint.py`로 마스크 수정 작업을 먼저 거쳤는가?
- [ ] 최종 키프레임을 `upscale_image.py --backend seedvr2`로 고화질 업스케일 하였는가?

---

## 🎬 4단계: LTX2.3 분할 모션 및 Extend 체인

영상의 움직임을 만들 때는 **단일 클립 97프레임(≈4초)** 제한 룰을 따릅니다. 8초짜리 긴 컷을 기획했다면 다음과 같이 2개 세그먼트로 나누어 제작합니다.

### 1세그먼트 (0~4초) 생성:
```bash
python scripts/generate_i2v.py \
  -i keyframe_hero_1080.png \
  -p "slow push-in toward face, subtle breathing, continuous, no warp" \
  --frames 97 \
  -o cut01_seg01.mp4
```

### 2세그먼트 (4~8초) 선행 마지막 프레임에서 연장(Extend):
```bash
python scripts/chain_si2v_last_frame.py \
  --prev cut01_seg01.mp4 \
  -p "continuing push-in, she slowly faces the camera, eyes hold lens, rain continuous, no jump cut" \
  --frames 97 \
  -o cut01_seg02.mp4
```

### 하나로 이어붙이기:
```bash
python scripts/assemble_single_take.py \
  --clips cut01_seg01.mp4 cut01_seg02.mp4 \
  -o cut01_final.mp4
```

---

## 💡 유저 실전 팁 (Tip)

- **기획 단계에서 질답하기**: 에이전트가 올린 `CREATIVE.md`가 평이하다면, "패러독스를 조금 더 쓸쓸하게 바꾸고 모티브에 시든 꽃을 추가해줘"라고 지시하여 뼈대를 다듬으세요.
- **모션 프롬프트 검수**: I2V 단계에서 에이전트가 "빨간 외투를 입은 여자가 걸어간다"처럼 인물 묘사를 재서술하는 실수를 하면 지적해주세요. 모션 단계는 오직 **움직임(slow push-in, hair drift)**만 서술해야 형태 붕괴가 없습니다.
