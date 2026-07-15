# Lighting & look — light, color, grade for emotion

- **Skill:** `video-direction`  
- **Pairs with:** [camera_direction.md](camera_direction.md) · [composition.md](composition.md)  
- **Factory:** `looks/<look_id>/` · `docs/look_style_system.md` · Moody light clauses in `docs/generation_prompt_craft.md`  
- **Research:** [lighting_and_look_research.md](lighting_and_look_research.md)

**Prime rule:** Light is **shape + mood + separation**.  
Look is **consistent world physics** across shots (palette, contrast, skin policy).

Without light intent, size/angle/composition still read as “flat AI default.”

---

## 0. Decision order

```text
1) EMOTION / GENRE FEEL   what should the light *do*?
2) MOTIVATION             where does light “come from” in the world?
3) KEY                    direction, hardness, height
4) FILL / NEG FILL        how deep are shadows?
5) SEPARATION             rim / hair / edge vs background
6) BACKGROUND / PRACTICALS world lights that sell the set
7) COLOR TEMP + GELS      warm/cool story
8) CONTRAST KEY           high-key / low-key / soft noir
9) LOOK LOCK              palette, skin, grain — match looks/ package
10) PROMPT + CONTINUITY   same physics next shot
```

SHOT_DESIGN / Visual Theme fields:

```yaml
lighting: "soft key camera-left, neg fill right, cool window rim, warm practical BG"
light_key: soft_high | soft_low | hard_low | mixed_neon   # short code optional
look_id: cinematic_moody_v1
color_notes: "skin natural; teal shadows; amber practicals"
```

CREATIVE already has visual world — **lighting must obey it**.

---

## 1. Emotion map (light → feel)

Craft consensus (set lighting + color grade teaching):

| Feel | Light levers | Color levers |
|------|--------------|--------------|
| **Trust / clean talk** | Soft key ~45°, gentle fill, clean eye light, mild rim | Neutral–warm skin, low drama grade |
| **Warm intimacy** | Soft warm key, low contrast, practical lamps | Amber/rose practicals, soft rolloff |
| **Romance / glamour** | Soft key + strong gentle rim, catchlights | Warm skin, soft bloom optional |
| **Melancholy / rain loneliness** | Soft cool fill, weak warm practical far, wet reflections | Cool bias, desat midtones |
| **Mystery / thriller** | Harder key or slash, deep neg fill, pool of light | Cool shadows, sparse highlights |
| **Horror dread** | Underlight or single hard source, crushed blacks | Sick green/cyan optional; avoid random |
| **Power / hero chorus** | Stronger key contrast, rim edge, slightly harder | Richer contrast, selective color pop (motif) |
| **Documentary honest** | Motivated available-light feel, softer ratios | Minimal grade, true whites |
| **Neon night / MV** | Mixed color sources, rim neon, practical signs | Complementary gels (e.g. cyan+amber) — controlled |
| **Luxury / brand mood** | Soft large source, elegant neg space dark BG | Restrained palette, clean blacks |
| **Comedy clarity** | Bright, even, readable faces | Clean, slightly high-key |
| **Product desire** | Soft specular control on material, clean BG light | True product color; skin secondary |

---

## 2. Building blocks

### 2.1 Three-point (and why we still teach it)

| Light | Role | Emotion if strong |
|-------|------|-------------------|
| **Key** | Main shape of face/body | Direction = drama side |
| **Fill** | Opens shadows | High fill = safe/soft; low = mood |
| **Rim / hair / back** | Separates subject from BG | Glamour, depth, “cinematic edge” |

**Talking-head pro tip (creator + DP):** key **off-axis** (not flat on lens) for cheek shadow shape.  
**Neg fill** (black flag / dark side): deepen shadow without adding light — instant “cinema contrast.”

### 2.2 Hard vs soft

| | Soft | Hard |
|--|------|------|
| **Look** | Diffused, gentle falloff | Sharp shadows, graphic |
| **Feel** | Beauty, talk, rain soft window | Noir, noon sun, horror slash |
| **AI prompt** | `soft diffused key`, `overcast soft` | `hard sunlight`, `single hard rim` |

### 2.3 Ratios (practical language, not lab meters)

