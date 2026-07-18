# 레퍼 유튜브 / 웹 인제스트 도구 — 실현 가능성 리서치

- **작성**: 2026-07-18  
- **목적**: 참고 유튜브 URL(및 웹·소셜·학술 검색 결과)에서  
  **자막 추출 · 내용 요약 · 하이라이트 클립** 이 기술적으로 가능한지,  
  **agent_custom 공장 도구**로 넣을 수 있는지 정리  
- **범위**: 기술 스택 · 한계 · ToS/저작권 주의 · 공장 설계안 (구현 전 구상)  
- **관련**: [tool_catalog.md](tool_catalog.md) · [shorts_subtitles.md](shorts_subtitles.md) (출력 자막) · [agent_native_capability_autonomy.md](agent_native_capability_autonomy.md)

---

## 1. 한 줄 결론

| 기능 | 기술적으로 | 공장 CLI로 | 비고 |
|------|------------|------------|------|
| **메타** (제목·길이·채널·챕터) | ✅ 쉬움 | ✅ 쉬움 | yt-dlp / oEmbed / Data API |
| **자막/트랜스크립트** (공식·자동자막) | ✅ 쉬움 | ✅ 쉬움 | yt-dlp `--write-auto-subs` 등 |
| **자막 없을 때 ASR** (Whisper 등) | ✅ 가능 | ✅ 가능 (로컬 GPU) | 오디오 다운로드 필요 |
| **텍스트 요약 · 섹션 구조** | ✅ 가능 | ✅ 가능 | transcript + LLM (에이전트 또는 로컬) |
| **하이라이트 구간 후보** (타임코드) | ✅ 가능 | ✅ 가능 | 자막 밀도·챕터·휴리스틱/LLM |
| **실제 하이라이트 영상 클립 파일** | ✅ 가능 | ✅ 가능 | ffmpeg 구간 컷 (다운로드 전제) |
| **웹·유튜브·학술 “검색으로 링크 찾기”** | ✅ 가능 | ⚠️ 혼합 | 세션 웹검색 + 선택적 API |
| **ToS/저작권 “합법 보장”** | ❌ 자동 보장 불가 | 정책 문구만 | 개인/내부 레퍼 전제 권장 |

**총평:**  
에이전트 공구함 관점에서 **P0(자막+메타+요약 패키지)는 충분히 만들 수 있고**,  
**P1(하이라이트 클립 파일)도 ffmpeg로 현실적**이다.  
Comfy 생성 스택과 분리된 **INGEST 선반**이 맞다.

---

## 2. 지금 공장 / 세션 상태

| 층 | 유튜브 레퍼 이해 | 비고 |
|----|------------------|------|
| **채팅 에이전트** (Grok 등) | 링크·페이지·검색으로 **일부** 가능 | 세션마다 편차 · SSOT 파일 안 남김 |
| **agent_custom scripts** | **전용 인제스트 없음** | 출력 자막만 `episode_subtitles` |
| **OpenMontage / skills** | 연출 문서 중심 | URL→transcript 파이프 없음 |

→ “유튜브 보고 쇼츠 만들어” 실험에서 자막을 쓰는 것처럼 보인 것은 **공장 도구가 아니라 세션 능력**인 경우가 많다.

---

## 3. 기능별 실현 가능성 (기술)

### 3.1 자막 / 트랜스크립트 추출

| 방식 | 입력 | 출력 | 장점 | 단점 |
|------|------|------|------|------|
| **A. yt-dlp 자막만** | URL | VTT/SRT/JSON | 로컬·빠름·자동자막 지원 넓음 | 형식 변환 필요 · 가끔 막힘 |
| **B. YouTube Data API captions** | videoId + OAuth | 공식 자막 | 공식 경로 | **업로더 권한** 없으면 남의 자막 거의 불가 |
| **C. 서드파티 transcript API** | URL | 텍스트 | 구현 단순 | 유료·의존·ToS 회색 |
| **D. 오디오 다운로드 + Whisper** | URL → wav | 타임스탬프 텍스트 | 자막 없어도 OK | 시간·용량·다운로드 정책 |

**공장 권장 기본:** **A → (실패 시) D**  
에이전트 루프:

```text
youtube_ingest URL
  1) yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs ko,en
  2) VTT → segments[{start,end,text}]
  3) empty → download audio (worst/bestaudio) + whisper/faster-whisper
  4) write transcript.json + transcript.srt + meta.json
```

커뮤니티/문서에서 2026년에도 실무 표준은 **yt-dlp 자막 경로**가 많다.

### 3.2 메타 · 챕터 · 설명

| 소스 | 내용 |
|------|------|
| yt-dlp `-J` / `--print` | title, duration, channel, description, chapters, tags |
| oEmbed | 가벼운 제목·썸네일 (제한적) |
| Data API search.list | 키워드 검색 (API 키 필요) |

