# Illustrious / NoobAI XL tag prompts

**CLI:** `generate_illustrious_standard`  
**When:** anime / illustration XL checkpoints (Fabricated XL, WAI, NoobAI, etc.)  
**Not for:** photoreal MV keyframes on Krea/Z-Image — wrong dialect  

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| Illustrious / NoobAI community (Civitai guides, HF README) | **Danbooru-style tags** primary; quality tags matter |
| NoobAI | Danbooru + e621; quality: `masterpiece, best quality, newest, absurdres, highres` |
| Illustrious | Quality ladder: worst→masterpiece; composition tags like `upper body`, `cowboy shot` |
| Illustrious 2.0+ | Small amount of natural language OK; pure pre-2.0 prefers tags |
| Official-ish tips | Don’t overstack conflicting composition tags |

**Exception to global ban:** On Illustrious, `masterpiece, best quality` is **correct** — do **not** strip them here.  
They remain **banned** on Krea/Z-Image photoreal paths.

---

## Structure

```text
[quality tags], [count], [character/series if any], [artist optional],
[general tags: hair eyes clothes pose], [composition], [background], [year/style tags]
```

Canonical order (NoobAI caption style):

```text
1girl/1boy, character, series, artists, special, general, other
```

### Quality positive (start)

```text
masterpiece, best quality, newest, absurdres, highres
```

### Quality negative (typical)

```text
worst quality, low quality, normal quality, bad anatomy, bad hands, watermark, text errors
```

### Composition (pick one primary)

`portrait`, `upper body`, `cowboy shot`, `full body`, `from side`, `from behind`, `looking at viewer`

Avoid stacking `close-up` + `full body` + `cowboy shot` together.

---

## Example

```text
masterpiece, best quality, newest, absurdres, highres,
1girl, solo, long black hair, brown eyes, school uniform, white shirt, pleated skirt,
upper body, looking at viewer, soft smile, simple background, anime coloring
```

---

## Factory switches (prompt-adjacent)

- Face / hand / eyes detailers — enhance after base tags  
- Hires / USDU — don’t put “8k” spam; use switches  
- I2I: change tags + denoise  
- Clip skip 2 typical  

See `workflows/human/illustrious_standard_v37/AGENT_GUIDE.md`.

---

## Gates

FAIL if:

- [ ] Using this dialect for Krea/Z-Image photoreal MV still  
- [ ] No subject count (`1girl` / `1boy` / group) when relevant  
- [ ] Contradictory composition tag pile  
- [ ] Empty prompt with only quality tags  
