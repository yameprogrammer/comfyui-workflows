---
name: generation-prompt
version: 1.2.0
description: >
  Translate shot design into high-quality IMAGE and VIDEO model prompts for agent_custom.
  Routes each factory CLI/backend to its researched dialect (Krea2 NL, Z-Image clauses,
  Illustrious Danbooru, Qwen edit instructions, Ideogram JSON, Wan/LTX motion).
  Use for T2I/I2I/I2V/SI2V, shot_compose, generate_*, prompt pack, "make it more detailed".
  Bans tag-soup on photoreal paths and wardrobe re-essay on motion. Slash: /generation-prompt
---

# generation-prompt — Image & video prompt craft (factory)

You turn **direction** into **model-readable English** (or tags/JSON when that model requires it).  
You are not a lyric poet and not a one-size-fits-all tag dump.

**Upstream:** `skills/video-direction` → CREATIVE + SHOT_DESIGN  
**Factory longform:** `docs/generation_prompt_craft.md` (Rule 7.5)  
**Tool pick:** `docs/tool_catalog.md`  
**This skill:** dialects · lexicons · quality gates · PROMPT_PACK

---

## 0. Equip (mandatory before generate_*)

```bash
# from factory root
# read this SKILL + model_prompt_matrix + the one dialect file for your CLI
```

1. SHOT_DESIGN (or CREATIVE shot row) loaded  
2. **CLI / backend chosen** (QUALITY_POLICY or tool_catalog)  
3. Open **`references/model_prompt_matrix.md`** → dialect row  
4. Open that dialect’s primary reference file  
5. Write still/motion/edit string → gates → CLI only with that string  

---

## 1. SYSTEM identity

```text
Expand SHOT fields into visible nouns and verbs (or correct tags/JSON for that model).
One primary intent per prompt.
Route dialect by model — never force Krea prose onto Illustrious or Danbooru onto Krea.
Photoreal stills: ban masterpiece/best quality/8k spam.
Illustrious only: quality tags are allowed and expected.
I2V/SI2V: motion + camera (+ performance); never re-describe face/wardrobe.
English for model prompts; Korean OK for notes / on-image Korean text strings.
```

---

## 2. Workflow

```text
A. Load SHOT + CREATIVE theme (look, materials, chm, world)
B. Mode: still | i2i | edit | inpaint | i2v | si2v | typography | t2v
C. Dialect from model_prompt_matrix (CLI name)
D. Expand with correct reference template
E. Quality gates (global + dialect)
F. Write PROMPT_PACK entry
G. Call scripts/generate_*.py with that string only
```

---

## 3. Dialect map (summary)

| CLI family | Dialect | Ref file |
|------------|---------|----------|
| `generate_krea*` | NL one paragraph 90–140w | `krea2_still_prompts.md` |
| `generate_moody*` | Clause stack 40–120w | `still_image_prompts.md` + `moody_zimage.md` |
| `generate_illustrious_standard` | Danbooru + quality tags | `illustrious_tags.md` |
| `generate_qwen_edit` / inpaint / angle | Imperative keep-rest | `qwen_edit.md` |
| `generate_ideogram4` / `boogu_typo` | JSON / exactly reading | `ideogram4_typography.md` |
| `generate_i2v` LTX default | Motion chronological | `ltx23_video.md` + `motion_video_prompts.md` |
| `generate_yaw_wan22` / Wan | Motion→camera lexicon | `wan22_i2v.md` + `motion_video_prompts.md` |
| `generate_s2v` SI2V | Mouth + micro perf | `motion_video_prompts.md` |
| `generate_flf2v` / v2v | Bridge / change | `ltx23_video.md` |

Full matrix + DO/DON’T: **`references/model_prompt_matrix.md`**.

---

## 4. Still recipes (pointers)

### 4a. Krea2 — **기본 실사 T2I** — § see `krea2_still_prompts.md`

Natural language paragraph · medium-first · materials · positive spatial locks · no NO-spam · no casting-plate merge.

### 4b. Moody / Z-Image — § see `moody_zimage.md` + `still_image_prompts.md`

```text
[look], [identity], [wardrobe], [SHOT], [ACTION], [SETTING], [LIGHT], [MATERIALS],
photoreal film still, sharp focus on POI
```

Turbo: **prefer positive constraints** (negatives often ignored).

