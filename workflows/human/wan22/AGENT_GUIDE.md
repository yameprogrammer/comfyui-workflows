# WAN 2.2 워크플로 팩 — 에이전트 가이드

> **Toolbox shelf:** MOTION (fallback) · FINISH (face / experimental upscale)  
> **품질 본선 I2V/FLF:** LTX — `generate_i2v` / `generate_flf2v` (Wan 아님)  
> **Wan CLI:** `generate_i2v --backend wan22` · `wan22_flf` · **`generate_wan22_nsfw_i2v` (18+)** · `generate_yaw_wan22` · face/upscale  
> **한 장 맵 (SSOT):** [docs/wan22_workflow_map.md](../../../docs/wan22_workflow_map.md)  
> **구조·효율 리서치:** [docs/wan22_workflow_research_and_design.md](../../../docs/wan22_workflow_research_and_design.md)  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.4 · §2.6

**소스 원본:** `F:\ComfyUI_workflows\WAN 2.2 *.json`  
**Human SSOT (이 폴더):** 검증·재export용 UI 스냅샷  
**Agent 실행:** `workflows/agent/presets/*.api.json` + 런타임 inject

원칙: 커뮤니티 팩의 **서브그래프(UUID) + Set/Get/UE** 는 에이전트가 직접 돌리기 어렵다.  
→ **쓸 만한 것만 보관**하고, 본선은 **API 평탄 프리셋**으로 고정한다.  
→ **거대 All-in-one Wan** 은 넣지 않는다 (LTX AIO + 얇은 Wan 레인).

---

## 0. 정책 (고정)

| 항목 | 값 |
|------|-----|
| 에피소드 기본 I2V | `ltx23_aio_i2v` |
| 에피소드 기본 FLF | `ltx23_aio_flf` |
| Wan 역할 | 폴백 · 명시 · 텍스처/카메라 무게 · LoRA/장르 · FINISH |
| 효율 스택 | High/Low MoE GGUF + lightx2v + 4–8 step + **CFG=1 강제** + sageattn |
| 속도 프로필 | `preview` / **`deliver`** / `quality` (`generate_i2v --profile`) |
| Tea/Mag cache | deliver **off** (품질 탈락 이력) |
| 튜닝 CLI | `--wan-scheduler` · `--wan-shift` · `--lora-strength-high/low` · `--wan-boundary` · `--wan-quant` |
| inject SSOT | `lib/wan22_i2v_inject.py` (로더 역할=샘플러 배선) |

A/B: [wan_vs_ltx_i2v_ab_2026-07-17.md](../../../docs/wan_vs_ltx_i2v_ab_2026-07-17.md)

---

## 1. 이 폴더 선별표

| 파일 | 판정 | 레인 | 에이전트 |
|------|------|------|----------|
| `wan22_i2v.json` | **폴백 MOTION** | I2V | **ready** `i2v_wan22_a14b` · `--backend wan22` |
| `wan22_i2v_start_end.json` | **폴백 FLF** | first+last | **ready** `i2v_wan22_a14b_flf` · `--backend wan22_flf` |
| `wan22_face_enhance.json` | **FINISH** | 얼굴 스미어 | **ready_experimental** `generate_wan22_face_enhance` |
| `wan22_upscale.json` | **FINISH opt-in** | Wan 확산 업스케일 | **ready_experimental** `generate_wan22_upscale` |
| `wan22_upscale_face_enhance.json` | **planned** | 업스케일+얼굴 | Human only · API 미배선 |
| `wan22_animate.json` | **planned 장르** | pose/SAM2 리타겟 | `video_backends.wan22_animate` planned |
| `wan22_flf2v_native.json` | **참고** | 네이티브 FLF | 재export 후보 |
| `wan22_i2v_lightning_native.json` | **참고** | 네이티브 4step | 경량 참고 |

### 의도적으로 안 넣은 원본

| 원본 | 이유 |
|------|------|
| **WAN 2.2 UPSCALE BATCH** | 에피 배치 SSOT = `episode_upscale` / CLI 루프 |
| **AllInOne-wan2.2** | 163노드 중복 · LTX AIO + 얇은 Wan API로 분담 |
| **WAN 2.2 S2V** | 립 = InfiniteTalk / LTX AIO |
| **FunCamera / FASTWAN 5B / T2I·T2V 배치** | 본선 겹침·실험 |
| **LORA COMPARE** | 휴먼 비교 전용 |

