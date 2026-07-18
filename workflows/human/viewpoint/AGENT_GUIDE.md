# Viewpoint / depth camera — AGENT_GUIDE

> **Toolbox shelf:** CAMERA  
> **CLI:** `python scripts/generate_viewpoint.py`  
> **Alternatives:** turntable multi-view only → `generate_qwen_angle` · crop framing only → `generate_reframe` (no Comfy) · pose structure → `generate_moody_controlnet`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)  
> **Research:** [docs/viewpoint_research.md](../../../docs/viewpoint_research.md)

**Role:** Change **camera height, pitch, and distance** on a still (high/low/bird’s/worm’s eye, wide vs tight hero) via **Comfy Qwen multi-angle**.

**Not:** PIL reframe crop; full 3D relight; depth-ControlNet pose lock (use controlnet tool).

---

## When / when not

| Use | Use something else |
|-----|---------------------|
| High / low / bird’s / worm’s eye restyle | Side/back turnaround sheet → `qwen_angle` views |
| Wide establishing vs tight hero on same subject | Shot size crop only → `generate_reframe` |
| Dramatic camera for a keyframe before I2V | Style medium change → `generate_style_transfer` |

---

## Presets

```bash
python scripts/generate_viewpoint.py --list-presets
```

| id | Meaning |
|----|---------|
| `eye_level` | Neutral |
| `high_angle` / `birds_eye` | Looking down |
| `low_angle` / `worms_eye` | Looking up |
| `high_qf` / `low_qf` | 3/4 + height |
| `side_low` / `side_high` | Profile + height |
| `wide_establishing` | More environment (distance) |
| `tight_hero` | Close + slight low |
| `ot_s` | OTS-ish |
| `dutch_hint` | Uses **edit** engine (tilt language) |

---

## CLI

```bash
# Named intent
python scripts/generate_viewpoint.py -i still.png --preset low_angle \
  -o out_low.png --seed 42 --strength medium

# Stronger elevation
python scripts/generate_viewpoint.py -i still.png --preset birds_eye \
  -o top.png --strength hard

# Custom ports (multi-angle node)
python scripts/generate_viewpoint.py -i still.png --h 30 --v -40 --zoom 6.5 \
  -o custom.png

# Instruction extreme (no multi-angle ports)
python scripts/generate_viewpoint.py -i still.png --preset worms_eye \
  --engine edit -o extreme.png
```

**Strength:** scales elevation magnitude (+ optional zoom push).  
**Identity lock:** default on for edit path.

---

## Backend

| Engine | Stack |
|--------|--------|
| `angle` (default) | `generate_qwen_angle` → `qwen_multiangle_image` + h/v/zoom |
| `edit` | `generate_qwen_edit` camera instruction |

---

## Smoke

```bash
python scripts/generate_viewpoint.py --list-presets
python scripts/generate_viewpoint.py \
  -i dumps/park_avatar_v1/cand_t2i_s52001.png \
  --preset low_angle -o dumps/park_avatar_v1/viewpoint_low_smoke.png --seed 9
```
