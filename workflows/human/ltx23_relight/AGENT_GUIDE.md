# LTX-2.3 IC-LoRA Relight — agent / human guide

- **LoRA id:** `relight`
- **SSOT:** [docs/ltx_loras_agent.md](../../../docs/ltx_loras_agent.md)
- **HF:** [Lightricks/LTX-2.3-22b-IC-LoRA-Relight](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Relight)
- **Status check:** `python scripts/ltx_lora_status.py`
- **CLI:** `python scripts/generate_ltx_relight.py` (fail-closed until weights + WF ready)

---

## What it is

**Exterior video re-lighting** (V2V finish pass).  
Not I2V quality boost, not dance retarget, not face identity.

Input = finished outdoor clip + **light-direction ball** (top-right) + short caption.  
Output = same content, different sun direction / hardness / magic-hour look.

---

## When / when not

| Use | Skip |
|-----|------|
| Exterior hero clip needs golden hour / side sun / backlight | Interior dialogue / cafe / studio |
| Episode **FINISH** look pass after motion approved | First-pass generation |
| Unify outdoor lighting across shots | Dance choreography / identity fixes → `wan22_animate` / Asian Face |

---

## Install (one-time, human)

1. HF login + model page **Agree and Access**  
2. Weights:

```bash
hf auth login --force
python scripts/ltx_lora_status.py download-relight
# → F:\model\loras\LTX2.3\ltx-2.3-22b-ic-lora-relight-1.0.safetensors
```

3. Official graph from HF repo:  
   `LTX-2.3_Relight_ICLoRA_SingleStage_Distilled.json` → this folder  
4. Custom node: [Sphere-Light-Render](https://github.com/eric-venti-seeds/Sphere-Light-Render-ComfyUI)  
5. Base: LTX-2.3-22B distilled (already in factory model library)

---

## Prompt format (fixed)

```text
relight the video to match the light-direction ball. <look> from <direction>
```

### Looks (12 trained)

```
hard directional sunlight
hard high-angle sunlight
hard low-angle sunlight
soft diffused daylight
soft warm afternoon light
cool soft daylight
dim overcast light
strong backlight with rim light
soft hazy backlight
warm golden low front sun
warm golden low side sun
frontal sunlight
```

### Directions

`the front` · `the front-right` · `the right` · `the back-right` · `behind` · `the back-left` · `the left` · `the front-left`

Do **not** re-describe scene content. Match caption direction to the ball.

---

## Settings

| Knob | Value |
|------|-------|
| LoRA strength | **1.0** |
| Geometry sweet spot | **1280×704 · 121f · 24fps** |
| Pipeline | **single-stage only** (2-stage drops ref/LoRA) |
| Control | ball top-right every frame (~143px @ 22px margin) |

---

## Agent CLI

```bash
python scripts/ltx_lora_status.py
python scripts/generate_ltx_relight.py --list-looks
python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 \
  --look "warm golden low side sun" --direction "the left" --seed 42
```

If status ≠ `ready` → **do not call** generate; ask human for HF gate / login.

---

## Related (do not confuse)

| Tool | Role |
|------|------|
| **asian_face** | LTX I2V Asian face prior (auto ON) — not lighting |
| `generate_wan22_face_enhance` | Face polish post |
| `upscale_video` | Resolution delivery |
| `generate_wan22_animate` | Dance retarget + face lock |
