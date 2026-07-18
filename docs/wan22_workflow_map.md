# Wan 2.2 워크플로 맵 (공장 정리 SSOT)

- **작성**: 2026-07-18  
- **역할**: 에이전트·인간이 “무엇을 언제 쓰는지” 한 장으로 본다  
- **깊이**: 구조·효율 원리 → [wan22_workflow_research_and_design.md](wan22_workflow_research_and_design.md)  
- **속도 노브** → [wan22_i2v_speed_research.md](wan22_i2v_speed_research.md)  
- **품질 정책 (vs LTX)** → [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md)

---

## 0. 한 줄 정책

| 질문 | 답 |
|------|-----|
| 에피소드 **기본 I2V / FLF** | **LTX 2.3** (`ltx23_aio_i2v` / `ltx23_aio_flf`) |
| Wan 2.2 는? | **폴백 · 명시 요청 · 텍스처/카메라 무게 · LoRA/장르 · FINISH 보조** |
| 효율 본선 구조 | **High/Low MoE + lightx2v + 4–8step + CFG1 + sage + GGUF** |
| All-in-one 거대 팩? | **도입 안 함** (역할 분리 유지) |

```text
키프레임 준비
    │
    ├─[기본]──► LTX AIO I2V / FLF / S2V
    │
    ├─[폴백·명시]──► generate_i2v --backend wan22
    │                    └─ FLF 명시 ──► --backend wan22_flf  또는  --last + wan
    │
    ├─[쉬운 MoE UI / T2V]──► generate_yaw_wan22
    │
    └─[후처리]
         ├─ 얼굴 스미어 ──► generate_wan22_face_enhance
         ├─ Wan 확산 업스케일 (opt-in) ──► generate_wan22_upscale
         └─ 납품 업스케일 본선 ──► esrgan / seedvr2 / rtx_vsr  (Wan 아님)
```

---

## 1. 패밀리 한눈에 (레인 × 상태)

### 1.1 MOTION — 생성

| id | 역할 | 상태 | CLI | Human UI | Agent preset |
|----|------|------|-----|----------|--------------|
| **`wan22`** | I2V 폴백 (A14B GGUF dual + lightx2v) | **ready** · quality_tier=fallback | `generate_i2v --backend wan22` | `workflows/human/wan22/wan22_i2v.json` | `presets/i2v_wan22_a14b.api.json` |
| **`wan22_flf`** | First+Last frame 폴백 | **ready** · fallback | `generate_i2v --backend wan22_flf` · `--last` | `wan22_i2v_start_end.json` | `presets/i2v_wan22_a14b_flf.api.json` |
| **`wan22_nsfw_i2v`** | **빨간맛 I2V (18+)** | **ready** | `generate_wan22_nsfw_i2v` | `wan22_i2v.json` (+ optional NSFW LoRA pair) | same `i2v_wan22_a14b` + LoRA chain |
| **`yaw_wan22`** | 쉬운 MoE T2V+I2V 실 UI | **ready** | `generate_yaw_wan22` | `workflows/human/yaw_wan22/…v050Moe.json` | `presets/yaw_wan22_v050_moe.api.json` |
| **`wan22_animate`** | 레퍼 모션→캐릭 (SAM2+pose) | **planned** | (미배선) | `wan22_animate.json` | — |

### 1.2 FINISH — 후처리 (생성 본체 아님)

| id | 역할 | 상태 | CLI | Human UI | Agent preset |
|----|------|------|-----|----------|--------------|
| **`wan22_face_enhance`** | I2V 후 얼굴 스미어 보정 | **ready_experimental** | `generate_wan22_face_enhance` | `wan22_face_enhance.json` | `presets/wan22_face_enhance.api.json` |
| **`wan22_upscale`** | Wan 디퓨전 영상 업스케일 | **ready_experimental** | `generate_wan22_upscale` | `wan22_upscale.json` | `presets/wan22_upscale.api.json` |
| **`wan22_upscale_face`** | 업스케일+얼굴 연속 | **planned** | — | `wan22_upscale_face_enhance.json` | — |

### 1.3 참고만 (에이전트 본선 아님)

| 파일 | 용도 |
|------|------|
| `wan22_flf2v_native.json` | 네이티브 FLF 참고 · 재export 후보 |
| `wan22_i2v_lightning_native.json` | 네이티브 4step lightning 참고 |
| `workflows/agent/I2V-wan22-a14b.json` | API 변환 원본 UI 스냅샷 |

### 1.4 의도적으로 안 넣는 것

