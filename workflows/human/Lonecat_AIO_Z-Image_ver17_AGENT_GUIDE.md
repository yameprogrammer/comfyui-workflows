# Lonecat AIO Z-Image ver 17 — Agent 선택 가이드

에이전트는 **UI에서 스위치를 클릭하지 않는다.**
대신 **feature_id / agent_preset** 을 고르고, 준비된 `*.api.json` 을
`run_workflow_api` / `workflow_api_runner` 로 호출한다.

기계 가독 SSOT:
- `F:/ComfyUI_workflows/agent_custom/workflows/human/Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json`
- `F:/ComfyUI_workflows/agent_custom/workflows/agent/presets/lonecat_feature_presets.json`
- 사람용 상세: `Lonecat_AIO_Z-Image_ver17_USAGE.md`

---

## 1. 선택 흐름 (에이전트)

```text
1) 작업 종류 판별: T2I | I2I | edit | upscale | controlnet | inpaint
2) 모델 파일 확장자: .safetensors → model_diffusion | .gguf → model_gguf
3) feature_presets.json → agent_preset 이름
4) run_workflow_api -p <preset> --positive ... [--port unet_name=...]
```

### 기본 프리셋

| 상황 | preset |
|------|--------|
| 일반 T2I (권장) | `lonecat_t2i_turbo` |
| 저VRAM / GGUF | `lonecat_t2i_gguf` |
| I2I 아이덴티티 (예정) | `lonecat_i2i_identity` |

---

## 2. Bypasser = 기능 스위치 (UI 분석)

rgthree **Fast Groups Bypasser** 는 `matchTitle` 문자열이 **그룹 제목에 포함**되면 그 그룹을 통째로 on/off 한다.

| id | UI 제목 | matchTitle | restriction | 켜면 (매칭 그룹) | feature_id |
|----|---------|------------|-------------|------------------|------------|
| 1068 | Options | `` | default | — | `` |
| 1318 | Bypasser | `#` | default | #  Hi Rez Fix/ Upscale, #   Seed Variance, #   Qwen Prompt Enhancer, #Save Mask🎭, #Save Draft 📐, #Save w/Metadata🗒️ | `hash_options_master` |
| 1329 | Model selector | `Model` | always one | Diffusion Model, GGUF Model, Checkpoint Model | `model_diffusion` |
| 1352 | — | `` | default | — | `` |
| 1708 | Meta 📂📅+ | `` | default | — | `save_meta` |
| 1744 | — | `` | default | — | `` |
| 1863 | psst...over here 🤫 | `#  Seed` | default | #  Seed VR2 Upscale | `seed_vr2` |
| 1866 | psst...over here 🤫 | `Klein Inpaint 🖌️` | default | # Klein Inpaint 🖌️ | `inpaint` |
| 1867 | psst...over here 🤫 | `Prompt` | default | #   Qwen Prompt Enhancer, #     📝 Img Prompt | `prompt_qwen_enhancer` |
| 1872 | Group switches | `📷` | default | ✂️Crop 📷, Optical Realism 📷 | `post_optical_crop` |
| 1874 | Post processing selector | `` | default | — | `` |
| 2028 | psst...over here 🤫 | `!` | default | #      Remove Background!, #     I2I 🖼️!, #      🖼️Load Image! | `load_image_i2i` |
| 2029 | psst...over here 🤫 | `📝 Img Prompt` | default | #     📝 Img Prompt | `` |
| 2031 | Picture or Mask? | `'` | max one | Create Mask', Load Mask' | `` |
| 2034 | psst...over here 🤫 | `🥅` | default | #   🥅Controlnet | `controlnet` |
| 2046 | psst...over here 🤫 | `Hi Rez Fix/ Upscale` | default | #  Hi Rez Fix/ Upscale | `hires_upscale` |
| 2094 | pssst....over here 🤫 | `::` | default | # ::Face 🙂, # ::Eyes 👀, # ::Hands ✋, # ::Spare 🛞 | `detailers` |
| 2100 | LLM Prompt Instructions | `` | max one | — | `llm_instruct` |

### Model selector (id 1329) — always one

```text
Diffusion Model  → UNETLoader      → Model switch any_01
GGUF Model       → UnetLoaderGGUF  → Model switch any_02  (+ ClipLoaderGGUF → Clip switch any_02)
Checkpoint Model → Checkpoint      → Model switch any_03
```

**에이전트:** 파일 확장자로 diffusion vs gguf 프리셋을 고른다. 한 요청에 두 모델 경로를 섞지 않는다.

### Latent Switch (id 1800)

| 모드 | 슬롯 | denoise |
|------|------|---------|
| T2I | EmptyLatent | 1.0 |
| I2I | VAEEncode(LoadImage) | 0.4–0.65 |

---

## 3. Feature 목록 (에이전트 체크리스트)

