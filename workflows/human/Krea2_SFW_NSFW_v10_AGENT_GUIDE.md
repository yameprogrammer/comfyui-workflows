# krea2SFWNSFWUncensoredImageTo_v10 — Agent 선택 가이드

**원본:** `F:\ComfyUI_workflows\krea2SFWNSFWUncensoredImageTo_v10.json`  
**기계 가독:** `Krea2_SFW_NSFW_v10_CAPABILITIES.json`  
**ready 프리셋:** `krea2_t2i_v10` · **NSFW 별칭:** `krea2_nsfw_t2i`  
**NSFW CLI:** `scripts/generate_krea_nsfw.py`

에이전트는 UI 스위치를 누르지 않고 **feature_id / preset** 으로 고른다.

```text
# SFW 또는 일반 Krea2
python scripts/generate_krea.py -p "..." --seed 42

# 빨간맛 / NSFW 스틸 (권장 엔트리)
python scripts/generate_krea_nsfw.py -p "adult woman, sheer lingerie, ..." -o out.png --seed 42

python scripts/run_workflow_api.py -p krea2_nsfw_t2i --positive "..." --seed 42
python scripts/run_workflow_api.py --list-features
```

---

## 0. NSFW (빨간맛) — 팩토리 역할

| 항목 | 내용 |
|------|------|
| **가능 여부** | ✅ 스모크 2026-07-17 통과 (lingerie / uncensored still) |
| **이유** | Krea2 turbo + **abliterated** Qwen3-VL CLIP (`type=krea2`) — safety filter 약화 경로 |
| **UI 라벨** | “Uncensored patch” |
| **프리셋** | 동일 그래프 `krea2_t2i_v10` (별도 센서드 스위치 없음 — 프롬프트로 SFW/NSFW) |
| **에이전트 도구** | **`generate_krea_nsfw`** / catalog `krea2_nsfw_t2i` |

### 에이전트 정책 (강제)

| 규칙 | |
|------|--|
| **성인만** | 피사체 **18+** (또는 성인 설정 픽션). 미성년·애매한 연령 금지 |
| **SFW 본선** | 일상·스토리 키프레임은 Lonecat / `generate_moody` 우선 |
| **NSFW 본선** | 에로·누드·란제리 등 **빨간맛 still** → 이 도구 |
| **금지** | CSAM, loli/shota, school sexualization of minors |

스모크 산출: `F:\generated_images\krea2_nsfw_smoke\krea2_nsfw_smoke.png`

---

## 1. 그룹 맵 (15)

| 그룹 | 역할 (노트·구조 기준) |
|------|----------------------|
| **Models** | UNET / CLIP(krea2) / VAE 로드 · members=8 |
| **Main settings** | 시드·글로벌 시드 · members=12 |
| **Resolution** | 해상도 상위 · members=2 |
| **Simple image size** | 간단 해상도 · members=1 |
| **Advanced image size** | 고급 해상도 · members=1 |
| **Prompt** | POSITIVE PROMPT 입력 · members=16 |
| **Image to prompt** | Reference image → 캡션 · members=4 |
| **Prompt enhancer** | 프롬프트 강화/LLM · members=1 |
| **Main sampler** | 1st Clownshark pass · members=16 |
| **2nd pass** | 2nd sampling pass · members=9 |
| **Noise** | 그레인 · members=1 |
| **Color correction** | 밝기/대비 · members=1 |
| **Sharpen** | 샤픈 · members=1 |
| **SeedVR2 upscaler** | SeedVR2 4K · members=1 |
| **CivitAI metadata** | 메타·해시 저장 · members=16 |

---

## 2. Fast Groups Bypasser (기능 스위치)

matchTitle 이 **그룹 제목과 매칭**(일부는 정규식)되면 해당 그룹 on/off.

| id | title | matchTitle | restriction | 매칭 그룹 |
|----|-------|------------|-------------|-----------|
| 14 | 2nd pass | `2nd pass` | default | 2nd pass |
| 15 | Extra nodes | `` | default | — |
| 16 | Upscaler | `SeedVR2 upscaler` | default | SeedVR2 upscaler |
| 17 | Prompt groups | `^(?!prompt$).*prompt.*$` | default | Image to prompt, Prompt enhancer |
| 18 | — | `image size` | max one | Simple image size, Advanced image size |
| 43 | — | `Image to prompt` | default | Image to prompt |
| 47 | — | `prompt enhancer` | default | Prompt enhancer |
| 88 | — | `SeedVR2 upscaler` | default | SeedVR2 upscaler |
| 89 | Extra nodes | `` | default | — |
| 95 | — | `2nd pass` | default | 2nd pass |

