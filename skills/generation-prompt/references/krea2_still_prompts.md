# Krea2 still prompts (T2I)

**When:** `generate_krea` / `krea2_t2i_*` / QUALITY_POLICY 키프레임 메인 = Krea  
**Researched:** 2026-07-17 (official + fal + Comfy + Reddit/Civitai/HF)  
**Episode SSOT example:** project `01_기획/PROMPT_PACK_KREA.md` + `KREA2_PROMPT_RESEARCH.md`

---

## 1. Why Krea differs from Moody tag-stack

| Moody / older SD habits | Krea2 (official + community) |
|-------------------------|------------------------------|
| comma tag soup OK-ish | **Natural language prose** preferred |
| short cores + expand by habit | **Long detailed** yields best; expander optional |
| heavy negative in positive string | **Positive spatial facts**; put neg in negative slot only |
| 40–80 word clause lists | **~90–140 words one paragraph** (stay under ~450–512 tokens) |
| “NO second person” spam | “**solitary** woman”, “**one** yellow parasol **over her head**” |

Sources: [krea-2/docs/prompting.md](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md), [expansion.txt](https://github.com/krea-ai/krea-2/blob/main/docs/expansion.txt), fal Krea 2 guide, Comfy Krea-2 docs, HF reverse-prompt system prompts, r/StableDiffusion tips (specificity, token length ~512).

---

## 2. Hard rules (agents must follow)

1. **One cohesive English paragraph** — no Danbooru tags, no `masterpiece/best quality`.
2. **Start with medium** when photoreal MV: `Photoreal cinematic film still, …`
3. **Never** meta: `In this image…`, `The photo shows…`.
4. **Structure inside the paragraph** (can be one or two sentences groups, still prose):  
   Subject+Pose/Action → Appearance/Wardrobe materials → Props → Composition/Camera → Environment → Light/Mood → Medium suffix.
5. **Spatial locks as positives** (right third, under parasol, standing upright).
6. **Do not paste casting-plate** (grey seamless, bare shoulders face-lock plate) into scene prompts.
7. **Do not paste long NEGATIVE lists into the positive `-p` string.** Use negative slot if workflow supports it; else omit.
8. **Token budget:** avoid &gt;512 tokens / heavy duplication (Comfy/reference code truncate risk).
9. **Prompt enhance / LLM expand:** OFF when shipping a full handcrafted paragraph (expander may invent extra people/props). ON only for thin seeds you intentionally want expanded — then re-check faithfulness.
10. **Insert / empty shots:** hero is prop or fragment — face/full body must not win.

---

## 3. Assembly template (Krea still)

```text
Photoreal cinematic film still, [SHOT SIZE] at [ANGLE], [LENS feel].
A solitary [IDENTITY short] [exact pose/action verbs].
[WARDROBE with fabric: knit / nylon / denim / plastic bag].
[PROPS + relation: under one pure yellow nylon parasol covering her head].
[COMPOSITION: placement, lead room, crop notes].
[SETTING: real architecture anchors — not studio seamless].
[LIGHT: overcast soft / fluorescent / wet asphalt reflections], [palette].
Natural skin texture, sharp focus on [POI], [grade], K-R&B music-video keyframe.
```

### Length

| Model path | Target |
|------------|--------|
| Krea2 still | **90–140 words**, one paragraph |
| Moody still | 40–120 words / 6–10 clauses (see still_image_prompts.md) |
| I2V motion | 8–40 words (unchanged) |

---

## 4. Positive vs negative (critical)

**Good (positive lock):**
```text
A solitary mid-20s Korean woman stands fully upright under one pure yellow nylon parasol
that covers her head and shoulders; she occupies the right third of the frame.
Only one person and one yellow parasol.
```

**Bad (negation soup — can still spawn duals/posters):**
```text
ONE woman ONLY. NO second person. NO poster. NO empty parasol. NO twin. NO collage.
```

**Negative slot (optional, separate):**
```text
two women, twin, clone, poster face, billboard portrait, collage, split screen,
grey seamless studio backdrop outdoors, empty yellow parasol beside her,
deformed hands, extra limbs, gibberish text, brand logos, anime, illustration
```

---

## 5. Shot-type recipes

### Single hero (default)

`solitary` + full pose + wardrobe materials + one location + light + camera.

### Duo (only if SHOT says duo)

Name count explicitly: `one woman + one man`. Prefer man **rear / far / silhouette / soft blur**. Never imply two women.

### Insert (hands, cup, drip, fabric)

POI first. `Detail insert` / `product insert`. No full-body portrait language as hero.

### Empty frame

`empty of people`, prop or architecture as subject. Do not introduce a figure “for scale” unless designed.

---

## 6. Materials language (Krea loves texture)

Prefer tactile nouns:

- cream **knit** cardigan, white blouse cotton  
- pure yellow **nylon** parasol canopy  
- translucent **plastic** shopping bag  
- wet dark asphalt **reflections**, rain **beads**  
- condensation on plastic cup lid  
- natural skin **pores**, freckles (not plastic skin)

fal tip: more specific material/render language → more precise output.

---

## 7. Quality gates — Krea still (extra)

FAIL before `generate_krea` if:

- [ ] Tag soup or banned fluff  
- [ ] No medium / photoreal film still (for photoreal MV)  
- [ ] No concrete pose/action  
- [ ] No light clause  
- [ ] No shot size or angle  
- [ ] Casting-plate seamless mixed into location scene  
- [ ] Long “NO/without” list in positive body  
- [ ] Duo language on single-hero shot  
- [ ] Insert but face is primary subject  
- [ ] Paragraph empty of materials when Theme materials_hero set  
- [ ] Prompt likely &gt;512 tokens (trim duplicates)

---

## 8. Workflow settings (prompt-adjacent)

| Item | Default for sonagi / MV keyframes |
|------|-----------------------------------|
| CLI | `python scripts/generate_krea.py` |
| Preset | `krea2_t2i_v10` (or project QUALITY_POLICY) |
| Size | 1920×1088 (`work_16x9_1080`) unless policy says otherwise |
| Turbo steps | baked ~8; community optional: raw+turbo LoRA @0.6, ~12 steps for quality experiments |
| Realism LoRA | optional experiment for candid photo look |
| Face ID | Qwen 2-image **after** clean T2I only |

---

## 9. Mini example (parasol MS)

```text
Photoreal cinematic film still, medium shot from a slight low angle. A solitary mid-20s Korean woman with freckles, warm dark brown eyes, and collarbone-length dark soft waves stands fully upright under one pure yellow nylon parasol that covers her head and shoulders; she occupies the right third of the frame. Cream knit cardigan over white blouse, light-wash blue jeans, white low-top sneakers, translucent plastic bag in her left hand. Wet dark asphalt with rain reflections, real convenience store glass front softly blurred under overcast daylight. Only one person and one yellow parasol. Natural skin texture, 35mm, sharp focus on her face and torso, rainy Seoul music-video still.
```

---

## 10. Handoff

1. Build from SHOT_DESIGN + this file.  
2. Write `still_prompt` into PROMPT_PACK (full paragraph).  
3. Pass gates §7.  
4. `generate_krea -p "<still_prompt>"` only — no appearance_prompt garbage merge.  
5. Visual QA → optional face lock.
