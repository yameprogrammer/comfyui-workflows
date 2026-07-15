# Genre / format recipes — minimal coverage set (v1.1)

**목적:** 지구상 모든 장르를 나열하지 않는다.  
학술·산업·숏폼 실무에서 **반복되는 구분**을 리서치한 뒤, 이 공장에서 **결정 트리로 쓸 최소 레시피 세트**만 둔다.

**상세 출처·매핑:** [genre_research.md](genre_research.md)  
**스킬 본체:** [../SKILL.md](../SKILL.md) Gate 0 분류

---

## 0. 3층 모델 (세분화 원칙)

| 층 | 이름 | 개수 목표 | 역할 |
|----|------|-----------|------|
| **L0** | Mode | 4–5 | 공장 `production_mode` · 오디오/립 계약 |
| **L1** | Format recipe | **12** (최소 커버리지) | 샷 구조·커버리지·모션 드라이버 기본값 |
| **L2** | Tone / craft module | 조립 | 공포 지연, 코미디 반응컷, 후렴 점프… (장르 “맛”) |

**규칙:** 유저 요청 → **L0 1개 + L1 1개(최근접) + L2 0~3개**.  
없는 장르명(느와르, 멜로…)은 L1 최근접 + L2 톤 모듈로 합성한다.

---

## 1. L0 — Mode (공장 계약)

| L0 id | production_mode | 시간 척추 | 립(SI2V) | 비고 |
|-------|-----------------|-----------|----------|------|
| `M_story` | `story` | 대사·내러티브 비트 | 대사 컷 기본 | 카페 상담, 미니 드라마 |
| `M_mv` | `music_video` | **마스터 음원 섹션** | 온캠 보컬만 | 가사 직역 금지 |
| `M_hybrid` | `hybrid` | 대사 섬 + BGM | 대사 구간만 | 이야기+음악 |
| `M_dance` | `dance_challenge` | 비트+안무 레퍼 | 비주력 | 별 파이프 문서 |
| `M_visual` | `video_only` | 순수 비주얼 비트 | 없음 | VO 없음·분위기 |

---

## 2. L1 — Format recipes (최소 12)

실무 숏폼/영상 제작에서 자주 갈리는 **포맷** + 학술 “내러티브 vs 논내러티브/퍼포먼스” 축을 합친 세트.

### R01 — Talking performance short  
**별칭:** 토킹헤드, 상담, 인터뷰형 쇼츠  
**L0:** `M_story` / `M_hybrid`  
**구조:** cold open → 문제/상황 → 대사 턴(2–4) → 모티프 버튼  
**Coverage 최소:** wide 지리 1 · MS 대화 1 · insert 소품 1 · (감정 시) MCU 1  
**Driver:** 대사=`si2v` · sip/제스처=`i2v`  
**금지:** face CU만 전 컷 · 동일 미디엄 3연속  

### R02 — Narrative mini-drama  
**별칭:** 초단편, 스케치 드라마  
**L0:** `M_story`  
**구조:** setup → turn → payoff (3막 압축, 30–90s)  
**Coverage:** master → medium → CU/insert → release (클래식 coverage 축소판)  
**Driver:** 감정 대사 si2v, 공간/이동 i2v  
**학술 대응:** 허구 내러티브 + 연속성 편집  

### R03 — Music video (song spine)  
**별칭:** MV, 퍼포먼스+컨셉 비주얼  
**L0:** `M_mv`  
**구조:** Intro/V/Pre/**Chorus=사건**/Br/Out — 구간당 **시각 직무 1**  
**Coverage:** 후렴 size/motion/motif jump · verse는 texture·공간  
**Driver:** 온캠 보컬만 si2v · 나머지 i2v  
**금지:** 가사 1:1 삽화 슬라이드쇼  

### R04 — Dance / choreography short  
**별칭:** 챌린지, 안무 쇼츠  
**L0:** `M_dance` (또는 `M_mv` 댄스 위주)  
**구조:** 훅 포즈 → 8카운트 구간 → 포인트 무브 리핏 → 엔딩 포즈  
**Coverage:** full/FS 위주 · 얼굴 CU 최소화 · 손발 리스크 태그  
**Driver:** i2v (+ 포즈 가이드 파이프)  
**문서:** `docs/dance_challenge_pipeline_design.md`  

