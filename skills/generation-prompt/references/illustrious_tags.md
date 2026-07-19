# Illustrious / NoobAI XL tag prompts (T2I / I2I)

**CLI:** `generate_illustrious_standard`  
**When:** Anime / Illustration XL checkpoints (Fabricated XL, NoobAI, WAI, etc.)  
**Not for:** Photoreal MV keyframes on Krea/Z-Image — wrong dialect  
**Related:** [docs/illustrious_prompt_guide.md](../../../docs/illustrious_prompt_guide.md) · [keyframe_production_pipeline.md](../../../docs/keyframe_production_pipeline.md)

---

## ⚠️ 핵심 규칙 (생성 전 필독)

| 규칙 | 내용 |
|------|------|
| **형식 금지** | 자연어 산문(Prose) 기술 금지. 철저히 콤마로 구분된 **단부루(Danbooru) 태그**만 사용 |
| **품질 태그** | Krea와 달리 **`masterpiece, best quality, newest, absurdres`** 사용이 올바름 (필수 포함) |
| **단일 구도** | 서로 충돌하는 구도 태그 동시 사용 금지 (예: `close-up`과 `full body` 동시 스택 금지) |
| **안면 복원** | 원경(Distant View) 및 문제 컷은 **`--face --eyes --hires-post` 삼중 스택** 필수 적용 |

---

## 1. 프롬프트 구조 (5단계 태그 빌더)

Illustrious/NoobAI는 단어 순서에 민감합니다. 아래 순서에 따라 태그를 나열합니다.

```text
[1. 품질 & 안전 태그] , [2. 캐릭터 정보 & 인원수] , [3. 인물 외모 & 복장] , [4. 구도 & 앵글 & 액션] , [5. 배경 & 조명 & 화풍]
```

### 1.1 단계별 세부 가이드

1. **품질 & 안전 태그 (Quality & Safety Prefix)**
   - `masterpiece, best quality, newest, absurdres, very aesthetic, rating_safe` (또는 `safe`)
2. **캐릭터 정보 & 인원수 (Subject & Identity)**
   - `1girl, solo` / `1boy, solo` / `1girl, 1boy, duo`
   - 기존 캐릭터인 경우: `[character name], [series name]` (예: `hatsune miku, vocaloid`)
3. **인물 외모 & 복장 (Appearance & Attire)**
   - 헤어/눈: `blue hair, twin tails, yellow eyes`
   - 옷/복장: `school uniform, white blouse, pleated skirt, black thighhighs`
4. **구도 & 앵글 & 액션 (Composition & Camera & Action)**
   - 구도: `cowboy shot` (바스트~허벅지 기본), `upper body` (상반신)
   - 앵글: `from below` (로우 앵글), `from side` (옆모습)
   - 액션: `holding umbrella, looking at viewer, soft smile`
5. **배경 & 조명 & 화풍 (Setting & Light & Style)**
   - 배경: `rainy day, street, puddle reflections, city backdrop`
   - 조명: `backlighting, neon spill`
   - 화풍: `anime coloring, cel shading, official art style`

---

## 2. 연출 및 카메라 태그 사전 (Lexicon)

일반적인 카메라 연출 문법을 Illustrious 단부루 태그로 일치시킨 매핑 테이블입니다.

### 2.1 샷 크기 (Framing)
* **바스트 샷 (Standard)**: `upper body`
* **미디엄/허벅지 샷 (최적 권장)**: `cowboy shot`
* **얼굴 근접 (CU)**: `close-up`
* **눈/입 초근접 (ECU)**: `macro shot`
* **전신 샷**: `full body` (*인체 붕괴 위험이 높으므로 `--face` 필수 수반*)

### 2.2 카메라 앵글 & 뷰 (Angle & View)
* **로우 앵글 (Low Angle)**: `from below`, `worm's-eye view`
* **하이 앵글 (High Angle)**: `from above`, `bird's-eye view`
* **측면 샷 (Side View)**: `from side`, `profile`
* **뒷모습 (Back View)**: `from behind`, `back view`
* **3/4 각도**: `three-quarter view`
* **사선/기울임**: `dutch angle`

### 2.3 시선 (Eyeline)
* **카메라 응시**: `looking at viewer`
* **시선 회피**: `looking away`, `looking aside`
* **위/아래 응시**: `looking up` / `looking down`

---

## 3. 오리지널 캐릭터(OC) 일관성 유지 공식

새로운 고유 캐릭터의 일관성을 유지하려면 아래 패턴을 따르십시오.

1. **디자인 태그 고정**: 머리색, 헤어스타일, 눈 색, 상의, 하의, 신발 등 고정 외모 태그 묶음을 만듭니다.
2. **주입**: 모든 샷 프롬프트의 3단계(인물 외모/복장) 영역에 이 고정 묶음을 동일하게 복사하여 붙여넣습니다.
3. **구도/동작만 변경**: 4단계(구도/앵글/액션)와 5단계(배경)만 변경하여 컷의 연출을 조정합니다.

---

## 4. 원경 및 문제 컷 복원 정책 (ADetailer & Hires)

원경(Distant View) 컷은 해상도 한계로 인해 얼굴과 눈동자가 심하게 뭉개집니다.

- **기본 복원**: `--face` (얼굴 디테일러)와 `--hires-post` (하이레스 2패스)를 활성화합니다.
- **눈동자 정밀 복원**: `--eyes` (Eyes ADetailer) 모델(`Eyeful_v2-Individual.pt` 등)이 로컬에 배치 완료되었으므로, 이제 `--face --eyes --hires-post` 삼중 스택을 동시에 사용하여 얼굴 전체 윤곽과 안구 세부 디테일을 모두 살립니다.
- **명령어 예시**:
  ```bash
  python scripts/generate_illustrious_standard.py \
    -p "masterpiece, best quality, newest, 1girl, solo, school uniform, cowboy shot, from below, rainy day..." \
    --face --eyes --hires-post \
    -o out_heroic.png
  ```

---

## 5. Quality Gates (Illustrious 검수 기준)

- [ ] 프롬프트 시작부에 `masterpiece, best quality` 등 품질 태그 존재 여부
- [ ] 문장(Prose) 형태가 아닌 콤마(`,`) 구분 태그 나열 형식인가
- [ ] 충돌하는 구도 태그가 동시에 들어가 있지 않은가 (예: `close-up`과 `full body` 공존 금지)
- [ ] 원경 또는 전신(`full body`) 샷인 경우 `--face` 및 `--hires-post` 옵션이 명시되었는가
- [ ] 캐릭터 일관성 유지를 위해 외모 디자인 태그 묶음이 고정되었는가
