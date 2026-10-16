<!-- LTX25-ADVANCED-FOLLOWUP-20261017 -->
## LTX-2.5 latest validation states — 2026-10-17T08:00:31.657607+09:00

**Do not merge execution success, bounded visual quality, user review, and missing models.** New4small advanced probes completed on the existing INT8 server; no model/package/node downloads, installation, restart or permanent default changes. APIs live in the validation project, not a newly deployed general production CLI.

| Feature | Execution | Quality | User review / missing component |
|---|---|---|---|
| Ingredients public original/portrait-only/matched-text + close-up | completed | scene integration without panels and framing change observed | exact all-angle face identity pending |
| Korean/English generated speech and A2V | completed | ASR phrase match; A2V waveform preservation; tested quality-on face drift fails | pronunciation/noise/timbre/listening and phoneme-level sync pending |
| Temporal Retake local mask probe | completed | requested blue-ball change FAILED; outside-window preservation bounded | not unchanged native RetakePipeline |
|49to97frame video extension | completed | actual new motion, no conspicuous seam jump, bounded visual success | exact pan unverified; source audio was not preserved |
| Union canny92/200and25/80 | both completed | ball path partially followed; tabletop geometry FAILED in both | depth/pose not tested; exact official2.5example2.3adapter used |
| MotionTrack / In-Outpainting | not run | none | adapter not installed; exact filenames/sizes in report |
| DFR / temporal upscale | not run | none | detailing/temporal assets missing; native route needs compatible weights/runtime, not Comfy ConvRot |

Panel causality is **not isolated**. No enhancer/I2Vanchor was active and CropGuides wiring is correct in tested graphs. Public input/graph controls disprove blanket reference impossibility; reference sheet/prompt/seed/resolution/sampler/strength/decoder/output differences remain confounded. Threshold-only repair did not resolve Union geometry. Preserve the original quality default; one English adapter-off ablation is not general incompatibility evidence.

[Latest state-by-state report](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/ADVANCED_REPORT.md) includes causal audit, actual audio-boundary frames, prompt IDs/hashes/time/VRAM, missing official files/bytes/license/gates, and user listening material. Library contains **LTX25_Validation_Comparisons_20261017.zip** (sanitized fictional characters/stock voices/prop comparisons only; no real-person public portrait/API/accounts/computer paths). Overall production/whole-feature validation remains incomplete. Earlier pending/completed paragraphs below are dated history.


<!-- LTX25-QUALITY-FOLLOWUP-20261017 -->
## LTX-2.5 face/dialogue followup — 2026-10-17T07:48:44.784216+09:00

Status remains **ready_experimental**. Public original → portrait-only replacement → matched-character text all generated one scene without retained panels. A close-up wording repair also worked. This does not establish exact facial identity; earlier local two-view sheet failures remain valid bounded failures, not proof that Ingredients is impossible. No I2V anchor or enhancer was active; conditioned positive/negative reached CropGuides correctly.

Korean/English LTX-generated speech and input-frozen A2V phrases matched offline CPU ASR. A2V waveform correlation was0.999294/0.999134. **Listening, precise phoneme sync and production identity remain pending**; ASR/spectra/mouth-energy curves are not auditory passes. In one controlled English case, disabling the two added AIO quality adapters reduced facial/expression drift (supplementary mid-frame reference cosine0.437→0.786), but decoded audio overshoot needs review. Keep the original quality default and generic2.3 route; this is one explicit ablation, not a blanket incompatibility claim.

Approved fictional photoreal/anime sources and cached Qwen stock voices only; no cloned character-pack voice, external upload, model/package/node installation or restart. Current phase:10additional completed jobs; all phase records22include one invalid metadata-only prompt ablation preserved/excluded. Retake candidate is **prepared only, not queued**; extension/Union/MotionTrack/DFR runtime quality is still pending.

Read [the quality report](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/QUALITY_REPORT.md) for exact input/prompt/API/history/hash/time/VRAM, public graph audit, failed cases and source/output listening previews. Machine result: [QUALITY_RESULTS.json](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/QUALITY_RESULTS.json). Older status paragraphs below are historical snapshots.


