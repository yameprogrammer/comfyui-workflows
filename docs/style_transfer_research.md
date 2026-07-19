# Style transfer research → factory tool

**Date:** 2026-07-18  
**Tool:** `scripts/generate_style_transfer.py`  
**Goal:** Reliable **content-preserving style change** for agent toolbox (TRANSFORM shelf).

---

## 1. Sources (community · tutorials · practice)

| Source | Takeaway |
|--------|----------|
| [CG Pixel — Qwen Edit style transfer (YouTube)](https://www.youtube.com/watch?v=_XOV4KMxdug) | Multi-image Qwen edit: text + refs; style without full ControlNet stack |
| Reddit r/comfyui — Qwen style transfer threads | Original / Edit-2509 family works for “style of B onto A”; prompt fidelity matters |
| [IPAdapter Plus style (Comflowy / cubiq)](https://www.comflowy.com/blog/IPAdapter-Plus) | Classic SDXL/SD15 style ref; strong ecosystem, **different UNet family** than Lonecat Z-Image |
| [ControlNet + IPAdapter deep dive](https://comfyui.org/en/image-style-transfer-controlnet-ipadapter-workflow) | Style (IPA) + structure (CN) when pose must lock |
| [InstantStyle / Flux style threads](https://www.reddit.com/r/StableDiffusion/comments/1gzos3y/) | Flux style adapters improve consistency; extra weights/stack |
| Academic lineage (Gatys et al. neural style) | Separate **content** vs **style** losses — modern diffusion maps this to multi-ref edit or adapter weights |
| This factory | `generate_qwen_edit` already supports `-i` / `-i2` / `-i3`; Lonecat I2I for soft restyle |

---

## 2. Method ladder (what works when)

| Tier | Method | Pros | Cons | Factory choice |
|------|--------|------|------|----------------|
| **A** | **Instruction edit multi-image** (content + style ref) | One stack we already run; identity lock in text; no SDXL IPA | Needs clear prompt; heavy models | **Default `mode=ref`** |
| **B** | **Named style preset** (text dialect only) | No style image; fast agent UX | Weaker than real ref | **`mode=preset`** |
| **C** | Soft I2I + style text (Lonecat) | Photoreal continuity | Weak “medium” change | **`engine=i2i` opt-in** |
| D | IPAdapter Style (SDXL) | Classic quality | Not Z-Image native; SOP avoided | Not default |
| E | InstantStyle / Flux IPA | Strong Flux | Different model family | Future / opt-in pack |
| F | Pure Gatys NST | Classic art | Poor identity for photo faces | Out of scope |

**Policy:** Prefer **Qwen Edit 2509 multi-ref** for ref-based transfer; named presets for zero-ref; avoid inventing a second IPA graph on Z-Image.

---

## 3. Prompt craft (research → templates)

### 3.1 Dual-image (image1=content, image2=style)

```text
Using image 1 as the CONTENT (subject, pose, composition) and image 2 ONLY as STYLE reference:
Restyle image 1 to match the artistic medium, brushwork/texture, color palette, and lighting character of image 2.
Preserve identity, facial structure, body proportions, wardrobe silhouette, and camera framing from image 1.
Do not copy people, faces, or objects from image 2 — transfer style only.
{extra}
```

### 3.2 Named preset (no style image)

```text
Restyle this image into {style_name} while keeping the same person identity, pose,
composition, and camera framing. Change medium, palette, and rendering only.
Style details: {style_clauses}.
```

### 3.3 Strength

| Strength | Instruction bias |
|----------|------------------|
| soft | “subtle restyle, keep photoreal cues where possible” |
| medium | default balance |
| hard | “strong stylization, commit fully to the target medium” |

---

## 4. Factory mapping

| CLI mode | Backend |
|----------|---------|
| `ref` | `generate_qwen_edit` `-i content -i2 style` |
| `preset` | Qwen instruction (default) or Lonecat `i2i` |
| `look` | Qwen/I2I using `looks/<id>/prompts/positive_core.txt` as style dialect |

Not a replacement for **look packages** (series tone prefix) — this tool is **per-image transform**.

---

## 5. Agent when / when not

| Use | Avoid as only tool |
|-----|---------------------|
| Photo → anime / paint / comic once | Replacing full identity lock workflow |
| Moodboard style ref → one still | Expecting perfect face across 20 shots without ref pack |
| Poster style polish | Anatomy fix (edit/inpaint first) |

---

## 6. Smoke

```bash
python scripts/generate_style_transfer.py --list-styles
python scripts/generate_style_transfer.py --mode preset --style anime \
  -i photo.png -o out_anime.png --seed 42
python scripts/generate_style_transfer.py --mode ref \
  -i content.png --style-image style_mood.png -o out.png
```
