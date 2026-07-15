---
name: generation-prompt
version: 1.0.0
description: >
  Translate shot design into high-quality IMAGE and VIDEO model prompts for agent_custom.
  Use when writing prompts for T2I/I2I keyframes, I2V/SI2V motion, shot_compose, generate_moody,
  generate_i2v, generate_s2v, episode_i2v/s2v, or when user says "write the prompt", "prompt pack",
  "make it more detailed", "I2V prompt". Converts video-direction SHOT_DESIGN fields into concrete
  English clauses. Bans tag-soup and wardrobe re-essay on motion. Slash: /generation-prompt
---

# generation-prompt — Image & video prompt craft (factory)

You turn **direction** into **model-readable English**.  
You are not a lyric poet and not a tag dump.

**Upstream:** `skills/video-direction` → CREATIVE + SHOT_DESIGN (if missing, equip direction first).  
**SSOT longform:** `docs/generation_prompt_craft.md` (Rule 7.5).  
**This skill:** enforceable structure, lexicons, quality gates, per-shot **PROMPT_PACK**.

---

## 0. Equip

```bash
python scripts/skill_equip.py install generation-prompt
# or read skills/generation-prompt/SKILL.md fully
```

Before **any** `shot_compose` / `generate_*` / `episode_i2v` / `episode_s2v`:

1. SHOT_DESIGN exists (or build via video-direction).  
2. This skill active.  
3. Output **still_prompt** and/or **motion_prompt** per shot with gates pass.

---

## 1. SYSTEM identity

```text
You expand SHOT fields into visible nouns and verbs.
Order for stills: Subject → Action → Setting → Light → Camera/lens → Materials → Look.
One primary intent per prompt.
Ban: masterpiece, best quality, 8k, ultra detailed, cinematic (alone), stunning, epic.
I2V/SI2V: motion + camera only; never re-describe face/wardrobe/identity.
English for model prompts; Korean OK for notes.
Prefer 40–120 words still; 8–40 words motion.
Map every filled SHOT column into at least one clause (or mark N/A).
```

---

## 2. Workflow

```text
A. Load shot row (+ CREATIVE theme: look, materials_hero, optical_feel, chm, world)
B. Choose mode: still | i2i | i2v | si2v | (optional t2v note)
C. Expand using references/lexicon + templates
D. Quality gate (fail → rewrite)
E. Write PROMPT_PACK entry
F. Call factory CLI with that string only
```

### Modes

| Mode | When | Body focus |
|------|------|------------|
| **still** | T2I keyframe / board | Full stack from SHOT |
| **i2i** | Surgical edit / denoise change | **What changes** first + keep face/wardrobe short |
| **i2v** | Motion from approved keyframe | **Camera + body motion** only + continuous |
| **si2v** | Lips from audio | Speech micro-motion + stability + performance |

---

## 3. Still prompt recipe (T2I)

**Expand order** (community + factory Rule 7.5):

```text
[look short], [identity/CHM], [wardrobe],
[ACTION concrete], [SETTING/world anchors],
[LIGHT], [CAMERA: size angle lens move-if-static],
[COMPOSITION placement], [MATERIALS 2–4],
[optical_feel short], photoreal film still, sharp focus on POI
```

**Must include if SHOT has them:**

| SHOT field | Becomes |
|------------|---------|
| action / blocking | verbs + contact (hands on cup) |
| composition | on right third, lead room, FG glass… |
| lighting | soft key cam-left, cool window fill… |
| world | café wood counter, rain streaks… |
| chm | cream blouse, damp hair ends, natural makeup… |
| materials / theme | ceramic condensation, cotton weave… |
| risk | feet flat, two hands five fingers, no extra limbs… |

**Length:** ~40–120 words equivalent · 6–10 clauses.  
**Language:** English.

Full patterns: `references/still_image_prompts.md`  
Lexicon: `references/keyword_lexicon.md`  
Banned: `references/banned_and_weak.md`

---

## 4. I2I prompt recipe

