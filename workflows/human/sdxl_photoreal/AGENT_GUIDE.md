# SDXL photoreal — agent guide

Classic **SDXL checkpoints** already on disk.  
**Not** Illustrious/NoobAI (`generate_illustrious_*`). **Not** cinematic default (`generate_krea`).

## Profiles

| `--model` | Checkpoint | Steps | When |
|-----------|------------|-------|------|
| `juggernaut` (default) | `SDXL\juggernautXL_ragnarokBy` | 28 / CFG 5 | Classic photoreal XL |
| `lightning` | `SDXL\dreamshaperXL_lightningDPMSDE` | 6 / CFG 2 | Fast scout |
| `pony` | `SDXL\gonzalomoXLFluxPony_v60PhotoXLDMD` | 25 / CFG 6 | Pony score tags |
| `nsfw` | `SDXL\pornmaster_proSDXLV8` | 28 / CFG 5 | SDXL NSFW **look** — default 18+ is still `generate_krea_nsfw` |

```bash
python scripts/generate_sdxl.py --list-profiles
python scripts/generate_sdxl.py -m juggernaut -p "cinematic portrait, window light" -o "%AGENT_WORKSPACE%/stills/sdxl.png"
python scripts/generate_sdxl.py -m lightning -p "street fashion full body" -o "%AGENT_WORKSPACE%/stills/scout.png"
```

Do **not** pass these ckpts into `generate_illustrious_* --ckpt`.

Dialect: `skills/generation-prompt/references/sdxl_still.md`.  
Engine family: `sdxl_still`.
