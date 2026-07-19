# Krea2 Still Prompts (T2I) — Enhanced Reference

**When:** `generate_krea` / `krea2_t2i_*` / QUALITY_POLICY keyframe main = Krea  
**Updated:** 2026-07-19 (architecture-aware rewrite)  
**Episode SSOT example:** `01_기획/PROMPT_PACK_KREA.md` + `KREA2_PROMPT_RESEARCH.md`  
**Related:** [docs/krea2_prompt_guide.md](../../docs/krea2_prompt_guide.md) · [Krea2_SFW_NSFW_v10_AGENT_GUIDE.md](../../workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md)

---

## 1. Architecture Awareness — Why Krea2 Behaves Differently

| Component | Detail |
|-----------|--------|
| **Diffusion backbone** | 12B DiT (Flux-class) — large capacity, texture-rich |
| **Text encoder** | Qwen3-VL 4B — processes **natural language prose** like an LLM, NOT CLIP token embeddings |
| **Design philosophy** | Aesthetic-first: engineered to avoid the "AI look" (waxy skin, fake bokeh, plastic surfaces) |
| **Optimal prompt style** | One cohesive English paragraph (90–140 words). NL prose, NOT tag soup |
| **Token budget** | Stay under 512 tokens. Qwen3-VL handles long text gracefully, but truncation hurts at edges |

**Key implication:** Because Qwen3-VL reads context like an LLM, word order and sentence structure
matter. "A woman in a knit cardigan walks through rain" outperforms "woman, knit, rain, walking".

