# Krea2 프롬프트 최적화 가이드

- **작성:** 2026-07-19  
- **범위:** 에이전트가 Krea2로 최고 품질 키프레임을 생성하기 위한 실전 가이드  
- **관련:** [skills/generation-prompt/references/krea2_still_prompts.md](../skills/generation-prompt/references/krea2_still_prompts.md) · [Krea2_SFW_NSFW_v10_AGENT_GUIDE.md](../workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md)

---

## 목차

1. [왜 Krea2인가](#1-왜-krea2인가)
2. [RAW vs Turbo 운용 전략](#2-raw-vs-turbo-운용-전략)
3. [핵심 프롬프트 구조 — 7레이어 빌더](#3-핵심-프롬프트-구조--7레이어-빌더)
4. [Krea2 특화 어휘 사전](#4-krea2-특화-어휘-사전)
5. [피해야 할 패턴](#5-피해야-할-패턴)
6. [에이전트 실패 사례 → 교정 레시피](#6-에이전트-실패-사례--교정-레시피)
7. [프롬프트 Expander 전략](#7-프롬프트-expander-전략)
8. [생성 전 체크리스트](#8-생성-전-체크리스트)
9. [참고 링크](#9-참고-링크)

---

## 1. 왜 Krea2인가

### 아키텍처 요약

| 컴포넌트 | 상세 |
|---------|------|
| **확산 백본** | 12B DiT (Flux-class) — 대규모 파라미터, 텍스처 재현 능력 최상위 |
| **텍스트 인코더** | **Qwen3-VL 4B** — LLM 방식의 자연어 이해. CLIP 토큰 임베딩이 아닌 문맥 독해 |
| **설계 철학** | Aesthetic-first: "AI 냄새"(왁스 피부, 과도한 보케, 플라스틱 광택) 회피 설계 |
| **최적 프롬프트** | 영어 산문 문단 1개 (90–140 단어). 태그 덤프 금지 |
| **토큰 예산** | 512 토큰 이하 유지 |

### Krea2가 로컬 최고 품질인 이유

- **텍스처 우위:** 소재(니트 조직, 젖은 아스팔트, 피부 모공)를 이름만 명시해도 재현
- **AI 냄새 억제:** `natural skin texture`, `candid editorial` 같은 표현이 즉시 효과
- **프롬프트 이해도:** Qwen3-VL이 문장 구조와 문맥을 파악 → 단어 순서가 출력에 영향
- **캐릭터 일관성:** Face ID LoRA 패스로 후처리 가능 (별도 단계)

---

## 2. RAW vs Turbo 운용 전략

| 항목 | Turbo | RAW |
|------|-------|-----|
| **스텝 수** | ~8 (distilled) | ~52 (undistilled) |
| **속도** | 빠름 (production 기본) | 5–7배 느림 |
| **품질 차이** | **구형 turbo(SDXL/SD1.5)와 달리 품질 손실 최소** | 최고 품질 천장 |
| **주 용도** | 모든 MV 키프레임, 빠른 이터레이션, 날씨/조명 탐색 | 히어로 샷, LoRA 학습 데이터, 포스터/앨범 아트 |
| **에이전트 기본값** | ✅ **Turbo 사용** | 명시적 요청 시만 |
| **preset** | `krea2_t2i_v10` | `krea2_t2i_v10` + steps=52, turbo LoRA OFF |

> **중요:** Krea2 Turbo는 SDXL Turbo처럼 품질이 대폭 저하되지 않는다.
> Turbo가 실제 프로덕션 주요 경로이며, RAW는 "조금 더 높은 천장이 필요한 히어로 샷"에만 opt-in.

---

## 3. 핵심 프롬프트 구조 — 7레이어 빌더

### 레이어 표

| # | 레이어 | 내용 | 예시 |
|---|--------|------|------|
| **L1** | **Medium / Style prefix** | 렌더링 계약 설정 | `Photoreal cinematic film still,` |
| **L2** | **Shot size + angle** | 프레이밍 + 카메라 위치 | `medium shot waist-up, slight low angle,` |
| **L3** | **Subject + pose / action** | 구체적 동사, 신원 단축형 | `A solitary mid-20s Korean woman stands fully upright,` |
| **L4** | **Wardrobe + materials** | 촉각적 명사 — 소재 유형, 마감 | `cream knit rib cardigan over white cotton blouse,` |
| **L5** | **Props + spatial relations** | 사물, 배치, 상호작용 | `one pure yellow nylon parasol arching overhead,` |
| **L6** | **Setting + environment** | 실제 건축, seamless 금지 | `wet dark asphalt behind a Seoul convenience store,` |
| **L7** | **Light + mood + grade suffix** | 분위기, 팔레트, 품질 클로저 | `overcast soft key, rain reflections, natural skin texture, sharp focus.` |

### 조립 템플릿

```text
[L1 style prefix], [L2 shot size + angle].
A [L3 solitary subject + pose/action verbs].
[L4 wardrobe with fabric names].
[L5 props + spatial relations].
[L6 real setting anchor — seamless 금지].
[L7 light], [palette/grade], natural skin texture, sharp focus on [POI], [project tag].
```

### 길이 기준

| 모델 경로 | 목표 |
|---------|------|
| **Krea2 still (Turbo / RAW)** | **90–140 단어, 문단 1개** |
| Moody still | 40–120 단어 / 6–10 절 |
| I2V motion | 8–40 단어 (동작 + 카메라만) |

---

## 4. Krea2 특화 어휘 사전

### 4-1. Style Prefix 카탈로그 (L1)

| Prefix | 최적 용도 |
|--------|----------|
| `Photoreal cinematic film still,` | MV 키프레임, 내러티브 씬, 아웃도어/인테리어 |
| `Editorial fashion photograph,` | 워드로브 히어로, 룩북, 온-로케이션 스타일 |
| `Luxury product shot,` | 인서트 / 소품 히어로 (향수, 주얼리, 패브릭) |
| `Gritty documentary photograph,` | 도시 캔디드, 리포르타주, 텍스처 헤비 씬 |
| `K-drama BTS shoot,` | 촬영장 비하인드, 내추럴 라이트 캔디드 |
| `Architecture render,` | 빈 프레임, 인테리어 / 익스테리어 구조물 주인공 |
| `Concept art matte painting,` | 스타일라이즈드 와이드 에스터블리싱, 논포토리얼 |
| `High-key beauty editorial,` | 페이스 CU, 클린 포트레이트, 화이트 키 |
| `Wet plate collodion photograph,` | 빈티지 모노크롬 포트레이트 처리 |

### 4-2. 조명 어휘 (L7)

| 어휘 | 특성 |
|------|------|
| `overcast soft key from above` | 흐린 날 균일 확산광 — 피부 포근 |
| `golden hour rim light, low camera-left` | 황금빛 에지 라이트 — 실루엣 윤곽 강조 |
| `fluorescent overhead wash` | 편의점 / 병원 / 지하철 내부 형광등 |
| `neon spill, pink / cyan` | 야간 도시 네온 반사 |
| `hard studio strobe, beauty dish` | 강한 스트로보 — 명암 대비 최대 |
| `practical window light, north-facing` | 자연광 디퓨즈 — 스튜디오 느낌 없음 |
| `moonlit ambient, blue-cool` | 야간 달빛 분위기 |
| `candlelight, warm flicker` | 따뜻한 불빛, 저콘트라스트 섀도 |

### 4-3. 소재 어휘 (L4 + L6)

#### 의상 / 패브릭

| 어휘 | 시각적 효과 |
|------|-----------|
| `knit rib cardigan` | 니트 리브 조직 패턴 |
| `sheer nylon blouse` | 반투명 + 드레이프 |
| `washed raw denim` | 페이드 라인, 실밥 |
| `patent leather boots` | 미러 글로스 |
| `oversized linen coat, natural crumple` | 린넨 구김 |
| `matte jersey crop top` | 무광 신축성 소재 |

#### 표면 / 환경

| 어휘 | 시각적 효과 |
|------|-----------|
| `wet asphalt reflections` | 노면 반영 — 야간 / 비 씬 핵심 |
| `condensation on plastic cup lid` | 컵 이슬 맺힘 |
| `rain-beaded glass shopfront` | 유리창 빗방울 |
| `brushed chrome railing` | 무광 크롬 핸드레일 |
| `concrete pillar with stain blooms` | 콘크리트 얼룩 |
| `fluorescent tube flicker on white tile` | 형광등 타일 반사 |

#### 피부 / 포트레이트

| 어휘 | 효과 |
|------|------|
| `natural skin texture, visible pores` | AI 왁스 피부 방지 |
| `candid editorial skin, no plastic smoothing` | 리터칭 없는 자연스러운 피부 |
| `fine freckles across the nose bridge` | 주근깨 디테일 |
| ~~`smooth perfect skin`~~ | ❌ 왁스 피부 유발 금지 |

### 4-4. 카메라 / 렌즈 어휘 (L2)

| 어휘 | 프레이밍 효과 |
|------|------------|
| `medium shot waist-up` | 허리 위 미디엄 샷 |
| `full-length shot, tip-to-toe` | 전신 샷 |
| `extreme close-up` | 얼굴 / 소품 디테일 |
| `wide establishing shot` | 공간 전체 에스터블리싱 |
| `over-the-shoulder` | 어깨 너머 시점 |
| `35mm lens feel` | 표준 광각, 왜곡 최소 |
| `50mm lens feel` | 인물 가장 자연스럽게 |
| `85mm portrait compression` | 배경 압축, 피사체 강조 |
| `slight low angle` | 피사체 위엄 강조 |
| `bird's eye view` | 부감 — 패턴 / 레이아웃 강조 |

---

## 5. 피해야 할 패턴

| ❌ Bad | ✅ Good | 이유 |
|--------|---------|------|
| `masterpiece, best quality, 8k, hyper-detailed` | `Photoreal cinematic film still,` (style prefix) | 플러프 토큰은 토큰 예산 낭비 + 효과 없음 |
| `woman, knit, rain, walking, Seoul` (Danbooru 태그) | `A solitary woman in a knit cardigan walks through rainy Seoul streets,` (NL prose) | Qwen3-VL은 문맥 독해 — 태그는 의미 손실 |
| `NO second person. WITHOUT twin. AVOID clone.` (NO-spam) | `A SOLITARY woman occupies the RIGHT THIRD; only ONE yellow parasol.` (positive lock) | 부정어는 모델이 무시하기 쉬움; 긍정 공간 잠금이 효과적 |
| 캐스팅 플레이트(회색 심리스, 흰 배경 얼굴) → 씬 프롬프트에 붙여넣기 | 위치 프롬프트에는 실제 건축 묘사만. 페이스 ID는 별도 패스 | 심리스+씬 혼합 → 스튜디오 배경이 씬에 삽입됨 |
| 인서트 샷에 `full body, face CU` 포함 | 인서트 prefix + POI(소품/손) 우선. 얼굴/전신 제외 | 인서트 히어로는 소품/단편 — 인물이 이기면 안 됨 |
| `blurred background, heavy bokeh` 남용 | 배경을 구체적 장소로 묘사 + 적당한 노출 거리 | 뭉개진 배경 강조 → AI 가짜 심도 현상 |
| 한 문단에 두 가지 style prefix 혼용 | prefix 하나만 선택 | 렌더링 계약 충돌 |
| 150단어 초과 에세이 | 90–140단어 트리밍 | 후반 토큰 무언 절단 위험 |

---

## 6. 에이전트 실패 사례 → 교정 레시피

### Case 1 — 태그 수프 → 산문 변환

**실패 프롬프트:**
```
korean woman, parasol, rain, Seoul, knit cardigan, wet street, night, neon
```

**문제:** Qwen3-VL이 관계성을 파악 못 함. 구도/동작 없음. 스타일 없음.

**교정 프롬프트:**
```
Photoreal cinematic film still, medium shot at slight low angle.
A solitary Korean woman in her mid-20s stands still under one pure yellow nylon parasol
covering her head; she is placed in the right third of the frame.
Cream knit rib cardigan over a white cotton blouse, light-wash straight-leg denim.
Translucent plastic bag in her left hand.
Narrow Seoul back alley at night — wet asphalt with scattered neon reflections,
convenience store fluorescent light spilling from the left.
Pink neon spill from signage overhead, cool blue ambient fill, natural skin texture,
sharp focus on face and torso, Seoul midnight K-R&B music-video keyframe.
```

---

### Case 2 — NO-spam → Positive Lock

**실패 프롬프트:**
```
ONE woman ONLY. NO second woman. NO twin. NO duplicate. WITHOUT clone.
NO poster. NO billboard. AVOID collage.
```

**문제:** 부정어 반복은 모델이 쉽게 무시. 실제로 쌍둥이/콜라주 출력 유발.

**교정 (positive string):**
```
A SOLITARY woman occupies the RIGHT THIRD of the frame.
Only one person. Only one yellow parasol directly over her head.
She stands alone on an empty wet street.
```

**교정 (negative slot에만):**
```
two women, twin, clone, collage, split screen, poster face, empty parasol beside her
```

---

### Case 3 — 캐스팅 플레이트 씬 혼합

**실패 프롬프트:**
```
A woman on grey seamless backdrop, bare shoulders, face forward.
Rainy Seoul alley background behind her.
```

**문제:** "grey seamless"와 "rainy alley"가 충돌 → 스튜디오 배경이 씬에 침투.

**교정:**
```
Photoreal cinematic film still, medium shot.
A solitary woman stands in a real Seoul back alley — wet asphalt, glass shopfront
blurred behind her. [... 워드로브 + 조명 ...]
```
→ 페이스 ID가 필요하면 **별도 Face ID 패스**에서 처리.

---

### Case 4 — 인서트 샷에 전신 언어 삽입

**실패 프롬프트:**
```
A full body shot of a woman holding a coffee cup with her hand in the foreground.
```

**문제:** "full body"가 히어로를 인물로 고정 → 컵/손이 배경으로 밀림.

**교정:**
```
Luxury product shot, extreme close-up at eye level.
Detail insert: a woman's hand with natural unpainted nails holds a condensation-beaded
clear plastic cup; the hand occupies the centre-left frame.
No full body visible; wrist and lower forearm only, soft grey knit sleeve edge.
White marble café counter beneath, blurred warm café interior behind.
Soft north-window light, sharp focus on the cup and knuckles.
```

---

### Case 5 — Expander가 인물 추가

**씨드 입력:**
```
woman, parasol, Seoul rain
```
**Expander ON 결과 (실패):**
```
... a woman and her companion share a yellow parasol in the rain ...
```

**문제:** expander가 "companion"을 hallucination으로 추가 → SHOT_DESIGN 위반.

**교정:**
- expander **OFF**
- 90–140 단어 직접 작성 (§3 템플릿 사용)
- 또는 expander 결과 확인 후 "companion" 삭제 + spatial lock 추가

---

### Case 6 — 왁스 피부 출력

**실패 프롬프트:**
```
... beautiful smooth flawless skin, perfect complexion, airbrushed ...
```

**문제:** "smooth/flawless/airbrushed" → Krea2가 과도한 리터칭 모드로 진입.

**교정:**
```
... natural skin texture, visible pores, candid editorial skin, fine freckles, no plastic smoothing ...
```

---

## 7. 프롬프트 Expander 전략

Krea2 워크플로에는 **Prompt Enhancer / LLM expand** 노드가 내장되어 있다.

| 조건 | Expander 설정 |
|------|-------------|
| 수작업 완성 문단 (90–140 단어) | **OFF** — expander가 인물/소품 hallucination 추가 위험 |
| 씬 씨드 (< 30 단어, 탐색용) | **ON** → 확장 결과 반드시 검수 (인물 추가 여부 확인) |
| 레퍼런스 이미지 캡션 재사용 | **OFF** — 이미 충분히 서술됨 |
| 알려진 문제 샷 반복 생성 | **OFF** — 정밀 제어 필요 |

**Expander ON 시 워크플로:**
1. 씨드 입력
2. 확장 결과 문자열 읽기
3. 게이트 §8 체크 — 통과하면 생성
4. 실패(인물 추가 등) → 수동 편집 후 expander OFF로 재실행
5. PROMPT_PACK에 씨드 + 확장 결과 모두 기록

---

## 8. 생성 전 체크리스트

### 아키텍처 / 스타일 체크

- [ ] Style prefix 존재 + 촬영 유형과 일치 (L1)
- [ ] Shot size + angle 명시 (L2)
- [ ] 메타 언어 없음 (`In this image…`, `The photo shows…`)
- [ ] `masterpiece`, `best quality`, `8k`, `hyper-detailed` 플러프 토큰 없음

### 피사체 & 공간 잠금 체크

- [ ] 구체적 동작 동사 존재 (L3)
- [ ] 단독 히어로 샷: spatial lock 있음 (`SOLITARY`, `right third`, `ONE prop`)
- [ ] 단독 샷에 듀오 언어 없음
- [ ] 인서트: 얼굴/전신이 주인공 아님

### 소재 & 환경 체크

- [ ] 패브릭/소재 명사 최소 1개 이상 (L4)
- [ ] 실제 장소 앵커 존재 — seamless/studio 없음 (L6)
- [ ] 씬 프롬프트에 캐스팅 플레이트 언어 없음
- [ ] 포트레이트 샷: `natural skin texture` 또는 동등 표현 존재

### 네거티브 / 토큰 체크

- [ ] positive string에 "NO/without/avoid" 리스트 없음
- [ ] 네거티브(있다면) negative slot에만 배치
- [ ] 예상 단어 수: 90–140 단어 (150 초과 시 트리밍)
- [ ] 토큰 예산: 중복 제거 후 ≤ 512 토큰

### Expander / 핸드오프 체크

- [ ] Expander 설정 확인 (완성 문단 → OFF; 씨드 → ON + 검수)
- [ ] `generate_krea -p "..."` 단독 실행 — appearance_prompt 병합 금지
- [ ] 생성 후: Visual QA → 선택적 Face ID 패스

---

## 9. 참고 링크

| 리소스 | 링크 |
|--------|------|
| **공식 Krea2 prompting 가이드** | [github.com/krea-ai/krea-2/blob/main/docs/prompting.md](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md) |
| **공식 expansion.txt** | [github.com/krea-ai/krea-2/blob/main/docs/expansion.txt](https://github.com/krea-ai/krea-2/blob/main/docs/expansion.txt) |
| **Comfy.org Krea2 가이드** | [comfy.org/models/krea-2](https://comfy.org/models/krea-2) |
| **fal Krea2 가이드** | [fal.ai/models/fal-ai/krea-2](https://fal.ai/models/fal-ai/krea-2) |
| **로컬 krea2_still_prompts.md** | [skills/generation-prompt/references/krea2_still_prompts.md](../skills/generation-prompt/references/krea2_still_prompts.md) |
| **로컬 워크플로 에이전트 가이드** | [workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md](../workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md) |
| **로컬 generation-prompt SKILL** | [skills/generation-prompt/SKILL.md](../skills/generation-prompt/SKILL.md) |
| **도구 카탈로그** | [docs/tool_catalog.md](tool_catalog.md) §2.1 |
