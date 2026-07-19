# Model → prompt dialect matrix (factory)

**When:** before writing any `still_prompt` / `motion_prompt` / edit instruction.  
**Catalog:** `docs/tool_catalog.md` · CLI under `scripts/generate_*.py`  
**Updated:** 2026-07-17 (web + community + factory docs)

---

## 1. Pick dialect by CLI / backend

| CLI / backend | Model family | Prompt dialect | Length | Primary ref |
|---------------|--------------|----------------|--------|-------------|
| `generate_krea` / `generate_krea_nsfw` | Krea2 Turbo | **Natural language paragraph** | 90–140w still | `krea2_still_prompts.md` |
| `generate_moody*` / Lonecat Z-Image | Z-Image Turbo | **Clause stack** NL + concrete nouns | 40–120w still | `still_image_prompts.md` · `moody_zimage.md` |
| `generate_moody_i2i*` | Z-Image I2I | **Change-first** + keep identity | 15–40w | `still_image_prompts.md` §I2I |
| `generate_moody_controlnet` | Z-Image + CN | Pose/structure from CN; text = materials/light/mood | short–medium | `moody_zimage.md` |
| `generate_illustrious_standard` | Illustrious / NoobAI XL | **Danbooru tags** + quality prefix | tag list | `illustrious_tags.md` |
| `generate_qwen_edit` | Qwen Image Edit | **Imperative instruction** | 1–3 sentences | `qwen_edit.md` |
| `generate_qwen_inpaint` | Qwen InstantX | Instruction for **masked region only** | 1–2 sentences | `qwen_edit.md` §inpaint |
| `generate_qwen_angle` | Qwen + Angles LoRA | Angle/view instruction + identity keep | short | `qwen_edit.md` §angle |
| `generate_ideogram4` | Ideogram 4 | **Structured JSON caption** (or factory slot) | schema | `ideogram4_typography.md` |
| `generate_boogu_typo` | Boogu→Ideogram→Krea | Prose with `exactly reading "TEXT"` | medium | `ideogram4_typography.md` §boogu |
| `generate_i2v` (default LTX AIO) | LTX 2.3 I2V | **Motion + camera + time**; image owns look | 8–40w (simple) or chronological events | `ltx23_video.md` · `motion_video_prompts.md` |
| `generate_yaw_wan22` / Wan I2V | Wan 2.2 | **Subject → motion → camera → env** | 15–80w I2V short / 80–120 T2V | `wan22_i2v.md` |
| `generate_flf2v` | LTX FLF | Motion **between** first & last frame | motion bridge | `ltx23_video.md` §flf |
| `generate_s2v` / SI2V | LTX AIO / InfiniteTalk | Mouth/performance only | 8–30w | `motion_video_prompts.md` §SI2V |
| `generate_v2v` | LTX V2V | What **changes** in motion/style | short | `ltx23_video.md` §v2v |
| Grok native `image_gen` / `image_to_video` | Grok | NL 2–5 sentences / 1–2 motion sentences | short | SKILL §Grok |

---

## 2. Hard rules by family (cheat sheet)

| Family | DO | DON'T |
|--------|----|-------|
| **Krea2** | One prose paragraph, medium-first, materials, positive spatial locks | Tag soup; NO-spam in positive; casting-plate merge |
| **Z-Image / Moody** | Subject→action→set→light→camera; long detailed OK; LLM enhance optional | masterpiece 8k spam; turbo ignores heavy negative reliance |
| **Illustrious** | `masterpiece, best quality` + Danbooru tags, clip skip 2 | Krea-style long photoreal essays as primary |
| **Qwen Edit** | One change + keep identity/framing | Full re-direct + wardrobe + pose at once |
| **Ideogram4** | JSON / typed `text` elements for literal letters | Bury brand text only inside free prose |
| **Wan I2V** | One primary motion + camera language; continuous | Face/wardrobe re-essay; multi competing moves |
| **LTX I2V** | Chronological actions; image = appearance; optional audio quotes | Re-describe entire scene look; ignore time order |
| **SI2V** | Lip + micro performance | Big travel, wardrobe essay |

---

## 3. Agent workflow

```text
1. Read QUALITY_POLICY / tool_catalog → which CLI?
2. Open this matrix → dialect row
3. Load the primary ref file
4. Expand from SHOT_DESIGN
5. Pass model-specific gates in that ref
6. Write PROMPT_PACK field
7. Call CLI with that string only
```

**Never** use Illustrious quality tags on Krea/Z-Image photoreal MV stills.  
**Never** use Krea 140w essay as Wan motion prompt.  
**Krea2 = 기본 실사 경로. Moody = I2I·스타일 대안.**

---

## 4. Factory SSOT cross-links

| Doc | Role |
|-----|------|
| `docs/generation_prompt_craft.md` | Factory longform Rule 7.5 |
| `docs/tool_catalog.md` | Which tool when |
| `docs/moody_workflow_guide.md` | Lonecat ops |
| `video_backends.json` | I2V backend defaults |
| Episode `PROMPT_PACK_*.md` | Shot strings (not dialect rules) |
