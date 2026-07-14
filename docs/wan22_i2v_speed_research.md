# Wan2.2 I2V 속도 리서치 · 도구 개선 검토

- **작성일**: 2026-07-13  
- **대상**: 에이전트 파이프 `backend=wan22` (`scripts/generate_i2v.py` · `workflows/agent/I2V-wan22-a14b.json`)  
- **관련**: [video_delivery_and_backends.md](video_delivery_and_backends.md) · [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md) §10 (SI2V/IT 가속 — 별 경로)  
- **상태**: 리서치 + **P0·P1 구현·스모크 완료** (2026-07-13)

---

## 0. 한 줄 요약

우리 Wan2.2 경로는 이미 **A14B GGUF + lightx2v 4step LoRA + 6step** 이라 “완전 풀퀄 20step”보다는 빠르지만,  
**SageAttention / TeaCache·MagCache / TorchCompile / BlockSwap 튜닝 / steps CLI 배선 / preview 프로필** 이 비어 있어  
커뮤니티에서 흔히 쓰는 가속의 상당 부분을 **아직 도구가 안 켠 상태**다.  
IT 경로에 이미 넣은 가속(lightx2v+TeaCache+sage)을 **I2V wan22에도 대칭 이식**하는 것이 1순위다.

---

## 1. 현재 우리 스택 (실측 구성)

| 항목 | 현재 값 | 출처 |
|------|---------|------|
| 엔진 | Wan2.2 I2V **A14B dual** HighNoise + LowNoise GGUF Q4_K_M | `generate_i2v.py` inject |
| Distill | **lightx2v HIGH/LOW 4step LoRA** rank64 fp16 @ strength 1.0 | 로컬 `loras/Wan2.2/…` |
| steps | 워크플로 INTConstant **6** (high 0→3 / low 3→끝) | API 변환 결과 |
| CFG / shift / scheduler | cfg=1, shift=8, `dpm++_sde` | sampler |
| attention | **`sageattn` 기본** (`AGENT_WAN_ATTENTION` / `--attention`) | `generate_i2v.py` P0 |
| TorchCompile | 노드 있음, **enable=False** | WF id 35 |
| BlockSwap | **20 blocks** | WF id 39 |
| T5 | `umt5-xxl-enc-bf16` + offload_device | WF |
| VAE | `wan_2.1_vae` bf16 | inject |
| 해상도 | episode work (쇼츠 **544×960**) | `work_9x16_540` |
| fps / frames | 기본 fps=16, frames≈duration×fps (4n+1 snap) | CLI / episode_i2v |
| 로드 | `load_device=offload_device`, `force_offload=True` | 메모리 우선 |
| TeaCache / MagCache | Comfy에 **노드 존재**, **우리 WF에 미연결** | object_info |
| SageAttention | IT 경로 사용 중; **wan22 I2V는 sdpa** | 코드 |

**이미 잘 된 것**

- lightx2v 4step 계열 LoRA 적용 (커뮤니티 최우선 가속 중 하나)  
- work 해상도 정책 (납품은 upscale)  
- 프레임 4n+1 · 공간 16 배수 snap  
- 엔진 패밀리 free 훅 (`comfy_engine_session`)  
- SI2V 기본을 LTX로 빼서 “매 컷 Wan 풀” 부담 감소  

**아직 느린 체감 이유 (추정 기여도)**

1. **14B × 2패스(high/low)** 본질 비용  
2. attention = **sdpa** (sage 미사용)  
3. **TeaCache/MagCache 미연결**  
4. BlockSwap 20 + offload (VRAM 절약 ↔ 속도 손해)  
5. TorchCompile off (반복 생성 시 워밍업 이득 없음)  
6. 쇼츠 544×960 · 프레임 수 (3~5s @16fps ≈ 49–81f)  
7. (버그성) CLI `--steps` 가 sampler INTConstant를 **거의 안 바꿈** (값 30만 패치)

---

## 2. 커뮤니티·문서 가속 레퍼런스 (요약)