| 원본 계열 | 이유 |
|-----------|------|
| AllInOne-wan2.2 (거대 AIO) | LTX AIO + 얇은 Wan API로 역할 분담 |
| WAN S2V | 립 본선 = InfiniteTalk / LTX AIO |
| UPSCALE BATCH | 에피소드 배치는 `episode_upscale` / CLI 루프 |
| FunCamera / FASTWAN 5B / T2I 배치 | 본선 중복·실험 |
| LORA COMPARE | 휴먼 전용 |

---

## 2. 언제 무엇을 (의사결정)

| 상황 | 고를 것 | 말고 |
|------|---------|------|
| 에피소드 work 클립 기본 | **LTX** `generate_i2v` | Wan 기본 금지 |
| LTX 모션이 가볍거나 카메라 무게 필요 | `--backend wan22` | 전 컷 Wan 고정 |
| 첫·끝 프레임 브리지 품질 본선 | **LTX flf** | Wan flf 실험만 |
| 텍스트→영상 쉬운 MoE | `generate_yaw_wan22 --task t2v` | 에피소드 본선 대체 아님 |
| I2V 후 얼굴만 깨짐 | `generate_wan22_face_enhance` | 전체 해상도 대용 |
| 납품 해상도 업 | **esrgan / seedvr2 / rtx_vsr** | `wan22_upscale` 기본 경로 |
| 댄스 포즈 리타겟 | `wan22_animate` (planned) / `generate_dance_ref` | — |
| **빨간맛 영상 (18+)** | **`generate_wan22_nsfw_i2v`** 또는 `generate_ltx_nsfw_i2v` | SFW i2v |
| 빨간맛 스틸 (18+) | `generate_krea_nsfw` | — |
| 립싱크 | InfiniteTalk / LTX s2v | Wan S2V 미도입 |

---

## 3. 에이전트 I2V (`wan22`) 레시피

엔진: **Wan2.2 I2V A14B · High/Low GGUF Q4_K_M · lightx2v 4step LoRA 쌍 · sageattn**

| profile | steps | block_swap | 용도 |
|---------|-------|------------|------|
| `preview` | 4 | 8 | 모션 스카우트 · long_edge cap |
| **`deliver`** (기본) | **6** | **10** | 폴백 본선 |
| `quality` | 8 | 10 | 히어로 후보 |

**2026-07-18 inject 개선** (`lib/wan22_i2v_inject.py`)

| 노브 | 기본 | CLI |
|------|------|-----|
| CFG (high+low) | **1.0 scalar** (스케줄 링크 제거) | `--cfg` |
| High/Low 로더 | 샘플러 배선으로 역할 판별 | (자동) |
| quant | **q4** | `--wan-quant q4\|q5` (q5 파일 필요) |
| scheduler | 그래프 `dpm++_sde` | `--wan-scheduler euler\|res_multistep\|…` |
| shift | 그래프 8 · euler 시 auto **5** | `--wan-shift` |
| lightx2v strength | 1.0 / 1.0 | `--lora-strength-high` · `--lora-strength-low` |
| boundary | steps//2 | `--wan-boundary N` (비대칭 high/low) |

```bash
# 폴백 I2V
python scripts/generate_i2v.py -i KEY.png -p "MOTION/CAMERA only..." -o out.mp4 \
  --backend wan22 --profile deliver --seed 42

# 스카우트 / 히어로
python scripts/generate_i2v.py ... --backend wan22 --profile preview
python scripts/generate_i2v.py ... --backend wan22 --profile quality

# VRAM
python scripts/generate_i2v.py ... --backend wan22 --block-swap 0   # 여유 시 속도
python scripts/generate_i2v.py ... --backend wan22 --block-swap 20  # OOM/긴 클립

# lightx2v 정석에 가깝게 A/B
python scripts/generate_i2v.py ... --backend wan22 --wan-scheduler euler \
  --lora-strength-high 0.7 --lora-strength-low 1.0

# 비대칭 steps (예: 4 high + 8 low)
python scripts/generate_i2v.py ... --backend wan22 --steps 12 --wan-boundary 4

# FLF (Wan 명시)
python scripts/generate_i2v.py -i start.png --last end.png -p "..." -o bridge.mp4 \
  --backend wan22_flf

# YAW 쉬운 T2V/I2V
python scripts/generate_yaw_wan22.py --task t2v -p "..." -o t2v.mp4
python scripts/generate_yaw_wan22.py --task i2v -i KEY.png -p "..." -o i2v.mp4

# FINISH
python scripts/generate_wan22_face_enhance.py -i clip.mp4 -o face_fix.mp4
python scripts/generate_wan22_upscale.py -i clip.mp4 -o up.mp4   # opt-in only

# 빨간맛 I2V (18+ only) — dual GGUF+lightx2v + optional NSFW LoRA HIGH/LOW
python scripts/generate_wan22_nsfw_i2v.py -i adult_key.png -p "adult woman..." -o nsfw.mp4
python scripts/generate_wan22_nsfw_i2v.py --list-loras
# after installing pair under models/loras/Wan2.2/nsfw/:
python scripts/generate_wan22_nsfw_i2v.py -i adult_key.png -p "..." --require-lora -o nsfw.mp4
```

