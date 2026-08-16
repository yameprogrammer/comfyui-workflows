# Flux.1 — agent guide

Local **Flux.1 Dev Q4** T2I and **Flux.1 Fill** mask inpaint.  
These are **not** the cinematic default (`generate_krea`) and **not** Qwen InstantX.

## When

| CLI | When | When not |
|-----|------|----------|
| `generate_flux` | Flux look, prompt-following, illustration / general T2I | Krea keyframes · Ideogram type · Illustrious/Anima tags |
| `generate_flux_fill` | Photoreal/general **mask** inpaint (white = edit) | No mask → `generate_qwen_edit` · Qwen look → `generate_qwen_inpaint` · anime → `generate_anima --mode inpaint` |

## CLI

```bash
python scripts/generate_flux.py -p "a red bicycle in a rainy alley" -o "%AGENT_WORKSPACE%/stills/flux.png" --seed 42
python scripts/generate_flux.py --check-models

python scripts/generate_flux_fill.py -i still.png --mask hole.png -p "keep the cup, no straw" -o "%AGENT_WORKSPACE%/stills/fill.png"
```

Defaults: 1024² · 20 steps · guidance 3.5 · euler/simple · CFG 1.

## Weights (`F:\model`)

| Role | File |
|------|------|
| T2I unet | `diffusion_models/Flux1/flux1-dev-Q4_K_S.gguf` |
| Fill unet | `diffusion_models/Flux1/flux1-fill-dev-Q4_K_S.gguf` |
| CLIP | `text_encoders/clip_l.safetensors` + `t5xxl_fp16.safetensors` |
| VAE | `vae/ae.safetensors` (fallback `vae-flux1-dev.safetensors`) |

## Prompt dialect

Natural English paragraph. No Danbooru soup, no Krea 140-word keyframe essay required.  
See `skills/generation-prompt/references/flux_still.md`.

Engine family: `flux1` (VRAM free on switch away from Krea/Z-Image/LTX).
