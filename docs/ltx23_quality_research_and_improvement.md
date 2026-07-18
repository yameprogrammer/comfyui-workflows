# LTX 2.3 품질 리서치 · 에이전트 갭 · 개선 백로그

- **작성**: 2026-07-18  
- **범위**: 웹·유튜브·커뮤니티·공식 가이드 + 공장 로컬 스택 대조  
- **관련**: [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md) · [ltx_face_stability.md](ltx_face_stability.md) · [ltx23_aio_ia2v_agent_usage.md](ltx23_aio_ia2v_agent_usage.md) · [upscale_research_and_design.md](upscale_research_and_design.md)  
- **코드 SSOT**: `lib/ltx_quality_profiles.py` · `video_backends.json` → `ltx_quality_profiles` · CLI `--ltx-profile`

---

## 1. 한 줄 결론

| 질문 | 답 |
|------|-----|
| LTX 2.3 **엔진 선택**이 로컬 오픈 실무 상급이냐? | **예** (2026 Comfy/오픈 컨센서스 + 공장 Wan A/B) |
| **에이전트 기본 출력**이 유튜브 쇼케이스급이냐? | **아니오** — work/FAST 티어 |
| “영 아닌 느낌”의 주원인 | 해상도·클립 길이·프롬프트·키프레임·양자화/2-stage·얼굴 운영 갭 (엔진 오선택 단독 아님) |

> **LTX 채택은 타당. 기본값은 매일 돌리는 work 레인. 유튜브급은 hero 프로필·짧은 클립·좋은 still·프롬프트 방언으로 끌어올린다.**

---

## 2. 외부 평가 요약

### 2.1 공식 / 벤더

| 소스 | 요지 |
|------|------|
| Lightricks Comfy workflow guide | work **1280×720** 권장 시작 → 익숙하면 1080/1440; 디테일 이득 실재, 시간 대략 선형 |
| FPS | 24 방송 표준 · 30 유연 · 고 FPS 시네마 취향 |
| CFG | ~2.0–5.0 (기본 ~3–3.5 계열 언급) |
| 공식 example WF | single-stage distilled · **two-stage + upsample** · IC-LoRA control/detail |

### 2.2 YouTube / 튜토리얼

- “best free local AI video” 류로 LTX 2.3 다수.
- LTX vs Wan: **해상도·steps·FPS·2-pass** 올리면 체감 급변 (코멘트: LTX 1080 + 30fps + stage steps, detailer/IC LoRA).
- 쇼케이스는 대개 **고품질 still + 짧은 의도 명확 모션 + (자주) 2-stage/후처리**.

### 2.3 Reddit / 커뮤니티

- **공식/검증 2.3 워크플로 > 엉성한 내장 템플릿**.
- Distilled ≈ 빠름·실용 / Dev·Full ≈ 텍스처·일관성 천장 (~90–95% vs full).
- GGUF Q4–Q6 실무 스윗스팟; 품질 극대화는 Q6/Q8·detailer·해상도·sampler.
- “며칠 튜닝 후 재현 품질” — **모델 이름만으로 유튜브급 불가**.

### 2.4 공장 자체 A/B (2026-07-17)

| | Wan 2.2 lightx2v | LTX AIO |
|--|------------------|---------|
| 모션 | 플랫/프리즈 경향 | **승** |
| 필름감 | 플라스틱 | **승** |
| 샤프 | 약간 우위 | 다소 소프트 |
| **정책** | fallback | **default I2V/FLF** |

---

## 3. 공장 LTX 인벤토리 (현 상태)

| 항목 | 상태 |
|------|------|
| 본선 | `ltx23AllInOneWorkflowForRTX_v44` + `ltx_aio_workflow_runner` (real UI 스위치) |
| 기본 I2V | `ltx23_aio_i2v` |
| 기본 SI2V | `ltx23_aio` (image+audio) |
| 립 히어로 | `infinitetalk` (분리됨) |
| 얼굴 | detailer ON @0.55 · distill ~0.6 (`ltx_face_stability.md`) |
| work 해상도 기본 | **`work_*_720`** (예 1280×720 / 720×1280) — **2026-07-18 상향** · 레거시 540은 draft |
| 납품 | upscale 레이어 (work 품질 상한 유지) |
| 부가 | LatentHeart · REDMix · NSFW Kenpechi (opt-in) |

---

## 4. 유튜브 vs 에이전트 갭 (우선순위)

| # | 갭 | 유튜브/히어로 | 에이전트 기본 | 개선 레버 |
|---|-----|---------------|---------------|-----------|
| **G1** | 생성 해상도 | 720p–1080p work | ~~기본 ~540~~ → **기본 720p (2026-07-18)** · draft=540 · hero≈1080 | `--ltx-profile` · presets |
| **G2** | 클립 길이 | 짧고 한 의도 | 긴 SI2V/장 I2V | max clip 캡 · 분할 |
| **G3** | 얼굴 | CU + detailer + 짧은 테이크 | 와이드·장클립 drift | face_stability · IT 히어로 |
| **G4** | 프롬프트 | 시간순 모션 | 룩 재서술·태그수프 | generation-prompt LTX 방언 |
| **G5** | 키프레임 | 고품질 still | 미QA still | shot QA 게이트 |
| **G6** | 모델 티어 | full/dev·2-stage | distilled 실무 | hero 2-stage / quant (후속) |
| **G7** | 합본 체감 | 단일 히어로 | work 다컷 + soft upscale | 컷 승인 + SeedVR2 마감 |

