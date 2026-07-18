# LTX 2.3 All-In-One v44 — Agent feature selection

> **Toolbox shelf:** MOTION  
> **CLI:** `generate_i2v` · `generate_s2v` · `generate_flf2v` · `run_ltx_aio_features.py --list`  
> **Alternatives:** fast experiment → wan22 / `generate_yaw_wan22` · talking lip hero → `generate_s2v --backend infinitetalk` · adult → `generate_ltx_nsfw_i2v`  
> **Catalog:** [docs/tool_catalog.md](../../docs/tool_catalog.md) §2.4

Source UI: `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json`

This AIO is **not** a single linear graph. Agents pick a **Select options** combination
(via `[[P:]]` mute table) then inject ports. Implementation: `ltx_aio_mode_select` + `ltx_aio_workflow_runner`.

## How to choose

1. Decide mode: T2V / I2V / FLF / FML / V2V (± Audio)
2. Pick **quality tier** (`--ltx-profile`): `draft` | `work` (default) | `hero`
3. Call `generate_s2v` / `generate_i2v` with matching `--backend ltx23_aio_*` **or** `--ltx-mode <mode>`
4. Pass required media: `-i` / `--last` / `--mid` / `-a` / `--video`
5. Do **not** build mini graphs; do **not** rename `[[P:]]` tags

List features / profiles:
```bash
python scripts/run_ltx_aio_features.py --list
python scripts/generate_s2v.py --list-ltx-profiles
```

### Quality profiles (why YouTube ≠ agent default)

| Profile | Long edge | Face detailer | Max pure I2V | When |
|---------|-----------|---------------|--------------|------|
| `draft` | ~960 (~540p) | 0.5 | ~3s | 러프·초고속 |
| **`work`** | **~1280 (720p)** | 0.55 | ~5s | **기본 배치·에피 (2026-07-18)** |
| `hero` | **~1920 (~1080 work)** | 0.65 | ~4s | 히어로 1컷 · 더 무거움 |

Research + backlog: [docs/ltx23_quality_research_and_improvement.md](../../docs/ltx23_quality_research_and_improvement.md)  
Face melt: [docs/ltx_face_stability.md](../../docs/ltx_face_stability.md)

```bash
# Work (default practical)
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow push in" --ltx-profile work

# Hero (slower, higher gen res — not batch default)
python scripts/generate_i2v.py -i key.png -o hero.mp4 -p "gentle head turn, eyes hold lens" \
  --ltx-profile hero --frames 73
```

**Hard rules:** short clips for faces · motion-only prompts · fix still before I2V · lips CU → InfiniteTalk.

### Default models + LoRA tune (2026-07-18)

| Slot | File / setting |
|------|----------------|
| **UNET** | `diffusion_models/LTX2.3/ltx-2.3-22b-dev-Q6_K.gguf` |
| **Pipeline** | **2-stage already ON** (stage1 → spatial x2 → stage2) |
| Distill fro09 | **@ 0.7** (work; was 0.9 UI / 0.6 hard face) |
| Detailer IC-LoRA | **ON @ 0.55** (work) · hero 0.62 |
| Upscale IC-LoRA | **ON @ 0.45** (supports 2-stage; env can OFF) |
| OmniNFT | **@ 0.45** |
| TE / VAE | Gemma3 + projection · LTX23 video/audio VAE |

```bash
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow push in" --ltx-profile work
# stronger face/detail
python scripts/generate_i2v.py -i key.png -o h.mp4 -p "..." --ltx-profile hero --frames 73
```

Legacy Q4 on disk: `ltx-2.3-22b-dev-Q4_K_M.gguf`.

## Select options → agent mode

| Feature | Mode | Select options (ON) | Backend | Required inputs |
|---------|------|---------------------|---------|-----------------|
| Text to Video | `t2v` | `01 Text to Video` | `ltx23_aio_t2v` | prompt |
| Text + Audio to Video | `t2v_audio` | `01 Text to Video`, `Audio input` | `ltx23_aio_t2v_audio` | prompt, audio |
| Image to Video | `i2v` | `02 Image to Video` | `ltx23_aio_i2v` | image, prompt |
| Image + Audio to Video (SI2V default) | `i2v_audio` | `02 Image to Video`, `Audio input` | `ltx23_aio` | image, audio, prompt |
| First/Last Frame | `flf` | `02 Image to Video`, `Last Frame input` | `ltx23_aio_flf` | image, last_image, prompt |
| First/Last + Audio | `flf_audio` | `02 Image to Video`, `Audio input`, `Last Frame input` | `ltx23_aio_flf_audio` | image, last_image, audio, prompt |
| First/Mid/Last Frame | `fml` | `02 Image to Video`, `Last Frame input`, `Mid Frame input` | `ltx23_aio_fml` | image, mid_image, last_image, prompt |
| First/Mid/Last + Audio | `fml_audio` | `02 Image to Video`, `Audio input`, `Last Frame input`, `Mid Frame input` | `ltx23_aio_fml_audio` | image, mid_image, last_image, audio, prompt |
| Video to Video | `v2v` | `03 Video to Video` | `ltx23_aio_v2v` | image_or_ref, video, prompt |
| Video to Video + Audio | `v2v_audio` | `03 Video to Video`, `Audio input` | `ltx23_aio_v2v_audio` | image_or_ref, video, audio, prompt |

## CLI examples

```bash
# Pure I2V (no audio)
python scripts/generate_s2v.py --backend ltx23_aio_i2v -i first.png --prompt '...'

# Image + Audio SI2V (default s2v)
python scripts/generate_s2v.py --backend ltx23_aio -i first.png -a drive.wav --prompt '...'

# First/Last frame
python scripts/generate_s2v.py --backend ltx23_aio_flf -i first.png --last last.png --prompt '...'

# Explicit mode flag (same runner)
python scripts/generate_s2v.py --backend ltx23_aio --ltx-mode flf_audio -i f.png --last l.png -a a.wav
```

## [[P:]] port inventory (scanned)

- `03 Video to Video` — 20 tagged nodes
- `02 Image to Video` — 11 tagged nodes
- `01 Text to Video` — 6 tagged nodes
- `Last Frame input` — 5 tagged nodes
- `Mid Frame input` — 4 tagged nodes
- `Audio input` — 4 tagged nodes

## Secondary switches (scanned)

These are additional Comfy switch/orchestrator nodes. Mode path uses **[[P:]] mute** as SSOT;
secondary switches are applied by the expanded AIO graph / runner inject where needed.

- id `923` `Note` — Select Options (root)
- id `1353` `OrchestratorNodeMuter` — Select options (see Table above) (root)
- id `1110` `Sampler Selector (Image Saver)` — (no title) (root)
- id `1801` `ComfySwitchNode` — (no title) (root)
- id `211` `Power Lora Loader (rgthree)` — (no title) (root)
- id `1798` `ComfySwitchNode` — (no title) (root)
- id `1072` `FinalFrameSelector` — (no title) (New Subgraph)
- id `1549` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1360` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1748` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1329` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1382` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1541` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1056` `KSamplerSelect` — (no title) (New Subgraph)
- id `1373` `Any Switch (rgthree)` — (no title) (New Subgraph)
- id `1771` `Any Switch (rgthree)` — (no title) (New Subgraph)

## Machine-readable

- `workflows/human/LTX23_AIO_v44_CAPABILITIES.json`
- `workflows/agent/presets/ltx23_aio_feature_presets.json`
- `workflows/agent/ltx23_aio.manifest.json`

Rescan: `python scripts/_analyze_ltx23_aio_features.py`

