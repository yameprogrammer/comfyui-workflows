# Ideogram 4 & Boogu typography prompts

**CLI:** `generate_ideogram4`, `generate_boogu_typo`  
**Code helpers:** `lib/ideogram4_prompt.py`  
**Official:** ideogram-oss `docs/prompting.md` (structured JSON captions)

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| Ideogram 4 official prompting | Trained on **structured JSON captions**; plain text weaker |
| Schema | `text` elements = **literal** string; `obj` = painted NL description |
| bbox | `[y_min, x_min, y_max, x_max]` normalized **0–1000**, row-first |
| Style fork | `photo` vs `art_style` paths — pick one family |
| Community | Exact JSON key order/spelling matters; fake braces ≠ schema |
| Factory Boogu pipe | Prose with `exactly reading "LUXE"`; then Ideogram→Krea polish |

---

## When to use

| Need | Tool |
|------|------|
| Light title card / menu / sign | `generate_ideogram4` --slot |
| Dense magazine cover, poster, ad | `generate_boogu_typo --mode pipeline` |
| Photoreal still without critical text | Krea / Moody — **not** Ideogram |

---

## Ideogram JSON dialect (best)

Prefer factory builders / slots so schema stays valid.

### Text element (literal letters)

```json
{
  "type": "text",
  "bbox": [50, 100, 200, 900],
  "text": "에피소드 제목",
  "desc": "bold condensed Korean display type, high contrast, centered"
}
```

- `text` = exact glyphs to render  
- `desc` = how type looks (not the copy itself)

### Object element

```json
{
  "type": "obj",
  "bbox": [400, 200, 900, 800],
  "desc": "mid-20s woman soft portrait, cream cardigan, shallow DOF"
}
```

### Style block

- Photo path: aesthetics, lighting, **photo**, medium, optional color_palette  
- Art path: aesthetics, lighting, medium, **art_style**, optional color_palette  

Do **not** mix photo + art_style as co-equal primaries.

### Color palette

Uppercase hex: `"#1A1A1A"`, `"#F5F0E8"` (up to ~5).

---

## Factory slots (`generate_ideogram4`)

| Slot | Use |
|------|-----|
| `title_card` | Clean title, max legibility |
| `end_card` | Outro |
| `menu_board` | Cafe menu mood |
| `signage` | Storefront sign |

Pass `--text "..."` for the literal string; builder fills schema.

---

## Boogu / magazine prose dialect

When using freeform `-p` for Boogu pipeline:

```text
High fashion magazine cover, masthead text exactly reading "LUXE",
subtitle exactly reading "RAIN ISSUE", central model portrait cream knit,
clean layout, photoreal print, muted cool palette
```

Rules:

- Quote **exact** strings for every readable word  
- Prefer prose layout language over inventing JSON keys as on-image text  
- Don’t put schema key names (`high_level_description`) as visible type  

---

## Gates

FAIL if:

- [ ] Critical brand text only buried in free prose without `text` field / `exactly reading`  
- [ ] Invalid fake-JSON without schema  
- [ ] Using Ideogram for non-text photoreal keyframe that Krea should own  
- [ ] bbox in pixel coords instead of 0–1000  