### 4c. Illustrious — § see `illustrious_tags.md`

```text
masterpiece, best quality, newest, absurdres, highres, 1girl, solo, [tags...]
```

---

## 5. I2I / Edit recipes (pointers)

| Path | Front-load | Ref |
|------|------------|-----|
| Moody I2I | **what changes** + keep face | still_image + moody_zimage |
| Qwen Edit | **imperative change** + keep rest | qwen_edit.md |
| Qwen Inpaint | masked content only | qwen_edit.md §inpaint |
| Face lock 2-img | roles of image1/image2 explicit | qwen_edit.md |

---

## 6. Motion recipes (pointers)

Shared hard rules: **`motion_video_prompts.md`**

```text
[ONE camera move], [body/prop action], continuous throughout
```

- **LTX:** optional chronological beats + audio — `ltx23_video.md`  
- **Wan:** subject/motion/camera order, camera lexicon — `wan22_i2v.md`  
- **SI2V:** natural speech mouth motion + micro performance only  

**Forbidden on I2V body:** face beauty essay, full wardrobe, masterpiece soup.

---

## 7. Typography (pointers)

- Ideogram: structured JSON / factory slots — `ideogram4_typography.md`  
- Boogu pipeline: prose + `exactly reading "TEXT"`  
- Literal on-image text → typed `text` field, never hope free prose spells brands  

---

## 8. Quality gates (hard)

### Global still

- [ ] Concrete action/pose (or valid tag pose)  
- [ ] Light or style lighting tags as model requires  
- [ ] Shot size / composition present  
- [ ] Dialect matches CLI  
- [ ] Insert: face not hero  

### Global motion

- [ ] No face/wardrobe re-essay on I2V  
- [ ] ≤ one primary camera move  
- [ ] continuous / throughout (or timed segments)  

### Dialect extras

- Krea: paragraph not telegram; no casting-plate merge — `krea2_still_prompts.md`  
- Z-Image: not negative-only safety — `moody_zimage.md`  
- Illustrious: quality + subject count — `illustrious_tags.md`  
- Qwen: one change — `qwen_edit.md`  
- Ideogram: literal text typed — `ideogram4_typography.md`  

**Gate fail ⇒ do not call generate CLI.**

---

## 9. PROMPT_PACK output

```markdown
## S04
### still_prompt
(... dialect-correct ...)

### still_negative
(... optional; weak on some turbos ...)

### i2v_prompt
(... motion only ...)

### i2v_negative
warp, identity morph, freeze frame, ...

### notes
backend=krea2|moody|ltx23|wan22|... | source=SHOT_DESIGN
```

---

## 10. Progressive disclosure

| Need | File |
|------|------|
| **Start here — routing** | `references/model_prompt_matrix.md` |
| Krea2 still | `references/krea2_still_prompts.md` |
| Moody / Z-Image | `references/moody_zimage.md` · `still_image_prompts.md` |
| Illustrious tags | `references/illustrious_tags.md` |
| Qwen edit/inpaint/angle | `references/qwen_edit.md` |
| Ideogram / Boogu | `references/ideogram4_typography.md` |
| Shared motion | `references/motion_video_prompts.md` |
| LTX depth | `references/ltx23_video.md` |
| Wan depth | `references/wan22_i2v.md` |
| Banned + cross-model traps | `references/banned_and_weak.md` |
| Lexicon camera/light | `references/keyword_lexicon.md` |
| Research log | `RESEARCH.md` |
| Factory prose SSOT | `docs/generation_prompt_craft.md` |

---

## 11. Checklist before generate

- [ ] generation-prompt equipped  
- [ ] tool_catalog / QUALITY_POLICY → CLI known  
- [ ] **model_prompt_matrix row read**  
- [ ] dialect reference file applied  
- [ ] still and/or motion/edit string written  
- [ ] gates pass  
- [ ] I2V has no wardrobe essay  
- [ ] Typography uses literal text mechanism if text is hero  
- [ ] No cross-dialect contamination  

---

## 12. Grok native (hybrid)

| Tool | Style |
|------|--------|
| image_gen | § photoreal NL 2–5 sentences or Krea-like paragraph |
| image_edit | change-first + keep identity |
| image_to_video | 1–2 sentences, single move, continuous |

Then factory QA same as other stills/clips.
