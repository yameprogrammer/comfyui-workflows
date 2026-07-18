# YAW Wan 2.2 MoE v0.50 — Agent 가이드

> **Toolbox shelf:** MOTION (easy MoE UI · not episode quality default)  
> **CLI:** `python scripts/generate_yaw_wan22.py`  
> **Alternatives:** default quality I2V → `generate_i2v` (LTX) · agent Wan I2V → `generate_i2v --backend wan22` · lip → `generate_s2v`  
> **Family map:** [docs/wan22_workflow_map.md](../../../docs/wan22_workflow_map.md)  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.4

**출처:** [Yet Another Workflow: easy t2v + i2v (YAW - Wan 2.2)](https://civitai.red/models/2008892/yet-another-workflow-easy-t2v-i2v-yaw-wan-22)  
**파일:** `yetAnotherWorkflowEasyT2vI2v_v050Moe.json`  
**제작:** boobkake22 · 쉬운 T2V+I2V 템플릿 (서브그래프 없음, 컨트롤 노출)  
**CLI:** `python scripts/generate_yaw_wan22.py`

> **실 UI 유지.** 미니 그래프 재작성 금지.  
> 스위치/그룹 mode + 확산 GGUF 스왑 + 포트만.

---

## 1. 목적 (출처)

- Wan **2.2 MoE** (High noise + Low noise 듀얼 모델) 로 **T2V / I2V** 를 한 화면에서.
- MoE 변형 = 메인 YAW 대비 **시각 복잡도 최소** (개념 입문용).
- 초보도 만질 수 있게 라벨·색 코딩; 숨김 최소화.

팩 노트 요약:

- lightx2v: 4-step 가속 (품질·표현력 트레이드오프). 제작자 권장 steps ~8–10.
- 품질: T2V는 steps/sampler; I2V는 시작 프레임 품질이 큰 영향.
- 카메라 키워드: [wan-22.toolbomber.com](https://wan-22.toolbomber.com/) (가로에 더 잘 먹힘).

---

## 2. 스위치 맵 (세심히)

### 2.1 Fast Groups Muter (rgthree)

| UI id | match | restriction | 역할 |
|-------|-------|-------------|------|
| **174** | color **green** | **always one** | **T2V ↔ I2V** 메인 분기 |
| **308** | color **Purple** | always one | Final framerate **32 fps / 60 fps** |
| **1233** | title `^(GIMM-VFI\|RIFE VFI)` | max one | 프레임 보간 (GIMM 또는 RIFE) |
| **1357** | title `^(End Image)` | default | I2V 끝 프레임 그룹 |

### 2.2 Green: T2V vs I2V (출하 기본 = **T2V**)

| 그룹 | mode 출하 | 포함 노드 |
|------|-----------|-----------|
| **T2V** | ON (0) | UNET high/low T2V, TaskSelector `T2V` |
| **I2V** | NEVER (2) | UNET high/low I2V, Load Start Image, TaskSelector `I2V` |

에이전트:

- `--task t2v` → T2V mode=0, I2V mode=2  
- `--task i2v` / `-i` → I2V mode=0, T2V mode=2  

### 2.3 SimpleSwitch (first live input)

| 제목 | 선택 의미 |
|------|-----------|
| Model Switch High/Low | I2V UNET vs T2V UNET (muted 쪽 제외 → 활성 모델) |
| Task Switch | T2V Planner vs I2V Planner |
| Width/Height Switch | 수동 SetImageSize(bypass) vs WanResolutions |
| Image for Size Switch | start/end 이미지 비율 (T2V에선 둘 다 off → image 없음) |
| Framerate Switch | 32 / 60 / Wan FPS |
| Frame Mult Switch | VFI 배수 2 vs 4 |
| VFI Switch | GIMM / RIFE / ColorCorrect passthrough |
| Model Shift Switch | override float vs MoE plan sigma |

### 2.4 기타 기본 ON/OFF

| 기능 | 출하 | 에이전트 |
|------|------|----------|
| lightx2v LoRA pair | ON (`High + Low`) | `--acceleration` |
| Color Correct | bypass (4) | 기본 유지 |
| GIMM-VFI | 팩에 따라 ON | 에이전트 기본 **OFF** (`--vfi` 로 ON) |
| RIFE | NEVER | max-one with GIMM |
| End Image | NEVER | `--end-image` |
| Post sharpen + film grain | ON | 실 UI 유지 |

---

## 3. 모델 (걱정 포인트)

### 팩 기본 = fp16 풀 (큼)

```
wan2.2_t2v_high_noise_14B_fp16.safetensors
wan2.2_t2v_low_noise_14B_fp16.safetensors
wan2.2_i2v_high_noise_14B_fp16.safetensors
wan2.2_i2v_low_noise_14B_fp16.safetensors
```

각각 수십 GB급 · 로컬에 없으면 실패.

### 에이전트 기본 = **GGUF Q4_K_M** (검증됨)

| 역할 | UnetLoaderGGUF 경로 |
|------|---------------------|
| T2V high | `Wan2.2\Wan2.2-T2V-A14B-HighNoise-Q4_K_M.gguf` |
| T2V low | `Wan2.2\Wan2.2-T2V-A14B-LowNoise-Q4_K_M.gguf` |
| I2V high | `Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf` |
| I2V low | `Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf` |

- 노드만 `UNETLoader` → `UnetLoaderGGUF` (구조 유지).  
- CLIP: `umt5_xxl_fp8_e4m3fn_scaled` · VAE: `wan_2.1_vae`.  
- lightx2v LoRA 파일은 팩 경로 그대로 (로컬 `loras/Wan2.2/...`).  
- 풀 fp16 강제: `--fp16` (디스크·VRAM 여유 있을 때만).

**스모크:** GGUF T2V 성공 (`stories/_tool_smoke/yaw_t2v_gguf_*.mp4`).

---

## 4. CLI

```bash
python scripts/generate_yaw_wan22.py --list-features

# T2V (기본 GGUF)
python scripts/generate_yaw_wan22.py --task t2v \
  -p "a cat walking, cinematic, natural motion" \
  -o out.mp4 --seed 42 --length-seconds 2

# I2V
python scripts/generate_yaw_wan22.py -i start.png \
  -p "slow push-in, natural motion" -o i2v.mp4

# VFI + more steps
python scripts/generate_yaw_wan22.py --task t2v -p "..." --vfi --steps 10 -o out.mp4
```

| 포트 | UI |
|------|-----|
| positive/negative | CLIPTextEncode 351/352 |
| seed | Seed rgthree 158 |
| length seconds | mxSlider 139 |
| steps | StepBudget 1352 `accelerated_steps` |
| image | Load Start 166 |
| end image | Load End 339 |

---

## 5. 에이전트가 고를 때

이 레포는 **도구 카탈로그**다. “본선/폴백”을 강제하지 않는다.  
프로젝트 에이전트가 목표에 맞게 YAW / LTX / 기타 중 **스스로 고른다.**

```text
1) Wan 2.2 MoE T2V 또는 I2V가 필요하면 이 도구
2) T2V vs I2V (green muter)
3) GGUF 기본 — 없거나 OOM이면 --fp16 또는 모델 확보
4) lightx2v 유지(빠름) vs --acceleration None (느리고 표현 넓음)
5) 필요 시 --vfi / --end-image
```

---

## 6. 커스텀 노드

- ComfyUI-GGUF (`UnetLoaderGGUF`)  
- comfyui-simple-switch  
- ComfyUI-WanMoeKSampler / Sampling Planner (Wan 2.2)  
- rgthree, VHS, easy-use, KJNodes (SageAttention patch)  
- GIMM-VFI (옵션)

---

## 7. 실패 시

1. `/prompt` `node_errors` 확인 — 과거: empty SimpleSwitch(359), missing `denoise`  
2. GGUF 파일명 `object_info` UnetLoaderGGUF 목록과 일치하는지  
3. lightx2v LoRA 경로  
4. 미니그래프로 쪼개지 말 것 — 스위치 mode + GGUF만  
