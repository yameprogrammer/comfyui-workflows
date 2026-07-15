# Lighting & look — research notes

- **Date**: 2026-07-16  
- **Artifact:** [lighting_and_look.md](lighting_and_look.md)

---

## 1. Sources (types)

### A. Industry fundamentals

| Source / tradition | Absorbed |
|--------------------|----------|
| **Three-point lighting** (film/TV teaching, countless pro primers) | Key / fill / rim roles |
| **StudioBinder & cinematography education blogs** | Motivated light, practicals, high/low key as mood |
| **Talking-head pro tutorials** (YouTube/creator DP: off-axis key, diffusion, contrast ratio, BG practicals) | R01 defaults, neg fill, separation |
| **Neg fill practice** (set & creator commentary) | Deepen shadow without more fill fixtures |

### B. Color & grade craft

| Source type | Absorbed |
|-------------|----------|
| Colorist / grade education (contrast, skin protection, palette restraint) | Look layer vs light layer |
| Complementary accent practice (warm practical + cool ambient — common modern cinema) | Mixed temp recipes |
| Teal-orange *as cliché warning* | Allow only if motivated; prefer CREATIVE palette |

### C. Genre lighting

| Genre craft | Absorbed |
|-------------|----------|
| Noir / thriller pools & slash | R10 |
| Comedy high-key readability | R09 |
| MV section energy via contrast/color | R03 |
| Doc available-light honesty | R07 |

### D. Short-form / vertical

| Practice | Absorbed |
|----------|----------|
| Soft key for faces on phone screens | R01/R11 |
| Rim/BG for depth in tall frame | Separation § |
| Practicals read well in vertical night | Recipes |

### E. Factory-specific

| Asset | Absorbed |
|-------|----------|
| `looks/` style cores | look_id lock |
| `generation_prompt_craft` Light slot | prompt section |
| Moody I2I denoise / identity | don’t relight randomly mid-chain |

---

## 2. Emotion ← light (stance)

Mappings are **craft defaults** used in production teaching, not single-paper psychology claims.  
Agents should treat them as strong priors, overridable by CREATIVE.

---

## 3. Split: lighting design vs look

| | Lighting | Look |
|--|----------|------|
| Per shot/scene | Sources, direction, ratio | Global episode grade policy |
| Changes | With location/time | Rarely mid-episode |
| Factory hook | Prompt clauses | `looks/<id>` cores |

---

## 4. Evolution

| Shift | Skill response |
|-------|----------------|
| Classical studio 3-point | Still baseline for talk |
| “Naturalism” motivated light | Prefer window/lamp stories |
| LED RGB / neon culture | Controlled mixed color, not rainbow spam |
| Vertical creator economy | Soft face + separation minimal kits |
| AI generation | Name sources; lock look; no I2V re-light |

---

## 5. Next

- `blocking.md` — body placement interacting with key side  
- Optional: per-look_id recipe cards under `looks/`  

## Version

| Ver | Note |
|-----|------|
| 2026-07-16 | Initial lighting_and_look pack |