Sources: [krea-ai/krea-2 prompting.md](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md),
[expansion.txt](https://github.com/krea-ai/krea-2/blob/main/docs/expansion.txt),
fal Krea 2 guide, Comfy krea-2 docs, HF reverse-prompt system prompts.

---

## 2. RAW vs Turbo — Mode Selection

| Mode | Steps | Use case | Agent default? |
|------|-------|----------|----------------|
| **Turbo** | ~8 (distilled) | All production keyframes, music video stills, fast iteration | ✅ YES |
| **RAW** | ~52 (undistilled) | Hero shots needing maximum quality ceiling, LoRA training data, poster frames | Opt-in only |

> **Critical difference from older turbos:** Krea2 Turbo does NOT severely sacrifice quality compared
> to RAW the way SDXL Turbo or SD1.5 LCM do. Turbo IS the primary production path. Reserve RAW for
> shots where that extra ceiling matters (album art, billboard-scale hero).

**Workflow flag:** preset `krea2_t2i_v10` = Turbo by default. For RAW, bump steps to 52 and
disable turbo LoRA in the sampler group.

---

## 3. Hard Rules (Agents Must Follow)

1. **One cohesive English paragraph** — no Danbooru tags, no `masterpiece/best quality/8k` fluff.
2. **Start with medium/style prefix** for photoreal: `Photoreal cinematic film still,`
3. **Never use meta-language:** `In this image…`, `The photo shows…`, `I want…`
4. **Structure inside the paragraph** — follow the 7-layer order (§4).
5. **Spatial locks as POSITIVES:** `she occupies the right third`, `under ONE parasol`, `SOLITARY woman`.
6. **Do not paste casting-plate** (grey seamless, bare shoulders face-lock) into scene location prompts.
7. **Negatives belong in the negative slot only.** Never dump "NO/without/avoid" lists in positive string.
8. **Token budget:** stay under 512 tokens. Trim duplicates aggressively.
9. **Prompt expander:** OFF for full handcrafted paragraphs. ON only for thin seeds — then verify faithfulness.
10. **Insert shots:** hero is prop or fragment. Face / full body must NOT be the primary subject.
11. **Materials matter:** Krea2 excels at texture rendering. Always name fabrics, surfaces, finishes.
12. **No casting plate merge:** if you need a face reference, run Face ID lock AFTER clean T2I.

---

## 4. Seven-Layer Prompt Structure

Build every still prompt in this order. Each layer is required for photoreal production shots.

| Layer | What | Example tokens |
|-------|------|----------------|
| **L1: Medium / Style prefix** | Sets the rendering contract | `Photoreal cinematic film still,` · `Editorial fashion photograph,` · `Gritty documentary photograph,` |
| **L2: Shot size + angle** | Framing + camera position | `medium shot waist-up, slight low angle,` · `extreme close-up, eye level,` |
| **L3: Subject + pose / action** | Concrete verbs, identity short-form | `A solitary mid-20s Korean woman stands fully upright, arms loose at sides,` |
| **L4: Wardrobe + materials** | Tactile nouns — fabric type, finish | `cream knit rib cardigan over white cotton blouse, light-wash denim, white leather low-tops,` |
| **L5: Props + spatial relations** | Object, placement, interaction | `translucent plastic shopping bag in her left hand, one pure yellow nylon parasol arching overhead,` |
| **L6: Setting + environment** | Real architecture, not seamless | `wet dark asphalt alley behind a Seoul convenience store, glass shopfront softly blurred,` |
| **L7: Light + mood + grade suffix** | Quality, atmosphere, palette closer | `overcast soft key from above, rain reflections, desaturated cool grade, natural skin texture, sharp focus on face and torso, rainy-Seoul music-video keyframe.` |

### Assembly Template

```text
[L1 style prefix], [L2 shot size + angle].
A [L3 solitary subject + pose/action verbs].
[L4 wardrobe with fabric names].
[L5 props + spatial relations].
[L6 real setting anchor — no seamless].
[L7 light descriptor], [palette/grade], natural skin texture, sharp focus on [POI], [project tag].
```

### Length Target

| Model path | Target |
|------------|--------|
| **Krea2 still (Turbo / RAW)** | **90–140 words, one paragraph** |
| Moody still | 40–120 words / 6–10 clauses |
| I2V motion | 8–40 words (motion + camera only) |

---

## 5. Positive vs Negative — Spatial Lock Philosophy

### Good — Positive spatial lock (anchors reality)

```text
A SOLITARY mid-20s Korean woman stands fully upright under ONE pure yellow nylon
parasol that covers her head and shoulders; she occupies the RIGHT THIRD of the frame.
Only one person. Only one yellow parasol.
```

### Bad — Negation spam (can still conjure the thing it tries to avoid)

```text
ONE woman ONLY. NO second person. NO poster. NO empty parasol. NO twin. NO collage.
WITHOUT duplicates. NEVER two people. AVOID clone.
```

### Negative slot (keep here, not in positive string)

```text
two women, twin, clone, poster face, billboard portrait, collage, split screen,
grey seamless studio backdrop outdoors, empty yellow parasol beside her,
deformed hands, extra limbs, gibberish text, brand logos, anime, illustration,
plastic skin, waxy complexion, excessive lens blur
```

---

## 6. Materials Language — Krea2 Loves Texture

Krea2's 12B DiT backbone is trained to excel at material rendering. Naming specific materials,
finishes, and surfaces gives the model precise texture targets.

### Fabric / Clothing

- `cream knit rib cardigan` (shows weave pattern)
- `sheer nylon blouse` (translucency + drape)
- `washed raw denim` (fade lines, thread)
- `matte jersey crop top`
- `patent leather boots` (mirror-gloss)
- `oversized linen coat, natural crumple`

### Surfaces / Environment

- `wet dark asphalt with scattered rain reflections`
- `condensation beads on a plastic cup lid`
- `rain-beaded glass shopfront`
- `brushed chrome railing`
- `concrete pillar with stain blooms`
- `fluorescent tube flicker on white tile`

### Skin / Portrait

- `natural skin texture, visible pores`
- `candid editorial skin, no plastic smoothing`
- `fine freckles across the nose bridge`
- (Avoid: `smooth perfect skin`, `airbrushed`, `flawless` — these trigger the waxy-AI look)

---

## 7. Style Prefix Catalog

Choose ONE prefix that matches the output contract. Never stack two.

| Prefix | Best for |
|--------|----------|
| `Photoreal cinematic film still,` | Music video keyframes, narrative scenes, outdoor/interior |
| `Editorial fashion photograph,` | Wardrobe hero, lookbook frame, on-location style |
| `Luxury product shot,` | Insert / prop hero (perfume, jewelry, fabric swatch) |
| `Gritty documentary photograph,` | Urban candid, reportage, texture-heavy social scenes |
| `K-drama BTS shoot,` | Behind-the-scenes candid on set, natural light |
| `Architecture render,` | Empty frame, interior or exterior structure as subject |
| `Concept art matte painting,` | Stylized wide establishing, non-photoreal hero |
| `High-key beauty editorial,` | Face CU, clean portrait, white key |
| `Wet plate collodion photograph,` | Vintage monochrome portrait treatment |

---

## 8. Shot-Type Recipes

### Single Hero (Default)

`SOLITARY` + full pose + wardrobe materials + one real location + light + camera.
Never imply secondary figure unless shot type explicitly requires it.

### Duo (Only If SHOT_DESIGN Specifies Duo)

Name count explicitly: `one woman + one man`. Prefer man **rear / far / silhouette / soft blur**.
Never write in a way that implies two women unless cast says so.
Add spatial lock: `the man stands two steps behind and to the left, soft out of focus`.

### Insert (Hands, Cup, Drip, Fabric Detail)

POI is the prop fragment. Use `Detail insert,` or `Product insert,` as prefix.
Do NOT include full-body portrait language as hero. Face must NOT win the frame.

### Empty Frame

`empty of people`. Prop or architecture is the subject.
Do not introduce a figure "for scale" unless explicitly designed in SHOT_DESIGN.

---

## 9. LLM Expander Strategy

The Krea2 workflow includes an optional **Prompt Enhancer / LLM expand** node.

| Condition | Expander setting |
|-----------|-----------------|
| Full handcrafted 90–140 word paragraph | **OFF** — expander may hallucinate extra people, props, or style shifts |
| Thin seed (< 30 words, exploratory) | **ON** — then read expanded string and verify it didn't add people/location drift |
| Re-using a reference image caption | **OFF** — caption is already descriptive |
| Iterating on a shot with known issues | **OFF** — you need precise control |

When expander is ON: always log the expanded string in PROMPT_PACK alongside the seed.
If expanded string fails gates §10, edit manually or turn expander OFF and write full paragraph.

---

## 10. Common Failures & Fixes

| Failure | Symptom | Fix |
|---------|---------|-----|
| **Tag soup input** | Outputs look generic, style undefined | Rewrite as NL prose paragraph |
| **masterpiece/8k fluff** | No improvement, wastes token budget | Delete entirely; use style prefix instead |
| **Casting plate merged in** | Portrait on seamless inserted into rainy alley scene | Keep casting plate in a separate Face ID workflow; location prompt must describe real architecture |
| **NO-spam negations in positive** | Twins/duplicates still appear | Replace with positive spatial lock: `solitary`, `ONE parasol`, `right third` |
| **Wardrobe essay on insert shot** | Full-body description for a hand/prop shot | Insert prefix + POI first; omit full wardrobe |
| **Over-long prompt (>512 tokens)** | Late-paragraph tokens silently truncated | Trim duplicates; aim 90–140 words |
| **Expander invents extra person** | Second figure appears not in SHOT_DESIGN | Turn expander OFF; write full handcrafted paragraph |
| **Waxy / plastic skin output** | Smooth AI look | Add: `natural skin texture, candid editorial, visible pores, no plastic skin` |
| **Excessive bokeh / fake depth** | Background looks smeared | Remove vague `blurred background` language; describe specific setting at low detail instead |
| **Wrong shot size** | MS when CU needed | Check L2 layer — shot size must match SHOT_DESIGN exactly |

---

## 11. Gallery of Examples

### Example A — Portrait (Medium Shot, Rainy Seoul)

```text
Photoreal cinematic film still, medium shot waist-up at slight low angle.
A solitary mid-20s Korean woman with warm dark brown eyes and collarbone-length dark
soft waves stands fully upright under one pure yellow nylon parasol covering her head
and shoulders; she occupies the right third of the frame.
Cream knit rib cardigan over a white cotton blouse, light-wash straight-leg denim,
white canvas low-top sneakers, translucent plastic shopping bag in her left hand.
Wet dark asphalt with scattered rain reflections, real Seoul convenience store glass
shopfront softly blurred behind her.
Overcast soft key from above, cool desaturated grade, natural skin texture, fine
freckles across the nose bridge, sharp focus on face and torso, rainy-Seoul K-R&B
music-video keyframe.
```
*Word count: ~112 · Layers: all 7 · Spatial lock: right third, ONE parasol*

---

### Example B — Editorial Fashion (Full Body, Golden Hour Street)

```text
Editorial fashion photograph, full-length shot at eye level, 50mm lens feel.
A solitary woman in her late 20s strides forward with loose confident arms, occupying
the left half of the frame, gaze angled slightly off-camera right.
Oversized sand linen blazer over a ribbed black cotton crop top, wide-leg chalk-white
trousers with a pressed centre crease, tan leather mule sandals.
No props; negative space is the graphic element.
A wide empty Tokyo side-street at golden hour, long building shadows cutting across
pale concrete.
Hard golden rim light from low camera-left, warm amber grade, natural skin texture
with visible shoulder freckles, sharp focus tip-to-toe, minimal editorial silence.
```
*Word count: ~110 · Layers: all 7 · Style: editorial, not photoreal*

---

### Example C — Gritty Urban Street (Wide, Night Rain)

```text
Gritty documentary photograph, wide establishing shot slightly above eye level.
A solitary young man in his early 30s walks away from camera through a narrow back
alley, hood up, hands in jacket pockets, shoulders hunched against the rain.
Black nylon zip-up bomber jacket, dark grey cargo trousers, white rubber-sole boots.
Crumpled plastic convenience bag tucked under his arm.
Narrow alley between concrete apartment buildings, laundry lines overhead,
a single fluorescent sign in Korean script bleeding pink neon onto the wet asphalt.
Mixed sources: pink neon spill from right, cool overhead fluorescent wash, rain
reflections doubling the signage, heavy grain, desaturated except the neon pink,
sharp focus on the jacket back and wet ground, Seoul midnight noir keyframe.
```
*Word count: ~115 · Night / neon palette · Spatial lock: solitary, walks away*

---

### Example D — Insert Shot (Product / Detail)

```text
Luxury product shot, extreme close-up at eye level, macro lens feel.
Detail insert: a woman's hand with natural unpainted nails holds a condensation-beaded
clear plastic convenience store cup; the hand occupies the centre-left of the frame.
No full body; wrist and lower forearm only, soft grey knit sleeve edge visible.
White marble café counter beneath, blurred café interior bokeh behind.
Soft diffused north-light from a large window, clean cool highlights on the
condensation beads, sharp focus on the cup lid and knuckles, still-life product
editorial silence.
```
*Word count: ~90 · Insert prefix · Face/full body excluded · Texture: condensation, knit*

---

## 12. Quality Gates — Krea2 Still (Full Checklist)

FAIL before `generate_krea` if ANY item is unchecked:

**Architecture / Style Check**
- [ ] Style prefix present and matches shoot type (L1)
- [ ] Shot size + angle specified (L2)
- [ ] No meta-language (`In this image…`, `The photo shows…`)
- [ ] No `masterpiece`, `best quality`, `8k`, `hyper-detailed` fluff tokens

**Subject & Spatial Lock Check**
- [ ] Concrete pose/action verbs present (L3)
- [ ] Spatial lock for single-hero shots (`SOLITARY`, `right third`, `ONE prop`)
- [ ] Duo language absent on single-hero shots
- [ ] Insert: face/full-body NOT the primary subject

**Material & Environment Check**
- [ ] At least one fabric/material noun present (L4) — not just colour
- [ ] Real setting anchor present — not seamless/studio (L6)
- [ ] Casting-plate language NOT in scene prompt
- [ ] `natural skin texture` or equivalent anti-waxy phrase present for portrait shots

**Negative / Token Check**
- [ ] No "NO/without/avoid" list in positive string
- [ ] Negatives (if any) placed in negative slot only
- [ ] Estimated word count: 90–140 words (trim if over ~150)
- [ ] No obvious duplication that wastes token budget

**Expander / Handoff Check**
- [ ] Expander set correctly (OFF for full paragraph; ON only for thin seed + verified)
- [ ] Prompt passed into `generate_krea -p "…"` as-is — no appearance_prompt merge
- [ ] After generation: Visual QA → Face ID lock (optional second pass)

---

## 13. Workflow Settings (Prompt-Adjacent)

| Item | Default for MV keyframes |
|------|--------------------------|
| CLI | `python scripts/generate_krea.py` |
| Preset | `krea2_t2i_v10` (or project QUALITY_POLICY) |
| Size | 1920×1088 (`work_16x9_1080`) unless policy overrides |
| Turbo steps | ~8 (baked); bump to 52 for RAW |
| Realism LoRA | Optional for candid photo look (add @0.6) |
| Face ID | Qwen 2-image lock **after** clean T2I only |
| Expander | OFF by default for handcrafted paragraphs |
| NSFW | Use `generate_krea_nsfw` / preset `krea2_nsfw_t2i` — adult 18+ only |

---

## 14. Handoff Checklist

1. Build from `SHOT_DESIGN` + this reference.
2. Write `still_prompt` into `PROMPT_PACK` as full paragraph (all 7 layers).
3. Pass ALL gates in §12.
4. Run: `generate_krea -p "<still_prompt>"` — no external string merge.
5. Visual QA on output.
6. Optional: Face ID lock with reference image (separate pass).
7. Log result path + seed in PROMPT_PACK.