별 패밀리: **YAW MoE** → [../yaw_wan22/AGENT_GUIDE.md](../yaw_wan22/AGENT_GUIDE.md) · `generate_yaw_wan22`

---

## 2. 서브그래프 해부 (핵심)

### I2V / StartEnd
- dual `WanVideoModelLoader` (HighNoise + LowNoise) + lightx2v LoRA  
- dual `WanVideoSampler` + steps/boundary  
- StartEnd = LoadImage ×2 → 동일 샘플러 (FLF)

### Face Enhance
- `BatchCLIPSeg` + mask grow → Wan encode/sample/decode + EnhanceAVideo  
- 입력: **영상** (`VHS_LoadVideo`)  
- 용도: I2V 후 얼굴 붕괴·스미어 (구조 오류는 업스케일 **전**에 수정)

### Upscale
- Florence2 캡션 보조 + WanSampler **재생성** 업스케일  
- 기본 납품 **금지** → `upscale_backends` 의 esrgan / seedvr2 / rtx_vsr

### Animate
- SAM2 + pose + mask → `WanVideoAnimateEmbeds`  
- `dance_challenge` / dance_ref 와 정합 (배선 planned)

---

## 3. CLI 치트시트

```bash
# 폴백 I2V
python scripts/generate_i2v.py -i key.png -p "gentle head turn, slow push-in" \
  -o out.mp4 --backend wan22 --profile deliver --seed 42

# FLF (Wan)
python scripts/generate_i2v.py -i start.png --last end.png -p "..." \
  -o bridge.mp4 --backend wan22_flf

# 빨간맛 I2V (18+ only) — optional dual NSFW LoRA under models/loras/Wan2.2/nsfw/
python scripts/generate_wan22_nsfw_i2v.py -i adult_key.png -p "adult woman..." -o nsfw.mp4
python scripts/generate_wan22_nsfw_i2v.py --list-loras

# 얼굴 / 업스케일 (FINISH)
python scripts/generate_wan22_face_enhance.py -i clip.mp4 -o face.mp4
python scripts/generate_wan22_upscale.py -i clip.mp4 -o up.mp4

# 쉬운 MoE (다른 폴더)
python scripts/generate_yaw_wan22.py --task i2v -i key.png -p "..." -o yaw.mp4
```

### 3.1 NSFW 정책

| | |
|--|--|
| 도구 | `generate_wan22_nsfw_i2v` · backend id `wan22_nsfw_i2v` |
| 연령 | **18+ only** · age 키워드 차단 exit 11 |
| **기본 UNet** | **Remix NSFW High/Low fp8** (빨간맛 전용 모델 — base GGUF 아님) |
| lightx2v | 속도용 distill 유지 |
| LoRA | remix 기본 off · `--with-lora` / `--lora-preset` 로 추가 |
| 폴백 | `--unet-profile base` = GGUF + General LoRA |
| LTX 대안 | `generate_ltx_nsfw_i2v` (10Eros) |

프로필·BlockSwap·cache: [wan22_i2v_speed_research.md](../../../docs/wan22_i2v_speed_research.md) · 맵 §3.

---

## 4. API export 절차

1. ComfyUI에 해당 Human JSON 로드  
2. 입력 채운 뒤 **Save (API Format)** 또는 graphToPrompt  
3. `workflows/agent/presets/<name>.api.json` + `.ports.json`  
4. [wan22_workflow_map.md](../../../docs/wan22_workflow_map.md) 표 갱신 · backends · `process.md`  

**금지:** 서브그래프 UUID 노드를 Python으로 재조립.

---

## 5. 관련 경로

| 항목 | 경로 |
|------|------|
| 맵 SSOT | `docs/wan22_workflow_map.md` |
| I2V API | `workflows/agent/presets/i2v_wan22_a14b.api.json` |
| FLF API | `workflows/agent/presets/i2v_wan22_a14b_flf.api.json` |
| UI 변환 원본 | `workflows/agent/I2V-wan22-a14b.json` |
| CLI | `scripts/generate_i2v.py` · `generate_wan22_*.py` · `generate_yaw_wan22.py` |
| Backends | `video_backends.json` · `upscale_backends.json` |
| 프롬프트 | `skills/generation-prompt/references/wan22_i2v.md` |
