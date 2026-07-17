# WAN 2.2 워크플로 팩 — 선별 가이드 (agent_custom)

**소스 원본:** `F:\ComfyUI_workflows\WAN 2.2 *.json`  
**Human SSOT (이 폴더):** 검증·재export용 UI 스냅샷  
**Agent 실행:** `workflows/agent/presets/*.api.json` + port patch (가능 시)

원칙: 커뮤니티 팩의 **서브그래프(UUID) + Set/Get/UE** 는 에이전트가 직접 돌리기 어렵다.  
→ **쓸 만한 것만 보관**하고, 본선은 **API 평탄 프리셋**으로 고정한다.

---

## 1. 선별 결과

| 파일 (이 폴더) | 원본 이름 | 판정 | 역할 | 에이전트 상태 |
|----------------|-----------|------|------|----------------|
| `wan22_i2v.json` | WAN 2.2 I2V | **폴백** | 단일 이미지→영상 (Kijai WanVideoWrapper) | agent `i2v_wan22_a14b` — **품질 본선은 LTX AIO** (A/B 2026-07-17) |
| `wan22_i2v_start_end.json` | WAN 2.2 I2V StartEnd Frames | **폴백 FLF** | First/Last frame | agent `i2v_wan22_a14b_flf`; **품질 FLF 본선 = `ltx23_aio_flf`** |
| `wan22_face_enhance.json` | WAN 2.2 FaceEnhance | **채택** | 클립 얼굴 보정 (CLIPSeg + Wan refine) | planned — post-I2V polish |
| `wan22_upscale.json` | WAN 2.2 UPSCALE | **채택** | Wan diffusion 영상 업스케일 | planned — opt-in quality lane |
| `wan22_upscale_face_enhance.json` | WAN 2.2 UPSCALE + FACE ENHANCE | **채택** | 업스케일+얼굴 연속 | planned — hero 마감 |
| `wan22_animate.json` | WAN ANIMATE 2.2 | **채택 (장르)** | 레퍼 모션→캐릭 (pose/SAM2) | planned — dance_challenge |
| `wan22_flf2v_native.json` | wan22_flf2v | **참고** | 네이티브 FLF (서브그래프 적음) | FLF API 후보 |
| `wan22_i2v_lightning_native.json` | Wan2.2-I2V-…lightning | **참고** | 네이티브 4step lightning | 경량 I2V 후보 |

### 의도적으로 넣지 않음

| 원본 | 이유 |
|------|------|
| **WAN 2.2 UPSCALE BATCH** | 폴더 크롤 배치 UX. 에피소드 배치는 `episode_upscale` / CLI 루프가 SSOT |
| **AllInOne-wan2.2** | 163노드 AIO·중복. LTX AIO + 본선 Wan I2V로 역할 분담 |
| **WAN 2.2 S2V** | 립 본선은 InfiniteTalk / LTX AIO. 이중 스택 유지 비용 |
| **FunCamera / FASTWAN 5B / T2I·T2V 배치** | 본선 파이프와 겹치거나 실험용 |
| **LORA COMPARE** | 휴먼 비교 전용 |

---

## 2. 서브그래프 해부 (핵심)

### Face Enhance (`e9eacb42-…`)
- `BatchCLIPSeg` + mask grow → `WanVideoEncode/Sampler/Decode` + `WanVideoEnhanceAVideo`
- 입력: **영상** (`VHS_LoadVideo`)
- 용도: I2V/SI2V 후 얼굴 붕괴·스미어 완화 (구조 오류는 업스케일 전에 고칠 것)

### Upscale (`caefe725-…`)
- Florence2 캡션 보조 + `WanVideoSampler` 기반 **재생성 업스케일**
- RTX VSR / SeedVR2와 **별 레인** (느리고 비쌈 → 기본 납품 금지)
- 기본 납품은 계속 `upscale_backends.json` → `rtx_vsr` / hero `seedvr2`

### Animate
- PREPROCESSOR: SAM2 + pose + mask  
- `WanVideoAnimateEmbeds` + 레퍼 비디오 + 캐릭 이미지  
- `dance_challenge` 파이프와 정합 (설계 문서 P3-1)

### I2V / StartEnd
- Model Loader 서브그래프: dual `WanVideoModelLoader` + LoRA  
- StartEnd = LoadImage ×2 → 같은 샘플러 경로 (FLF)

---

## 3. 공장 매핑

| 생산 단계 | 사용 |
|-----------|------|
| Work I2V (Wan 백엔드) | `generate_i2v --backend wan22` → **API 프리셋** |
| Work I2V (기본) | LTX AIO `ltx23_aio_i2v` (video_backends default) |
| FLF / last-frame chain | `wan22_i2v_start_end` 또는 native flf2v → 향후 `generate_i2v --flf` |
| 얼굴 후처리 | `wan22_face_enhance` (planned CLI) |
| 납품 업스케일 기본 | `rtx_vsr` / `seedvr2` (기존) |
| Wan 확산 업스케일 | `wan22_upscale` opt-in only |
| 댄스 모션 리타겟 | `wan22_animate` + dance_challenge 설계 |

---

## 4. API export 절차 (서브그래프 팩)

1. ComfyUI에 해당 JSON 로드  
2. 필요 입력 채운 뒤 **Save (API Format)** 또는 agent `graphToPrompt` export  
3. `workflows/agent/presets/<name>.api.json` + `.ports.json`  
4. catalog 등록 · `process.md` 한 줄  

**금지:** 서브그래프 UUID 노드를 Python으로 재조립.

---

## 5. 관련 코드

| 항목 | 경로 |
|------|------|
| Wan I2V API | `workflows/agent/presets/i2v_wan22_a14b.api.json` |
| UI 소스 (재export) | `workflows/agent/I2V-wan22-a14b.json` |
| CLI | `scripts/generate_i2v.py` |
| Backends | `video_backends.json` · `upscale_backends.json` |
| FLF 로드맵 | `docs/flf2v_f2f_roadmap.md` |
| 업스케일 정책 | `docs/upscale_research_and_design.md` |
