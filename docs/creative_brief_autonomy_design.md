# 기획 자율 모드 — 가드레일 · 에이전트 SOP (문서 레일)

- **작성**: 2026-07-14  
- **상태**: ✅ **문서 레일 (기능 구현 필수 아님)**  
- **합의**: 키워드만 / 음악+정보만 등 **풀 시놉 없이도** 에이전트가 기획→시놉→보드→공장 공정을 진행할 수 있다.  
  **필수 작업 = 이 문서 수준의 가드레일·절차**이며, 별도 멀티에이전트 제품·신규 CLI는 **필수가 아니다**.  
- **관련**: [agent_video_tooling_todo.md](agent_video_tooling_todo.md) · [commission_workflow.md](commission_workflow.md) · [commission_brief.schema.json](commission_brief.schema.json) · [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md) · [audio_motion_production_modes.md](audio_motion_production_modes.md) · [agent_rules.md](../agent_rules.md) Rule 8

---

## 0. 한 줄

```text
유저 입력 (시놉 풀 / 키워드 / 음악…) 
  → 에이전트가 이 SOP로 Brief·시놉·샷리스트 작성 
  → 기존 공장 (자산 → 보드 → 키프레임 → 모션 → 승인 → assemble → export)
```

**기능 개발 없이도** 에이전트 참고 문서만으로 운용 가능.  
안정화가 필요해지면 (선택) 브리프 템플릿 강제·초안 JSON 생성 CLI를 나중에 추가.

---

## 1. 입력 유형 (에이전트가 먼저 분류)

| 유형 | 유저가 주는 것 | 에이전트가 채울 것 |
|------|----------------|-------------------|
| **A. 풀 시놉** | 시놉·대사·연출 상당 부분 | 샷 분할·보드·공장 태우기 |
| **B. 키워드/한 줄** | 테마·톤·길이·채널 감 | logline → 시놉 → 대사 → 샷리스트 |
| **C. 음악 중심** | 음원/장르/BPM/무드/훅 길이 | MV·훅 구조·비주얼 콘셉트·샷 (대사 최소) |
| **D. 댄스 레퍼** | 챌린지 영상·훅 | [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md) |
| **E. 혼합** | 위 조합 | 주 모드 하나 고르고 나머지를 보강 |

유저가 모드를 안 말해도 **에이전트가 유형을 고르고** 진행한다 (도구 선택 Rule 8과 동일 정신).

---

## 2. 에이전트 페르소나 (문서상 역할)

별도 봇 프로세스 없이, **한 에이전트가 역할을 순서대로 수행**한다.

| 순서 | 역할 이름 | 출력물 |
|------|-----------|--------|
| 1 | **쇼츠 PD** | Brief 카드 (아래 §3) |
| 2 | **작가** | 시놉 / 훅 구조 / 대사(필요 시) |
| 3 | **콘티** | 샷 리스트 · 보드 요지 (S01…) |
| 4 | **프로듀서** | 자산 ID (캐릭·룩·로케) · production_mode · mix_policy |
| 5 | **공장 오퍼레이터** | 기존 CLI 공정 + 게이트 |

유저가 “확인 후 진행”을 원하면 2–3 뒤에 **짧은 확인 게이트** 1회.  
“알아서 끝까지”면 확인 없이 공장까지 (리스크는 보고에 한 줄).

---

## 3. Brief 카드 (필수 최소 필드)

에이전트는 공장에 들어가기 **전** 아래를 채운다 (대화 또는 `stories/<ep>/BRIEF.md`).

```text
title / episode_id 후보
input_type: A|B|C|D|E
production_mode: story | music_video | dance_challenge | …
mix_policy: layered | music_locked | …
format: shorts_9x16 · fps · 목표 초
logline: 1–2문장
tone / audience
character_id · look_id · location_id  (없으면 생성·재사용 계획)
must_have: 유저 고정 요소
must_not: 금지·톤 이탈
refs: 음악 경로, 레퍼 영상, 키워드 원문
```

`commission_brief.schema.json` 과 맞출 수 있으면 맞춤 (강제 스키마 검증 CLI는 선택).

---

## 4. 유형별 절차 가드레일

### 4A. 풀 시놉 (A)

1. 시놉 SSOT 확정 (오타·대사 정리)  
2. beats → shots.json  
3. 기존 story 파이프  

### 4B. 키워드만 (B)

1. Brief 카드  
2. logline 3안 중 **에이전트가 1안 채택** (또는 유저 확인)  
3. 시놉 초안 (30–60초 쇼츠면 짧게)  
4. 대사 있으면 TTS 톤/performance 메모  
5. 샷 6–12개 수준으로 분할 → story 파이프  
6. **과한 설정 금지**: 키워드에 없는 세계관 폭주 자제  

### 4C. 음악 + 정보 (C)

1. Brief + 훅 길이·코러스 위치 추정  
2. **대사는 기본 없음** 또는 훅 1–2소절만  
3. `mix_policy=music_locked` 또는 layered(보컬 under)  
4. 비주얼: 비트 구간별 샷 (와이드/디테일/루프)  
5. I2V 중심, SI2V는 필요할 때만  
6. 음원 저작권·사용 가능 여부 유저 확인 한 줄  

### 4D. 댄스 레퍼 (D)

→ [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md) 전용 파이프.  
이 문서의 Brief만 채우고 모드를 `dance_challenge` 로 넘긴다.

---

## 5. 공장 진입 전 체크리스트

- [ ] Brief 카드 완성  
- [ ] production_mode / mix_policy 결정  
- [ ] 자산 ID 결정 (없으 생성 일정)  
- [ ] 샷 리스트에 motion_driver (i2v/si2v) 표시  
- [ ] 원 테이크면 **last-frame 체인** 사용 (`chain_one_take` 등) — 독립 키프레임만으로 합본하지 않기  
- [ ] 유저 확인 게이트 여부 결정  

그 다음: look/char/loc → storyboard → keyframe → (TTS) → motion → clip approve → BGM → assemble → 1080 → **export_to_workspace**.

---

## 6. 가드레일 (품질·안전)

| 규칙 | 내용 |
|------|------|
| 입력 존중 | 유저 키워드·음악·금지를 최우선. 임의 정치/민감 설정 확대 금지 |
| 모드 분리 | story 립 파이프와 dance/MV를 한 에피에 뒤섞지 않기 |
| 게이트 유지 | keyframe / clip approve · assemble hard gate 우회 금지 |
| 길이 | 쇼츠 기본 15–60s. 긴 요청은 파트 분할 제안 |
| 오디오 | 대사 컷은 TTS 길이 계약 (tooling_todo P0-1). 음악 모드는 훅 루프 |
| export | 공장만 두고 끝내지 말 것 (AGENTS.md) |
| 도구 선택 | 유저가 툴을 지정하기 전 **에이전트 자율** (Rule 8) |

---

## 7. 기능 개발은 언제? (선택)

문서만으로 부족한 신호가 반복되면:

| 신호 | 선택 구현 |
|------|-----------|
| Brief 누락이 잦음 | `stories/<ep>/BRIEF.md` 템플릿 자동 생성 |
| shots 초안 실수 | `episode_init_from_brief` 얇은 CLI |
| 톤 들쭉날쭉 | performance/모드 프리셋 테이블 (P0-2) |

→ 백로그: [agent_video_tooling_todo.md](agent_video_tooling_todo.md) **P3-2**.

---

## 8. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-14 | 초안. 유저 합의: 기능 필수 아님, 기획 가드레일·SOP 문서로 에이전트 자율 기획 가능. |
