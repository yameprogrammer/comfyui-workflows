# Style Transfer — AGENT_GUIDE

> **Toolbox shelf:** TRANSFORM  
> **CLI:** `python scripts/generate_style_transfer.py`  
> **Alternatives:** soft denoise only → `generate_moody_i2i` · instruction any edit → `generate_qwen_edit` · series tone prefix → `looks/` package  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)  
> **Research:** [docs/style_transfer_research.md](../../../docs/style_transfer_research.md)

**Role:** Restyle a still (anime, paint, comic, moodboard ref, look dialect) while keeping content/identity.

**Not:** full Gatys NST, SDXL IPAdapter graph (different family), or Flux InstantStyle pack (future opt-in).

---

## When / when not

| Use | Use something else |
|-----|---------------------|
| Photo → illustration / paint / noir once | Identity scene change without style → `character_consistent` |
| Moodboard style image → apply to subject | Masked region only → `qwen_inpaint` |
| Named style quick pick | Episode-wide tone SSOT → `look_create` + compose |
| Look package as style dialect | |

---

## Modes

| Mode | Needs | Backend |
|------|-------|---------|
| **`preset`** | `--style anime` (etc.) | Qwen instruction (default) or `--engine i2i` |
| **`ref`** | `-i` content + `--style-image` | Qwen multi-image (`-i2` style) |
| **`look`** | `--look-id cinematic_moody_v1` | Qwen / i2i from look core text |

```bash
python scripts/generate_style_transfer.py --list-styles

# Named style
python scripts/generate_style_transfer.py --mode preset --style anime \
  -i photo.png -o out_anime.png --seed 42 --strength medium

# Style reference image
python scripts/generate_style_transfer.py --mode ref \
  -i content.png --style-image moodboard.png -o out.png --strength hard

# Factory look dialect
python scripts/generate_style_transfer.py --mode look --look-id cinematic_moody_v1 \
  -i frame.png -o graded.png

# Softer photoreal-friendly restyle
python scripts/generate_style_transfer.py --mode preset --style vintage_film \
  -i photo.png -o film.png --engine i2i -d 0.55
```

---

## Strength

| Value | Effect |
|-------|--------|
| `soft` | Subtle medium shift |
| `medium` | Default balance |
| `hard` | Strong stylization |

Identity lock is **on** by default (`--no-identity` to relax).

---

## Research basis (short)

- Community: Qwen Image Edit multi-image style transfer (YouTube / Reddit).  
- Classic: IPAdapter Style (SDXL) — not default here (Z-Image / Qwen stack).  
- Factory: reuse `generate_qwen_edit` multi-ref + named style dialect library.

---

## Smoke

```bash
python scripts/generate_style_transfer.py --list-styles
python scripts/generate_style_transfer.py --mode preset --style noir \
  -i dumps/park_avatar_v1/cand_t2i_s52001.png \
  -o dumps/park_avatar_v1/style_noir_smoke.png --seed 7 --timeout 300
```