### 선택 요약 (에이전트)

| 하고 싶은 일 | Bypasser 설정 (UI export 시) | preset |
|--------------|------------------------------|--------|
| **순수 T2I** | Image to prompt OFF, enhancer OFF, SeedVR2 OFF | `krea2_t2i_v10` ✅ |
| 이미지→프롬프트 | Image to prompt ON + Reference image | planned |
| 프롬프트 강화 | prompt enhancer ON | planned |
| 2nd pass | 2nd pass ON | planned |
| 4K | SeedVR2 / Upscaler ON | planned |
| 간단 해상도 | image size → Simple (max one) | documented |
| 고급 해상도 | image size → Advanced (max one) | documented |

---

## 3. 설명 노드 (Note / Markdown / Label) — 워크플로우 작성자 가이드

- **Label id=10:** USE ONE OR THE OTHER
- **Label id=57:** Change your seed here
### id=72 — Recommended settings

```
### Krea2 turbo
---
**sampler_name:** linear/euler
- eta: 0
- scheduler: simple
- steps: 8
- cfg: 1

**sampler_name:** exponential/res_2s
- eta: 0.7
- scheduler: bong_tangent
- steps: 8
- cfg: 1
```

- **Label id=137:** EVERYTHING HERE IS AUTOMATIC
### id=157 — 💡 Tip

```
You can safely delete this "CivitAI metadata" group if you are not gonna use it. Just don't forget to enable the standard save image node.
```

### id=160 — 💡 Tip

```
Change attention mode to the option compatible with your setup.
If you are in windows and you don't have sage attention installed, use SDPA.
```

### id=166 — 💡 Tip

```
A seed value of -1 = Random seed
Any other number (including 0) will be treated as a fixed seed.
"Use last queued seed" will fix the seed from the last execution, same as easyGlobalSeed.
```

- **Label id=171:** PRESS 1 TO MOVE HERE
- **Label id=172:** PRESS 2 TO MOVE HERE
- **Label id=174:** PRESS 3 TO MOVE HERE
- **Label id=176:** PRESS 4 TO MOVE HERE
- **Label id=181:** PRESS 6 TO MOVE HERE
- **Label id=180:** PRESS 5 TO MOVE HERE
- **Label id=182:** PRESS 7 TO MOVE HERE
### id=159 — Note

```
You can delete this node if you want, it sends a notification via a system notification but it has to be setup
```

### id=161 — MODEL LINKS

```
**diffusion_models**

- [krea2_turbo_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_fp8_scaled.safetensors?download=true)

**text_encoders**
- [qwen3vl-4b-abliterated_fp8_e4m3fn.safetensors](https://civitai.red/models/2731465/qwen3-vl-4b-abliterated-comfyui-krea-2-text-encoder-bf16-fp8) (download the FP8 variant)

**vae**

- [qwen_image_vae.safetensors](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors)

**Recommended LoRAs**

- [Krea2 NSFW v3](https://civitai.red/models/2725430/krea-2-nsfw-v3?modelVersionId=3071760)

## Model Storage Location

```
📂 ComfyUI/
├── 📂 models/
│   ├── 📂 diffusion_models/
│   │   └── krea2_turbo_fp8_scaled.safetensors
│   ├── 📂 text_encoders/
│   │   └── qwen3vl-4b-abliterated_fp8_e4m3fn.safetensors
│   ├── 📂 vae/
│   │   └── qwen_image_vae.safetensors
│   └── 📂 loras/
│       └── LORAS GO HERE
```
```

- **Label id=185:** Uncensored patch 
### id=162 — Instructions