| 기법 | 기대 효과 (문헌·커뮤니티) | 품질 리스크 | 우리 적용 상태 |
|------|---------------------------|-------------|----------------|
| **lightx2v / Lightning distill LoRA + 4–8 step** | 수 배 (steps 선형) | LoRA 없이 저step 붕괴 | ✅ 적용 (6step) |
| **SageAttention** | ~10–30%+ (환경 의존) | 간헐 수치 불안정 | ✅ I2V default sage (P0); warm smoke ~5% vs sdpa |
| **TeaCache** (WanVideoTeaCache) | ~30–50% (설정 공격적 시 ~2× 보고) | **자글자글/grain 품질 탈락** (사용자 육안 07-13) | ⚡ CLI opt-in only · **deliver 기본 off** |
| **MagCache** | TeaCache 대체/우위 보고 다수 | **동일 품질 탈락** | ⚡ CLI opt-in only · **deliver 기본 off** |
| **TorchCompile** | 워밍업 후 반복 생성 가속 | 첫 런 느림, 디버그 어려움 | ⬜ 노드 off |
| **BlockSwap 축소** | VRAM 여유 시 체감 큼 | OOM | ⬜ 20 고정 |
| **해상도↓ / frames↓** | 거의 선형 | 디테일·모션 길이 | △ preset 있으나 profile 약함 |
| **T5 fp8/quant** | 로드·encode 약간 | 프롬프트 추종 | ⬜ bf16 only |
| **fp8 quant on UNet** (loader quantization) | 속도·VRAM | GGUF와 중복 시 효과 제한 | ⬜ disabled |
| **RIFE 등 프레임 보간** | 생성 frames 절반 후 늘리기 | 모션 보간 위화 | ⬜ 파이프 미연결 |
| **백엔드 대체 (LTX I2V)** | 구조적 해결 | 모션 톤 다름 | △ `ltx23` planned / AIO i2v 있음 |

참고 맥락: kijai WanVideoWrapper TeaCache/MagCache, SageAttention 벤치 스레드, lightx2v 4step 튜토리얼, stable-diffusion-art TeaCache+Sage 가이드 (2025–2026).  
수치는 **우리 4090급·GGUF·쇼츠 해상도에서 재측정 필수**.

---

## 3. 도구 코드 갭 (구체)

### 3.1 `generate_i2v.py`

| 갭 | 내용 | 개선 방향 |
|----|------|-----------|
| attention 고정 | `attention_mode = "sdpa"` 강제 | `AGENT_WAN_ATTENTION` 기본 `sageattn` (폴백 sdpa) — IT와 동일 패턴 |
| steps 미배선 | INTConstant `value==30` 만 패치 → 실제 steps 노드는 **94=6** | `value`가 steps 링크 노드(및 boundary INT 91)를 **직접** 세팅 |
| dual boundary | high/low 분할 = INT 91 (기본 3 = steps/2) | `steps` 변경 시 `boundary = steps // 2` 자동 |
| cache 없음 | TeaCache/MagCache 미주입 | API에 `cache_args` 연결 또는 WF에 노드 추가 후 inject |
| compile 없음 | TorchCompile off | 프로필 `preview` 에서 opt-in / env `AGENT_WAN_COMPILE=1` |
| blockswap 고정 | 20 | env/프로필로 0~40; VRAM 여유 시 0~10 |
| 프로파일 없음 | IT는 preview/deliver/hero 있음 | I2V에도 `preview` / `deliver` 파라미터 세트 |
| 타이밍 | IT는 `elapsed_sec` 기록 | I2V meta에도 wall time 필수 (벤치 SSOT) |

### 3.2 워크플로 `I2V-wan22-a14b.json`

- TeaCache / MagCache / EnhanceAVideo **미배선**  
- Compile 노드 있으나 비활성  
- 기본 encode 해상도 위젯 잔재(832×480 등) — 런타임 inject로 덮음  

### 3.3 `video_backends.json` / `episode_i2v`

- wan22 notes에 속도 프로필 없음  
- episode 기본 frames = duration×fps → 긴 establishing은 비용 급증  
- `ltx23` general I2V runner **미구현** (빠른 alt 백엔드 후보이나 별 티켓)

### 3.4 이미 있는 자산 (재사용)