### R05 — Hook-first social short  
**별칭:** 릴스/틱톡 훅형, “첫 1초”  
**L0:** 상황 따라 story/mv/hybrid  
**구조:** **0–1.5s 스크롤 스톱** → build 2–3컷 → payoff → CTA/버튼  
**Coverage:** Shot1 = 최강 한 장 (이상·모티프·행동) · 설명은 뒤로  
**Driver:** 대부분 i2v · 말 있으면 후반 si2v  
**실무:** 플랫폼 퍼스트 포맷  

### R06 — Product / UGC demo  
**별칭:** 제품 리뷰 톤, 언박싱, 앱 데모 감  
**L0:** `M_story` 또는 `M_visual`  
**구조:** 문제 → 제품/해결 등장 → 사용 디테일(insert) → 결과/CTA  
**Coverage:** ECU 제품 · hands insert · 얼굴은 신뢰 1–2컷만  
**Driver:** i2v · VO/대사는 선택  
**주의:** 읽히는 가짜 텍스트 난립 금지 (Ideogram은 타이포 전용)  

### R07 — Documentary / vlog texture  
**별칭:** 브이로그, 데이인더라이프, 관찰  
**L0:** `M_hybrid` / `M_visual`  
**구조:** 도착 → 과정 디테일 → 사람/장소 관계 → 잔상  
**Coverage:** wide 환경 · insert 손·사물 · occasional MCU · jump-cut 허용 시 메모  
**Driver:** i2v 위주 · 보이스오버는 오디오 트랙  
**학술 대응:** nonfiction / observational 톤 (완벽한 다큐 주장 금지)  

### R08 — Atmospheric mood / brand film  
**별칭:** 무드 필름, 브랜드 감성, 시네마틱 무대사  
**L0:** `M_visual` / `M_mv`(연주곡)  
**구조:** 모티프 도입 → 변주 → 클라이맥스 텍스처 → 잔여  
**Coverage:** LS/insert 비중↑ · face CU↓ · **intentional still** 명시 가능  
**Driver:** i2v · still 허용 시 `motion_driver=still` + `--allow-freeze`  
**금지:** 의미 없는 face CU 채우기  

### R09 — Comedy / reaction timing  
**별칭:** 개그 숏, 리액션, 스케치 코미디  
**L0:** `M_story`  
**구조:** setup 이미지 → beat(침묵/시선) → punch (리액션 컷) → tag  
**Coverage:** 투샷/OTS + **reaction CU** · 타이밍이 size보다 중요  
**Driver:** 짧은 i2v · 대사는 짧게 si2v  
**모듈:** L2 `mod_reaction_cut`, `mod_hold_before_punch`  

### R10 — Thriller / horror pressure  
**별칭:** 미스터리, 호러 숏, 불안  
**L0:** `M_story` / `M_visual`  
**구조:** 정상 공간 → 정보 제한 → 지연 → **reveal** → 잔상(또는 sudden stop)  
**Coverage:** high/dutch  sparingly · insert 단서 · 얼굴 전체 공개 늦게  
**Driver:** i2v · 점프스케어는 1회만  
**모듈:** L2 `mod_delay_reveal`, `mod_offscreen_threat`  

### R11 — Educational / explain quick  
**별칭:** 설명, 팁, 리스트형 쇼츠  
**L0:** `M_story` / `M_visual`  
**구조:** 주장 훅 → 포인트 1–3 (각 1 비주얼) → 요약/CTA  
**Coverage:** 토킹 MS + 도해/insert 교대 (텍스트는 burn/subtitle 파이프)  
**Driver:** si2v 설명 · insert i2v  
**주의:** 화면 안 AI 텍스트 가독 기대 금지 → `episode_subtitles`  