```
**Press `0` to center the workflow on these instructions any time you need.**

⚠️ **WARNING:** Always make a backup of your ComfyUI installation before updating or installing new custom nodes so you can roll back if anything goes wrong.

---

## Prerequisites

- ComfyUI-Krea2T-Enhancer Nightly version, to access the latest patch. The node used to have a cache bug that caused the workflow to re-run the entire pipeline even when the seed was exactly the same, it was fixed in the latest version.

---

## General Instructions

> **Node color legend**
> | Color | Meaning |
> |-------|---------|
> 🔴 Red | Instructional notes — read-only reference |
> 🟡 Yellow | Configurable elements — adjust to your needs |
> 🟣 Purple | Toggle switches — enable or disable option groups |

**TIP:** Disable all groups at the start using the fast group bypasser switches (press `1` to center the workflow). Then enable groups one by one as needed. Try not to manually bypass anything; use the fast group bypasser switches instead. Otherwise, you could accidentally bypass something important. As a general rule of thumb, if it doesn't have a bypasser switch, it shouldn't be bypassed.

You can first quickly generate a set of several images at 720p queuing several generations with a random seed in one go, then pick and choose the one you like from the results, fix the seed and second pass it or upscale it.

---

## 1. Main Settings (press `1`)

### Resolution

Two resolution modes are available. Use the **Fast Groups Bypasser (rgthree)** node to switch between them:

- **Advanced image size** — use this if you are familiar with Resolution Master and want fine-grained control.
- **Simple video size** — recommended for most users; provides straightforward resolution and image orientation selection.

### LoRAs

LoRAs are loaded via the **Power LoRA Loader** node. For each LoRA you wish to use:

1. Select the LoRA file from the dropdown.
2. Adjust the **strength** value to control its influence on the generation.

> Multiple LoRAs can be stacked within the same Power LoRA Loader node.

If you are going to generate NSFW content, I strongly recommend using the [Krea2 NSFW v3](https://civitai.red/models/2725430/krea-2-nsfw-v3?modelVersionId=3071760) LoRA by [19doorsside884](https://civitai.red/user/19doorsside884).

This workflow already patches the model to remove its built-in censorship. However, some prompts may still require a little extra "punch." This LoRA gives the model the additional push it needs to fully "understand" those types of prompts.

**Recommended strength:** `1.5`

---

## 2. Prompt (press `2`)

Three prompt input methods are available. Select one based on your use case:

### Option A — Manual Prompt (default)

Enter your prompt directly into the **`POSITIVE PROMPT`** node inside the **Prompt** group. This is the standard input method. Optionally, you can enable the **`Prompt enhancer`** to allow the text encoder model to improve your base positive prompt.

### Optio
```

- **POSITIVE PROMPT (id=46):** 메인 유저 프롬프트 슬롯 (에이전트 port `positive`)
---

## 4. feature_id 목록

### `krea2_t2i` — Krea2 Text-to-Image (core)

- **status:** ready
- **when:** Default Krea2 photoreal T2I; CLIP type must be krea2
- **preset:** `krea2_t2i_v10`

### `krea2_img2prompt` — Image to prompt (reference → caption)

- **status:** planned
- **when:** Derive prompt from a reference still before generation

### `krea2_prompt_enhancer` — Prompt enhancer

- **status:** planned
- **when:** Expand short prompts; may need extra models / slower
- **batch default:** OFF

### `krea2_resolution_simple` — Simple image size

- **status:** documented
- **when:** Quick fixed resolutions

### `krea2_resolution_advanced` — Advanced image size

- **status:** documented
- **when:** Custom / calculated sizes

### `krea2_2nd_pass` — 2nd pass refine

- **status:** planned
- **when:** Second sampling pass for detail

### `krea2_seedvr2` — SeedVR2 upscaler

- **status:** planned
- **when:** 4K upscale; high VRAM
- **batch default:** OFF

### `krea2_post_noise_color_sharpen` — Post: Noise / Color / Sharpen

- **status:** documented
- **when:** Film grain, grade, sharpen polish

### `krea2_civitai_metadata` — CivitAI metadata save

- **status:** documented
- **when:** Embed hashes for CivitAI; WidgetToString may break pure API — agent T2I uses SaveImage instead

### `krea2_krea2t_enhancer` — ComfyUI-Krea2T-Enhancer (model patch)

- **status:** ready_in_t2i_preset
- **when:** On by default in main model chain; strength widget on node 4

---

## 5. Any Switch / 기타 분기