| 자산 | 위치 |
|------|------|
| lightx2v HIGH/LOW LoRA | `models/loras/Wan2.2/Wan_2_2_I2V_A14B_*_lightx2v_4step_*` |
| SageAttention (Comfy env) | IT에서 `attention_mode=sageattn` 검증됨 |
| `WanVideoTeaCache` / `MagCache` 노드 | Comfy object_info 확인 |
| 엔진 free 훅 | `lib/comfy_engine_session.py` |

---

## 4. 권장 적용 로드맵 (우선순위)

### P0 — 저위험 · 코드만 · 기대 중~큼 — **✅ 2026-07-13**

| ID | 작업 | 기대 | 상태 |
|----|------|------|------|
| **W0** | steps/boundary INTConstant 정확히 패치 + meta 기록 | 정확성 + 4step 실험 가능 | ✅ |
| **W1** | `attention_mode=sageattn` 기본 (`AGENT_WAN_ATTENTION` / `--attention`) | +10–30% 체감 후보 | ✅ (warm ~5% on 17f smoke) |
| **W2** | I2V wall-clock `elapsed_sec` + 벤치 로그 포맷 | 이후 A/B 필수 | ✅ |

스모크 산출: `stories/cafe_gomin_ep01/clips/work/_bench_wan22_speed/`  
CLI: `--dry-run` · `--attention` · meta `steps_boundary` / `elapsed_sec`

### P1 — 중간 공수 · 기대 큼 — **✅ 2026-07-13**

| ID | 작업 | 기대 | 상태 |
|----|------|------|------|
| **W3** | **TeaCache** 연결 | +30–50% 후보 | ✅ 구현 · **품질 탈락** → 기본 off |
| **W4** | **MagCache** A/B | 동급 또는 우위 | ✅ 구현 · **품질 탈락** → 기본 off |
| **W5** | I2V **preview/deliver/quality 프로필** | 공정 속도 | ✅ steps/해상도/swap (cache 아님) |
| **W6** | BlockSwap 프로필화 + 벤치 | VRAM/속도 | ✅ smoke 기록; **기본값=출발점, 상황별 조절** (아래 §4.1) |

추가: unique VHS prefix (캐시 히트 시 구 mp4 오인 방지).  
**본선 기본 (품질 게이트 후)**: `deliver` + **cache=none** + sageattn + lightx2v steps.  
Tea/Mag는 `--cache teacache|magcache` 실험용만 (더 낮은 thresh 실험 여지 있으나 현재 본선 비권장).

### 4.1 BlockSwap 운용 정책 (SSOT · 2026-07-13 확정)

**개념:** UNet 블록을 GPU에 덜/더 올리는 **VRAM ↔ 속도 트레이드오프**.  
샘플링을 건너뛰는 품질 해킹(Tea/Mag)이 **아님**. 육안 깨짐은 보통 없음.

| `blocks_to_swap` | GPU 상주 | VRAM | 속도 | 큰 작업 |
|------------------|----------|------|------|---------|
| **높음 (20+)** | 적음 | 여유 ↑ | 느림 | **안전** |
| **중간 (10)** | 중간 | 중간 | 중간 | 평소 출발점 |
| **0** | 많음 | 사용 ↑ | 가장 빠름 | **OOM 위험 ↑** |

**정책: 고정 만능값이 아니라 상황별 조절.**

| 상황 | 권장 |
|------|------|
| 일상 쇼츠 work (짧은 클립) | 프로필 기본 (**deliver=10**) 또는 여유 있으면 ↓ |
| 고해상 / 긴 프레임 / OOM 경험 | **`--block-swap 20`** (또는 더) |
| VRAM 여유 확실 + 짧은 반복 | **`--block-swap 0`** 시도 |
| preview 탐색 | 프로필 preview (이미 낮은 swap + 작은 long_edge) |

```bash
python scripts/generate_i2v.py ... --block-swap 20   # 안전
python scripts/generate_i2v.py ... --profile deliver # 기본 10
python scripts/generate_i2v.py ... --block-swap 0    # 최대 속도 (위험)
```

스모크 참고 (368×640 · 17f · 6step · cache=none · sage):  
swap20 **32.2s** · swap10 **24.2s (−25%)** · swap0 **20.3s (−37%)**, 해당 스펙 OOM 없음.  
→ 풀 스펙(544×960·장프레임)에서는 **재측정·OOM 시 swap↑**.

