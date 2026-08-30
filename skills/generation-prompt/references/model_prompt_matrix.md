# Model → prompt dialect matrix (factory)

**When:** before writing any `still_prompt` / `motion_prompt` / caption / edit instruction.  
**Catalog:** `docs/tool_catalog.md` · CLI under `scripts/generate_*.py`  
**Updated:** 2026-08-15 (v1.4 official still dialects + `prompt_dialect` CLI)

If a CLI is **not** in this table: **stop**. Do not invent a Krea essay. Add a row or use the "no prompt" line.

---

## 1. GENERATE — stills

| CLI / backend | Family | Official form | Ref |
|---------------|--------|---------------|-----|
| `generate_krea` / `generate_krea_nsfw` | Krea2 Turbo | NL paragraph 90–140w (krea-ai prompting.md) | `krea2_still_prompts.md` |
| `generate_krea_draft` | Krea2 draft | Same NL, shorter 40–80w | `krea2_transform.md` |
| `generate_moody*` / Lonecat Z-Image | Z-Image Turbo | Long detailed clauses; Turbo ignores neg (Tongyi HF) | `moody_zimage.md` |
| `generate_illustrious_standard` | Illustrious / NoobAI | Danbooru + quality tags | `illustrious_tags.md` |
| `generate_illustrious_advanced` | Illustrious + extras | Same tags; no photoreal essay | `illustrious_tags.md` |
| **`generate_anima`** | Anima DiT 2B | Hybrid tags + short NL (not Krea) | `anima_2d.md` |
| **`generate_flux`** | Flux.1 Dev | BFL NL 30–80w; no negatives | `flux_still.md` |
| **`generate_flux2_klein`** | Flux.2 Klein 9B | BFL Subject→Action→Style→Context; no upsample | `flux_still.md` |
| **`generate_sdxl`** | SDXL | Juggernaut NL or tags; Pony scores | `sdxl_still.md` |
| Grok `image_gen` | Grok | NL 2–5 sentences | SKILL §Grok |

Picker: `python scripts/prompt_dialect.py pick "…"` · `show <id>` · `still_model_picker.md`

---

## 2. TRANSFORM / CAMERA / FINISH (image)

| CLI | Dialect | Ref |
|-----|---------|-----|
| `generate_moody_i2i*` / `i2i_lock` / `i2i_ipadapter` | Change-first + keep face | `still_image_prompts.md` §I2I |
| `generate_moody_controlnet` | Materials/light; pose from CN | `moody_zimage.md` |
| `generate_qwen_edit` | Imperative, one change | `qwen_edit.md` |
| `generate_qwen_inpaint` | Masked region only | `qwen_edit.md` §inpaint |
| `generate_flux_fill` | Mask contents only | `flux_still.md` |
| `generate_qwen_angle` | Angle + keep identity | `qwen_edit.md` §angle |
| `generate_krea2_style` | Krea NL **content**; style from `-i` | `krea2_transform.md` |
| `generate_krea2_control` | Materials/light; pose from map | `krea2_transform.md` |
| `generate_krea2_identity_edit` | One change | `krea2_transform.md` |
| `generate_krea2_face/eyes/hand/anatomy/region_detail` | Local part only | `krea2_transform.md` |
| `generate_krea2_color_match` / `_post` | Grade/finish only | `krea2_transform.md` |
| `generate_krea2_img_prompt` | Florence caption → then **rewrite** in Krea dialect (do not ship raw caption) | `krea2_still_prompts.md` |
| `generate_krea2_moodboard` | Short Krea NL per tile | `krea2_still_prompts.md` |
| `generate_style_transfer` | Instruction / `--style` preset | `style_viewpoint.md` |
| `generate_viewpoint` | `--preset` first | `style_viewpoint.md` |
| `generate_character_consistent` | Mode lock/soft/remix — change-first | `style_viewpoint.md` |
| `generate_ref_pack` | Tiny lock prompts per tile | `style_viewpoint.md` |
| `generate_openpose_pose` | No appearance prompt (map only) | — |
| `generate_reframe` | No / crop intent only | — |
| `generate_illustrious_detailer` | Local tags for the part | `illustrious_tags.md` |
| `generate_rmbg` / `upscale_*` / `generate_krea2_post` polish | **No creative prompt** | — |

---

## 3. MOTION

