# One-shot ref pack — AGENT_GUIDE

> **Toolbox shelf:** TRANSFORM / ASSETS-lite  
> **CLI:** `python scripts/generate_ref_pack.py`  
> **Example:** `python scripts/generate_ref_pack.py -i face.png -o out/pack --profile quick --seed 42`  
> **Alternatives:** one scene only → `character_consistent --mode lock` · angles only → `generate_qwen_angle` · long-term SSOT → `character_full_sheet`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) · [toolbox_card_standard.md](../../../docs/toolbox_card_standard.md)

**Role:** From **one face/portrait**, build a small **identity reference board** without creating `characters/<id>/`.

**Not:** Episode pipeline gate · permanent character package · full costume/turn SSOT.

---

## When / when not

| Use | Skip |
|-----|------|
| Shorts / one video, package overkill | Already have approved `master_front` |
| Need shared `-i` for several lock/i2v/style calls | Single cut: go straight to `character_consistent` |
| Show user a contact board of “this person” | Series multi-episode identity → promote to `characters/` |

---

## Profiles

```bash
python scripts/generate_ref_pack.py --list-profiles
```

| profile | Output (approx) | Comfy |
|---------|-----------------|--------|
| **copy** | `master_face` only | No |
| **quick** | + clean + smile/neutral expr | I2I |
| **default** | quick + `angle_head_left_45` | I2I + angle |
| **full** | + front / L45 / R45 | I2I + angles |

---

## CLI

```bash
# Recommended short jobs
python scripts/generate_ref_pack.py -i face.png -o out/pack --profile quick --seed 42

# Balance: soft + one side angle
python scripts/generate_ref_pack.py -i face.png -o out/pack --profile default

# Full angle board
python scripts/generate_ref_pack.py -i face.png -o out/pack --profile full
```

### Pack contents

| File | Role |
|------|------|
| `master_face.png` | Source copy |
| `master_clean.png` | Soft identity polish (if soft on) |
| `angle_*.png` | Multi-view (if angles on) |
| `expr_*.png` | Expression variants |
| `contact_sheet.png` | Overview |
| **`manifest.json`** | `primary_ref` + file map for agents |
| `ref_pack.meta.json` | Stages / errors |
| `README.md` | Human/agent next steps |

**Downstream:** use `manifest.primary_ref` (usually `master_clean`) as `-i` for:

- `generate_character_consistent --mode lock`
- `generate_i2v` / `--motion-preset`
- `generate_style_transfer`
- `generate_viewpoint`

---

## Smoke

```bash
python scripts/generate_ref_pack.py -i dumps/park_avatar_v1/cand_t2i_s52001.png \
  -o dumps/park_avatar_v1/ref_pack_demo --profile copy
python scripts/generate_ref_pack.py -i dumps/park_avatar_v1/cand_t2i_s52001.png \
  -o dumps/park_avatar_v1/ref_pack_quick --profile quick --seed 11
```