### P2 — 선택 · 환경 의존

| ID | 작업 | 기대 | 비고 |
|----|------|------|------|
| **W7** | TorchCompile opt-in (배치 2번째 샷부터) | 반복 루프 | 첫 샷 워밍업 |
| **W8** | T5 fp8/quant 또는 경량 encoder | 로드·encode | 품질 확인 |
| **W9** | 저프레임 생성 + RIFE 보간 스테이지 | 긴 클립 | 파이프 설계 |
| **W10** | `ltx23` general I2V runner 완성 | 구조적 alt | 톤 다름 — establishing 후보 (S01에 AIO i2v 이미 사용 가능) |

---

## 5. 제안 기본 프로필 (초안)

| profile | 해상도 감 | steps | attention | cache | blockswap | 용도 |
|---------|-----------|-------|-----------|-------|-----------|------|
| **preview** | short edge ~368–480 | **4** | sageattn | Tea/Mag aggressive | 낮음 | 모션 탐색 |
| **deliver** (기본) | work_*_540 | **6** | sageattn | Tea mild or off | 10–20 | 본선 I2V |
| **quality** | 540–720 | 8–12 | sageattn | off | 필요시 | 히어로 무대사 |

CLI 스케치:

```bash
# 현재
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format shorts_9x16

# 목표
python scripts/generate_i2v.py ... --profile preview   # 빠름
python scripts/generate_i2v.py ... --profile deliver   # 기본
python scripts/episode_i2v.py -e EP --profile preview
```

---

## 6. 벤치 프로토콜 (구현 전·후 공통)

고정:

- 동일 키프레임 (예: `cafe_gomin_ep01` S01 또는 캐릭터 medium)  
- 동일 prompt / seed  
- 해상도 명시 (544×960 또는 960×544)  
- frames 고정 (예: 49 = 4n+1)  
- Comfy free 후 1회 워밍업 제외하고 2~3회 중앙값  

측정:

- wall `elapsed_sec`  
- VRAM peak (가능하면)  
- 육안: 모션 자연스러움, 얼굴/사물 안정, flicker  

저장:

```text
stories/<ep>/clips/work/_bench_wan22_speed/
  README.md
  base_sdpa_6step.mp4 + .json
  sage_6step.mp4
  sage_teacache_6step.mp4
  preview_4step.mp4
```

---

## 7. 파이프라인 운용 팁 (코드 전에도 가능)

1. **무대사 establishing** — 이미 `ltx23_aio_i2v` 가능 (S01). Wan 전량 고집이 아니면 시간 절약.  
2. **짧은 클립** — 3–4s work I2V + 필요 시 보간/연장.  
3. **미리보기 해상도** — 모션 확정 전 `work_*_360` 급.  
4. **이종 전환** — Wan↔LTX 전 `free` (기존 세션 규칙).  
5. **IT와 혼동 금지** — IT 가속 ≠ Wan2.2 I2V 그래프. lightx2v 파일도 2.1 vs 2.2 다름.

---

## 8. 결론 · 다음에 할 구현

**도구로 성능을 올릴 여지: 있음.**  
가장 ROI 큰 묶음:

1. **W0+W1+W2** (steps 배선 + sage + 계측) — 반나절 급  
2. **W3+W5** (TeaCache + preview/deliver 프로필) — 품질 게이트 포함 1–2일  
3. 장클립·대안은 **LTX I2V / 프레임 정책**으로 우회  

구현 착수 시 권장 순서: **W0 → W1 → 스모크 벤치 → W3 → 프로필 고정 → 문서/Rule 반영**.

---

## 9. 참고 파일

| 경로 | 역할 |
|------|------|
| `scripts/generate_i2v.py` | wan22 inject · attention · steps |
| `scripts/episode_i2v.py` | 배치 I2V |
| `workflows/agent/I2V-wan22-a14b.json` | dual GGUF + lightx2v 그래프 |
| `video_backends.json` | `wan22` SSOT |
| `docs/agent_video_tooling_reliability.md` §10 | SI2V/IT 가속 (대칭 참고) |
