# Moody / Lonecat Z-Image Turbo still prompts

**CLI:** `generate_moody`, `generate_moody_i2i*`, `generate_moody_controlnet`  
**Model:** Z-Image-Turbo (Flow Matching) via Lonecat AIO  
**Also:** `docs/moody_workflow_guide.md` · factory `generation_prompt_craft.md` §2

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| HF Tongyi-MAI/Z-Image-Turbo PROMPTING | **Long detailed prompts** work best; manual draft → LLM enhance; PE template exists; ~512 token caution (600–1000 words ≈ too long for default max) |
| Comfy Z-Image docs | Strong photoreal; prompt enhancer optional |
| Community (Reddit/YouTube) | Turbo is fast (few steps, CFG~0); **Turbo often ignores negative prompts** — put constraints in **positive** |
| Factory practice | Clause stack Subject→Action→Setting→Light→Camera→Materials; look/char/loc cores short |

---

## Dialect

**Not** pure Danbooru. **Not** Krea essay-only.  
Use **English clause stacks** or short sentences with concrete nouns/verbs.

### T2I template

```text
[look/grade short], [identity/CHM short], [wardrobe],
[SHOT size, angle, lens], [ACTION concrete],
[SETTING anchors], [LIGHT], [MATERIALS 2–4],
photoreal film still, sharp focus on [POI], natural skin texture
```

### Length

| Use | Target |
|-----|--------|
| Hero keyframe | 40–120 words · 6–10 clauses |
| Insert | 30–70 words · POI first, no face |
| LLM-enhanced | keep under ~450–512 tokens after enhance |

### T2I example

```text
cinematic photoreal film still, soft overcast light, mid-20s Korean woman freckles warm brown eyes
collarbone-length dark soft waves, cream knit cardigan white blouse light jeans,
medium shot mid-thigh up, 35mm eye level, standing under bright yellow parasol on right third,
translucent plastic bag in left hand, wet reflective Seoul asphalt, convenience store glass front behind,
natural skin micro-texture not plastic, sharp focus
```

---

## I2I

**Front-load change.** Denoise table (factory):

| Goal | denoise | Prompt focus |
|------|---------|--------------|
| Prop / local | 0.70–0.73 | object only |
| Light / mood | 0.75–0.78 | lighting |
| Pose / wardrobe | 0.82–0.86 | pose + clothes |
| Near-regen | 0.90+ | full restage |

```text
[CHANGE], same person keep face and identity, [optional keep wardrobe], [shot size if needed]
```

---

## ControlNet

Image/pose map owns structure. Text should **not** fight the map.

- Emphasize: materials, light, wardrobe color, mood  
- Avoid: conflicting pose/camera that CN already fixed  

---

## Gates (Z-Image still)

FAIL if:

- [ ] No action/pose  
- [ ] No light  
- [ ] No shot size/angle  
- [ ] Only banned fluff tags  
- [ ] Insert but face is hero  
- [ ] Relying only on negative for dual-person / feet / hands (Turbo may ignore)  
- [ ] Character portrait core crushing insert action  

---

## Negatives

Short optional pack (weak on Turbo):  
`deformed hands, extra limbs, plastic skin, gibberish text, logos, watermark`

Prefer **positive** risk clauses: `both feet planted flat`, `solitary woman`, `five fingers natural grip`.