<!-- LTX25-CURRENT-START -->
> **LTX-2.5 현재 상태 (2026-10-16T15:46:24.123116+00:00): ready_experimental.** T2V/I2V/FLF/T2A/A2V 짧은 실행 확인; Ingredients는 소품/장소 참조 시각 PASS, 정확 얼굴·청취는 pending. 이전 실패/접근 차단 문장은 당시 이력이다. [현재 사용 가이드](F:/Agent_media_tools/workflows/human/ltx25_official/AGENT_GUIDE.md)에서 시트 규칙·실패 양상·검증 입력/출력·정확 재현 명령·미검증 목록을 확인한다. [복구 진단](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md).
<!-- LTX25-CURRENT-END -->

## Ingredients recovery update — 2026-10-16T15:42:42.646004+00:00

Earlier two visual failures remain in history, but they are no longer the final result. A controlled untiled-only ablation failed; rebuilding the reference as one distinct prop panel plus a separate empty location and matching the positional inventory prompt removed the panel layout/dark occluder at the same seed4747, strength1, official768×448/121/24 bucket. This bounded prop/motion case visually PASSED. Black background is part of the official sheet contract and remains in the successful input; removing it is not the general fix. The individual contribution of image design versus wording is not isolated.

The same INT8+new2.5 Ingredients stack also combined a published character/guitar/stage sheet into one scene; exact face/hair fidelity and listening remain pending. No general production identity guarantee. Detailed hypotheses, official/community confidence, actual API and contacts: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md`; latest records: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-repair-status.json`.

CLI Ingredients defaults are now5sec/768×448 with untiled reference encoding, strength1 and Euler ancestral. Community comparison controls are explicit `--adapter-strength 1.4 --sampler euler_ancestral_cfg_pp`; they do not replace the official default or original AIO quality policy. All prior T2A/A2V graphs and other successful paths are preserved. No new models/nodes/packages, no restart. Model remains only at `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`; Downloads duplicate absent and full SHA reverified.


## Latest LTX-2.5 validation (2026-10-16T15:25:12.160419+00:00)

Eight short GPU runs completed on original8188: T2V quality/none, I2V, FLF, T2A, A2V, Ingredients twice. Basic visual motion checks and technical audio checks passed; full playback/listening and production identity remain pending. **Historical initial trials: both failed; subsequent repaired prop case visually PASSED**, despite successful exact 2.5 adapter loading/execution. See [official-derived task guide](ltx25_official/AGENT_GUIDE.md) for commands, provenance and failures. Existing AIO quality LoRA policy and generic 2.3 defaults remain. No package/node updates or restart. Evidence: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/runtime-validation.json`. Earlier pending-stage entries below are historical and superseded by this entry.

# LTX-2.5: explicit version, preparation and validation





Updated: 2026-10-16. Status: `ready_experimental`. GPU execution and media QA: **not run**.





## Choose the version explicitly





- LTX-2.5: `python scripts/generate_ltx25_aio.py --mode <mode> ... -o D:/my_project/clip.mp4`.


- Existing `generate_i2v`, `generate_s2v --backend ltx23_aio` and `generate_flf2v` keep their LTX-2.3 defaults. They do not become 2.5 because 2.5 models are on disk.


- The 2.5 CLI passes its dedicated UI JSON explicitly, preserves the original quality-LoRA tuning by default (`--lora-policy quality`), and checks the expanded model selections. Keep the base DiT/encoder/VAEs on 2.5. Do not reject a LoRA because its filename says 2.3; adapter compatibility and task conditioning are separate checks.


- The shared runner's default behavior remains unchanged for legacy callers.





## Inputs and commands





Ten modes are declared: t2v, t2v_audio, i2v, i2v_audio, flf, flf_audio, fml, fml_audio, v2v, v2v_audio. Declared does not mean runtime verified.





```text


