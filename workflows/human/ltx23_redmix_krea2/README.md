# LTX2.3 REDMix Krea2 I2V

**Civitai:** [579280 · LTX2.3REDMixKrea2](https://civitai.red/models/579280/newkrea2-and-ltx23-and-ideogram-4-wf-in-collection)

I2V-only subgraph workflow (animate stills). Stills often come from Krea2/Ideogram tools separately.

```bash
python scripts/generate_ltx23_redmix_i2v.py --list-backends
python scripts/generate_ltx23_redmix_i2v.py -i still.png -p "natural motion..." -o out.mp4
```

Default: **GGUF distilled** (pack REDGTA int4 not required for smoke).
