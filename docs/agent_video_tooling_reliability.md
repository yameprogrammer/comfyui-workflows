# 에이전트용 영상 도구 — 신뢰성 평가 · 갭 · 계획

- **작성일**: 2026-07-12  
- **관점**: 에이전트(이 도구 세트를 호출하는 모델)가 **재현 가능하게** 영상을 끝낼 수 있는가  
- **근거**: `sonagi_cafe_smoke_v1` E2E 프로세스 검증 + 립/믹스 사고 분석  
- **관련**: [video_delivery_and_backends.md](video_delivery_and_backends.md), [audio_motion_production_modes.md](audio_motion_production_modes.md), [video_pipeline_roadmap.md](video_pipeline_roadmap.md)

---

## 0. 한 줄 결론

| 질문 | 답 |
|------|----|
| 기능 골격이 있나? | **예** — compose → I2V/SI2V → assemble 까지 CLI 존재 |
| 지금 상태로 다수 에이전트에 열어도 되나? | **아니오** — 조용한 실패·기본값 함정·비율 점프·문서/코드 불일치 |
| 에이전트 똑똑함으로 메울 수 있나? | **기대 금지** — 실패가 늦고, exit 0 + 이상한 mp4 가 흔함 |
| 목표 | **좁은 고속도로 1개** + 가드레일 + 자동 QA. 자유도는 플래그/고급 모드 |

---

## 1. 에이전트 관점 신뢰성 기준 (이 문서의 채점표)

에이전트가 도구를 **신뢰**하려면 최소:

| ID | 기준 | 의미 |
|----|------|------|
| R1 | **Safe defaults** | 플래그 최소로 돌리면 “납품 가능 루트” |
| R2 | **Fail loud** | 잘못된 입력/위험한 조합은 **exit ≠ 0** + 한 줄 원인 |
| R3 | **Idempotent stages** | 같은 샷 재실행 시 경로·메타 예측 가능 |
| R4 | **Contract stability** | `shots.json` 필드·exit code·출력 경로 SSOT |
| R5 | **Format consistency** | 에피소드 format(aspect)이 키프레임·클립·final까지 유지 |
| R6 | **Audio contract** | VO/dialogue 길이·spill·SI2V driving 규칙 강제 |
| R7 | **Post-run QA** | 생성 후 duration/aspect/has_speech/driver 메타 검증 |
| R8 | **One entrypoint** | 일상 작업은 `episode_pipeline` 한 방 (세부 CLI는 내부) |
| R9 | **Observable** | 단계별 로그 + 기계 판독 report JSON |
| R10 | **Cost-aware** | 느린 경로(InfiniteTalk) vs 빠른 프리뷰(LTX) 명시 |

**신뢰 점수 목표**: 각 기준 ≥ 4/5, 전체 **“에이전트 기본 경로 신뢰”** 판정.

---

## 2. 현황 평가 (2026-07-12, 에이전트 시선)

점수: 1=위험 · 3=파일럿 · 5=에이전트 기본 경로 OK

| 영역 | 점수 | 메모 |
|------|------|------|
| 에피소드 SSOT (`shots.json`) | 4 | 구조 좋음. 필드 과다·중복 프롬프트 노이즈 |
| 키프레임 compose/approve | 4 | approve 게이트 명확 |
| I2V wan22 | 4 | 스모크 4/4 OK. 모델 경로 하드코딩은 취약 |
| SI2V 기본 정책 | **2** | JSON default=`ltx23_ia2v`(빠름) vs 실측 립 안정=`infinitetalk`. 프롬프트 함정 |
| episode_tts + bind-si2v | 3 | 동작함. VO>샷 길이 가드 없음. driving/dialogue 이중 참조 |
| assemble | **3** | bake 경로로 개선됨. 정사각 SI2V→16:9 pad 비율 점프 남음 |
| episode_pipeline | 3 | 오케스트레이션 있음. 정책(백엔드/프롬프트/format) 내장 약함 |
| 문서 vs 코드 | **2** | 로드맵 “조립 미구축”, S2V default LTX vs generate_s2v docstring 혼선 |
| 자동 QA | **1** | 성공=파일 존재 수준. 립/무음/spill 미검증 |
| 한 방 E2E 재현 | 3 | 사람 개입 후 성공. 플래그 최소 재현 아직 아님 |

### 2.1 이미 겪은 “에이전트가 당할 조용한 실패”