python scripts/generate_ltx25_aio.py --mode t2v -p "A wide shot frames a red ball rolling across a wooden table; the camera remains static. A soft rolling sound follows the ball." --clip-length 2 --longer-edge 768 -o D:/my_project/t2v.mp4


python scripts/generate_ltx25_aio.py --mode i2v -i first.png -p "The subject slowly turns, then pauses. The camera remains static." -o D:/my_project/i2v.mp4


python scripts/generate_ltx25_aio.py --mode flf -i first.png --last last.png -p "The camera slowly moves from the opening composition to the final view." -o D:/my_project/flf.mp4


python scripts/generate_ltx25_aio.py --mode i2v_audio -i first.png -a voice.wav -p "The subject speaks naturally; the camera remains static." -o D:/my_project/a2v.mp4


```





A2V AIO is an unverified compatibility route. Prefer validating the separately staged current official A2V graph next. T2A is audio-only and is not an AIO mode: the local `LTX-2.5_T2A_Ambience_int8.json` provides that graph.





`--export-api FILE --object-info OBJECT_INFO.json` builds without copying input media, freeing memory, queueing, launching or restarting a server. It writes an envelope with `prompt`, `metadata`, and `models`; submit only `prompt` to ComfyUI after resource authorization. Without a saved object_info, the converter may GET the existing local server's node schemas.





## Models and 4090 policy





Existing stack: distilled INT8 ConvRot DiT, LTX-specific INT8 Gemma4-12B, 2.5 DiffVAE, 2.5 audio VAE, 2.5 spatial x2 upscaler. All paths resolve through F:/model.





- The official lower-VRAM recipe uses the lighter `ltx-2.5-video-vae-conv-bf16.safetensors`; it was not present at audit. Do not silently swap to 2.3 Pruna/stock VAE.


- INT8 ConvRot is ComfyUI-only. It cannot be fed to native ltx-pipelines as if it were BF16.


- About ten seconds is our conservative production recommendation, not an official model limit. Valid video frame counts are `8n+1`, not exactly 240. Record effective frames and duration from output; the AIO runner currently rounds requested seconds upward to whole seconds.


- Begin with 41–81 frames and modest resolution. A two-stage graph doubles base width/height. Do not promise 4K/8K performance on 24GB.


- Memory cleanup is a mutation and happens only during actual CLI execution after shared-resource coordination. The CLI never auto-starts ComfyUI.





## Success and evidence





1. The server history must say successful and completed; missing/failed history is a failure.


2. The referenced output must exist, be nonempty, be under the server output root, and be video. Subfolders are resolved correctly.


3. The requested project copy and `.run.json` record model names, prompt id, mode and timing. Exit zero means render completion only; `quality_review=not_run` until visual/audio inspection.


4. Use output-review: probe duration/audio, inspect first/middle/last frames and motion, record pass/fail. A frozen/broken clip is not accepted.





## Expansion order and version boundaries





Basic T2V/I2V/FLF/T2A execution+QA → official A2V → Ingredients. Union/Motion Track only when needed. No batch installation of every adapter.





- Ingredients requires the exact reference-sheet adapter and its prompt syntax. The older official 2.5 example selects a 2.3 Ingredients adapter while the 2.5 card publishes a different file; follow one exact source, not an arbitrary filename substitution.


- Union has an existing 2.3 adapter intentionally used by an official 2.5 graph, but local depth preprocessing nodes are missing. Sparse Motion Track requires a missing adapter. Motion Transfer is a separate feature.


- DFR requires detailing IC-LoRA and a keyframe-aware path; a spatial upscaler alone is not DFR. Temporal upscaler, HDR/EXR and Tiled Fusion are separate expansions.


- Foley, Dub-It and Relight documented for 2.3 must not be relabelled 2.5 without explicit matching evidence.





## Coordination and licenses





The pre-Higgs backup is F:/backups/ComfyUI_env/env_20261016_232422_before_higgs3. Per-file originals/hashes are retained under C:/Users/parkp/Documents/Codex/2026-10-16/task-8/before_ltx25.





At preparation time Higgs isolated-engine work is concurrent. Do not change shared Python/nodes, restart ComfyUI, load models, or generate on GPU until the parent's resource coordination message.





Use the exact official model's LTX-2.x license. Existing local weights do not establish access to a gated adapter. If Hugging Face requests new contact-sharing/terms consent, stop that download and report it; do not accept on the user's behalf. No commercial eligibility or gated access was inferred in this preparation pass.





## Official sources





- Model/version/files: https://huggingface.co/Lightricks/LTX-2.5


- Compatibility: https://docs.ltx.io/open-source-model/reference/workflow-asset-compatibility


- Comfy low-VRAM/templates: https://docs.ltx.io/open-source-model/integration-tools/comfy-ui


- A2V: https://docs.ltx.io/open-source-model/usage-guides/audio-to-video


- Ingredients: https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients


- Prompt input/enhancer: skills/generation-prompt/references/ltx25_video.md


- Current release history: https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md





## LoRA compatibility review — 2026-10-16 correction





The official LTX-2.5 model card says the large majority of LTX-2.3 LoRAs and IC-LoRAs run on 2.5 unchanged, with some exceptions requiring validation. A 2.3 filename is not grounds for disabling an adapter. https://huggingface.co/Lightricks/LTX-2.5#training--fine-tuning





Restored the pre-change runtime default: `--lora-policy quality --ltx-profile work`. This enables `LTX2.3\ltx-2.3-22b-distilled-1.1_lora-dynamic_fro09_avg_rank_111_bf16.safetensors` at 0.7 and `LTX2.3\ltx2.3_upscale_ic-lora_06250.safetensors` at 0.45. The former is a distilled/speed/model-behavior LoRA; the latter is an upscale IC-LoRA (header reference_downscale_factor=2). They are not interchangeable with identity/Union/Ingredients adapters. The retained Cameraman slot is OFF@0.7 and was not affected. Detailer and Omni were not slots in this 2.5 graph; VBVR was already explicitly off before the change.





`--lora-policy workflow` preserves the saved UI on/off/strength settings (all three current slots off); `--lora-policy none` explicitly disables all Power LoRA slots for a controlled baseline comparison. Neither setting is a compatibility verdict. Active filenames/strengths/policy are recorded in run metadata. Files and UI settings have never been deleted or replaced.





Historical before GPU validation: exact two-adapter-on-LTX2.5 quality/runtime evidence had not yet been found. The local July-17 detailer A/B supports the old 2.3 detailer use only, not these exact two files on 2.5. At that historical checkpoint GPU work was pending; completed short-run evidence is summarized in the current guide. The original automatic stack is preserved as requested; compare quality/workflow/none after the basic paths run.




## Partial runtime checkpoint — 2026-10-17 00:06 KST



Original8188 completed four49-frame,448×768,24fps samples: T2V quality40.25s, T2V none29.89s, I2V quality39.91s, FLF quality39.16s. Times are per-run observations with different cache state, not a controlled speed benchmark. Same-seed T2V shows different surface/detail with the two quality adapters enabled; this does not establish universal quality superiority. Render compatibility of that combination is confirmed for this short toy-ball case only. First/middle/last frames were inspected; audio semantics, speech/identity and broad production QA remain pending.



Evidence: C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation. Status remains ready_experimental. After FLF, queue was empty and models unloaded for the requested Higgs GPU handoff. Historical at this entry: T2A/A2V had not run; both subsequently executed. Ingredients2.3 and2.5 access both returned401 with existing HF credentials; no model downloaded or new consent accepted.


## Ingredients access diagnosis correction — 2026-10-17 KST

The existing HF credential was rejected by `/api/whoami-v2` (401 Invalid username or password). File HEAD returned GatedRepo. This does not establish whether the account previously accepted the gate. Restore valid authorized authentication before checking repository access; do not infer missing consent from401 alone. Exact2.5-card versus2.3-adapter-in-official-JSON routes, components and conditions: [Ingredients checkpoint/access note](ltx25_official/INGREDIENTS_CHECKPOINT_AND_ACCESS.md). No GPU work, model download or gate acceptance in this pass.
