# Image Upscale Dual — Agent Guide

> **Toolbox shelf:** FINISH  
> **Pick first:** `python scripts/upscale_recommend.py --media image --goal …`  
> **CLI:** `python scripts/upscale_image.py` · video → `upscale_video.py`  
> **Alternatives:** fix identity/anatomy first (edit/inpaint) — upscale does not repair bad structure  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.6

**Pack:** still image upscale (photoreal + anime)  
**UI:** `image_upscale_dual.json`  
**CLI:** `python scripts/upscale_image.py`  
**Models:** `F:\model\upscale_models` · `F:\model\SEEDVR2`  
**SSOT:** `upscale_backends.json` · research `docs/upscale_research_and_design.md`

---

## Agent: pick the right upscaler

```bash
# Classify + get copy-paste CLI (no Comfy)
python scripts/upscale_recommend.py --media image --goal delivery --domain photo
python scripts/upscale_recommend.py --media image --goal hero --source blurry
python scripts/upscale_recommend.py --media video --goal batch
python scripts/upscale_recommend.py matrix
python scripts/upscale_recommend.py scenarios
```

| Your job | media | goal | domain | source | Typical pick |
|----------|-------|------|--------|--------|--------------|
| Keyframe batch 1080 | image | batch | photo/anime | normal | `esrgan` + style |
| Poster / hero still | image | hero | photo | normal/blurry | `seedvr2` |
| 4K master still | image | master_4k | photo | normal | `seedvr2_max` |
| Episode clips deliver | video | batch | photo | normal | `esrgan` |
| AI I2V muddy | video | delivery/hero | photo | blurry | `seedvr2` |
| Face smear only | video | face_fix | photo | ai_artifacts | `wan22_face_enhance` then upscale |

---

## When / when not

| When | When not |
|------|----------|
| Keyframe / poster deliver 1080–4K | Fixing bad anatomy (edit first) |
| Photo vs anime model choice matters | Video default deliver → `upscale_video` |
| Hero detail restore (SeedVR2) | Batch of 50+ clips at hero quality |

---

## Lanes

### A · FAST (ESRGAN family)

```text
LoadImage → UpscaleModelLoader → ImageUpscaleWithModel → ImageScale → SaveImage
```

| Style | Model file |
|-------|------------|
| `photo` | `4xRealWebPhoto_v4_dat2.pth` |
| `photo_sharp` | `4x-UltraSharp.pth` |
| `anime` | `4x-AnimeSharp.pth` |
| `anime_fast` | `RealESRGAN_x4plus_anime_6B.pth` |
| `general` | `4x_NMKD-Siax_200k.pth` |

### B · HERO (SeedVR2)

```text
LoadImage → SeedVR2LoadDiT + VAE → SeedVR2VideoUpscaler (batch=1) → SaveImage
```

- Default DiT: `seedvr2_ema_7b_fp8_e4m3fn_mixed_block35_fp16.safetensors`
- `resolution` = **short edge** (1080 / 1440 / 2160)
- Weights: `F:\model\SEEDVR2`

### C · Other (video / experimental)

| Backend | Role |
|---------|------|
| `rtx_vsr` | optional hardware FAST on clean sources |
| `seedvr2_max` | FP16 hero / 4K |
| `wan22_face_enhance` | face refine after I2V (not resolution) |
| `wan22_upscale` | experimental WAN diffusion upscale |

---

## CLI

```bash
# Photoreal keyframe → 1080 short edge (source aspect kept when no --format)
python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080

# Anime / Illustrious still
python scripts/upscale_image.py -i anime.png -o anime_2k.png --style anime --preset deliver_1440

# UltraSharp photo
python scripts/upscale_image.py -i p.png -o p_s.png --style photo_sharp

# Hero SeedVR2 (slow, best open local)
python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080

# Explicit size
python scripts/upscale_image.py -i key.png -o key_out.png --style photo --width 1664 --height 2432

# Video
python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080
python scripts/upscale_video.py -i work.mp4 -o d4k.mp4 --backend seedvr2 --preset deliver_2160 --two-pass
```

---

## Policy (4090)

| Priority | Backend | Notes |
|----------|---------|-------|
| Default still FAST | `esrgan` + style | seconds |
| Hardware fast (if node present) | `rtx_vsr` | clean sources |
| Hero | `seedvr2` | minutes; opt-in |
| Hero max | `seedvr2_max` | FP16 7B |

Do **not** use upscale to fix hands/identity — QA/edit first.

---

## Research snapshot (2025–2026)

- **Comfy Handbook:** SeedVR2 = strong conservative open quality; work → 1080 → optional 4K.
- **Reddit:** SeedVR2 often preferred vs SUPIR for reliability/speed; SUPIR still creative restore king.
- **Anime:** 4x-AnimeSharp (Kim2091) community standard for linework; anime_6B for lighter/faster.
- **Photo:** UltraSharp / RealWebPhoto / RealESRGAN_x4plus depending on skin vs web photo bias.
