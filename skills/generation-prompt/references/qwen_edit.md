# Qwen Image Edit / Inpaint / Multi-angle prompts

**CLI:** `generate_qwen_edit`, `generate_qwen_inpaint`, `generate_qwen_angle`, `character_qwen_turns`  
**Models:** Qwen-Image-Edit (factory 2509/2511 GGUF + Lightning) · InstantX inpaint · Angles LoRA

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| Reddit Qwen-Image-Edit playbook | Imperative edits; always **keep everything else unchanged**; lock face/clothes; chain small edits |
| Community demos | Object add/remove/replace; text change with preserve font; background swap |
| Official/sample rewriters | Structured edit instructions; avoid ambiguous “make better” |
| Factory | Default Lightning 4step; quality path `--no-lightning --steps 20 --cfg 4`; multi-ref face lock |

---

## Edit dialect (global instruction — no mask)

**One primary change.** Imperative English.

```text
[CHANGE verb phrase]. Keep the same [identity / framing / wardrobe / lighting / pose as needed]. Photoreal.
```

### Patterns

| Goal | Pattern |
|------|---------|
| Remove | `Remove the plastic straw from the iced drink. Keep the same cup, woman, and framing.` |
| Replace | `Replace the black umbrella with a pure yellow nylon parasol in her right hand. Keep face and outfit.` |
| Background | `Change the background to rainy Seoul night street bokeh. Keep the woman identity and medium shot framing.` |
| Face lock (2-image) | `Match the face identity to image2 reference. Keep pose, wardrobe, and scene from image1.` |
| Text in image | `Replace sign text with "OPEN". Preserve font style, size, perspective. Do not alter background.` |

### Pro tips (community)

- End with **`Keep everything else unchanged`** when drift appears.  
- **Chain** 2–3 small edits instead of one mega-instruction.  
- Name **left/right**, colors, materials.  
- Avoid: `fix anatomy`, `make it better`, `improve quality` alone.

### Multi-reference

Explicit roles:

```text
Image1 is the scene to edit. Image2 is the face identity reference only.
Transfer facial identity from image2 onto the woman in image1.
Keep pose, camera, wardrobe, and background from image1.
```

---

## Inpaint dialect (mask required)

Prompt describes **only what appears inside the white mask**.

```text
[object/material to generate in masked region], seamless match to surrounding light and color
```

- Mask covers face → face will rewrite (usually bad for ID).  
- Mask + prompt body part must match (hand mask → hand text).

---

## Multi-angle / turns

```text
same character identity, [target view: front / three-quarter / left profile / back],
same wardrobe and lighting style, photoreal character sheet
```

Use factory angle tokens / `<sks>` when CLI documents them — don’t invent conflicting LoRA triggers.

---

## Lightning vs quality

| Pass | Settings | When |
|------|----------|------|
| Fast | Lightning ON (factory default) | First try, candidates |
| Quality | `--no-lightning --steps 20 --cfg 4` | Prop flies away, approve retry |

---

## Gates

FAIL if:

- [ ] No concrete change verb  
- [ ] Full T2I scene rewrite + new pose + new wardrobe + new light in one go  
- [ ] Face-lock without stating which image is face ref  
- [ ] Inpaint prompt describes unmasked regions as primary  
- [ ] “Make cinematic / better quality” only  
