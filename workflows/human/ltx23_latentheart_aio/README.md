# LatentHeart LTX2.3 AIO (Director)

**Civitai:** [2553704](https://civitai.red/models/2553704/ltx23-all-in-one-sfw-nsfw-ltx-director-id-lora-controlnet-detailer-upscaler-interpolator)

| File | Role |
|------|------|
| `LTX23LTXDirector2.json` | Director v2 SSOT (default) |
| `LTX23LTXDirector13.json` | Director v1.3 SSOT |
| `AGENT_GUIDE.md` | Purpose · switches · GGUF · CLI |
| `CAPABILITIES.json` | Machine-readable features/profiles |

```bash
python scripts/generate_ltx23_latentheart.py --list-profiles
python scripts/generate_ltx23_latentheart.py -p "..." -o out.mp4 --profile gguf_distilled
```

Agent default: **GGUF Q4** (VRAM). Real UI + group modes only.
