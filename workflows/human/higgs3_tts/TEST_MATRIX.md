# Higgs TTS 3 — original8188 validation matrix

2026-10-16, PC-HOME RTX4090 24GB / RAM64GB. Status: **ready_experimental**. Actual original ComfyUI graph execution succeeded; listening emotion/voice QC remains pending.

## Integration and preservation

- Original server: `http://127.0.0.1:8188`, ComfyUI0.41.1. Graph path: Higgs3IsolatedTTS → SaveAudio; reference tests also execute LoadAudio.
- Ten original-server prompt IDs/API/history/results are retained beside audio. The worker path in each history proves private Transformers5.3.0; original Transformers4.57.3 is preserved.
- Official9,309,834,930-byte model SHA256: `2f7965264c360b38180885006944aa16bd1de20f4e6cff79f6473bfcf8ae3d5a`, pinned revision239f63fb7b02b1aa085f98d9efae5e35cc5523e8.
- UI/API3presets passed node/input/link static checks against live8188. Browser execution was unavailable because the computer-use runtime failed to initialize (SystemDrive/MXC sandbox); actual browser import/Queue is unverified.

## Sample results

bf16 / SDPA / seed42 / temperature0.8 / top-p0.95 / top-k50 / max256 audio-token steps. All output24kHz mono. Eight conditioned samples use the existing user-created Park Soft VoiceDesign sample and its exact Korean transcript. Two unconditioned samples are controls.

| Case | Audio(s) | Wall(s) | Worker generation(s) | GPU total sampled peak(MiB) | CUDA allocated peak(MiB) | RMS(dBFS) | ASR number-normalized CER |
|---|---:|---:|---:|---:|---:|---:|---:|
| en_unconditioned | 3.36 | 18.57 | 3.68 | 10999 | 8494.3 | -20.6 | 0.000 |
| ko_unconditioned | 3.92 | 19.06 | 4.67 | 10996 | 8494.3 | -21.3 | 0.000 |
| en_neutral | 3.08 | 18.62 | 4.02 | 11011 | 8494.3 | -14.9 | 0.000 |
| en_elation | 3.08 | 18.55 | 3.99 | 11003 | 8494.3 | -14.5 | 0.000 |
| en_sadness | 3.28 | 18.57 | 4.09 | 10998 | 8494.3 | -19.2 | 0.000 |
| en_anger | 3.36 | 18.59 | 4.17 | 11010 | 8494.3 | -20.0 | 0.000 |
| ko_neutral | 4.04 | 19.10 | 4.90 | 11009 | 8494.3 | -16.1 | 0.000 |
| ko_elation | 3.88 | 19.09 | 4.80 | 11020 | 8494.3 | -14.3 | 0.000 |
| ko_sadness | 5.36 | 20.77 | 6.15 | 11010 | 8494.3 | -18.4 | 0.000 |
| ko_anger | 4.20 | 19.12 | 5.07 | 11019 | 8494.3 | -20.0 | 0.000 |

## Interpretation and limits

- Local Whisper large-v3-turbo detected all10languages correctly and recovered both full supplied sentences. Raw CER0–0.1053 reflects nine/아홉 versus digit9 orthography; the explicitly documented number-only normalization gives0 for every sample. ASR is an imperfect proxy, not human listening.
- All10passed non-silence/level checks. Nine had no samples at absolute amplitude≥0.999; en_elation had4such samples (0.0054%). No gross clipping or token-cap truncation was detected. Perceptual noise/clicks/pronunciation quality remain unverified.
- Each language’s4emotion inputs produced4distinct waveform hashes and measurable duration/pitch/level changes. This proves the tags reach inference and alter output; it does not prove a listener perceives the intended emotion. Audio review records therefore remain pending.
- The reference path executed8times. Neutral conditioned pitch summaries are about134Hz versus207Hz/241Hz for unconditioned English/Korean controls. Strong elation/anger can raise pitch markedly (Korean YIN summaries244Hz/257Hz); timbre can drift under strong performance control. YIN includes unvoiced errors and mel cosine is only a weak spectral proxy. No trained speaker-embedding or listening identity pass is claimed.
- The character remains on its locked Qwen3 VoiceDesign production path. No real-person recording fallback was used, and no reference left the PC.
- Long-form, streaming, multiple speakers, other languages/emotions/prosody/SFX and other GPUs are untested. Each request cold-loads and exits its worker; measured wall times include that overhead.

## Existing tools after Higgs inference

| Core tool | Wall(s) | GPU total sampled peak(MiB) | Execution / visual QC |
|---|---:|---:|---|
| flux3 | 9.35 | 11509 | exit0 / pass |
| krea | 8.82 | 19468 | exit0 / pass |
| qwen | 36.84 | 19570 | exit0 / pass |
| h3_square | 29.16 | 21554 | exit0 / pass_bounded_frames |

These are bounded representative fixtures using the prior regression commands/new seed, not exhaustive coverage of every node or preset. FLUX3/Krea use dense still-life captions; Qwen changes the pot to green; H3 is a2s square I2V camera slide decoded at2.333333s. Actual PNGs and H3 first/mid/last frames were opened.

## Reproduction and evidence

From `F:\Agent_media_tools`:

```powershell
python scripts/generate_higgs3_tts.py --text-file F:\Agent_media_sandboxes\higgs3\validation\ko_neutral.txt --emotion neutral --seed 42 --max-new-tokens 256 --ref-audio F:\Agent_media_sandboxes\higgs3\validation\reference_park_soft_design.wav --ref-text-file F:\Agent_media_sandboxes\higgs3\validation\reference_text.txt -o F:\my_project\voice\ko_neutral.wav
python F:\Agent_media_sandboxes\higgs3\tests\test_higgs_matrix.py
python F:\Agent_media_sandboxes\higgs3\tests\run_regression.py
```

Outputs: `F:\Agent_media_sandboxes\higgs3\validation\*.wav`. Source API/history, matrix-results.json, audio-qc.json, reference-provenance.json, spectrograms.png, reviews/*/probe.json and pending review records are beside them. Regression commands/results/media/review records: validation/regression. Private dependencies: engine root requirements-lock.txt and isolated-install-report.json.

## Backup, license and operational handoff

Pre-install verified backup: `F:\backups\ComfyUI_env\env_20261016_232422_before_higgs3`, including restore_supplement consistent SQLite snapshot/rollback notes. User explicitly accepted Boson terms before download. Published monetized creator audio/video needs prominent Boson AI’s Higgs Audio credit; see AGENT_GUIDE.md and the official LICENSE. No tokens/accounts or external audio uploads were used.

Initial Xet transfer stalled and was replaced by official HF HTTP resume. First inference hit Windows cp949 progress-output encoding; worker stdout/stderr were explicitly set to UTF-8, failure evidence retained and FN-20261016-006 recorded. No global dependency repair was used.

After all GPU tests, queue was idle and model memory was released; nvidia-smi reported2179MiB/6% at handoff. Original8188 remained running. Subsequent LTX work may change its current queue/GPU state. No further generation or restart is required for these docs.
