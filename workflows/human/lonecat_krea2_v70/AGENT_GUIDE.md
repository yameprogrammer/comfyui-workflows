# Lonecat's Krea 2 **v7.0** — Agent capability map

> **Not the same pack as** `krea2SFWNSFWUncensoredImageTo_v10` (slim uncensored T2I).  
> **v7.0** = full Lonecat Pro graph (~478 nodes, ~45 groups) with Fast Groups Bypasser toggles.  
> **Machine SSOT:** [CAPABILITIES.json](CAPABILITIES.json)  
> **List CLI:** `python scripts/krea2_features.py list`

## 0. Two Krea stacks (do not confuse)

| Stack | Nodes | Agent today | Role |
|-------|------:|-------------|------|
| **v10 SFW/NSFW Uncensored** | ~113 | **`generate_krea` / `generate_krea_nsfw`** ready | Daily T2I (and experimental I2I preset) |
| **Lonecat Krea 2 v7.0** | ~478 | **Feature map + routed CLIs** (this pack) | Pro UI: style refs, control, detailers, moodboard, SeedVR2, post suite… |

Shared rule: **CLIP type = krea2**. Never put Krea2 UNET into Lonecat Z-Image / Moody graphs.

### UI source

- Live: `F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\Lonecat's Krea 2 v7.0.json`
- Zip: `F:\ComfyUI_workflows\krea2ProGradeWImageEditStyle_v70Moodboard.zip` (+ LUTs)

---

## 1. What v7 provides (capability shelves)

```text
GENERATE     T2I core · GGUF/fp8 model select · draft vs final
PROMPT       Img→prompt · Qwen VL enhancer · LLM instruct notes
EDIT         Instruct / Qwen Image Edit (Image 2/3 flags)
STYLE        Style ref 1 · dual style · Moodboard apply
CONTROL      Krea2 ControlLoRA + control image encode
DETAIL       Face / eyes / hands / spare · NSFW anatomy detailers (18+)
UPSCALE      Hi-rez / UltimateSD · SeedVR2
POST         Post suite · crop · optical realism · RMBG
IO           Multi LoadImage · save metadata · subfolders
```

Bypass pattern: **purple Fast Groups Bypasser** nodes titled “psst…”, matching `#` / `!` / `::` / emoji prefixes on group titles. UI tip: disable all `#` groups, then enable only what you need.

---

## 2. Agent usability matrix (honest)

| feature_id | Agent path now | Status |
|------------|----------------|--------|
| `v70_t2i_core` | `generate_krea` | **ready_via_v10** |
| `v70_nsfw_t2i` | `generate_krea_nsfw` | **ready_via_v10** |
| `v70_i2i` | `run_workflow_api -p krea2_i2i_v10` | ready_experimental |
| `v70_instruct_edit` | `generate_qwen_edit` | ready_via_other_tool |
| `v70_hires_fix` | `upscale_image` | ready_via_other_tool |
| `v70_seedvr2` | `upscale_image --backend seedvr2` | ready_via_other_tool |
| `v70_style_ref_1` | **`generate_krea2_style`** | **ready** (minimal API slice) |
| `v70_controlnet` | **`generate_krea2_control`** | **ready** (depth ControlLoRA default) |
| `v70_style_ref_2` | — | planned (dual style) |
| `v70_moodboard` | — | planned |
| `v70_detailer_*` / NSFW detailers | — | planned |
| `v70_img_prompt` / enhancer | — | planned |
| `v70_post_suite` / rmbg / draft | — | planned |

**Summary:** core still generation is production-ready for agents **via the v10 API preset**. Most of v7’s *unique* toggles still need **UI → graphToPrompt → ports** export before they can be port-patched reliably.

---

## 3. Copy-paste agent recipes (use today)

```bash
# Feature inventory (this SSOT)
python scripts/krea2_features.py list
python scripts/krea2_features.py show v70_moodboard
python scripts/krea2_features.py search "style"

# Core photoreal T2I (v10 stack = agent default for Krea2 family)
python scripts/generate_krea.py -p "cinematic portrait..." -o out.png --seed 42 --width 1024 --height 576

# NSFW 18+
python scripts/generate_krea_nsfw.py -p "adult woman..." -o nsfw.png --seed 42

# Experimental Krea2 I2I
python scripts/run_workflow_api.py -p krea2_i2i_v10 --positive "same person, smile" \
  --input-image face.png -o i2i.png --seed 42

# Native style reference (P0 ready)
python scripts/generate_krea2_style.py -i style.png -p "cinematic portrait..." -o styled.png --seed 42

# Native ControlLoRA / depth (P0 ready)
python scripts/generate_krea2_control.py -i depth.png -p "hero standing..." -o controlled.png --seed 42

# Instruction edit (v7 Instruct path analogue)
python scripts/generate_qwen_edit.py -i still.png -p "change background to night street" -o edit.png

# Upscale / SeedVR2 (v7 upscale groups)
python scripts/upscale_image.py -i out.png -o out_1080.png --style photo --preset deliver_1080
python scripts/upscale_image.py -i out.png -o out_hero.png --backend seedvr2 --preset deliver_1080
```

---

## 4. How to promote a v7 toggle to **ready**

Factory rule (same as other real-UI tools):

1. In Comfy UI open **Lonecat's Krea 2 v7.0**
2. Set Fast Groups Bypasser / muters for **one** feature combo only
3. `graphToPrompt` → save API JSON under `workflows/agent/presets/krea2_v70_<feature>.api.json`
4. Write `*.ports.json` (prompt, seed, images, denoise, strengths…)
5. Set feature `status: ready` in CAPABILITIES.json + optional CLI flag
6. Smoke once; record in `process.md`

Do **not** hand-convert the full 478-node UI to API for production.

---

## 5. Priority backlog (agent value)

| Priority | Feature | Why |
|----------|---------|-----|
| ~~P0~~ | ~~Style ref 1~~ | **done** — `generate_krea2_style` / `krea2_style_ref_v70` |
| ~~P0~~ | ~~ControlLoRA~~ | **done** — `generate_krea2_control` / `krea2_control_v70` |
| P1 | Dual style ref | v7 TwoStyle path |
| P1 | Img→prompt + enhancer presets | Reference-driven T2I |
| P1 | Face/hands detailer chain | Post-T2I quality without leaving Krea |
| P2 | Moodboard apply | Needs asset browser contract |
| P2 | Post suite / RMBG / draft mode | Nice polish; partial via other tools |
| P3 | NSFW anatomy detailers | 18+ only; careful policy |

### Runtime note (Comfy 0.30+)

`ComfyUI-Krea2-StyleTransfer` used to break all Krea2 sampling after one style/control run
(`timestep_zero_index` kwargs). Fixed in portable custom node:

`ComfyUI/custom_nodes/ComfyUI-Krea2-StyleTransfer/nodes.py` — patched forwards accept `**kwargs`.

Restart Comfy after updating that file.

---

## 6. Alternatives (toolbox)

| Need | Prefer |
|------|--------|
| Simple SFW still | `generate_krea` (this family) or Lonecat Z-Image `generate_moody` for I2I experiments |
| Identity lock scene | `generate_character_consistent` |
| Typography | `generate_ideogram4` / `generate_boogu_typo` |
| OpenPose still | `generate_openpose_pose` |

Full feature table: [CAPABILITIES.json](CAPABILITIES.json).
