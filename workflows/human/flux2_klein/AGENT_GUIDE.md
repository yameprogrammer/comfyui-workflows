# Flux.2 Klein 9B — agent guide

Local **Flux.2 Klein 9B Q4** T2I and denoise I2I.  
Official Klein **edit** weights are **not** installed — do not treat this as `generate_qwen_edit`.

## When

| Mode | When | When not |
|------|------|----------|
| `--mode t2i` | Fast Flux2 Klein still | Cinematic default → `generate_krea` · type → Ideogram |
| `--mode i2i` | Pixel denoise restyle (`--denoise`) | Instruction edit → `generate_qwen_edit` |

## CLI

```bash
python scripts/generate_flux2_klein.py --mode t2i -p "vintage motorcycle at a diner sunset" -o "%AGENT_WORKSPACE%/stills/klein.png"
python scripts/generate_flux2_klein.py --mode i2i -i still.png -p "overcast coastal cliff" --denoise 0.55 -o "%AGENT_WORKSPACE%/stills/klein_i2i.png"
python scripts/generate_flux2_klein.py --check-models
```

T2I uses `EmptyFlux2LatentImage` + `Flux2Scheduler` + CFG 5.  
I2I uses `VAEEncode` + `KSampler` so `--denoise` is real.

## Weights (`F:\model`)

| Role | File |
|------|------|
| UNet | `diffusion_models/Flux2/flux-2-klein-9b-Q4_K_M.gguf` |
| CLIP | `text_encoders/qwen_3_8b_fp8mixed.safetensors` (`type=flux2`) |
| VAE | `vae/flux2-vae.safetensors` |

Dialect: `skills/generation-prompt/references/flux_still.md`.  
Engine family: `flux2_klein`.
