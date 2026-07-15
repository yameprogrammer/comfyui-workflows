# Texture, material & optical feel

- **Skill:** `video-direction`  
- **Job:** The **tactile + optical character** of the image — what surfaces are, how light kisses them, and the “lens/film” personality.  
- **Sibling layers:** materials live in the world ([production_design](production_design.md)); light shapes them ([lighting_and_look](lighting_and_look.md)); lens DOF overlaps ([camera_direction](camera_direction.md)); skin MU ([costume_hair_makeup](costume_hair_makeup.md)).  
- **Research:** [texture_material_optical_research.md](texture_material_optical_research.md)

**Prime rule:** Name **2–4 hero materials** + **one optical feel**.  
“Cinematic 8k masterpiece texture” is noise. `wet glass streaks, matte ceramic cup, cotton blouse, light film grain` is design.

---

## 0. Decision order

```text
1) EMOTION / GENRE     grit vs luxury vs clean broadcast
2) HERO MATERIALS      2–4 surfaces that must read
3) SURFACE RESPONSE    matte / glossy / wet / translucent
4) IMPERFECTION        wear, condensation, dust (story, not random)
5) OPTICAL FEEL        clean digital | light grain | soft bloom | harsh phone | anamorphic-feel
6) DOF / BOKEH FEEL    deep read vs shallow isolate (with lens)
7) FX OPTICS           flare, haze, rain smear — sparse
8) LOCK IN THEME       same family all episode
9) STILL PROMPT        Materials clause after Light/Camera
10) MOTION             do not invent new grain/flare mid-I2V
```

CREATIVE / Visual Theme:

```yaml
optical_feel: clean_digital_light_grain   # see §3 codes
materials_hero: [wet_window_glass, ceramic_cup, cotton_blouse, wood_table]
surface_bias: mixed_warm_matte_cool_specular
imperfection: condensation_rain_streaks
avoid_optical: [heavy_vhs, rainbow_flare_spam, plastic_skin]
```

SHOT (optional override):

```yaml
materials: "cup glaze + finger skin pores subtle; BG wood soft"
optical: "85mm shallow, soft circular bokeh, no flare"
```

---

## 1. Emotion map

| Feel | Materials | Optical |
|------|-----------|---------|
| **Trust / talk** | Natural skin, matte fabric, clean ceramic | clean or light grain; shallow–moderate DOF |
| **Luxury** | Smooth stone, silk, polished metal sparse | clean, controlled specular, soft falloff |
| **Lonely rain** | Wet glass, damp fabric, dark wood | cool speculars, light grain, window bokeh |
| **Grit / noir** | Concrete, scuffed metal, dusty glass | higher grain, harder speculars, haze optional |
| **Romance** | Soft textiles, skin, shallow wine glass | soft bloom careful, creamy bokeh |
| **Product desire** | True material (plastic/glass/metal accurate) | clean, sharp hero, soft BG |
| **MV glamour** | Shine fabric, wet street, neon acrylic | selective bloom/flare, richer grain ok |
| **Doc / real** | Mixed imperfect surfaces | clean–light grain, less beauty blur |
| **Horror** | Cold tile, dull metal, skin pale matte | crushed blacks, sparse specular, grain |
| **Comedy clarity** | Simple readable props | clean, open, avoid heavy haze |

---

## 2. Material catalog (prompt language)

Use **specific nouns + adjectives**. Max ~3–4 heroes per shot.

| Class | Example phrases | Notes |
|-------|-----------------|-------|
| **Skin** | natural skin texture, soft pores, not plastic | protect with MU natural; avoid “porcelain doll” |
| **Fabric** | cotton weave, knit, denim, silk sheen, wool | motion: fabric weight |
| **Wet** | rain-streaked glass, wet asphalt reflections, damp hair clumps | continuity with weather |
| **Ceramic / dish** | glazed ceramic, condensation on cold glass | cup scale with hands |
| **Wood** | warm oak grain, worn varnish | café default |
| **Metal** | brushed steel, chrome specular, dull iron | control hotspots |
| **Stone / concrete** | rough concrete, polished marble | grit vs luxury |
| **Paper** | matte receipt, soft menu (blur policy) | |
| **Foliage** | wet leaves, soft petals | |
| **Plastic** | cheap gloss vs matte ABS | product honesty |
| **Food / liquid** | translucent ice, amber coffee | |

**Surface response:**

| Word | Meaning |
|------|---------|
| matte | soft, no sharp highlight |
| glossy / glazed | tight specular |
| wet | streaks + reflections |
| translucent | light through ice/fabric |
| worn / scuffed | story age |
| dusty | neglected / beams |

---

## 3. Optical feel codes (episode lock)

Pick **one** primary for the episode (override rare).

| Code | Look | Use |
|------|------|-----|
| `clean_digital` | Sharp, low grain | Product, explain, comedy |
| `clean_digital_light_grain` | Slight film texture | **Default hybrid/story** |
| `filmic_medium_grain` | Noticeable grain | Mood MV, noir |
| `soft_bloom` | Highlight glow | Romance, some MV — easy to overcook AI |
| `anamorphic_feel` | Streaky bokeh/flare language | Stylized MV only |
| `hazy_atmosphere` | Soft contrast, air | Dream, pollution, soft thriller |
| `harsh_phone` | Hard, clinical | Intentionally lo-fi / found footage |
| `vhs_heavy` | Heavy artifact | Special episode only |

**Avoid stacking** grain + heavy bloom + anamorphic + haze = mud.