1. SI2V에 I2V 모션 프롬프트 → **입 안 벌림**, exit 0  
2. LTX default로 립 기대 → 품질 도박  
3. VO 7s + 샷 4s → 대사 겹침  
4. 조립이 SI2V 오디오/ TTS 재배치 → “대사 없음/이상” 체감  
5. 960×544 I2V + 640² SI2V → **화면 비율 점프**  
6. music 폴더 쓰레기 mp3가 BGM으로 선택  

→ 전부 **똑똑함보다 가드레일** 문제.

---

## 3. 갭 목록 (우선순위)

### P0 — 기본 경로를 안전하게 (에이전트 필수)

| 갭 | 현재 | 목표 |
|----|------|------|
| G1 SI2V default 엔진 | `ltx23_ia2v` (JSON + CLI) | **`infinitetalk` = quality/default**; LTX = `--fast` / profile `preview` |
| G2 SI2V 캔버스 | 기본 square 640 | 기본 **episode format work size** (비율 점프 제거). CU만 opt-in square |
| G3 말하기 프롬프트 | 부분 override (`episode_s2v`) | TTS bind + compose 시 **si2v 전용 motion 템플릿** 강제 기록 |
| G4 VO/dialogue 길이 | 무가드 | duration > shot → **fail** 또는 hard trim + `audio_spill_trimmed` 메타; 기본 fail-hard on `--strict` |
| G5 BGM 선택 | 폴더 첫 파일 | `audio.bgm` 필수(story mix) 또는 이름 화이트리스트; junk/archive 제외 |
| G6 조립 기본 | bake 개선됨 | bake 기본 고정; layered flat-stack 경로 deprecated; QA 리포트 출력 |

### P1 — 계약·관측

| 갭 | 목표 |
|----|------|
| G7 Post-run QA | `scripts/episode_qa.py` 또는 assemble 말미: aspect match, per-shot RMS, silence detect, duration sum, driver vs clip type |
| G8 Exit / report SSOT | 공통 `lib/agent_result.py`: `{ok, error, message, artifacts[], qa{}}` |
| G9 Pipeline 정책 내장 | `episode_pipeline --run` 이 S2V backend·format·strict 기본 적용 |
| G10 문서 정합 | roadmap/delivery/backends: default SI2V=infinitetalk, assemble ready, square policy |

### P2 — 품질·속도 옵션

| 갭 | 목표 |
|----|------|
| G11 Profile | `preview` (LTX SI2V, 낮은 res) / `deliver` (InfiniteTalk, work format, upscale) |
| G12 LTX I2V | 일반 I2V `ltx23` planned — 우선순위 낮음 (wan22 충분) |
| G13 Upscale 기본 | work 성공 후 deliver 단계 opt-in; pipeline `--to assemble` vs `--to package` 명확 |

---

## 4. 목표 에이전트 계약 (Safe highway)

### 4.1 일상 호출 (에이전트가 외울 것)

```bash
# 1) 키프레임 승인 후 (또는 compose --force 정책은 별도)
python scripts/shot_approve.py -e EP -s S01   # … 필요 샷

# 2) 대사 컷: TTS + SI2V bind (한 샷)
python scripts/episode_tts.py -e EP -s S02 --text "..." --bind-si2v

# 3) 한 방 (정책 내장)
python scripts/episode_pipeline.py -e EP --run --from i2v --to assemble --profile deliver
```

에이전트는 **텍스트·샷 ID·approve** 만 결정. 엔진/해상도/믹스는 프로필.

### 4.2 샷 드라이버 규칙 (코드 강제)

| 조건 | `motion_driver` | 엔진 | 캔버스 |
|------|-----------------|------|--------|
| dialogue/driving 있음 + 얼굴 온스크린 | `si2v` | infinitetalk (deliver) | episode work aspect |
| 무대사 | `i2v` | wan22 | episode work |
| VO only (오프) | `i2v` | wan22 | episode work; VO stem only in assemble |
| `--profile preview` + si2v | `si2v` | ltx23_ia2v | work 또는 long-edge 640 |

### 4.3 성공 정의

```json
{
  "ok": true,
  "episode_id": "...",
  "qa": {
    "aspect_consistent": true,
    "audio_spill": false,
    "si2v_backend": "infinitetalk",
    "shots": {
      "S02": {"driver": "si2v", "has_audio": true, "mean_db": -18.0}
    }
  },
  "output": "stories/.../exports/final/....mp4"
}
```

`ok=true` 이려면 QA 게이트 통과.

---

## 5. 구현 계획 (PR 단위)

### PR-A — SI2V 안전 기본값 (P0)