### `model_diffusion` — Diffusion UNET (safetensors ZIT/Moody)

- **category:** model
- **when:** Default high-quality Z-Image Turbo / Moody mixes (.safetensors)
- **preset:** `lonecat_t2i_turbo`
- **status:** documented
- **UI select:** Enable group whose title contains Diffusion Model; disable GGUF Model & Checkpoint Model

### `model_gguf` — GGUF UNET (low VRAM)

- **category:** model
- **when:** VRAM tight; Q4 GGUF e.g. ZImageTurbo\\z-image-turbo-Q4_K_M.gguf
- **preset:** `lonecat_t2i_gguf`
- **status:** documented
- **UI select:** Enable GGUF Model group only
- ⚠️ ModelSamplingAuraFlow may break some GGUF weights (unpack error) — GGUF preset skips AuraFlow
- ⚠️ UI default GGUF filename may differ from files on disk

### `model_checkpoint` — Checkpoint (merged AIO ckpt)

- **category:** model
- **when:** Merged checkpoint workflows; ensure ckpt path exists
- **preset:** `None`
- **status:** preset_pending
- **UI select:** Enable Checkpoint Model group only

### `prompt_qwen_enhancer` — Qwen VL prompt enhancer

- **category:** prompt
- **when:** Expand short prompts; needs llama_cpp + GGUF VL weights
- **preset:** `None`
- **status:** optional_heavy
- **UI select:** Turn ON groups matching Prompt (Qwen Prompt Enhancer, Img Prompt)

### `load_image_i2i` — Load image + I2I

- **category:** i2i
- **when:** Image-to-image keyframes / identity
- **preset:** `None`
- **status:** phase1_target
- **UI select:** Enable groups with ! (Load Image, I2I, Remove Background, …)

### `controlnet` — ControlNet

- **category:** control
- **when:** Pose/structure lock from reference image
- **preset:** `None`
- **status:** phase2_target

### `inpaint` — Inpaint (Klein)

- **category:** edit
- **when:** Local edit with mask
- **preset:** `None`
- **status:** phase2_target

### `detailers` — Face/Eyes/Hands detailers

- **category:** refine
- **when:** After base gen, refine anatomy
- **preset:** `None`
- **status:** phase1_optional

### `hires_upscale` — Hi-res / Ultimate SD upscale

- **category:** upscale
- **when:** 2x quality upscale after still
- **preset:** `None`
- **status:** phase2_target

### `seed_vr2` — SeedVR2 upscale

- **category:** upscale
- **when:** Heavy 4K upscale; high VRAM/time
- **preset:** `None`
- **status:** phase2_target

### `post_optical_crop` — Post: Optical Realism + Crop

- **category:** post
- **when:** Grade / crop polish
- **preset:** `None`
- **status:** optional

### `save_meta` — Save with metadata / folders

- **category:** io
- **when:** Organized delivery outputs
- **preset:** `None`
- **status:** optional

### `llm_instruct` — LLM system instruct presets

- **category:** prompt
- **when:** With Qwen enhancer — Realistic/Photographic/NSFW system prompts
- **preset:** `None`
- **status:** optional_heavy

### `hash_options_master` — Master toggle for # option groups

- **category:** meta
- **when:** Bulk enable/disable many optional # groups — use carefully
- **preset:** `None`
- **status:** advanced

---

## 4. 에이전트 의사결정 트리

```text
요청이 still 이미지인가?
  NO → video 프리셋(별도) / 범위 외
  YES ↓
입력 이미지 있는가?
  NO  → T2I
        unet이 .gguf? → lonecat_t2i_gguf
        else          → lonecat_t2i_turbo
        (+ detailer/upscale 요청 시 해당 프리셋 또는 후처리 프리셋)
  YES → I2I
        → lonecat_i2i_identity (준비되면)
        denoise 0.4~0.65, ports.input_image=경로
부분 수정/마스크? → inpaint 프리셋
포즈 고정? → controlnet 프리셋
프롬프트 자동 확장? → qwen enhancer (무거움, 기본 OFF)
```

---

## 5. 구현 규칙 (강제)

1. **port patch only** — API JSON 노드 id/키는 `*.ports.json` SSOT.
2. **기능 추가** = UI에서 바이패서 조합 고정 → `graphToPrompt` → `presets/<name>.api.json` + ports + feature_presets 등록.
3. **금지:** full AIO에 convert_ui_to_api, IPAdapter 런타임 inject, 바이패서를 코드로 흉내 내기.
4. 생성 메타에 `workflow_api`, `feature_ids`, `preset` 기록.
5. 불명확하면 USAGE.md + CAPABILITIES.json 의 features[] 를 읽고 preset status=ready 인 것만 사용.

---

*Generated from Lonecat's AIO Z-Image ver 17.json by _build_lonecat_capabilities.py*