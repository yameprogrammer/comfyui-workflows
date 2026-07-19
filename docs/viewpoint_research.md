# Depth / viewpoint exaggeration research → factory tool

**Date:** 2026-07-18  
**Tool:** `scripts/generate_viewpoint.py`  
**Shelf:** CAMERA  

---

## 1. Sources

| Source | Takeaway |
|--------|----------|
| Qwen-Image-Edit multi-angle LoRA + camera node (this factory) | Explicit **horizontal / vertical / distance (zoom)** ports — best fit for agent viewpoint changes without SD ControlNet depth stack |
| Community Qwen angle tutorials | Azimuth (orbit) + elevation (high/low) + distance (wide vs tight) |
| Classical cinematography | High angle / low angle / bird’s-eye / worm’s-eye as **intent**, not random denoise |
| Depth ControlNet + regen (generic Comfy guides) | Strong structure lock but **different** stack; we already have Fun Union CN for pose — not required for camera-intent restyle |
| Reposition / “move camera” diffusion posts | Instruction edit can fake extreme angles when LoRA range is limited |

---

## 2. Factory choice

| Approach | Use |
|----------|-----|
| **Default: Qwen multi-angle API** (`generate_qwen_angle` + h/v/zoom) | Named viewpoint presets + custom angles |
| **Opt-in: Qwen instruction edit** | Extreme exaggeration / “dramatic dutch-ish” text when angle ports are not enough |
| Not default | Pure depth-map NST, SDXL IPA, separate Reposition-only pack |

Identity: same person/scene as input; change **camera height, pitch, and distance**.

---

## 3. Preset mapping (intent → ports)

| Intent id | Typical h | v (elevation) | zoom* | Cine meaning |
|-----------|-----------|---------------|-------|--------------|
| `eye_level` | 0 | 0 | 5–8 | Neutral |
| `high_angle` | 0 | +30…+40 | mid | Looking down |
| `birds_eye` | 0 | +60…+75 | wider | Top-down |
| `low_angle` | 0 | −25…−35 | mid | Looking up |
| `worms_eye` | 0 | −50…−60 | tighter | Extreme up |
| `wide_establishing` | 0 | 0…+10 | **lower zoom** | More environment |
| `tight_hero` | 0 | −10…−20 | **higher zoom** | Hero CU + slight low |

\*Factory multi-angle node: larger zoom ≈ closer (head sheet uses ~8, body ~5).

Strength scales |v| magnitude and optional `angles_strength`.

---

## 4. Smoke

```bash
python scripts/generate_viewpoint.py --list-presets
python scripts/generate_viewpoint.py -i face.png --preset low_angle -o out_low.png --seed 42
```