| id | type | title | linked |
|----|------|-------|--------|
| 9 | `Any Switch (rgthree)` | — | any_01, any_02 |
| 8 | `Any Switch (rgthree)` | — | any_01, any_02 |
| 96 | `Any Switch (rgthree)` | — | any_01, any_02 |

---

## 6. 모델·CLIP (필수)

| | 값 |
|--|-----|
| UNET | `Krea2Turbo\krea2_turbo_fp8_scaled.safetensors` (alt: `Krea2Turbo\\krea2_turbo_int8_convrot.safetensors`) |
| CLIP | `Huihui-Qwen3-VL-4B-Instruct-abliterated-fp8_scaled.safetensors` **type=krea2** |
| VAE | `qwen_image_vae.safetensors` |

Lonecat/Z-Image 프리셋과 **섞지 말 것.**

---

## 7. 에이전트 규칙

- Use family=krea2 or -p krea2_t2i_v10 for Krea2; never put Krea2 UNET into Lonecat (CLIP type mismatch)
- CLIPLoader type must be krea2
- T2I batch: Image-to-prompt OFF, Prompt enhancer OFF, SeedVR2 OFF unless user asks
- Resolution: Simple vs Advanced via image size bypasser (max one)
- New feature combo = UI bypassers fixed → graphToPrompt → presets/*.api.json + ports + status ready
- Port patch only; no convert_ui_to_api on full graph for production

*Generated from krea2SFWNSFWUncensoredImageTo_v10.json by _build_krea2_capabilities.py*

---

## Author Instructions (from MarkdownNote id=162, summary)

- Press **0** to center on instructions; **1–7** bookmarks move to sections.
- **Color legend:** Red = notes, Yellow = configurable, Purple = toggle switches.
- Prefer **Fast Groups Bypasser** over manual node bypass.
- Start with optional groups off via bypassers, enable one by one.
- Typical flow: several 720p gens with random seed → pick one → fix seed → 2nd pass or upscale.
- **Resolution:** Simple image size (most users) vs Advanced (fine control). USE ONE OR THE OTHER (Label id=10).
- **LoRAs:** Power LoRA Loader — file + strength.
- **Seed:** `-1` = random; other numbers = fixed (Note id=166). Change seed in Main settings (Label: Change your seed here).
- **Attention:** Windows without sage attention → SDPA (Note id=160).
- **CivitAI metadata** group optional; agent T2I preset uses SaveImage (Note id=157).
- **Prereq:** ComfyUI-Krea2T-Enhancer (nightly preferred; cache bug fixed).
- **Recommended sampler (MarkdownNote id=72):**
  - `linear/euler`, eta 0, scheduler simple, steps 8, cfg 1
  - or `exponential/res_2s`, eta 0.7, scheduler bong_tangent, steps 8, cfg 1
- **Model links (MarkdownNote id=161):** krea2 turbo UNET, qwen3vl-4b abliterated CLIP (FP8), qwen_image_vae.

Full note bodies: `Krea2_SFW_NSFW_v10_CAPABILITIES.json` → `notes_and_labels`.

---

## Agent decision tree (Krea2)

```text
User wants Krea2 / krea family?
  YES → preset krea2_t2i_v10 (CLIP type krea2)
  Need img→prompt? → export planned preset with Image to prompt ON
  Need enhance prompt? → planned (enhancer ON)
  Need 2nd pass / SeedVR2? → planned exports
  Just T2I? → krea2_t2i_v10 ready
```

Do **not** use Lonecat preset with Krea2 weights (or vice versa) without matching CLIP stack.

### 모델 교체 매트릭스 (krea2_t2i_v10, seed 42)

| UNET | 결과 |
|------|------|
| Krea2Turbo\krea2_turbo_fp8_scaled.safetensors | OK ~18s |
| Krea2Turbo\krea2_turbo_int8_convrot.safetensors | OK ~29s |
| Krea2Turbo\moodyKrea2Mix_v40NonComfyFP8.safetensors | OK ~24s (works on Krea2 stack; failed on Lonecat/ZIT) |
| checkpoints\krea2_turbo.safetensors | not tested (Checkpoint loader preset needed) |

Outputs: 03_키프레임/v3_smoke_lonecat_v17/krea2_model_matrix/