챕터가 있으면 **하이라이트 후보 1차**로 바로 쓸 수 있다.

### 3.3 내용 요약

| 방식 | 어디서 | 공장 역할 |
|------|--------|-----------|
| transcript 파일만 덤프 | CLI | **필수 SSOT** |
| 에이전트가 읽고 요약 | 세션 LLM | 기본 권장 (공장에 LLM 강제 X) |
| 로컬 LLM 요약 스크립트 | 옵션 | 오프라인 배치용 후순위 |

요약 “품질”은 모델 몫이고, 공장은 **타임스탬프 달린 깨끗한 transcript** 를 주는 게 핵심.

### 3.4 하이라이트 클립

| 단계 | 방법 | 난이도 |
|------|------|--------|
| 구간 후보 | 챕터 / 자막 키워드 / 침묵·에너지(후순위) / 에이전트 지정 | 중 |
| 클립 파일 | `ffmpeg -ss -to -i video.mp4 -c copy clip.mp4` | 하 |
| “바이럴 AI 클리퍼”급 | 얼굴 추적·세로 리프레임·랭킹 | 상 · **1차 범위 밖** |

**공장 1차:**  
`highlights.json` (start/end/reason) + 선택적 `clips/*.mp4`  
Opus Clip류 풀 자동 바이럴은 Comfy 노드/클라우드 영역 → 공구함 P2.

### 3.5 웹·소셜·학술 “검색해서 링크 찾기”

| 소스 | 현실 |
|------|------|
| 일반 웹/유튜브 검색 | **에이전트 web_search** 가 이미 강함 |
| YouTube Data API `search` | 키·쿼터·필터 가능 → CLI 옵션 |
| X/Reddit | 에이전트 X/웹 도구 또는 API |
| 학술 (논문 속 영상 링크) | 에이전트 검색 + 수동 URL 확정 |

**설계 원칙:**  
검색 = **에이전트 기본 능력**에 맡기고,  
공장 도구는 **확정 URL 1개(또는 리스트) → 구조화 패키지** 에 집중.

```text
[에이전트] 주제 검색 → 후보 URL 3개
[공장]     youtube_ingest URL -o dumps/ref_xxx/
[에이전트] transcript/요약 읽고 CREATIVE · 샷 설계
[공장]     generate_* · assemble
```

---

## 4. 제약 · 리스크 (도구 설계에 넣어야 할 것)

### 4.1 YouTube ToS / 자동화

- ToS상 **자동 수단으로 콘텐츠 접근·다운로드** 제한 문구가 있음.  
- Data API는 **허용된 공식 경로**이나 자막 권한·쿼터 제한.  
- yt-dlp 등은 **광범위하게 쓰이지만 회색** — 개인/내부 레퍼·공정 사용 전제 권장.

### 4.2 저작권

- 트랜스크립트·클립도 **원작 보호 대상**일 수 있음.  
- 공장 정책 문구 예:  
  **“내부 레퍼·페어유즈 범위의 분석용. 재배포·원본 복제 납품 금지. 최종 영상은 자체 생성 자산.”**

### 4.3 기술 불안정

- 자동자막 언어/품질 편차  
- 지역·로그인·봇 차단으로 yt-dlp 실패  
- 라이브·멤버십·연령제한 영상  
- 긴 영상 전체 다운로드 시 디스크·시간

→ CLI는 **graceful fail + fallback 단계** 필수.

---

## 5. 공장 도구로 만들 수 있는가?

### 5.1 적합성 (agent_custom 철학)

| 기준 | 판정 |
|------|------|
| Comfy 없이 discovery/ingest | ✅ 업스케일 recommend · tool_intent 와 같은 층 |
| 출력 파일이 에이전트 핸드오프 SSOT | ✅ dumps/ 또는 stories/_refs/ |
| 생성 파이프 강제 아님 | ✅ 선반 **INGEST** · 필요할 때만 |
| 기존 자막 도구와 충돌 | ❌ 없음 (`episode_subtitles` = **출력**) |

### 5.2 제안 도구 분해

```text
INGEST 선반
├── youtube_ingest.py      # URL → meta + transcript (+ optional media)
├── youtube_highlights.py  # transcript/meta → highlights.json + optional clips
└── (옵션) ref_search.md   # 검색은 에이전트 SOP, CLI는 URL 확정 후만
```

### 5.3 출력 패키지 스키마 (초안)

```text
dumps/yt_ref_<id>/   또는  stories/_refs/<id>/
  meta.json           # url, video_id, title, duration, channel, chapters[]
  transcript.json     # segments[{start, end, text, source: manual|auto|whisper}]
  transcript.srt
  summary.md          # 에이전트 또는 --summarize 옵션 (선택)
  highlights.json     # [{start, end, label, score, reason}]
  clips/              # optional highlight_001.mp4
  SOURCE.md           # 출처·사용 제한 메모
```

### 5.4 구현 난이도 · 의존성