| CLI | Family | Dialect | Ref |
|-----|--------|---------|-----|
| `generate_i2v` (default LTX) | LTX 2.3 | Motion + time; image owns look | `ltx23_video.md` · `motion_video_prompts.md` |
| `generate_i2v --backend wan` / `generate_yaw_wan22` | Wan 2.2 | Subject → motion → camera | `wan22_i2v.md` |
| `generate_flf2v` | LTX FLF | Bridge A→B | `ltx23_video.md` §flf |
| `generate_v2v` / `episode_v2v` | LTX V2V | What changes | `ltx23_video.md` §v2v |
| `generate_s2v` / `episode_s2v` | SI2V | Mouth + micro perf | `motion_video_prompts.md` §SI2V |
| `generate_camera_move` / `idle_loop` / `i2v --motion-preset` | LTX/Wan + preset | **Preset id** + extra action only | `camera_move.md` |
| `generate_dance_ref` | Dance plate | Drive description, not identity | `camera_move.md` |
| `generate_wan_animate2` | Wan-Animate-2 | Split `--look` / `--background` / `--pose-prompt` | `wan_animate.md` |
| `generate_wan22_animate` | Wan 2.2 Animate | Optional look/set notes | `wan_animate.md` |
| `generate_wan22_nsfw_i2v` | Wan I2V | Same as Wan I2V | `wan22_i2v.md` |
| `generate_ltx23_latentheart` / `redmix_i2v` / `ltx_nsfw_*` | LTX family | Same I2V; no brand words | `ltx23_video.md` §10.5 |
| `generate_ltx_relight` | Relight | Light only | `ltx23_video.md` §10.5 |
| `generate_minimax_h3` | H3 T2V/I2V/R2V/A2V | Shot + camera + audio tags; R2V contact-sheet = still collage | `minimax_h3.md` |
| Grok `image_to_video` | Grok | 1–2 sentences, one move | SKILL §Grok |

---

## 4. VOICE / MUSIC / MESH

| CLI | Dialect | Ref |
|-----|---------|-----|
| `generate_minimax_music` | 3-part caption (Global / Vocal / Arrangement); lyrics + section tags separate | `music_audio.md` |
| `generate_stable_audio` | Instrumental or SFX source+space | `music_audio.md` |
| `generate_bgm` | Short instrumental caption | `music_audio.md` |
| `generate_midi_*` | **No image/music NL prompt** (skeleton/arrange flags) | — |
| `generate_qwen3_tts` / `episode_tts` | Spoken text, not a visual prompt | — |
| `generate_hy3d_mesh` | Image is the prompt | `mesh_3d.md` |

---

## 5. Hard rules by family

| Family | DO | DON'T |
|--------|----|-------|
| **Krea2 still** | One prose paragraph, materials, positive locks | Tag soup; NO-spam; casting-plate merge |
| **Krea2 transform** | One job (style/control/edit/detail) | Full still re-essay |
| **Z-Image / Moody** | Subject→action→set→light→camera | masterpiece 8k; trust negatives on turbo |
| **Illustrious / Anima** | Quality tags + Danbooru-ish | Krea photoreal paragraph |
| **Qwen / viewpoint / style** | Imperative keep-rest / preset | Multi-change mega edit |
| **Wan / LTX I2V** | Motion + one camera | Face/wardrobe re-essay |
| **Wan Animate** | Split look / bg / pose | Choreograph in `--look` |
| **Camera-move** | Preset + extra | Second camera move |
| **MiniMax Music / SA3** | 3-part caption; lyrics in `--lyrics` | Visual still language; lyrics inside caption |
| **H3** | Shot + camera; `<Picture n>` + one job; contact sheet: P1 identity / P2 outfit | Untagged refs; outfit donor body; pose-photo bleed |
| **Hy3D** | Clean still | Treat as T2I |

---

## 6. Agent workflow

```text
1. tool_catalog / QUALITY_POLICY → CLI
2. This matrix → dialect row
3. Open the primary ref (one file)
4. Expand SHOT_DESIGN in THAT dialect
5. Pass that file's gates
6. PROMPT_PACK field
7. Call CLI with that string only
```

**Never** Illustrious/Anima quality tags on Krea photoreal.  
**Never** Krea 140w as Wan/LTX/H3/Anima/Music prompt.  
**Krea2 = 기본 실사. Anima = 2D. Moody = I2I·스타일 대안.**

---

## 7. SSOT

| Doc | Role |
|-----|------|
| This file | Routing |
| `docs/generation_prompt_craft.md` | Shared order (Rule 7.5) |
| `references/*.md` | Per-family dialect |
| `docs/tool_catalog.md` | Which tool |
| Episode `PROMPT_PACK` | Shot strings, not rules |
