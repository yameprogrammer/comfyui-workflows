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
| A | ✅ | SI2V format 캔버스 (`--square` opt-in); TTS bind 말하기 템플릿; QA/pipeline 골격 |
| B | ✅ | stem duration spill 검사 (`--strict`); BGM junk 이름 필터 (`_probe`, `_archive`, …) |
| C | ✅ | `scripts/episode_qa.py` + pipeline `qa` stage |
| D | ✅ | `episode_pipeline --profile preview\|deliver\|hero` |
| E | ✅ | 본 문서 + backends notes |
| Speed | 🔄 | §10 리서치 반영: **기본 SI2V=LTX**, IT는 hero. Comfy 그래프(lightx2v/TeaCache)는 보류 |

### 에이전트 기본 호출

```bash
# 일상 / 납품 루프 (빠름: LTX SI2V)
python scripts/episode_pipeline.py -e EP --run --from i2v --to assemble --profile deliver
python scripts/episode_qa.py -e EP --strict

# 히어로 CU 립만 InfiniteTalk (느림 — 컷 수 제한)
python scripts/episode_s2v.py -e EP --shots S03 --backend infinitetalk --profile-params
# 또는 pipeline
python scripts/episode_pipeline.py -e EP --run --from s2v --to s2v --profile hero --shots ...
```

| profile | SI2V | 속도 | 용도 |
|---------|------|------|------|
| **preview** | LTX | ★★★★★ | 탐색·스모크 |
| **deliver** (default) | **LTX** | ★★★★★ | 에이전트 실무 기본 (말하기 프롬프트 강제) |
| **hero** | InfiniteTalk | ★★ | 얼굴 CU 최종 립 (해상도/fps/steps 축소 적용) |

---

## 10. SI2V 속도 리서치 · 정책 (2026-07-12)

### 10.1 측정·체감 (이 머신 / RTX 4090급)

| 경로 | 대략 | 설정 예 |
|------|------|---------|
| LTX `ltx23_ia2v` | **~1–2 min / 5s** | distilled GGUF, custom-audio |
| InfiniteTalk (풀) | **~10–12+ min / 4–5s** | 960×544, 25fps, **20 steps**, lightx2v **미적용** |

→ 대사 컷을 전부 IT 풀퀄로 돌리면 **에이전트 반복 루프 불가**에 가깝다.

### 10.2 느린 이유 (현재 IT 그래프)

- Wan2.1 **14B** + InfiniteTalk 패치  
- 고해상(960×544) × 고 fps(25) × 다수 프레임(~100)  
- steps=20, **distill LoRA 미연결**  
- TeaCache / SageAttention 미적용  

### 10.3 커뮤니티·문서에서 알려진 가속 (우선순위)

| 방법 | 기대 | 위험/메모 | 우리 적용 |
|------|------|-----------|-----------|
| **lightx2v I2V distill LoRA + 4–8 steps** | 큰 폭 (수 배) | LoRA 없으면 저 step 품질 붕괴 | **로컬 LoRA 있음** (`Wan2.1/Wan21_I2V_14B_lightx2v_…`). **그래프 배선은 Comfy 직접 변경 → 보류** |
| 해상도 480p~832 long-edge | ~2× | 얼굴 디테일↓ | ✅ CLI: hero `long_edge=832` |
| fps 25→16 | ~1.5× | 보간 후처리 가능 | ✅ hero `fps=16` |
| steps 20→12 (LoRA 없이 중간값) | ~1.5× | 립/디테일 약간↓ 가능 | ✅ hero `steps=12` |
| 대사 2–3s 제한 | 선형 | 연출 제약 | 정책 권장 (strict spill과 맞음) |
| TeaCache / SageAttention | ~1.3–2× | 노드·호환 | **보류** (Comfy 커스텀 경로) |
| LTX를 기본 루프로 | 구조적 해결 | 립 상한 IT보다 낮을 수 있음 | ✅ **default SI2V = LTX** |

참고 링크·맥락: InfiniteTalk+lightx2v 4step, TeaCache on Wan, LTX vs IT 속도 비교 커뮤니티 리포트 (2025–2026).

### 10.4 정책 결정

1. **에이전트 기본 SI2V = `ltx23_ia2v`**  
   - 말하기 motion 템플릿 강제 유지 (입 안 벌림 재발 방지)  
   - format-consistent work aspect  
2. **InfiniteTalk = `hero` 프로필 / 명시적 `--backend infinitetalk`**  
   - 히어로 CU 1–2컷  
   - 기본 파라미터를 **조금 낮춤** (832 / 16fps / 12step) — 그래프 수정 없이  
3. **Comfy 그래프 변경 (lightx2v 노드 삽입, TeaCache) = 후순위**  
   - 위험·회귀 큼 → 파라미터/프로필 안정화 후 별도 작업  

### 10.5 다음에 안전하게 할 수 있는 작업 (Comfy 비침습)

- [x] 문서화 (본 절)  
- [x] profile 재정의: preview / deliver=LTX, hero=IT  
- [x] IT 호출 시 steps/fps/long_edge 기본 완화  
- [ ] 샷 단위 타이밍 로그 (`meta/*_s2v.json`에 `elapsed_sec`)  
- [ ] 대사 권장 최대 초 정책 (TTS/QA 경고)  
- [ ] lightx2v 그래프 배선 스모크 (별도 PR, Comfy 주의)

### 10.6 로컬 가속 자산 (배선 대기)

```
ComfyUI/models/loras/Wan2.1/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors
```

→ InfiniteTalk `WanVideoModelLoader` 경로에 LoRA 연결 시 4–8 step 실험 가능. **지금은 연결하지 않음.**