### NSFW 도구 노트

| 항목 | 값 |
|------|-----|
| CLI | `generate_wan22_nsfw_i2v` |
| 정책 | **adult_18_plus_only** (age string guard exit 11) |
| 엔진 기본 | **Remix NSFW High/Low fp8 UNet** + lightx2v (빨간맛 전용 모델) |
| 기본 프로필 | `quality` (8 step) |
| LoRA | remix 시 **기본 off** · `--with-lora` / `--lora-preset general\|dr34ml4y` |
| 폴백 | `--unet-profile base` = 공식 GGUF + General LoRA |
| UNet 경로 | `F:\model\diffusion_models\Wan2.2\nsfw_remix\` |
| vs LTX NSFW | LTX = 10Eros 전용 팩 · Wan = General LoRA / DR34M / Remix · **둘 다 18+** |

**고정 규칙**

- 프롬프트: **모션·카메라 only** ([generation-prompt](../skills/generation-prompt/SKILL.md) · `wan22_i2v.md`)  
- TeaCache/MagCache: **deliver 기본 off** (`--cache` 실험만)  
- work 해상도 생성 → 납품은 **별 업스케일 레인**  
- 짧은 I2V를 freeze-pad로 늘리기 **금지**

---

## 4. 파일 트리 (SSOT 위치)

```text
workflows/human/wan22/          # Human UI 팩 + AGENT_GUIDE (이 맵 요약 링크)
workflows/human/yaw_wan22/      # YAW MoE 쉬운 UI
workflows/agent/
  I2V-wan22-a14b.json           # 변환 원본
  presets/
    i2v_wan22_a14b.api.json
    i2v_wan22_a14b_flf.api.json
    wan22_face_enhance.api.json
    wan22_upscale.api.json
    yaw_wan22_v050_moe.api.json
scripts/
  generate_i2v.py               # --backend wan22 | wan22_flf
  generate_yaw_wan22.py
  generate_wan22_face_enhance.py
  generate_wan22_upscale.py
lib/
  yaw_wan22_runner.py
video_backends.json             # backends.wan22* + i2v_quality_policy
upscale_backends.json           # wan22_face_enhance / wan22_upscale*
docs/
  wan22_workflow_map.md         # ← 이 문서
  wan22_workflow_research_and_design.md
  wan22_i2v_speed_research.md
  wan_vs_ltx_i2v_ab_2026-07-17.md
```

---

## 5. 백엔드 JSON 키 (video_backends)

| key | status | quality_tier | notes 요약 |
|-----|--------|--------------|------------|
| `wan22` | ready | fallback | GGUF dual + lightx2v; 명시/폴백만 |
| `wan22_flf` | ready | fallback | start+end; 품질 FLF 본선은 LTX |
| `wan22_animate` | planned | — | dance/pose 리타겟 |
| `default_backend` | — | — | **`ltx23_aio_i2v`** (Wan 아님) |
| `default_backend_flf` | — | — | **`ltx23_aio_flf`** |

`i2v_quality_policy.wan22_role` = fallback / 실험 / 저VRAM 옵션 — **not quality default**.

---

## 6. 유지보수 규칙

1. **Human UI** = 재export·검증 SSOT. 서브그래프 UUID를 Python으로 재조립하지 않는다.  
2. **Agent** = 평탄 API preset + inject (모델 경로, steps, block_swap, attention).  
3. 새 Wan 도구 추가 시: 이 맵 표 1행 + `video_backends`/`upscale_backends` + catalog §2.4/2.6 + `process.md` 한 줄.  
4. 기본 품질 정책 변경은 **동일 키프레임 A/B** 후에만 (`wan_vs_ltx_*`).  
5. 효율 구조(듀얼+lightx2v)를 깨는 “단순화” 금지 — 느려지거나 품질 붕괴.

---

## 7. 관련 가이드

| 문서 | 내용 |
|------|------|
| [workflows/human/wan22/AGENT_GUIDE.md](../workflows/human/wan22/AGENT_GUIDE.md) | 팩 선별·서브그래프 해부 |
| [workflows/human/yaw_wan22/AGENT_GUIDE.md](../workflows/human/yaw_wan22/AGENT_GUIDE.md) | YAW 스위치 맵 |
| [docs/tool_catalog.md](tool_catalog.md) §2.4 · §2.6 | 도구 카탈로그 표 |
| [skills/generation-prompt/references/wan22_i2v.md](../skills/generation-prompt/references/wan22_i2v.md) | 프롬프트 방언 |
