# Still image prompts (T2I / I2I)

Factory: Moody / Z-Image · `shot_compose` · `generate_moody*`  
SSOT: `docs/generation_prompt_craft.md`

> **Model routing first:** `references/model_prompt_matrix.md`  
> - **Krea2** → `krea2_still_prompts.md` (NL paragraph 90–140w)  
> - **Moody / Z-Image** → this file + `moody_zimage.md`  
> - **Illustrious** → `illustrious_tags.md` (Danbooru — not this photoreal stack)

---

## 1. Master template

```text
[LOOK 5–15w], [IDENTITY/CHM], [WARDROBE],
[ACTION + BLOCKING], [SETTING/WORLD anchors 2–4],
[LIGHT full], [CAMERA: size, angle, lens, static|hold],
[COMPOSITION placement], [MATERIALS 2–4],
[OPTICAL feel short], photoreal film still, sharp focus on [POI]
```

Optional end: risk constraints (`two feet planted`, `five fingers per hand`).

---

## 2. Clause recipes

### Subject / CHM

```text
mid-20s Korean woman, oval face, warm brown eyes, long dark hair loose with rain-damp ends,
natural soft makeup matte lids, cream blouse and short summer skirt
```

### Action (never skip)

```text
both hands wrapped around iced americano on wooden table, eyes lowered then lifting to empty chair
```

Bad: `looking sad` · Good: `mouth closed in a small practiced smile, gaze on cup`

### Setting

```text
lived-in sparse Seoul café interior, oak table, rain-streaked window behind, soft blurred menu board
```

### Light

```text
soft warm key from camera left practical lamp, cool fill from window, gentle rim separation
```

### Camera

```text
medium close-up, eye level, 85mm look, shallow depth of field, eyes sharp
```

### Composition

```text
subject on right third, large negative space of wet glass on left, headroom tight for 9:16
```

### Materials

```text
glazed ceramic cup with cold condensation, matte cotton blouse weave, wet window glass streaks, natural skin texture not plastic
```

---

## 3. Insert / ECU special

**Face must not win.**

```text
extreme close-up INSERT of iced americano only, condensation droplets, bent straw, two fingers at rim,
correct human hand scale, wooden table grain, NO face NO torso, 50mm, soft practical light, sharp focus
```

---

## 4. I2I change-first

```text
replace closed umbrella with open yellow umbrella in right hand, keep same woman face and cream blouse,
medium shot, wet street, soft overcast light
```

---

## 5. Negative still (optional short)

```text
deformed hands, extra fingers, extra limbs, plastic skin, warped face,
readable gibberish text, logos, watermark, oversharpen, fish-eye unless asked
```

---

## 6. Length & style

- Prefer **comma-linked clauses** or short sentences **for Moody**.  
- Avoid 50 random tags.  
- Put **identity + action** before grade adjectives.  
- **Krea2:** one flowing paragraph (~90–140 words); see `krea2_still_prompts.md`.  