| Ratio feel | Face | Use |
|------------|------|-----|
| Flat / beauty | Shadows almost open | Comedy, beauty, some ads |
| Gentle shape | Soft cheek shadow | Default talk (R01) |
| Moody | Deep shadow side | Drama, café night, MV verse |
| Extreme | Near-silhouette | Thriller, silhouette beat only |

Prompt: `soft key with gentle fill` / `strong key, deep negative fill, minimal fill light`.

### 2.4 Motivated & practical lighting

- **Motivated:** light appears to come from window, neon, screen, lamp, sky.  
- **Practical:** visible sources in frame (lamp, sign, phone).  
- Emotion: *believable world* + free color accents.  
- AI: name the source — `warm table lamp motivating key from camera right`.

### 2.5 Color temperature & mixed light

| Choice | Feel |
|--------|------|
| Warm key (~tungsten feel) | Home, café, intimacy |
| Cool key (~day/overcast/moon) | Clean, sad, night exterior |
| **Mixed** warm practical + cool window | Modern cinema default “expensive” |
| Single gel world | Stylized MV — keep consistent |

Avoid random rainbow unless L1 R03/R08 and CREATIVE allows.

### 2.6 High-key vs low-key

| | High-key | Low-key |
|--|----------|---------|
| **Frame** | Bright, few hard blacks | Dark, selective light pools |
| **Feel** | Comedy, daytime pop, clean brand | Mystery, night drama, some MV |
| **Risk** | Flat if no shape | Muddy faces if underexposed |

### 2.7 Separation from background

Without rim/edge or BG darker/brighter than subject → “sticker on wallpaper.”  
Tools: rim, slight BG wash, smoke/haze *feel*, depth (composition FG).

### 2.8 Eye light / catchlight

Tiny reflection in eyes = life. Soft key usually provides it.  
Horror may kill catchlights intentionally — note it.

### 2.9 Day / night / weather cheats (prompt-level)

| Situation | Light recipe (language) |
|-----------|-------------------------|
| Overcast day | Large soft top-front, low contrast |
| Golden hour | Warm low-angle key, long soft shadows |
| Night interior | Practical lamps + controlled fill |
| Night rain street | Cool ambient + specular wet ground + neon rim |
| Midday harsh | Hard top/side; or cheat soft if story allows |

---

## 3. Look / grade layer (beyond single lights)

### 3.1 What “look” means here

| Layer | Owns |
|-------|------|
| **Lighting design** | Sources, direction, ratio in the scene |
| **Look / grade** | Global contrast, palette, skin, grain across the episode |
| **Factory look pack** | `looks/<id>/positive_core.txt` + negative — inject via compose |

**Rule:** pick `look_id` early (CREATIVE handoff). Don’t invent a new grade every shot.

### 3.2 Palette policy

- **2–3 dominant + 1 accent** (often motif color).  
- Skin: protect natural unless stylized MV.  
- Complementary accents (teal shadow / amber practical) work if **motivated**.  
- CREATIVE anti-list should ban muddy brown-gray or random hologram colors if unwanted.

### 3.3 Skin policy

| Policy | When |
|--------|------|
| Natural skin priority | R01 talk, R11 explain, most story |
| Stylized skin ok | R03 MV, R08 mood (still readable) |
| Beauty glow | Soft key + gentle bloom language — not plastic |

### 3.4 Contrast & density

- “Cinematic” ≠ crushed black soup.  
- Prefer **shape on face** + **clean blacks in BG**.  
- AI: `rich contrast but open shadows on face` when talk/lip.

### 3.5 Texture of image / optical feel

Deep vocabulary: **[texture_material_optical.md](texture_material_optical.md)**.

| | Feel |
|--|------|
| Clean digital | Product, explain, comedy |
| Light grain | Mood, filmic default story |
| Heavy grain/VHS | Style episode only — lock in Visual Theme |

---

## 4. Format notes

**9:16 talking:** soft key 30–45° off lens, slight top; avoid overhead raccoon eyes; BG darker or rim for separation.  
**Night vertical:** practicals behind/side read well in tall frame; wet floor speculars add depth.  
**16:9 cinematic:** more room for motivated window side light + environment.

---

## 5. L1 recipe lighting defaults