---

## 5. 판정표

| 기준 | 점수 | 메모 |
|------|------|------|
| 엔진 선택 | A− | 로컬 오픈 상급 실무 |
| 실무 성능 (4090 배치) | A | work/distilled |
| 품질 천장 | B~B+ | hero 티어로 상승 여지 |
| 기본 출력 ≈ 유튜브 | C+ | 의도적 work |
| 문서/가드레일 | A− | 실행 프로필로 고정 필요 |

업스케일과 동일 구조: **FAST/work 기본 + HERO opt-in**.

---

## 6. 개선 백로그 (할 수 있는 것)

### P0 — 이번 반영 (계약·기본 레버)

| ID | 작업 | 상태 | 산출 |
|----|------|------|------|
| **L0** | 본 리서치 문서 | ✅ | 이 파일 |
| **L1** | `draft` / `work` / `hero` **품질 프로필** SSOT | ✅ | `lib/ltx_quality_profiles.py` · `video_backends.json` |
| **L2** | CLI `--ltx-profile` (`generate_s2v` / `generate_i2v`) | ✅ | 해상도·face·detailer·clip 가이드 |
| **L3** | AGENT_GUIDE · tool_catalog · tooling_todo 링크 | ✅ | 발견 경로 |

### P1 — 근시일 (품질 상한)

| ID | 작업 | 난이도 | 메모 |
|----|------|--------|------|
| **L4** | Hero **2-stage upsample** 스위치 (AIO 내 노드 확인 후) | 중 | 공식 two-stage 정렬 |
| **L5** | Hero longer-edge **1280–1536** 실측 + OOM 가드 | 중 | 4090 벤치 로그 |
| **L6** | Pure I2V **max duration 강제**(기본 4s, override 플래그) | 하 | face melt 방지 |
| **L7** | 생성 전 **prompt dialect check** (룩 재서술 경고) | 중 | generation-prompt 연동 |
| **L8** | `failure_note` 태그 묶음 `ltx_face` / `ltx_soft` preflight | 하 | before-gen |

### P2 — 선택·실험

| ID | 작업 | 메모 |
|----|------|------|
| **L9** | Q6/Q8 또는 dev unet hero 경로 | VRAM·시간 trade-off |
| **L10** | LatentHeart / REDMix을 hero 대안 카드로 tool_intent 정리 | 이미 도구 존재 |
| **L11** | Episode batch: draft 전샷 → hero 승인컷만 | 파이프 정책 |
| **L12** | 자동 work→SeedVR2 마감 체인 옵션 | upscale_recommend 연동 |

### 하지 않음 (의도)

| 항목 | 이유 |
|------|------|
| 기본을 1080 full 생성으로 상향 | 배치·VRAM 붕괴 · work 레이어 철학 위반 |
| Topaz/클라우드 필수화 | 로컬 공구함 SSOT 밖 |
| 모든 컷 InfiniteTalk | 속도·모션 범위 부적합 · 립 히어로만 |

---

## 7. 에이전트 운용 규칙 (프로필 도입 후)

```text
일상 배치 / 본선       →  --ltx-profile work   (기본 = 720p)
러프 탐색              →  --ltx-profile draft  (~540)
히어로 1컷             →  --ltx-profile hero   (~1080 work) + 짧은 클립 + 좋은 KF
대사 얼굴 CU           →  infinitetalk (LTX 아님)
구조 깨진 still        →  edit/QA 후 I2V
납품 해상도            →  upscale_* (구조 고정 후) — deliver_1080/4K
```

```bash
# Work (default = 720p)
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow push in, soft blink"

# Draft (fast legacy 540)
python scripts/generate_i2v.py -i key.png -o scout.mp4 -p "..." --ltx-profile draft

# Hero (~1080 work)
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "gentle head turn, eyes hold lens" \
  --ltx-profile hero --frames 73
```

---

## 8. 참고 링크

- https://ltx.io/blog/comfyui-workflow-guide  
- https://github.com/Lightricks/ComfyUI-LTXVideo (example_workflows/2.3)  
- Reddit: official 2.3 WF > stock templates; distilled vs dev; GGUF Q-tier  
- 공장: `docs/wan_vs_ltx_i2v_ab_2026-07-17.md` · `docs/ltx_face_stability.md`

---

## 9. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-18 | 초안: 리서치 + 갭 + 백로그 · L0–L3 프로필 구현 |
| 2026-07-18 | **기본 work = 720p** (`work_*_720` · LTX work longer_edge 1280). draft=540 · hero≈1080 |
| 2026-07-18 | **기본 UNET = dev Q6_K** (`F:\model\diffusion_models\LTX2.3\ltx-2.3-22b-dev-Q6_K.gguf`); Q4 레거시 유지 |
| 2026-07-18 | **AIO = 이미 2-stage** 확인; LoRA 튜닝 work: distill 0.7 · detailer 0.55 · upscale IC 0.45 · omni 0.45 |