| 단계 | 의존 | 공수 (대략) |
|------|------|-------------|
| **P0** meta + caption transcript | `yt-dlp`, ffmpeg(optional) | 0.5–1일 |
| **P0b** whisper fallback | faster-whisper + GPU | +0.5–1일 |
| **P1** highlights 휴리스틱 + ffmpeg 클립 | ffmpeg | +0.5일 |
| **P1b** 에이전트/로컬 요약 훅 | LLM 호출 정책 | +0.5일 |
| **P2** 검색 API·바이럴 랭킹·얼굴 리프레임 | API 키 / 추가 모델 | 후순위 |

Windows 환경: `yt-dlp.exe` / `pip install yt-dlp` + 기존 ffmpeg 유틸과 맞출 수 있음.

### 5.5 tool_intent 카드 초안

```text
id: youtube_ref_ingest
shelf: INGEST (또는 META)
when: 유튜브 레퍼로 쇼츠/에피 기획 전
when_not: 이미 로컬 영상·대본 있음
eg: python scripts/youtube_ingest.py "https://youtu.be/..." -o dumps/ref_demo --lang ko,en
alternatives:
  - 자막 실패 → --whisper
  - 클립만 → youtube_highlights --from-json
  - 우리 쇼츠 자막 납품 → episode_subtitles
```

---

## 6. 추천 로드맵

### Phase 0 — 구상 확정 (본 문서) ✅

### Phase 1 — MVP ✅ 2026-07-18

```bash
python scripts/youtube_ingest.py URL -o dumps/yt_<id>/
  --lang ko,en
  # outputs: meta.json, transcript.json, transcript.srt, summary.md, highlights.json
```

- `lib/youtube_ingest.py` · `scripts/youtube_ingest.py`  
- tool_catalog §2.0 INGEST · tool_intent `youtube_ref_ingest`  
- whisper fallback: `--whisper` (faster-whisper / openai-whisper 설치 시)

### Phase 2 — 하이라이트 ✅ 2026-07-18

```bash
python scripts/youtube_ingest.py URL --cut --max-clips 5
python scripts/youtube_highlights.py -i dumps/yt_<id>/ --cut --rebuild
```

- 챕터 우선 → 없으면 자막 밀도 윈도우  
- ffmpeg cut (stream copy 기본)

### Phase 3 — 검색 보조 (선택) 📋

- `youtube_search.py "query" --limit 5` (Data API 키)  
- 또는 문서만: “검색은 tool_intent/web, ingest는 URL만”

### Phase 4 — 연출 연동 📋

- `video-direction` 스킬:  
  **“레퍼 URL 있으면 생성 전 youtube_ingest 필수”**  
- CREATIVE.md 필드: `ref_youtube_id`, `ref_transcript_path`

---

## 7. 하지 말 것 (범위 밖)

| 항목 | 이유 |
|------|------|
| 유튜브 원본을 납품 쇼츠로 재업로드 | 저작권·ToS |
| 매 생성에 강제 인제스트 | 공구함 자율 선택 철학 위반 |
| 풀 Opus-Clip 클론을 1차에 | 범위·VRAM·유지비 |
| API 키 없는 Data API 자막 환상 | 남의 영상 captions.download 불가 |

---

## 8. 판단 표 (질문 재답)

| 질문 | 답 |
|------|-----|
| 링크로 실제 영상에 접근 가능? | **기술적으로 예** (메타·자막 우선, 미디어는 옵션) |
| 하이라이트 클립 따오기? | **예** (구간 선정 + ffmpeg). 자동 “바이럴”은 단계적 |
| 내용 요약? | **예** (transcript SSOT + 에이전트/옵션 LLM) |
| 자막 추출? | **예** (가장 쉽고 1순위) |
| 웹/소셜/학술 검색? | **에이전트 강점** + 선택 API. 공장 핵심은 URL 이후 |
| 우리 툴로 만들 수 있나? | **예 — INGEST CLI로 적합. 구현 가치 높음** |

---

## 9. 다음 액션 (구현 시)

1. `scripts/youtube_ingest.py` + `lib/youtube_ingest.py`  
2. 출력 스키마 + dumps 경로 규약  
3. tool_catalog / TOOLS.md / tool_intent `youtube_ref_ingest`  
4. (선택) whisper fallback · highlights cut  
5. process.md 이력 · 사용 정책 한 줄 (내부 레퍼 전제)

---

## 10. 참고

- yt-dlp: subtitles / auto-subs / `--skip-download`  
- YouTube ToS: automated access 제한 · API Terms  
- ffmpeg: 구간 클립  
- faster-whisper: 무자막 폴백  
- 기존 공장: [shorts_subtitles.md](shorts_subtitles.md) (에피 **출력** 자막)

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-18 | 초안: 실현 가능성 · 설계 · 로드맵 (구현 전) |
| 2026-07-18 | **구현**: youtube_ingest + youtube_highlights + catalog/intent |
