# Measured DenoMix 8+2 validation

2026-10-30. RTX4090 24GB,64GB RAM, ComfyUI0.43.0, Python3.13.12, Torch2.13.0+cu130. Existing NVFP4 H3 encoder;896×512→1792×1024. Fixed seed301031 and the same synthetic adult reference, outfit, neutral studio and dialogue for the length sequence. Reference and generated media are caller data and are not shipped.

| Test | Actual frames / seconds | Wall seconds | Peak VRAM MiB | Result |
|---|---|---:|---:|---|
| Dialogue requested5s |124 /5.166667|91.65|21581|Executed, all frames decoded|
| Same dialogue requested10s |243 /10.125|183.32|21575|Executed, all frames decoded|
| Same dialogue requested15s |No output|385.27 to stop|23982|Own prompt deliberately interrupted at refinement203|
| Separate motion requested5s |124 /5.166667|97.87|21585|Executed; requested yaw not achieved|

Successful outputs: H264,1792×1024,24fps; AAC32kHz stereo. Decoded audio lengths5.152/10.112/5.152s. Finite audio, no clipping observed and no exact duplicate adjacent decoded frames. These are measured runs, not repeatability or performance guarantees. Cache state differed before the motion test.

For15s, minimum physical memory available was3.325GiB, minimum commit headroom305MiB, pagefile usage155→2058MiB. Targeted interruption affected only the validation prompt; existing server retained. Runtime caches were released through the official API after the queue was empty. No actual OOM exception. Allocation cause is unisolated; no retry or completed15s claim.

Twelve distributed and twelve consecutive frames were opened per successful clip. Hair, earrings, clothing and neutral background appeared stable; exact source identity remains a human comparison. Motion request30degree yaw/return became mostly mild tilt, so all-angle identity and motion compliance did not pass.

MOSS recognized the fixed Korean target once in5s and the main target in10s. In10s it additionally recognized thanks around8–9s, in an interval near−74dBFS with closed sampled mouth; possible ASR hallucination, not confirmed extra speech. Motion audio produced timestamps without recognized words and no parsed segments; it is not a silence approval. No Chinese text was recognized, but direct listening and phoneme lip sync were not approved. No original-H3 comparison sample was made.


## Agent CLI integration check

The separate agent CLI completed one new synthetic cube5s request end-to-end:124frames/5.166667s,1792×1024, native audio MP4 copied to the caller output, prompt ID/API/history/metadata retained. Measured CLI runtime85.84s. Offline10s dry-run reported243frames/10.125s and made no server request. Read-only status found all required installed nodes/models. Unit tests cover duration rejection before I/O, frozen-audio/refiner wiring, busy-queue preservation, timeout job-ID retention, collision/remote rejection and discovery. This transport check is separate from creative quality or human audio approval.