| L1 | Default light | Look notes |
|----|---------------|------------|
| R01 talking | Soft off-axis key, gentle fill, light rim | Natural skin, `look_id` clean or moody soft |
| R02 drama | Motivated window/lamp; deeper ratio on turns | Continuity of time of day |
| R03 MV | Section-based: verse softer, chorus contrast↑ / color pop | Motif color accent |
| R04 dance | Even body read + optional hard rim; avoid face-only beauty | Full-body exposure |
| R05 hook | High clarity figure-ground light first frame | Instant readable |
| R06 product | Soft controlled specular on material; clean BG | True product color |
| R07 doc/vlog | Available-light motivated | Minimal grade |
| R08 mood | Large soft + big dark neg space; practical sparks | Strong look pack |
| R09 comedy | Brighter, open shadows | High-key lean |
| R10 thriller | Slash/hard pools, neg fill, sparse practical | Cool shadows |
| R11 explain | Soft even face, neutral BG | Broadcast-clean |
| R12 one-take feel | Single motivated family of sources | Don’t relight every beat wildly |

---

## 6. Continuity (light is story)

| Check | Fail |
|-------|------|
| Time of day | Sunny then night no beat |
| Weather wetness | Dry face / wet street random |
| Key side | Left key then right with no move |
| Practical on/off | Lamp state flip |
| Color world | Warm café → cyan void unmotivated |

SHOT_DESIGN: note `light_cont: "window camera-left all SC01"`.

---

## 7. AI / factory prompt craft

### Still (Moody T2I/I2I) — include light + material

```text
… soft key light from camera left, gentle shadow on right cheek,
warm practical lamp in background, cool window rim light,
natural skin tones, subtle film contrast …
```

Order (factory Rule 7.5): Subject → Action → Setting → **Light** → Camera → Materials.

### I2V motion

Do **not** re-light in motion prompt. Light is in the keyframe.  
Motion: `slow push, continuous, stable exposure` — avoid `flashing lights` unless intentional.

### Look pack

```text
shot_compose injects looks/<look_id>/ cores
```

If look fights CREATIVE → change look_id or rewrite cores (don’t fight per-shot).

### QA light checklist

- [ ] Face readable for talk/lip shots?  
- [ ] Subject separated from BG?  
- [ ] Key direction consistent with neighbors?  
- [ ] Palette matches Visual Theme?  
- [ ] No random multicolored gels?  
- [ ] Night scene has motivated sources?  

---

## 8. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| LGT1 | Flat front light on face | Off-axis key + neg fill |
| LGT2 | No separation | Add rim or darken BG |
| LGT3 | Rainbow neon chaos | One accent color + motivation |
| LGT4 | Crushed face in low-key | Open face shadows; crush only BG |
| LGT5 | Look changes every shot | Lock look_id + Theme |
| LGT6 | I2V re-describes lighting | Motion-only prompt |
| LGT7 | Midday hard sun on beauty talk | Soften or motivate interior |
| LGT8 | Wet world / dry skin ignore | Continuity wetness |

---

## 9. Micro recipes (copy)

**Café hybrid talk (R01+rain):**  
Soft warm key cam-left (lamp-motivated), cool soft fill from window, light rim from wet street neon, BG practicals dim amber.

**MV chorus lift (R03):**  
Increase contrast vs verse; stronger rim; motif color gel kick; face still readable if lip.

**Thriller door (R10):**  
Single hard slash across eyes or hand, deep neg fill, cool ambient, warm practical far down hall.

**Product ECU (R06):**  
Large soft source for clean gradient, controlled highlight on material, seamless dark or soft BG wash.

**Comedy punch (R09):**  
Open soft key, minimal mystery shadow, clean white-ish practicals.

---

## 10. SHOT_DESIGN / CREATIVE checklist

- [ ] look_id chosen  
- [ ] lighting string per shot or per scene  
- [ ] emotion matches CREATIVE genre of feeling  
- [ ] motivated sources named when not pure studio  
- [ ] continuity note for key side / TOD  
- [ ] talk/lip shots: face open enough  

---

## 11. Not in this file

- Exact softbox brands / wattage  
- Full color science / ACES pipeline  
- Composition placement → `composition.md`  
- Body path / props → **[blocking.md](blocking.md)**  
