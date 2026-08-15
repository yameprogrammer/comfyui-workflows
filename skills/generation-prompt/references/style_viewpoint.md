# Style transfer, viewpoint, character-consistent

**CLI:** `generate_style_transfer` · `generate_viewpoint` · `generate_character_consistent` · `generate_qwen_angle` (angle details also in `qwen_edit.md`)

These are **instruction / preset** tools. Image is identity.

---

## Style transfer

| Mode | Prompt |
|------|--------|
| `preset` | Pick `--style anime\|oil_paint\|noir…` — do not also write a full new scene |
| `ref` | Style comes from `--style-image`. Text = **keep face, apply medium** |
| `look` | `looks/<id>` core is the style dialect |

```text
Restyle as [medium]. Keep the same person, pose, and framing.
```

---

## Viewpoint

Prefer `--preset low_angle` / `birds_eye` / …  
Custom: `--h --v --zoom`. Extra text = **keep identity**, not a new location.

---

## Character consistent

| Mode | Prompt |
|------|--------|
| `lock` | **New action/scene only** + implicit keep face (denoise ~0.52) |
| `soft` | Expression or light only |
| `remix` | Stronger wardrobe/set; still no new person |
| `anchor` | Short T2I master-face (Krea/Moody dialect, not Illustrious soup on photoreal) |
| `angle` / `pose` | View or pose change; appearance from ref |

Same I2I rule: **change-first**, no tag-soup face re-description.

---

## Gates

- [ ] One job (style or angle or lock)  
- [ ] Not a second T2I essay  
- [ ] Photoreal lock ≠ Illustrious quality tags  