---

## 4. Depth of field & bokeh (feel, not EXIF)

| Feel | When | Pair with |
|------|------|-----------|
| Deep focus | Establishing, geography, dance FS | 24–35, more light |
| Moderate | Talk MS | 35–50 |
| Shallow | MCU/CU intimacy, product hero | 50–85 |
| Creamy bokeh | Night lights, rain points | 85 + optical_feel soft |

Prompt: `shallow depth of field, eyes sharp, background soft bokeh` — not `f/1.2 EXIF spam`.

AI risk: over-shallow → face melt; keep **eyes sharp** language on CU.

---

## 5. Optical FX (use sparingly)

| FX | Emotion | Caution |
|----|---------|---------|
| Lens flare | energy, sun, neon | rainbow spam ban |
| Haze / volume light | god rays, club | soft mud |
| Rain on lens | immersion | can obscure face |
| Condensation layer | cold drink, window | continuity |
| Chromatic aberration | lo-fi/stylized | rare |
| Motion blur | speed | I2V may add itself |

---

## 6. Imperfection policy

| Level | Example | Use |
|-------|---------|-----|
| Clean | No wear | Brand product |
| Lived-in | Light scratches, condensation | Default story |
| Gritty | Dirt edge, scuff | Thriller, street |
| Broken | Cracked glass | Story event only |

Imperfections must be **motivated** (same as production design density).

---

## 7. L1 defaults

| L1 | materials_hero bias | optical_feel |
|----|---------------------|--------------|
| R01 talking | skin, fabric, ceramic cup, wood | clean_digital_light_grain |
| R02 drama | skin + environment material contrast | light–medium grain |
| R03 MV | wet street, fabric shine, motif material | filmic or soft_bloom selective |
| R04 dance | fabric motion, floor matte | clean, deep enough for feet |
| R05 hook | one hero material pop | clean, high clarity |
| R06 product | accurate product material | clean_digital |
| R07 vlog | mixed real materials | clean_digital_light_grain |
| R08 mood | glass, rain, textile | filmic_medium_grain or hazy |
| R09 comedy | simple matte props | clean_digital |
| R10 thriller | concrete, metal, dull glass | medium grain, hard specular sparse |
| R11 explain | matte desk, clean skin | clean_digital |
| R12 one-take | consistent materials no teleport | lock one optical_feel |

---

## 8. Shot size × texture

| Size | Texture job |
|------|-------------|
| ELS/LS | Environment materials (wet asphalt, glass façade) |
| MS | Table wood + wardrobe fabric + skin |
| MCU/CU | Skin + eye moisture + hair strand; BG material soft |
| ECU / insert | **Material hero** (glaze, condensation, fiber) |
| Product | True material > beauty blur |

---

## 9. Continuity

| Track | Example |
|-------|---------|
| Wetness | glass, street, hair, coat same beat |
| Cup condensation | builds then fades — don’t reset random |
| Grain/look | same optical_feel all cuts |
| Specular world | neon reflections consistent side |

---

## 10. AI / factory prompt craft

**Still order (Rule 7.5):**  
Subject → Action → Setting → Light → Camera → **Materials** → (optical feel)

```text
… soft key from left, 85mm look shallow DOF eyes sharp,
matte cotton blouse texture, glazed ceramic cup with cold condensation,
rain-streaked window glass background, light film grain, natural skin texture
```

**I2V:**  
`continuous motion, stable exposure` — **do not** add “increase grain / add anamorphic flare” unless intentional event.  
Texture is in the keyframe.

**Ban tag-soup:** `8k, ultra detailed texture, masterpiece, Unreal Engine` without material nouns.

**QA:**  
- Hero materials readable?  
- Skin plastic?  
- Optical feel consistent vs previous shot?  
- Wet world dry surfaces?  

---

## 11. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| TEX1 | No materials, only “cinematic” | Name 2–4 surfaces |
| TEX2 | Plastic skin | natural skin texture + MU natural |
| TEX3 | Optical soup (grain+bloom+haze+flare) | One optical_feel |
| TEX4 | New texture world every shot | Theme lock |
| TEX5 | I2V re-textures scene | Motion-only |
| TEX6 | Wet rain / dry table ignore | Continuity |
| TEX7 | Product wrong material | True material words |
| TEX8 | Over-shallow CU mush | eyes sharp clause |

---

## 12. Micro recipes

**Rain café hybrid:**  
`optical_feel: clean_digital_light_grain`  
`materials_hero: [wet_window_glass, ceramic_cup_condensation, cotton_blouse, oak_table]`  
CU: skin natural + cup glaze; LS: glass streaks + wood mid.

**Product ECU:**  
`clean_digital`, accurate plastic/glass/metal, controlled specular, soft seamless BG.

**Thriller corridor:**  
Dull painted wall, scuffed metal door, sparse wet floor specular, medium grain, no beauty bloom.

**MV chorus:**  
Wet asphalt reflections, fabric sheen, optional single streak flare, motif color on one glossy surface.

---

## 13. Stack position

| # | Layer |
|---|--------|
| 1–6 | camera → composition → light → blocking → world → CHM |
| **7** | **texture / material / optical** (this file) |

Often filled **with** Visual Theme at Gate 1–3; per-shot overrides rare.

---

## 14. Not in this file

- Sensor noise models, LUT vendor catalogs  
- Full grade pipeline (ACES)  
- Detailed lens prescription charts (use camera_direction feel)  