```text
[CHANGE first], same person keep face and identity,
[optional keep wardrobe], [shot size if reframing],
[light change if any]
```

Denoise guidance (factory): prop 0.70–0.73 · light 0.75–0.78 · pose/wardrobe 0.82–0.86.

---

## 5. I2V motion recipe

```text
[one camera move], [body/prop micro action], continuous motion throughout,
[optional: stable exposure]
```

**Negative (always consider):**  
`warp, identity morph, freeze frame, flicker, extra limbs, face melt, whip pan`

**Forbidden in I2V body:** face beauty essay, full wardrobe, “masterpiece”, re-setting the whole café.

Length: **8–40 words**. One move only (video-direction camera rule).

See `references/motion_video_prompts.md`.

---

## 6. SI2V motion recipe

```text
natural speech mouth motion, [performance micro], shoulders almost still,
[optional: hands rest on prop], continuous throughout
```

Align `performance` profile from SHOT / factory `performance_profiles`.  
Do not override speak with pure still language.

Negative: `big lean, stand up, closed mouth while talking, face morph, freeze pad`

---

## 7. Quality gates (hard)

### Still — FAIL if

- [ ] No concrete **action/pose**  
- [ ] No **light** clause  
- [ ] No **shot size or lens/angle**  
- [ ] Only banned fluff tags  
- [ ] Insert shot but face/torso described as hero  
- [ ] Missing material when Theme materials_hero set  
- [ ] Word-count fluff > 150 words with no new visible info  

### I2V — FAIL if

- [ ] Describes face/hair/outfit in detail  
- [ ] More than one primary camera move  
- [ ] No “continuous” / throughout intent  
- [ ] Empty “cinematic motion” only  

### SI2V — FAIL if

- [ ] No mouth/speech motion  
- [ ] Large body travel mid-line  
- [ ] Wardrobe re-essay  

**Gate fail ⇒ do not call generate CLI.** Rewrite.

---

## 8. Output format (per shot)

Write to `stories/<ep>/prompts/S0x.md` or episode `PROMPT_PACK.md`:

```markdown
## S04
### still_prompt
(...english...)

### still_negative (optional)
extra limbs, deformed hands, plastic skin, readable gibberish text, ...

### i2v_prompt
(...motion only...)

### i2v_negative
warp, identity morph, freeze frame, ...

### si2v_prompt
(if driver=si2v)

### notes
source: SHOT_DESIGN S04 | look_id=... | denoise=...
```

Template: `templates/PROMPT_PACK_SHOT.md`

---

## 9. Map from video-direction (do not invent blank)

If SHOT cell empty, either fill from CREATIVE Theme or mark `// not specified`.  
**Do not invent a second wardrobe** or new location_id.

Lexicon shortcuts: size/angle/move/light words in `keyword_lexicon.md`  
worked examples: `examples/` · factory `docs/generation_prompt_craft.md`

---

## 10. Handoff to factory

```bash
# after prompts pass gates
python scripts/shot_compose.py ...   # uses assembled still prompt / cores
python scripts/generate_i2v.py ... --prompt "i2v_prompt"
python scripts/episode_s2v.py ...    # performance + motion from pack
```

Then visual QA — prompt craft does not replace open-file QA.

---

## 11. Progressive disclosure

| Need | File |
|------|------|
| Still structure + Moody examples | `references/still_image_prompts.md` |
| I2V / SI2V / multi-model notes | `references/motion_video_prompts.md` |
| Camera/light/motion keyword bank | `references/keyword_lexicon.md` |
| Banned fluff | `references/banned_and_weak.md` |
| Field → clause map | `references/shot_field_map.md` |
| Research sources | `RESEARCH.md` |

---

## 12. Checklist before generate

- [ ] generation-prompt equipped  
- [ ] SHOT_DESIGN row loaded  
- [ ] still and/or motion string written  
- [ ] quality gates pass  
- [ ] English model prompt  
- [ ] I2V/SI2V has no wardrobe essay  
- [ ] Risk constraints present if feet/hands/glass  
