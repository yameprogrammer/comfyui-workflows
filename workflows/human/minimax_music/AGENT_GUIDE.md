# MiniMax Music 3 — Agent Guide

> **Official Backend:** `Comfy-Org/MiniMax-Music-3` (DiT + Qwen3-VL/Llama-based Text Encoder + DAV Audio VAE)  
> **Shelf:** VOICE / BGM  
> **Specialty:** Full-length, high-fidelity (32kHz stereo) song and instrumental BGM generation up to 5 minutes (300s).

---

## 1. When to use

| Goal | Tool / Mode | When NOT to use |
|------|-------------|-----------------|
| **Full Vocal Song (Verse/Chorus)** | `01_MiniMax_Music3_Text2Song_Full_Production.json` | Simple short speech TTS (use `generate_qwen3_tts`) |
| **Instrumental BGM / Soundtrack** | `02_MiniMax_Music3_BGM_Instrumental.json` | Fast sound effects / foley |

---

## 2. Caption & Lyrics Syntax Rules

### A. Caption 3-Part Structure
1. **Global Metadata**: Genre (K-Pop, Rock, EDM, Lo-fi, Cinematic), BPM (e.g. 120 BPM), Musical Key (e.g. C Major), overall emotional mood.
2. **Vocal Details**: Vocal gender/tone (Female/Male, Bright/Breathy/Belting), vocal layers, backing harmonies (or `Instrumental only, no vocals`).
3. **Arrangement**: Instrument breakdown (Drums, Bass, Piano, Electric Guitar, Synth pads) and sectional progression.

### B. Lyrics Section Tags
MiniMax Music 3 only understands structural changes via explicit section tags:
- `[Intro]`
- `[Verse 1]`, `[Verse 2]`
- `[Pre-Chorus]`
- `[Chorus]`
- `[Bridge]`
- `[Instrumental]` (solo instrument or break)
- `[Outro]`

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
