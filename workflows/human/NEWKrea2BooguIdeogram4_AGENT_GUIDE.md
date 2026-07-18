# Boogu + Ideogram4 + Krea2 — typography / design pipeline

> **Toolbox shelf:** GENERATE (typography / poster)  
> **CLI:** `python scripts/generate_boogu_typo.py`  
> **Alternatives:** light title only → `generate_ideogram4` · plain still without dense text → moody/krea  
> **Catalog:** [docs/tool_catalog.md](../../docs/tool_catalog.md) §2.1

**UI SSOT:** `workflows/human/NEWKrea2BooguIdeogram4_booguKrea2.json`  
**Civitai:** [NEW Krea2 & LTX2.3 & ideogram 4 WF — Boogu+Krea2 / Boogu+Ideogram4](https://civitai.red/models/579280/newkrea2-and-ltx23-and-ideogram-4-wf-in-collection?modelVersionId=3066747)  
**CLI:** `scripts/generate_boogu_typo.py` · runner `lib/boogu_ideogram_krea_runner.py`

## What it is

A **combined design poster pipeline** (not general T2I replacement):

| Stage | Engine | Strength |
|-------|--------|----------|
| 1 | **Boogu-Image** base + turbo LoRA | Dense CN/EN text, content fidelity |
| 2 | **Ideogram 4** | Typography / layout polish (structured caption) |
| 3 | **Krea2** (Moody mix FP8) | Photoreal polish (partial denoise) |
| 4 | SeedVR2 (optional) | Upscale — heavy VRAM |

Pack also has **Gemini** (image/NL → Ideogram JSON). Agent path **skips Gemini** and injects your caption into all stages.

## When to pick this tool

| Use | Don’t use for |
|-----|----------------|
| Title cards, posters, ads with **readable type** | Simple character keyframes (use Moody) |
| Dense multi-line text on image | Region inpaint only (use InstantX) |
| Design layout + photoreal finish | Pure Ideogram-only (lighter: `generate_ideogram4`) |

## CLI

```bash
# Full chain → download Krea2 stage (default)
python scripts/generate_boogu_typo.py \
  -p "Luxury villa courtyard poster, elegant serif title VILLA AURELIA, minimal layout, cream and sage" \
  -o out.png --mode pipeline --prefer krea2 --seed 42

# Boogu draft only (fast text check)
python scripts/generate_boogu_typo.py --mode boogu -p "..." -o draft.png --prefer boogu

# + SeedVR2 (VRAM heavy)
python scripts/generate_boogu_typo.py --mode upscale -p "..." -o hi.png --prefer seedvr2

# Structured Ideogram-style JSON caption (best for layout control)
python scripts/generate_boogu_typo.py --prompt-file caption.json -o out.png

# Dry-run
python scripts/generate_boogu_typo.py -p "test" --dry-run
```

| Flag | Meaning |
|------|---------|
| `--mode boogu` | Stage 1 only |
| `--mode pipeline` | Boogu → Ideogram → Krea2 (default) |
| `--mode upscale` | + SeedVR2 |
| `--prefer` | Which SaveImage to save as `-o` |
| `--width/--height` | Boogu EmptyLatent (+ Ideogram size hints) |

## Models (this machine)

| Role | Path (under `models/`) |
|------|-------------------------|
| Boogu | `diffusion_models/boogu_image_base_bf16.safetensors` (or folder `boogu\`) |
| Boogu turbo LoRA | `loras/Boogu/boogu_image_turbo_lora_rank_128_bf16.safetensors` |
| Ideogram4 | `diffusion_models/Ideogram4/ideogram4_*_fp8_scaled.safetensors` |
| Krea2 | `diffusion_models/Krea2Turbo/moodyKrea2Mix_v40NonComfyFP8.safetensors` |
| CLIP | `qwen3vl_8b` (boogu/ideo) · `qwen3vl_4b` type krea2 |
| VAE | `ae.safetensors` · `flux2-vae` · `qwen_image_vae` |
| SeedVR2 | `SEEDVR2/seedvr2_ema_7b_fp8_...` (upscale mode) |

## Relation to `generate_ideogram4`

| | `generate_ideogram4` | `generate_boogu_typo` |
|--|---------------------|----------------------|
| Focus | Pure Ideogram4 T2I + caption schema helpers | Multi-engine **chain** from pack WF |
| Text | Slot recipes / JSON builder | One caption into all stages |
| Polish | Optional | Krea2 + optional SeedVR2 |

Use Ideogram4 alone for lightweight title cards; use **boogu_typo** when you want Boogu text density + Krea finish.

## License notes

- Ideogram Non-Commercial Agreement may apply to Ideogram weights.
- Krea2 / Boogu models: check each model card before commercial use.
