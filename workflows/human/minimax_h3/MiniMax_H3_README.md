# MiniMax H3 Workflows (Seedance-class local video + audio)

Official ComfyUI native templates adapted for this install, plus **Audio-to-Video** workflows from Deno’s tutorial ([youtu.be/puBAu9qt5qM](https://youtu.be/puBAu9qt5qM)).

## Status (local install)

- ComfyUI restarted with Deno custom nodes: **registered**
- gemma4_e4b_it_fp8_scaled.safetensors: **installed** under `F:\model\text_encoders\`
- Local LLM: Ollama detected (gemma4 models available) — Full A2V defaults to Ollama

## Requirements

- ComfyUI **≥ 0.30.0** (this install: **0.30.0**)
- Models under `F:\model` via `extra_model_paths.yaml`

## Model check

| Role | File | Size | Status |
|------|------|------|--------|
| Diffusion T2V/I2V | `diffusion_models/MinimaxH3/minimax_h3_fl2va_pruned_int8_convrot.safetensors` | ~19.5 GiB | OK |
| Diffusion R2V / A2V | `diffusion_models/MinimaxH3/minimax_h3_ref2va_pruned_int8_convrot.safetensors` | ~19.5 GiB | OK |
| Text encoder | `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | ~14.6 GiB | OK |
| Video VAE | `vae/minimax_h3_video_vae_fp16.safetensors` | ~4.85 GiB | OK |
| Audio VAE | `vae/minimax_h3_audio_vae_fp32.safetensors` | ~0.56 GiB | OK |

Optional extras for full Deno A2V auto-prompt lane:

| Role | File | Notes |
|------|------|--------|
| Acoustic analysis CLIP | `text_encoders/gemma4_e4b_it_fp8_scaled.safetensors` (~8.4 GiB) | **OK** ([Comfy-Org/gemma-4](https://huggingface.co/Comfy-Org/gemma-4)) |
| Local prompt LLM | Ollama `gemma4:12b-it-qat` (or LM Studio) | **Ollama available** on this machine |
| Whisper | auto via `openai-whisper` | First run downloads checkpoint to `models/stt/whisper/` |

## Workflows

### Core (stock nodes)

| File | Mode | Notes |
|------|------|--------|
| `MiniMax_H3_T2V_TextToVideo.json` | Text → video+audio | `fl2va` weights |
| `MiniMax_H3_I2V_ImageToVideo.json` | First/last frame → video+audio | `fl2va` |
| `MiniMax_H3_R2V_ReferenceToVideo.json` | Multi-ref image/video/audio → video+audio | `ref2va` |

### Audio-to-Video (Deno mux — **not official MiniMax**)

H3 official speak = I2V/T2V above (`<d>[Korean]`, keep `VAEDecodeAudio`). Timbre = official R2V `ref_audios`, still H3 audio.  
These two graphs **throw away H3 audio** and mux the loaded wav. Looks synced when lucky. Do not use for host talking-head.

| File | Mode | Dependencies |
|------|------|----------------|
| **`MiniMax_H3_A2V_Simple.json`** | Deno: generate mouth, **mux original audio** | Stock nodes only |
| **`MiniMax_H3_A2V_AudioToVideo.json`** | Same mux + Whisper + Gemma + local LLM | `deno-custom-nodes`, VHS, gemma4, Ollama optional |

### Multi-ref anime R2V + post-polish ([s7JDBLfTGKI](https://youtu.be/s7JDBLfTGKI))

| File | Mode | Dependencies |
|------|------|----------------|
| **`MiniMax_H3_R2V_MultiRef_Deno.json`** | Multi-image Reference-to-Video (one-cable Deno loader, up to 9 pics) | `deno-custom-nodes` |
| **`MiniMax_H3_PostPolish_Upscale60fps.json`** | H3 MP4 → RTX VSR/Deblur → RIFE ×2 (24→**48**fps) → remux | Deno RTX VFX (optional), Frame-Interpolation RIFE |
| `MiniMax_LTX_Spatial_Full_Upscale.json` | Alternative generative upscale via LTX 2.3 | LTX nodes + models |

Also kept as official template copies: `video_minimax_h3_{t2v,i2v,r2v}.json`.

## Review: RTX 3060 Seedance-class anime pipeline ([s7JDBLfTGKI](https://youtu.be/s7JDBLfTGKI))

Deno’s “시댄스급 AI 애니 on 3060” talk is **not a new base model** — it is a **production recipe** around MiniMax H3 ref2va:

| Video claim / step | Our env (RTX **4090** 24GB) | Verdict |
|--------------------|----------------------------|---------|
| Multi-ref R2V UX (easy multi-image load) | Deno multi-ref nodes **installed** | **Adopt** → `MiniMax_H3_R2V_MultiRef_Deno.json` |
| Low MP gen so 8–12GB cards finish | We can run **higher MP** natively | Still useful for fast drafts (0.3–0.5 MP) |
| Local LLM prompt help | Ollama Gemma4 already wired for A2V | Reuse same prompt style on MultiRef |
| Upscale + Deblur after gen | `DenoRTXVFXEasyUpscale` + existing LTX spatial | **Adopt** polish graph (RTX VFX install optional) |
| 24→60fps interp | RIFE available (`rife49.pth`); API mult is int → **×2 = 48fps** | **Adopt** RIFE polish; true 60 needs extra tool |
| “Seedance-level” quality claim | Subjective; H3 multi-ref + polish is the real value | Worth using for anime / multi-character |

**Conclusion:** Highly applicable. Our 4090 is *above* the video’s target hardware, so the main gains are **workflow UX** (multi-ref) and **post polish**, not VRAM survival tricks. Stock R2V already works; MultiRef + polish is the missing production layer.

### Recommended anime pass (this PC)
1. Generate: `MiniMax_H3_R2V_MultiRef_Deno.json` @ **0.5 MP**, 5–8s, detailed `<Picture n>` prompt  
2. Polish: `MiniMax_H3_PostPolish_Upscale60fps.json` (VSR ×2 + RIFE ×2 → ~48fps)  
3. Heavy upscale alt: `MiniMax_LTX_Spatial_Full_Upscale.json`

Optional speed: KJ **PatchSageAttention** on the H3 UNet path (node available: `PatchSageAttentionKJ`).

---

## Audio-to-Video — what the video demonstrates

From [MiniMax H3 Audio-to-Video 워크플로 | 멀티 이미지부터 립싱크까지](https://youtu.be/puBAu9qt5qM) (Deno):

1. **Multi-image reference** as identity / style / scene control (`<Picture 1>` …)
2. **Audio reference** as the performance source (`<Audio 1>`) for singing / speech lip-sync
3. **Detailed prompts are mandatory** for MiniMax (unlike LTX, bare prompts fail)
4. Auto path: Whisper lyrics → Gemma acoustic fields → local LLM builds a structured H3 prompt
5. Final MP4 uses the **selected source audio**, not H3’s internal audio decode

### Quick start — Simple (recommended first)

1. Restart ComfyUI if it was running when nodes were installed.
2. **Load** → `ComfyUI/workflows/MiniMax_H3_A2V_Simple.json`
3. Set **Ref Image 1** (character / style)
4. Set **Load Audio** to a short clip (≈5–15 s of speech or song in `input/`)
5. Set **Duration** to that same length in seconds
6. Fill lyrics inside the prompt’s `<d>[Language] …</d>` tags
7. Queue Prompt (start at Resolution Selector **0.3–0.4 MP**, 16:9)

### Quick start — Full Deno auto-prompt

1. Custom nodes installed: `ComfyUI/custom_nodes/comfyui-deno-custom-nodes` (+ junction `deno-custom-nodes`)
2. `openai-whisper` installed in portable Python (done)
3. Optional: download `gemma4_e4b_it_fp8_scaled.safetensors` into `F:\model\text_encoders\`
4. Optional: LM Studio Local Server with a Gemma 4 instruct model
5. Load `MiniMax_H3_A2V_AudioToVideo.json`
6. Upload audio + reference images → run (analysis group can run with manual lyrics even if LLM is offline if you bypass/replace the refiner prompt)

## Prompt grammar (A2V)

Use reference tags that match connection order:

- Images: `<Picture 1>`, `<Picture 2>`, …
- Audio: `<Audio 1>`

Recommended four-block structure (Deno / H3-friendly):

```text
[reference generation + audio reference]
Use <Picture 1> as identity for S1 (same face, hair, outfit).
Use <Audio 1> exactly as the performance; lips sync every syllable.
Style: rendered exactly in the art style of <Picture 1>.

integrated_multimodal_description:
[Shot 1] Medium close-up. The singer (S1) sings: <d>[Korean] 가사</d>
At 00:04.000, [Shot 2] slight push-in, natural motion.

overall_soundscape: quiet room ambience of the location in <Picture 1>
non_diegetic_music: the song from <Audio 1> continues unchanged
```

## Low VRAM tips

- Resolution Selector megapixels: start **0.2–0.4** (e.g. 864×480 at 0.4)
- Duration: start **5–8 s** (valid lengths snap to H3’s 17k+5 frame grid at 24 fps)
- A2V uses **ref2va** weights (~same footprint as R2V)
- Optional: Sage Attention (KJNodes) for speed

## Sampling defaults (validated in Deno notes)

- Sampler: `res_multistep`
- Scheduler: `simple`, steps `20`
- Prefer not changing these until you have a working baseline

## How to load

1. ComfyUI menu → **Load** → pick a file from `ComfyUI/workflows/`
2. Or Workflows sidebar under user/default/workflows

## Docs

- https://docs.comfy.org/tutorials/video/minimax/minimax-h3
- https://huggingface.co/Comfy-Org/MiniMax-H3
- https://blog.comfy.org/p/minimax-h3-day-0-support-in-comfyui
- Deno nodes: https://github.com/Deno2026/comfyui-deno-custom-nodes
- Deno A2V on Civitai: https://civitai.com/models/2849510