1. `video_backends.json`: `default_backend_s2v` → `infinitetalk`  
2. `generate_s2v` / `episode_s2v` / `resolve_s2v_backend` 기본 정렬  
3. `episode_s2v`: default `--no-square` (format work); `--square` opt-in for CU  
4. `episode_tts --bind-si2v`: motion_prompt을 말하기 템플릿으로 **항상** set  
5. docs 한 줄 정책 업데이트  

**완료 조건**: 플래그 없이 SI2V 돌리면 InfiniteTalk + format 일치 해상도.

### PR-B — 오디오 가드 (P0)

1. `lib/audio_package.py`: stem duration vs shot duration  
2. `episode_tts` / assemble bake: spill → warn 또는 `--strict` fail  
3. BGM resolve: `audio.bgm` 우선, ignore `_archive*`, `_*probe*`  
4. SI2V bake: driving > dialogue > clip audio (현재 방향 유지)  

**완료 조건**: 긴 VO로 재현 시 spill 경고/실패; junk BGM 미선택.

### PR-C — episode_qa + assemble 리포트 (P1)

1. `scripts/episode_qa.py` (또는 assemble 내장)  
2. aspect / duration / per-segment RMS / silence  
3. `meta/*_qa.json` + non-zero exit on `--strict`  

**완료 조건**: 의도적 무음 SI2V 또는 비율 불일치 시 실패.

### PR-D — pipeline profiles (P1)

1. `--profile deliver|preview` on `episode_pipeline`  
2. deliver: s2v=infinitetalk, format work, assemble bake, qa strict  
3. preview: s2v=ltx23_ia2v optional, skip upscale  

**완료 조건**: `episode_pipeline -e sonagi --run --from i2v --to assemble --profile deliver` 문서 1커맨드.

### PR-E — 문서·로드맵 정합 (P1, 작음)

1. video_pipeline_roadmap: assemble ✅, SI2V defaults  
2. video_backends notes: LTX = fast/preview, InfiniteTalk = default lip  

---

## 6. 검증 계획 (에이전트 스모크)

고정 에피소드 `sonagi_cafe_smoke_v1` 또는 축소 `agent_av_smoke_v1`:

| # | 시나리오 | 기대 |
|---|----------|------|
| S1 | I2V only 2 shots assemble | aspect 일정, BGM only OK |
| S2 | TTS bind S03 + SI2V default | infinitetalk, 입 움직임 육안, format 유지 |
| S3 | 긴 VO > shot + strict | fail with AUDIO_SPILL |
| S4 | preview profile | LTX 허용, 메타에 profile=preview |
| S5 | junk file in music/ | 선택 안 됨 |

자동화 가능: S3, 메타 필드, aspect probe. 육안: S2 립만.

---

## 7. 비목표 (이번에 안 함)

- LTX 일반 I2V 러너 (`ltx23` planned)  
- FLF2V / 장편 연속성  
- 립 품질 자동 점수(비전 모델) — 1차 이후  
- 캐릭터 자산 git 대량 커밋  

---

## 8. 권장 착수 순서

```text
PR-A (SI2V defaults + format canvas)
  → PR-B (audio guards)
  → PR-C (QA)
  → PR-D (pipeline profile)
  → PR-E (docs)
  → S1–S5 smoke
```

예상: A+B만으로 에이전트 실수율 대부분 감소. C+D가 “신뢰 도구” 선언 가능 지점.

---

## 9. 구현 상태 (2026-07-12)

| PR | 상태 | 내용 |
|----|------|------|
| A | ✅ | `default_backend_s2v=infinitetalk`; SI2V 기본 episode work aspect (`--square` opt-in); TTS bind 말하기 템플릿; generate/episode defaults |
| B | ✅ | stem duration spill 검사 (`--strict`); BGM junk 이름 필터 (`_probe`, `_archive`, …) |
| C | ✅ | `scripts/episode_qa.py` + pipeline `qa` stage |
| D | ✅ | `episode_pipeline --profile deliver\|preview` |
| E | ✅ | 본 문서 + backends notes |

### 에이전트 기본 호출

```bash
python scripts/episode_pipeline.py -e EP --run --from i2v --to assemble --profile deliver
python scripts/episode_qa.py -e EP --strict
```

- **deliver**: InfiniteTalk SI2V, format 캔버스, assemble layered bake, QA strict  
- **preview**: LTX SI2V 빠른 프리뷰, QA soft  

다음 개선(비차단): format-일치 SI2V 재생성으로 ASPECT_MISMATCH 경고 제거, upscale 기본 경로.
