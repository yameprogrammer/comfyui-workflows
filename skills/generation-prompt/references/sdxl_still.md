# SDXL photoreal — official still dialect

**CLI:** `generate_sdxl` (`--model juggernaut|lightning|pony|nsfw`)  
**Not:** Illustrious Danbooru (`generate_illustrious_*`) · Krea cinematic default

**Official / card sources**

| Source | Takeaway |
|--------|----------|
| [RunDiffusion Juggernaut X prompting](https://huggingface.co/RunDiffusion/Juggernaut-X-v10) | Two styles: **Natural language** (scenes) or **Tagging** (fast / LoRA). Both valid. |
| [Juggernaut XI/XII guide](https://www.rundiffusion.com/prompt-guide-for-juggernaut-xi-and-xii) | Detailed + specific wins; simpler prompts also work on later Juggernaut. |
| Ragnarok card | Photoreal / digital paint / pose — start clean, add camera/light. |
| Pony community | `score_9, score_8_up, score_7_up` prefix (factory auto-prepends). Then tags, not Illustrious `newest, absurdres`. |

---

## `--model juggernaut` (default) / `nsfw`

Pick **one** style. Don't mix a novel + 40 Danbooru tags.

**Natural (preferred for scenes)**
```text
A photographer on a windswept cliff at golden hour, holding a vintage Leica,
the ocean churning below, 85mm, film grain
```

**Tagging (fast scout / LoRA)**
```text
photograph, photographer, cliff, golden hour, vintage Leica, ocean, cinematic lighting
```

Length: **20–50 words**. Name light + lens. Skip `masterpiece, 8k`.

`nsfw` uses the same dialect. Default 18+ still is still `generate_krea_nsfw` — this is an SDXL look only.

Negative: factory default (`lowres, extra fingers…`) is enough.

---

## `--model lightning` (Dreamshaper XL Lightning)

Same as Juggernaut **but shorter**. 4–8 step scout — extra clauses get ignored.

```text
street fashion full body, overcast Seoul sidewalk, wool coat, 35mm
```

---

## `--model pony`

Factory prepends `score_9, score_8_up, score_7_up` unless `--no-pony-scores`.  
Then **Pony tags**, not Illustrious quality soup.

```text
1girl, solo, leather jacket, neon alley, cowboy shot, looking at viewer
```

Do **not** also add `masterpiece, best quality, newest, absurdres` (that's Illustrious).

---

## Gates

- [ ] Not using Illustrious quality prefix on Juggernaut  
- [ ] Lightning prompt is short  
- [ ] Pony has count + framing tags  
- [ ] Not treating this as the episode keyframe default (that's Krea)  