### R12 — Performance one-take feel  
**별칭:** 원테이크 감, 롱테이크 미학, 싱글 로케 연속  
**L0:** `M_story` / `M_hybrid`  
**구조:** 공간 진입 → 행동 연속 → 감정 변위 → 퇴장/잔상  
**Coverage:** size 변주는 하되 **공간·의상 연속** 최우선  
**Driver:** chain_one_take / from-prev · si2v 구간 섞기 가능  
**금지:** 중간 freeze pad로 길이 메우기  

---

## 3. L1 선택 치트시트 (Gate 0)

```text
말이 중심인가?
  Y → 개그 타이밍? → R09
       설명/팁? → R11
       미니 플롯? → R02
       상담·일상 대화? → R01
       원테이크 로케? → R12
  N → 음악이 척추?
         Y → 댄스 안무? → R04
              노래/컨셉 비주얼? → R03
         N → 제품 팔기? → R06
              관찰/브이로그? → R07
              무드/브랜드? → R08
              불안/공포? → R10
              스크롤 훅만 급함? → R05 (+ 위 중 하나와 합성)
```

**합성 예:** “비 오는 카페 고민 상담 쇼츠” → L0 `M_hybrid` + L1 **R01** + L2 감성 라이트 + sip insert.  
**합성 예:** “가사 있는 감성 MV” → L0 `M_mv` + L1 **R03** (+ 훅 강화 시 R05 규칙만 차용).

---

## 4. L2 — Tone / craft modules (조립, 비망록)

장르 **이름** 대신 샷에 붙이는 모듈. 필요 시 SHOT_DESIGN에 `modules: [...]` 기록.

| id | 효과 | 붙이기 좋은 L1 |
|----|------|----------------|
| `mod_chorus_event` | 후렴 size/motion/motif jump | R03 |
| `mod_scroll_hook_1_5s` | 첫 컷 스크롤 스톱 강제 | R05 + any |
| `mod_reaction_cut` | punch 전후 리액션 | R09 |
| `mod_delay_reveal` | 정보 늦게 공개 | R10 |
| `mod_motif_trinity` | 모티프 3 회수 | R03, R08, R02 |
| `mod_insert_prop` | 소품 ECU 의무 | R01, R06 |
| `mod_rain_texture` | 날씨·표면 텍스처 비중 | R03, R08 |
| `mod_one_take_chain` | last-frame 연속 | R12 |
| `mod_lip_hero_sparse` | 립 히어로 1–2만 | R03, R01 |
| `mod_intentional_still` | 정물 허용 라벨 | R08 |

학술 “장르(호러/코미디…)”는 대부분 **L1 포맷 + L2 톤 모듈**로 표현한다.

---

## 5. 레시피 → 공장 기본값

| L1 | format 기본 | motion | QA 강조 |
|----|-------------|--------|---------|
| R01 | 9:16 자주 | si2v+i2v | identity, lip |
| R02 | 9:16/16:9 | si2v+i2v | continuity K13–14 |
| R03 | 9:16 or 16:9 | i2v+선택 si2v | size rhythm, freeze |
| R04 | 9:16 | i2v | full body, feet |
| R05 | 9:16 | i2v | S01 hook intent |
| R06 | 9:16 | i2v | product scale, hands |
| R07 | 9:16 | i2v | variety, inserts |
| R08 | any | i2v/still | anti face-spam |
| R09 | 9:16 | short clips | timing, reaction |
| R10 | 9:16 | i2v | reveal placement |
| R11 | 9:16 | si2v+i2v | subtitles not in-frame text |
| R12 | 9:16 | chain | freeze ban, clip gate |

---

## 6. 의도적으로 빼 둔 것

- 고전 영화 장르 전표 (웨스턴, 뮤지컬 넘버 전체…) — 요청 시 R02/R03+모듈  
- 순수 모션그래픽/인포그래픽 풀 파이프 — 자막·타이포 툴로 부분 처리  
- 장편 극영화 커버리지 전체 — R02 축소판만  

추가 레시피는 **실제 채널 반복 요청 3회 이상**일 때만 L1 번호를 늘다.