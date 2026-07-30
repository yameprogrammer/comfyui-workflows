# OpenPose + ControlNet — Agent Guide

> **One-stop CLI:** `python scripts/generate_openpose_pose.py`  
> **Backend:** Z-Image Fun Union ControlNet (**Pose** condition)  
> **Not Qwen:** Qwen Edit / multi-angle are text/instruction tools — they do **not** consume OpenPose stick maps.

---

## When to use

| Goal | Tool |
|------|------|
| Lock **limb angles** (walk cycle keys, combat stance, sit) | **This guide** (OpenPose → ControlNet) |
| Keep face + change scene loosely | `generate_character_consistent --mode lock` |
| Turn camera / multi-view of same person | `generate_qwen_angle` / `character_consistent --mode angle` |
| Freeform text edit of an existing still | `generate_qwen_edit` |
| Animate after pose is correct | green plate → `generate_i2v` / FLF (see project chroma lessons) |

**Rule:** Fix **pose on a still** with OpenPose ControlNet **before** I2V. Do not hope I2V will invent a clean gait.

---

## Pipeline

```text
① OpenPose RGB map
     - extract from photo/still, OR
     - synthetic template (walk_side, jog_contact, …)
② ControlNet generate (empty latent + Pose condition)
     - optional identity ref via character_consistency pose mode
③ QA stick vs output limbs
④ (game) solid green BG if needed → I2V for motion
```

---

## CLI

```bash
cd F:/ComfyUI_workflows/agent_custom   # or your agent_custom root

# List / materialize templates
python scripts/generate_openpose_pose.py list-templates
python scripts/generate_openpose_pose.py ensure-templates

# A) Extract skeleton from an existing still (photo or green plate)
python scripts/generate_openpose_pose.py extract \
  -i path/to/character.png \
  -o path/to/pose_map.png

# B) Generate from template + identity
python scripts/generate_openpose_pose.py generate \
  -i path/to/identity_ref.png \
  --template jog_contact \
  -p "same young office man, navy suit, briefcase, cel-shaded anime, solid chroma green screen" \
  -o out_jog_contact.png \
  --strength 0.85 --width 768 --height 1280

# C) Generate from extracted/custom map
python scripts/generate_openpose_pose.py generate \
  -i path/to/identity_ref.png \
  --control path/to/pose_map.png \
  -p "..." -o out.png --strength 0.9
```

### Equivalent low-level CLIs (already existed)

```bash
# ControlNet only
python scripts/generate_moody_controlnet.py \
  --control pose_map.png -p "..." -o out.png \
  --control-preprocess openpose --strength 0.85 --empty-latent

# Identity wrapper
python scripts/generate_character_consistent.py --mode pose \
  -i identity.png --control pose_map.png -p "..." -o out.png --strength 0.85
```

---

## Built-in templates

| ID | Use |
|----|-----|
| `walk_side` | Side walk / light step |
| `jog_contact` | Jog: front plant, rear trail |
| `jog_recoil` | Jog: weight absorb, rear knee up |
| `jog_pass` | Jog: feet under body |
| `jog_high` | Jog: long stride, rear high |
| `stand_side` / `stand_front` / … | Sheets & idle |

Maps live under `characters/pose_templates/openpose/`.

**Jog key order (loop):**  
`jog_contact → jog_recoil → jog_pass → jog_high → jog_contact`

---

## Qwen vs OpenPose (do not confuse)

| | OpenPose ControlNet | Qwen Edit / Angle |
|--|---------------------|-------------------|
| Input | Stick-figure **pose map** | Text instruction (+ image) |
| Strength | Limb geometry | Semantic edit / view |
| Good for | Run cycle keys, combat stance | “Look left”, wardrobe text edit |
| Bad for | Freeform “make him run better” without a map | Pixel-accurate foot phase |

There is **no** “Qwen OpenPose” node path in this toolbox. “Qwen + pose” in chat usually means: **use Qwen for face/view, ControlNet OpenPose for body**.

---

## Game project tip (gate_leave_work)

1. Build 4–8 **still** jog keys with `generate_openpose_pose.py` + green BG prompt.  
2. Optional: short FLF only between **adjacent** keys (small pose delta).  
3. Green key → `AnimatedSprite2D`.  
4. Do **not** sparse-sample a long messy I2V for foot phase.

See also: gate_leave_work `docs/SPRITE_CHROMA_I2V_LESSONS.md`.

---

## Failure notes

- Control image is a photo, not an OpenPose map → preprocess may treat as Canny; use `--control-preprocess openpose` or extract first.  
- Strength too low → limbs ignore map; try 0.8–1.0.  
- Strength too high + empty latent → stiff / broken anatomy; ease to 0.75–0.85 and improve prompt.  
- Identity drift → pass `-i` identity still + `character_consistency` pose path (default in `generate` subcommand).
