# Local media tool operating lessons

Execution, content checks, visual review and human listening approval are separate states. Preserve failed outputs and raw ASR; do not repair transcripts or trim unwanted speech and present the result as model success.

- Keep generated media, references, user project metadata, private voice provenance, cache and logs outside the toolbox and Git. Commit reusable code, templates, public model provenance and bounded validation summaries.
- Serialize GPU tools and respect existing ComfyUI jobs. Status/dry-run must not install, start/restart a server or clear a queue. Preserve prompt IDs; timeouts and lost submission responses require checking queue/history before retrying.
- For MOSS image Edit/Control, read each model's actual license and use the matching mode-specific preset. Missing model data is not permission for background downloads. Review geometry/text/identity separately from a saved PNG.
- Keep MOSS speech and transcription in isolated installations. Only reviewed local model source is allowed through their existing hash guards; do not update shared Transformers/Torch to satisfy a separate worker. Voice references require authorization and actual source provenance, not an arbitrary approved filename.
- ASR can hallucinate words in quiet or musical tails, omit speech or misassign anonymous speakers. Compare waveform bounds and content, then listen; text match is insufficient for pronunciation, timbre or lip sync.
- DenoMix896×512→1792×1024 on the measured4090/64GB desktop completed5/10s requests. The15s refinement was interrupted near commit exhaustion, not an actual OOM exception. The agent CLI caps requested duration at10s and reports243frames/10.125s alignment. This is a measured operating policy, not the base model maximum.
- Appearance held within limited neutral/small-motion samples, but requested head yaw was not achieved. Do not call a small tilt an all-angle identity pass or claim superiority without a matched baseline.

Detailed local failure notes and private evidence remain in the caller's environment. The DenoMix guide/test matrix and MOSS guides record the transferable observations without shipping user media or machine-specific evidence paths.
