# Anima DiT 2B — 2D anime / manga / webtoon prompts

**CLI:** `generate_anima` (`--mode t2i|lineart|depth|pose|inpaint|hires`)  
**Not for:** Photoreal MV keyframes (use Krea).  
**Default factory positive is weak** (`1girl, anime masterpiece…`) — never ship that as a hero prompt.

---

## Dialect

Anima is **tag-friendly 2D**, closer to Illustrious than Krea.  
Official (CircleStone): hybrid of **Danbooru tags + short natural language**; anime-specialized 2B. Studio `~style` phrases are weaker than real Danbooru tags.

```text
[quality], [count], [character], [hair/eyes], [wardrobe], [pose/action], [setting], [light], [style]
```

| DO | DON'T |
|----|--------|
| Danbooru-ish tags + short NL pose | Krea 90–140w photoreal essay |
| `anime coloring`, `cel shading`, `manga screentone` when you want that look | `photoreal, 8k, raw photo` |
| One character count (`1girl, solo` / `1boy`) | Dual unnamed people unless 2girls is intended |
| Mode-specific short change (lineart = colors only) | Re-describe the whole scene on inpaint |

Quality prefix (allowed here): `masterpiece, best quality, anime illustration`.

---

## Templates

**T2I**
```text
masterpiece, best quality, anime illustration, 1girl, solo, [hair], [eyes], [outfit],
[pose], [location], [time/light], detailed eyes, clean lineart, cel shading
```

**lineart** — color + material only (lines come from `-i`):
```text
vibrant flat colors, [palette], [skin/cloth materials], keep lineart, no extra line
```

**pose / depth** — appearance; pose/depth is the map:
```text
[character look], [wardrobe], [setting], [light], follow pose map, no extra limbs
```

**inpaint** — masked content only:
```text
[what appears in the hole], match surrounding anime style and line weight
```

**hires** — same as T2I, slightly more material tags (fabric, metal, rain).

---

## Negative (keep short)

```text
worst quality, low quality, photoreal, 3d, extra limbs, bad hands, deformed, blurry
```

---

## Gates

- [ ] Not using Krea photoreal paragraph  
- [ ] Count tag present if people  
- [ ] Mode matches what the prompt talks about  
- [ ] Default CLI positive was replaced  
