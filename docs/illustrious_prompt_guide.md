# Illustrious / NoobAI-XL 프롬프트 최적화 가이드

- **작성:** 2026-07-19  
- **범위:** 에이전트가 Illustrious 및 NoobAI 모델을 사용해 일관성 있는 고품질 애니메이션/일러스트 키프레임을 생성하기 위한 실전 가이드  
- **관련:** [skills/generation-prompt/references/illustrious_tags.md](../skills/generation-prompt/references/illustrious_tags.md) · [keyframe_production_pipeline.md](keyframe_production_pipeline.md)

---

## 목차

1. [왜 Illustrious/NoobAI인가](#1-왜-illustriousnoobai인가)
2. [핵심 프롬프트 구조 — 5단계 태그 빌더](#2-핵심-프롬프트-구조--5단계-태그-빌더)
3. [일러스트 특화 연출 태그 사전 (Lexicon)](#3-일러스트-특화-연출-태그-사전-lexicon)
4. [오리지널 캐릭터(OC) 일관성 유지 태깅 패턴](#4-오리지널-캐릭터oc-일관성-유지-태깅-패턴)
5. [안티 패턴 및 피해야 할 실수](#5-안티-패턴-및-피해야-할-실수)
6. [에이전트 실패 사례 ➜ 교정 레시피 (6대 Case)](#6-에이전트-실패-사례-➜-교정-레시피-6대-case)
7. [생성 전 체크리스트](#7-생성-전-체크리스트)
8. [참고 링크](#8-참고-링크)

---

## 1. 왜 Illustrious/NoobAI인가

### 아키텍처 및 학습 데이터의 특성

| 항목 | 상세 |
|:---|:---|
| **학습 소스** | Danbooru / Gelbooru 등 애니메이션 스타일의 일러스트 및 메타데이터 태그 |
| **작동 문법** | **태그 기반 콤마(`,`) 구분법**. 자연어 문장(Prose)은 무시되거나 형태 왜곡을 유발함 |
| **특이 사항** | Krea2 등 실사 모델과 달리 `masterpiece`, `best quality` 등의 품질 수식어가 강력히 가동됨 |
| **권장 CFG** | **4.5 ~ 7.5** (일반적으로 **5.5** 권장). CFG가 너무 높으면 선화가 튀거나 오버베이킹 발생 |
| **Clip Skip** | **2** (NoobAI / Illustrious 공통 규격) |

---

## 2. 핵심 프롬프트 구조 — 5단계 태그 빌더

일러스트 모델은 텍스트의 앞부분(Front-load)에 배치된 태그를 가장 강하게 반영합니다. 아래 5단계 빌더 템플릿을 철저히 고수해야 합니다.

### 2.1 태그 빌더 구성 테이블

| 단계 | 카테고리 | 역할 | 주요 사용 태그 |
|:---|:---|:---|:---|
| **Step 1** | **품질 & 안전 등급** | 모델의 화질 필터 작동 및 등급 설정 | `masterpiece, best quality, newest, absurdres, very aesthetic, rating_safe` |
| **Step 2** | **캐릭터 신원 & 인원** | 인물 정의 및 솔로/그룹 명시 | `1girl, solo` / `1boy, solo` / `hatsune miku, vocaloid` |
| **Step 3** | **인물 묘사 & 복장** | 캐릭터 고정 디자인 요소 주입 | `blue hair, twintails, yellow eyes, school uniform, pleated skirt` |
| **Step 4** | **구도 & 카메라 & 액션** | 샷의 크기, 앵글, 캐릭터 동적 묘사 | `cowboy shot, from below, looking at viewer, holding umbrella` |
| **Step 5** | **배경 & 조명 & 화풍** | 최종 무드 및 스타일 결정 | `rainy day, neon lights, backlighting, anime coloring, cel shading` |

### 2.2 태그 조립 예시 (노란 우산을 쓴 소녀)
```text
masterpiece, best quality, newest, absurdres, very aesthetic, rating_safe,
1girl, solo,
long black hair, brown eyes, school uniform, white shirt, pleated skirt,
cowboy shot, from below, looking at viewer, holding yellow umbrella,
rainy day, street, puddle reflections, backlighting, anime coloring
```

---

## 3. 일러스트 특화 연출 태그 사전 (Lexicon)

카메라 및 연출을 인위적으로 조정할 때 사용하는 단부루(Danbooru) 전용 연출 태그 세트입니다.

### 3.1 샷 크기 & 프레이밍 (Shot Size)
* `close-up` / `face portrait`: 얼굴만 밀착 묘사 (표정 컷)
* `upper body`: 상반신 샷 (일반 대화 컷)
* `cowboy shot` / `knee shot`: 골반~허벅지 위 컷 (**가장 권장됨**. 캐릭터의 동작과 배경이 조화롭게 표현되는 스윗스팟)
* `full body`: 전신 샷 (**손가락이나 발이 뭉개지기 쉬우므로, 사용 시 `--face` 디테일러 옵션 반드시 수반**)

### 3.2 카메라 앵글 & 시점 (Angle & View)
* `from below` / `worm's-eye view`: 아래에서 올려다보는 앵글 (역동성, 웅장함 연출)
* `from above` / `bird's-eye view`: 위에서 내려다보는 앵글 (외로움, 전경 연출)
* `from side` / `profile`: 캐릭터의 옆모습 묘사
* `from behind` / `back view`: 캐릭터의 뒷모습 묘사
* `three-quarter view`: 사선 3/4 구도
* `dutch angle`: 기울어진 구도 (불안감, 긴장감 연출)

### 3.3 시선 (Eyeline)
* `looking at viewer`: 카메라 렌즈를 정면으로 응시
* `looking away` / `looking aside`: 카메라가 아닌 옆을 응시
* `looking up` / `looking down`: 위 또는 아래를 바라봄

---

## 4. 오리지널 캐릭터(OC) 일관성 유지 태깅 패턴

원작이 없는 고유 캐릭터를 다중 컷에 적용할 때, 에이전트는 다음 **태그 고정 기법**을 필수적으로 수행해야 합니다.

### 4.1 캐릭터 디자인 태그 패키지화
캐릭터의 정체성을 규정하는 태그를 패키지로 묶어 고정합니다.
```text
[디자인 패키지 예시]:
short blue hair, side ponytail, hair ornament, yellow eyes, blue hoodie, pleated skirt, white sneakers
```

### 4.2 컷 배리에이션 주입법
에이전트는 샷 디자인에 맞춰 오직 **구도 태그**와 **배경 태그**만 변경하고, 캐릭터 패키지는 그대로 복사해 유지합니다.
* **컷 A (정면 샷)**:
  `[품질/안전 태그], 1girl, solo, [디자인 패키지], cowboy shot, looking at viewer, cafe background, warm lighting`
* **컷 B (옆모습/움직임 샷)**:
  `[품질/안전 태그], 1girl, solo, [디자인 패키지], upper body, from side, drinking coffee, indoor, window light`

---

## 5. 안티 패턴 및 피해야 할 실수

| 금지 패턴 (Anti-pattern) | 이유 | 올바른 방법 |
|:---|:---|:---|
| **자연어 산문 작성** | `A girl with red hair running in the rain...`식 서술은 무시됨 | `1girl, red hair, running, rain, street`식 태그 전환 |
| **구도 태그 중복 및 충돌** | `close-up, full body, cowboy shot` 동시 사용 시 인체 기형 발생 | 단 하나의 샷 크기만 선택해 기재 |
| **품질 태그 누락** | `masterpiece` 등이 없으면 화풍이 흐리멍덩해지거나 퀄리티 저하 | 프롬프트 극초반에 품질 태그 5개 고정 주입 |
| **광역 옷 묘사** | `clothing`, `outfit` 등 모호한 단어는 매 컷 옷 모양을 바꿈 | `white shirt, black pants`처럼 명사 단위로 옷을 특정 |

---

## 6. 에이전트 실패 사례 ➜ 교정 레시피 (6대 Case)

### Case 1: 에이전트가 "red-haired girl is running on the wet street" 형태로 자연어를 썼을 때
* **증상**: 인체 비례가 무너지고 배경이 어색해짐.
* **해결책**: 즉시 쉼표 단위의 태그 형식으로 강제 치환.
  * *교정*: `masterpiece, best quality, newest, 1girl, solo, red hair, running, wet street, rain`

### Case 2: 원경(Distant View) 컷에서 얼굴 이목구비가 뭉개져 뭉툭하게 나올 때
* **증상**: 애니 스타일 원경 컷의 눈/입이 뭉개짐.
* **해결책**:
  - `generate_illustrious_standard.py` 실행 시 `--face --eyes --hires-post` 옵션을 반드시 인입.
  - 배치 완료된 `Eyeful_v2-Individual.pt` 모델을 활용해 안면부와 안구를 초정밀 재생성.

### Case 3: 캐릭터가 매 컷 다른 옷으로 강제 환복(Teleport)할 때
* **증상**: 컷 1은 교복, 컷 2는 사복 등으로 순간이동.
* **해결책**: 캐릭터 정의 패키지에 옷의 구성(색상, 종류)을 구체적 태그로 묶어 고정 주입.
  * *교정*: `white t-shirt, blue denim jacket, black jeans`로 옷의 명칭과 색상을 매 컷 일치시킴.

### Case 4: 구도 태그가 충돌하여 머리가 다리 아래에 붙는 등의 기형이 발생할 때
* **증상**: 샷 사이즈 충돌로 인한 렌더러의 공간 왜곡.
* **해결책**: 프롬프트 안에서 `cowboy shot`과 `full body` 중 하나만 남기고 나머지는 완전 삭제.

### Case 5: "masterpiece, best quality" 품질 수식어를 배제하여 waxy(왁스칠한 듯한) 피부가 나올 때
* **증상**: Pony/Illustrious 계열 모델 특유의 과도하게 뭉개진 저화질 렌더링 노출.
* **해결책**: 프롬프트 헤드라인에 `masterpiece, best quality, newest, absurdres, very aesthetic` 5대 품질 접두사 강제 배치.

### Case 6: 눈동자의 좌우 초점이 맞지 않는 사시(Strabismus) 현상이 발생할 때
* **증상**: 원경 혹은 클로즈업 생성 시 눈동자의 초점이 어긋남.
* **해결책**: `--eyes` 옵션을 활성화하여 `Eyeful_v2-Paired.pt` 또는 `Eyeful_v2-Individual.pt` 디테일러 노드를 가동해 정렬.

---

## 7. 생성 전 체크리스트

- [ ] `masterpiece, best quality, newest` 등 일러스트용 품질 태그가 시작부에 들어갔는가?
- [ ] 문장이 아닌 콤마(`,`)로 구분된 단부루 태그 목록인가?
- [ ] 한 프롬프트에 `close-up`과 `full body` 같은 상충하는 태그가 동시에 존재하지 않는가?
- [ ] 캐릭터의 외모(머리스타일, 옷 등)를 정의하는 태그 패키지가 이전 컷과 완전히 동일한가?
- [ ] 원경 컷이거나 인체 전신 묘사가 필요한 경우 `--face --eyes --hires-post` 옵션을 켰는가?
- [ ] CFG 스케일이 5.0 ~ 6.0 사이의 권장 범위로 설정되었는가? (오버베이킹 방지)

---

## 8. 참고 링크
* **로컬 레퍼런스**: [illustrious_tags.md](../skills/generation-prompt/references/illustrious_tags.md)
* **공식 가이드**: [workflows/human/illustrious_standard_v37/AGENT_GUIDE.md](../../workflows/human/illustrious_standard_v37/AGENT_GUIDE.md)
* **단부루 태그 백과사전**: [Danbooru Wiki](https://danbooru.donmai.us/wiki_pages/help:home) (태그 명칭이 헷갈릴 때 유용)
