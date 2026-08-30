# MiniMax Music 3 — Agent Guide

> **Official Backend:** `Comfy-Org/MiniMax-Music-3` (DiT + MiniMax text encoder + DAV Audio VAE)  
> **Shelf:** VOICE / BGM  
> **Specialty:** Full-length, 32 kHz stereo song and instrumental BGM, up to 5 minutes (300s).  
> **License:** MiniMax-Music3 Community License (not Apache 2.0). Commercial use allowed under the community revenue cap; see the Hugging Face license.

---

## 1. When to use

| Goal | Tool / Mode | When NOT to use |
|------|-------------|-----------------|
| **Full Vocal Song (Verse/Chorus)** | `generate_minimax_music` (`01_…Text2Song…json`) | Simple short speech TTS → `generate_qwen3_tts` |
| **Instrumental BGM / Soundtrack** | `--mode bgm` (`02_…BGM_Instrumental.json`) | Fast SFX / foley → `generate_stable_audio` |

---

## 2. Caption & Lyrics

Dialect: `skills/generation-prompt/references/music_audio.md`.

### A. Caption — three headings (English)

1. **Global Metadata**: genre, BPM (range OK), key if useful, emotional arc, mix/production.
2. **Vocal Details**: gender/timbre/delivery/harmonies, or `Instrumental only, no vocals`.
3. **Arrangement**: section-by-section instrument entries and exits, not a static gear list.

Do not put lyric lines in the caption. Expand a one-line brief to this form before a production take.

### B. Lyrics section tags

Tags are the only executable structure. Put them on their own lines:

`[Intro]` `[Verse]` `[Verse 1]` `[Pre-Chorus]` `[Chorus]` `[Post-Chorus]` `[Bridge]` `[Instrumental]` `[Solo]` `[Outro]`

Korean (or other) lyric text is fine under the tags.

---

## 3. Required Models (`Comfy-Org/MiniMax-Music-3`)

```
ComfyUI/models/
├── diffusion_models/
│   └── minimax_music3_dit_fp16.safetensors (or minimax_music3_dit_int8_convrot.safetensors)
├── text_encoders/
│   └── minimax_music3_text_encoder_pruned_int8_convrot.safetensors
└── vae/
    └── minimax_music3_dav.safetensors
```

Default factory stack: **fp16 DiT + pruned int8 text encoder + DAV**.

---

## 4. Knobs (official template)

| Knob | Factory default | Notes |
|------|-----------------|--------|
| `--duration` | song **180s**, BGM **60s** | **Ceiling**, not exact length. Max 300s. Raise if tagged form is longer. |
| `--steps` | **30** | Do not copy image-sampler 35. |
| `--cfg` | **1.7** | KSampler and TextEncode both 1.7. Image CFG 4.0 is wrong here. |
| sampler / scheduler | euler / simple | Keep. |
| `--tiled-decode` | auto **on at ≥ 240s** | `VAEDecodeAudioTiled` tile 1536 / overlap 64. 4090 3-min: leave off (`--no-tiled-decode` if you forced a long cap). |

```powershell
python scripts/generate_minimax_music.py --caption-file cap.txt --lyrics-file lyr.txt -o song.flac
python scripts/generate_minimax_music.py --mode bgm --caption "..." --duration 120 -o bed.flac
python scripts/generate_minimax_music.py --caption-file cap.txt --lyrics-file lyr.txt --duration 300 --tiled-decode -o long.flac
```
