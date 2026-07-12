# ComfyUI 메모리 · 모델 전환 (공정 사고 분석)

- **작성일**: 2026-07-12  
- **계기**: `cafe_gomin_ep01` 빨대 제거 I2I 직후 LTX 2.3 AIO last-frame 체인 S02 실행 중 **사실상 hang**  
- **관련**: [ltx23_aio_pipeline_integration.md](ltx23_aio_pipeline_integration.md), [moody_workflow_guide.md](moody_workflow_guide.md), [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md)

---

## 0. 한 줄 결론

**순수 “C 메모리 누수 버그”라기보다, 우리 공정이 모델 전환 시 unload/free를 전혀 안 하고, Comfy가 `--disable-smart-memory`로 떠 있어서 VRAM 오프로드가 시스템 RAM에 쌓인 뒤 LTX 풀로드와 겹쳐 thrash/hang 한 사고**에 가깝다.

같은 LTX 그래프(544×960 · 89f · i2v_audio)는 **직전 스모크에서 ~80초 정상 완료**. 설정 자체는 가능 범위였다.

---

## 1. 관측 타임라인 (2026-07-12 로컬)

| 시각(대략) | 이벤트 | 메모 |
|------------|--------|------|
| ~22:31–22:33 | LTX AIO **스모크 성공** | ~80s, Prompt executed OK |
| ~22:35–22:37 | Moody **I2I ×3** (빨대 제거 시도) | ZImage TE ~7.6GB + Lumina2 ~11.7GB full load |
| 22:37:56 | LTX S02 **체인 큐** | 동일 스펙 89f / 544×960 / audio |
| 22:37:57–22:38:35 | AudioVAE → VideoVAE → LTXAVTE(partial+CPU offload) → LTXAV(partial) | 로그 마지막 정상 로드 지점 |
| 22:38:35–22:47:01 | **샘플러 progress 로그 없음** | ~8분 hang (스모크 대비 비정상) |
| hang 중 | Comfy **WS ~46GB / Private ~60–72GB**, free RAM ~0.2–7GB, VRAM ~23.9/24.5GB | thrash |
| 22:47:01 | `/interrupt` | Processing interrupted |
| 22:47:32 | Prompt executed in **576.38s** (중단 종료) | `Using RAM pressure cache.` |
| free 직후(실행 중) | free가 **즉시 효과 없음** | 실행 중 unload 불완전 |
| 종료 후 `/free` ×2 | VRAM ~5.5GB used, free RAM ~54GB, Comfy WS ~1GB | **정상 회복** |

---

## 2. 원인 분해

### 2.1 공정 쪽 (우리 코드 — 1순위)

| 항목 | 현황 | 영향 |
|------|------|------|
| `lib/comfy_client.py` | `queue_prompt` / `wait_for_history` / download **만** 존재 | **`/free`, `/interrupt` 헬퍼 없음** |
| `generate_moody_i2i.py` | 종료 후 unload 없음 | ZImage 계열이 VRAM/RAM에 잔류 가능 |
| `generate_s2v.py` (LTX) | 시작 전 free 없음 | 이질 모델 스택 위에 LTX 로드 |
| `chain_si2v_last_frame.py` | 샷 사이 free 없음 | 연속 LTX는 동종이라 덜 위험, **이종 직후 첫 샷이 위험** |
| 엔진 경계 | I2I(Moody/ZImage) ↔ LTX(Gemma TE + dual VAE + GGUF UNet) | **가중치 세트가 완전히 다름** — 전환 시 free 필수 수준 |

→ “누수”처럼 보이는 패턴의 **직접 원인**: **전환 훅 부재**.

### 2.2 Comfy 런타임 플래그 (환경 — 2순위)

`system_stats.argv` 실측:

```text
ComfyUI\main.py --windows-standalone-build --fast fp16_accumulation --disable-smart-memory
```

| 플래그 | 의미(실무) |
|--------|------------|
| `--disable-smart-memory` | 모델 교체 시 VRAM을 공격적으로 비우기보다, **오프로드·캐시를 유지**하는 경향. 수동 AIO 단일 세션에는 유리할 수 있으나, **에이전트 이종 엔진 연타에는 불리**. |
| hang 로그 | `0 models unloaded` / partial unload ~47MB only while TE residual ~15GB |
| 중단 후 | `Using RAM pressure cache.` — 시스템 RAM 압박 경로 진입 |

### 2.3 모델 스택 자체의 무게 (3순위 — “한 방” 비용)

LTX AIO i2v_audio 한 그래프가 동시에 요구하는 것:

- Gemma 계열 **LTXAVTE** (partial ~15GB + CPU offload ~9GB 관측)
- **LTXAV GGUF** Q4 (~17GB 급 partial)
- Video VAE + Audio VAE
- AV latent 544×960×89

**단독 실행**이면 4090 24GB + 64GB 시스템으로 스모크 성공.  
**직전 Moody full load 잔류 + disable-smart-memory** 가 겹치면 시스템 RAM 60GB+ private 까지 팽창.

### 2.4 “누수”인가?

| 가설 | 판정 |
|------|------|
| 프로세스 종료 없이 영구 증가만 하는 true leak | **이번 사고만으로 확정 불가**. free 후 WS ~1GB로 **대부분 회수됨** |
| 이종 모델 전환 시 unload 없는 **잔류 축적 (soft leak / cache pile-up)** | **강하게 지지** — 공정 코드에 free 경로 0 |
| LTX hang = OOM hard kill | **아니오** — 프로세스는 살아 있고 interrupt 후 종료. VRAM full + RAM thrash hang에 가까움 |
| 에이전트 그래프가 사용자 AIO보다 “항상” 더 무거움 | **스모크 동일 스펙 성공** → 그래프 단독 원인은 아님. 전환 컨텍스트가 핵심 |

