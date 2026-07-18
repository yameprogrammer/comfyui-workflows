# Character Consistency — AGENT_GUIDE

> **Toolbox shelf:** TRANSFORM (also CAMERA via `--mode angle|pose`)  
> **CLI:** `python scripts/generate_character_consistent.py`  
> **Alternatives:** no-ID mood still → `generate_moody` · full cast package → `character_full_sheet` · mask-only → `generate_qwen_inpaint` · angle-only → `generate_qwen_angle`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.2

**Role:** Keep the **same person** across stills (scenes, expressions, wardrobe, angles).  
**Research:** [docs/character_consistency_research.md](../../../docs/character_consistency_research.md)  
**Not:** full cast package A→B→C (use `character_full_sheet` for that).

---

## When to use

| Use this tool | Use something else |
|---------------|--------------------|
| You have a **face/body ref** and need more shots of **that person** | Pure mood still with no ID → `generate_moody` |
| Quick identity pack (expr/wardrobe/scene board) | Full L2 sheet → `character_full_sheet` |
| Same face, new action/location still | Mask torso only → `generate_qwen_inpaint` |
| Strong camera angle change | `generate_qwen_angle` directly (or `--mode angle`) |

---

## Modes (research → factory)

| Mode | What | Backend | Denoise default / cap |
|------|------|---------|------------------------|
| **`lock`** | Default identity scene | Lonecat `i2i_lock` | 0.52 / 0.58 |
| **`soft`** | Micro (expression, light) | same | 0.45 / 0.58 |
| **`remix`** | Stronger wardrobe/scene | same | 0.62 / 0.72 |
| **`anchor`** | Create master face (no ref) | Lonecat T2I | — |
| **`pack`** | Mini board + contact sheet | repeated lock | per-variant |
| **`angle`** | Multi-view | Qwen multi-angle | — |
| **`pose`** | Pose from control image | Fun Union ControlNet | 0.70 / 0.85 |

```bash
python scripts/generate_character_consistent.py --print-policy
```

---

## CLI recipes

### 1) Same person, new scene (mainline)

```bash
python scripts/generate_character_consistent.py --mode lock \
  -i path/to/master_face.png \
  -p "sitting in a sunlit cafe, medium shot, holding ceramic cup, soft smile" \
  -o out/scene_cafe.png --seed 42 -m pro
```

**Prompt rule:** describe **what changes** (pose, place, clothes, light). Do **not** re-essay the whole face.

### 2) Soft expression tweak

```bash
python scripts/generate_character_consistent.py --mode soft \
  -i master_face.png -p "gentle closed-mouth smile, eye contact" \
  -o out/smile.png -d 0.46
```

### 3) Stronger environment change

```bash
python scripts/generate_character_consistent.py --mode remix \
  -i master_face.png \
  -p "walking rainy neon street at night, medium full shot, wet asphalt reflections" \
  -o out/rain.png
```

### 4) No ref yet → lockable anchor

```bash
python scripts/generate_character_consistent.py --mode anchor \
  -p "Korean woman mid-20s, oval face, soft jaw, warm brown eyes, shoulder-length dark wavy hair, natural skin, cinematic head-and-shoulders" \
  -o out/anchor.png --seed 1001 --width 1024 --height 1024
# then use out/anchor.png as -i for lock/pack
```

### 5) Mini consistency pack (Mickmumpitz-style lite)

```bash
python scripts/generate_character_consistent.py --mode pack \
  -i master_face.png --pack-dir out/id_pack --seed 42 -m pro
# → expr_* , ward_* , scene_* , contact_sheet.png , pack.meta.json
```

### 6) Angle / pose

```bash
python scripts/generate_character_consistent.py --mode angle \
  -i master_face.png --view head_left_45 -o out/left45.png

python scripts/generate_character_consistent.py --mode pose \
  -i master_face.png --control pose_or_openpose.png \
  -p "same person in that pose, street clothes, daylight" \
  -o out/posed.png --strength 0.75
```

### Optional bible core

```bash
python scripts/generate_character_consistent.py --mode lock \
  -i master_face.png --core-prefix-file characters/X/prompts/core.txt \
  -p "running through rain" -o out/run.png
```

---

## Identity policy (do / don’t)

| Do | Don’t |
|----|--------|
| One approved master face | New pure T2I every shot |
| Fixed seed when comparing variants | denoise ≥ 0.75 on face without angle/CN |
| Change-only I2I prompts | Tag-soup face re-description on I2I |
| `pack` then pick winners | Mass-approve without opening files |
| Promote winners into `characters/<id>/` | Leave only dumps as SSOT |

---

## Relation to cast pipeline

```text
ad-hoc consistency (this tool)
        ↓ promote best face
characters/<id>/ + character_full_sheet  (package SSOT)
        ↓
shot_compose / episode keyframes
```

---

## Smoke

```bash
# Comfy :8188
python scripts/generate_character_consistent.py --mode lock \
  -i dumps/park_avatar_v1/cand_t2i_s52001.png \
  -p "soft smile navy blazer studio portrait" \
  -o dumps/park_avatar_v1/cc_lock_smoke.png --seed 7 --timeout 300
```

---

## Credits (techniques, not code)

Community patterns from Mickmumpitz ComfyUI character sheets, ThinkDiffusion Flux sheet guides, Stable Diffusion Art identity ladder, and this factory’s Lonecat I2I denoise policy. Implementation uses **our** validated API presets only.
