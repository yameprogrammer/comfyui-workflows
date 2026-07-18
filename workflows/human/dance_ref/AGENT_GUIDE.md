# Dance / reference motion — AGENT_GUIDE

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_dance_ref.py`  
> **Alternatives:** generic V2V → `generate_v2v --intent motion` · text camera only → `generate_camera_move` · idle loop → `generate_idle_loop`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)  
> **Design (full pipe later):** [docs/dance_challenge_pipeline_design.md](../../../docs/dance_challenge_pipeline_design.md)

**Role (v1):** One-shot **character still + optional dance ref video → motion clip**.

**Not:** Full dance-challenge episode factory · beat-locked multi-shot assemble · guaranteed choreography accuracy.

---

## Modes

| mode | Inputs | Backend |
|------|--------|---------|
| **`ref`** (default) | `-i` character still + `-v` dance video | LTX **V2V intent=motion** |
| **`i2v`** | `-i` only + `--style` | I2V with dance dialect (no structure from video) |

```bash
python scripts/generate_dance_ref.py --list-styles
```

---

## CLI

```bash
# Reference-driven (recommended when you have a dance clip)
python scripts/generate_dance_ref.py \
  -i character.png -v dance_ref.mp4 -o out.mp4 \
  --hook-sec 8 --trim-start 0 --seed 42

# Optional music under V2V audio path
python scripts/generate_dance_ref.py -i hero.png -v ref.mp4 -a hook.wav -o out.mp4

# No ref video — text dance energy only
python scripts/generate_dance_ref.py -i hero.png --mode i2v --style kpop -o out.mp4

# Dry-run
python scripts/generate_dance_ref.py -i hero.png -v ref.mp4 -o out.mp4 --dry-run
```

---

## When / when not

| Use | Skip |
|-----|------|
| “Move like this video” with our character face/body still | Dialogue lip — `generate_s2v` |
| Short dance / gesture retarget experiments | Full multi-shot challenge show (use design doc later) |
| Quick K-pop/hip-hop energy without a ref file | Precise beat-perfect commercial dance |

**Copyright:** only use reference videos you have rights to.

---

## Quality expectations

- Hands/feet/beat sync often imperfect — treat as **draft motion**, then QA.  
- Prefer clear full-body character still + clean ref motion.  
- For face consistency first: `generate_ref_pack` / `character_consistent` then dance_ref.

---

## Relation to full challenge pipe

`docs/dance_challenge_pipeline_design.md` describes multi-stage challenge production.  
**This CLI is stage “motion retarget one-shot” only** — not ingest/analyze/assemble.
