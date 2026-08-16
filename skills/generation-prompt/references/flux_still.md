# Flux.1 Dev / Fill / Flux.2 Klein — official still dialect

**CLI:** `generate_flux` · `generate_flux_fill` · `generate_flux2_klein`  
**Not:** cinematic default (`generate_krea`) · Ideogram type hero · Qwen instruction edit

**Official sources**

| Source | Takeaway |
|--------|----------|
| [BFL FLUX Prompting Guide](https://docs.bfl.ml/guides/prompting_summary) | Whole family: FLUX.1 + FLUX.2. Natural language. |
| [BFL Prompting Basics](https://docs.bfl.ml/guides/prompting_unified_basics) | Template slots, quotes for on-image text, iterate one detail at a time. English is most precise. |
| [BFL FLUX.2 [pro]/[max] guide](https://docs.bfl.ai/guides/prompting_guide_flux2) | **No negative prompts.** Subject + Action + Style + Context. Front-load. 30–80w ideal. Camera/film names. Hex + JSON optional. |
| BFL Klein note | Klein has **no prompt upsampling** — write the detail yourself. 9B TE = Qwen3-8B (NL). |

---

## Shared official formula (BFL)

```text
[SUBJECT], [LOCATION],
[STYLE], [CAMERA SETTINGS], [LIGHTING], [COLORS], [EFFECT],
[ADDITIONAL ELEMENTS]
```

Priority (word order matters): **subject → action → style → context → extras**.

| Length | When |
|--------|------|
| 10–30 words | scout / style test |
| **30–80 words** | production default |
| 80+ | only if every clause is a real spec |

**No negatives.** Say `empty street, sharp focus` not `no people, no blur`.  
Factory `-p` is the positive string. Leave `--negative` empty on Flux CLIs.

On-image text: put the **exact glyphs in quotes** — `the neon sign reads "OPEN"`.

Photoreal: name a camera / film, not “professional photo”.

```text
shot on Sony A7IV, 35mm, f/1.8
shot on Kodak Portra 400, natural grain
80s vintage photo, warm cast, soft focus
```

---

## Flux.1 Dev — `generate_flux`

T5 + CLIP-L. NL prose, not Danbooru. Prompt-following and short in-image text are the reason to pick this over Krea.

```text
A red bicycle leaning on a wet brick alley wall at night, cinematic still,
neon reflections in puddles, low angle, shot on 35mm, shallow depth of field.
```

**Don't:** Krea 90–140w seven-layer essay · masterpiece/8k · tag soup.

Guidance factory default **3.5** (HF FLUX.1-dev). Don't fight it unless a retry needs it.

---

## Flux.1 Fill — `generate_flux_fill`

Prompt = **what replaces the white mask only**. Unmasked pixels stay.

```text
smooth ceramic cup lid, no straw, same cafe lighting and condensation
```

**Don't:** re-describe the whole frame (that's Qwen edit). Anime holes → `generate_anima --mode inpaint`.

---

## Flux.2 Klein — `generate_flux2_klein`

Same BFL formula. Klein will **not** expand a thin seed — if the shot needs materials/camera, type them.

**T2I**
```text
vintage motorcycle parked in front of a retro diner at sunset,
80s vintage photo, film grain, warm color cast
```

**I2I** (denoise, not Qwen edit — no Klein edit weights on disk)
```text
Replace the sky with overcast coastal sunset. Keep the motorcycle and diner.
```

Hex/JSON from the FLUX.2 guide are optional (brand color). Default agent path is the 30–80w NL paragraph.

---

## Gates

- [ ] Natural language, not Danbooru  
- [ ] Subject/action in the first clause  
- [ ] No negative-novel in `-p`  
- [ ] 30–80w unless scout or a justified long spec  
- [ ] Fill: mask contents only  
- [ ] Klein I2I: one change + keep rest  
- [ ] On-image words in quotes  