---

## 3. 정리 절차 (재발 시 운영)

1. `POST /interrupt`  
2. 큐 비움 확인 (`queue_running` empty). **실행 중엔 free가 거의 안 먹힘.**  
3. 종료 후 `POST /free` `{"unload_models": true, "free_memory": true}` (필요 시 2회)  
4. 확인: `nvidia-smi` VRAM, `system_stats` ram_free, Comfy 프로세스 WS  
5. free 후에도 Private/WS 비정상 → **Comfy 프로세스 재시작** (가장 확실)

이번 세션: interrupt → (완료) → free×2 후  
**VRAM ~5.5GB used · free RAM ~54GB · queue empty · WS ~1GB** 로 회복.

---

## 4. 정책: **패밀리 전환 시에만 free** (구현됨)

매 샷·매 호출 free는 **비효율** (로드 비용 재발생). 기본 정책:

```
AGENT_COMFY_FREE_POLICY=on_switch   # default
```

| 상황 | 동작 |
|------|------|
| 같은 패밀리 연속 (LTX S02→S03→S04) | **free 스킵** |
| 패밀리 변경 (Moody I2I → LTX) | **unload + free + 메모리 게이트** 후 진행 |
| 콜드 스타트 (세션 파일 없음) | free 스킵 (이미 깨끗할 수 있음) |
| `always` / `never` | env로 강제 |

### 패밀리

| family | 도구 |
|--------|------|
| `moody_still` | T2I/I2I/ControlNet Moody |
| `ltx` | `ltx23_*` SI2V |
| `infinitetalk` | InfiniteTalk SI2V |
| `wan` | Wan I2V |
| `ace_step` | BGM (연동 시) |

### 코드

| 모듈 | 역할 |
|------|------|
| `lib/comfy_client.py` | `free_comfy_memory`, `interrupt_comfy`, `memory_snapshot` |
| `lib/comfy_engine_session.py` | `ensure_engine(family)` — **전환 시에만 free** |
| 상태 파일 | `.agent_cache/comfy_engine_session.json` (프로세스 간 유지) |

연동 스크립트: `generate_moody*.py`, `generate_s2v.py`, `generate_i2v.py`.

### 게이트 임계값 (env)

| env | default |
|-----|---------|
| `AGENT_COMFY_MIN_RAM_FREE_GB` | 12 |
| `AGENT_COMFY_MIN_VRAM_FREE_MB` | 4000 |

게이트 실패 시 생성 **abort** (`error=MEMORY_GATE`). Comfy 재시작 또는 수동 free 후 재시도.

### 아직 남은 것

| ID | 작업 |
|----|------|
| M3 | 초장시간 동종 체인 N샷마다 optional free (기본 off) |
| M4 | hang 감지 + auto interrupt |
| M5 | 결과 메타에 `engine_session` 항상 기록 |
| E1 | 에이전트 Comfy 기동 시 `--disable-smart-memory` 재검토 |

### P1 — 환경

| ID | 작업 |
|----|------|
| E1 | 에이전트 전용 Comfy 기동 시 **`--disable-smart-memory` 재검토** (수동 AIO 세션과 분리 권장) |
| E2 | 문서화: “이종 엔진 연속 작업 전 Manage → Free memory 또는 재시작” |

### P2 — 품질 분리 (관련)

| ID | 작업 | 비고 |
|----|------|------|
| I1 | **Still inpaint 도구** (마스크 국소 편집) | I2I로 소품 제거 반복 금지 → 전환 폭주 완화에도 도움. 로드맵 항목 참고 |

---

## 5. 에이전트 운용 규칙 (당장 문서 규율)

엔진 패밀리 예:

- **Still Moody**: T2I / I2I / ControlNet (ZImage + Lumina2)  
- **LTX 2.3**: GGUF UNet + Gemma TE + video/audio VAE  
- **InfiniteTalk / WAN**: 또 다른 스택  

**규칙**

1. 패밀리 A 작업 끝 → 패밀리 B 시작 전 **free 또는 Comfy 재시작**.  
2. 빨대·로고 등 **국소 수정은 I2I 연타 금지** (실패 + 메모리 낭비). 인페인트 도구 생길 때까지 로컬 마스크 응급 또는 재키프레임.  
3. LTX 장체인 전 **스모크 1샷**으로 VRAM/RAM 여유 확인.  
4. free RAM < ~12GB 또는 VRAM free < ~4GB 이면 LTX 풀로드 **시작하지 말 것**.

---

## 6. 재현 실험 (선택, 후속)

통제 조건:

1. Comfy 재시작 → LTX 스모크 1회 → 메모리 스냅샷  
2. 재시작 → Moody I2I 3회 → **free 없이** LTX → hang 여부  
3. 재시작 → Moody I2I 3회 → **free 후** LTX → 성공 여부  

기대: (2) thrash, (3) 정상 ≈ 스모크. 이게 맞으면 원인 확정.

---

## 7. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | cafe_gomin LTX hang 관측·interrupt/free 회복·원인 초안 기록 |
| 2026-07-12 | **on_switch free** 구현 (`comfy_engine_session` + generate_* 연동) |
