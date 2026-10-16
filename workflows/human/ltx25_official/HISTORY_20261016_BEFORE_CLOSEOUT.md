# Historical guide snapshot — superseded

This file preserves the earlier pending/failed-stage text. Current status and commands are in [AGENT_GUIDE.md](AGENT_GUIDE.md).

## Ingredients recovery update — 2026-10-16T15:42:42.646004+00:00

Earlier two visual failures remain in history, but they are no longer the final result. A controlled untiled-only ablation failed; rebuilding the reference as one distinct prop panel plus a separate empty location and matching the positional inventory prompt removed the panel layout/dark occluder at the same seed4747, strength1, official768×448/121/24 bucket. This bounded prop/motion case visually PASSED. Black background is part of the official sheet contract and remains in the successful input; removing it is not the general fix. The individual contribution of image design versus wording is not isolated.

The same INT8+new2.5 Ingredients stack also combined a published character/guitar/stage sheet into one scene; exact face/hair fidelity and listening remain pending. No general production identity guarantee. Detailed hypotheses, official/community confidence, actual API and contacts: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md`; latest records: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-repair-status.json`.

CLI Ingredients defaults are now5sec/768×448 with untiled reference encoding, strength1 and Euler ancestral. Community comparison controls are explicit `--adapter-strength 1.4 --sampler euler_ancestral_cfg_pp`; they do not replace the official default or original AIO quality policy. All prior T2A/A2V graphs and other successful paths are preserved. No new models/nodes/packages, no restart. Model remains only at `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`; Downloads duplicate absent and full SHA reverified.


# LTX-2.5 official-derived tasks — ready_experimental

Updated UTC: 2026-10-16T15:25:12.160419+00:00. GPU execution used existing original8188; no package/node update or server restart. This guide supersedes earlier pending-stage notes.

## Scope and evidence

`scripts/generate_ltx25_official.py` exposes T2A, A2V and Ingredients as explicit LTX-2.5 tasks. Graphs are hand-wired API adaptations of the pinned official recipes, using the installed Comfy-only INT8 transformer and Gemma4 encoder. They are **not unchanged official UI workflows**. Original UI source snapshots and provenance remain in this folder; browser import/execution has not been verified. Tested API envelopes are under `workflows/agent/ltx25_official/`.

| Task | Actual execution | Review / limit |
|---|---|---|
| T2A | 2 seconds, stereo 48kHz FLAC, 22.93 s | Non-silent, unclipped; listening and semantic correctness pending |
| A2V | Two-stage 384×256 → 768×512, 49 frames/24fps, 25.35 s | Stream motion contact sheet opened; source/output audio correlation 0.999209 after AAC; speech/lip-sync not tested |
| Ingredients | Exact 2.5 adapter, 768×448, 121 frames/24fps, two runs ~37.9 s | **Both visual FAIL**: reference-sheet panels persist; retry removes panels but leaves dark foreground occlusion. Model loading/execution is proven, usable identity/reference quality is not |

Evidence: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/runtime-validation.json`, `validation/*.run.json`, `*.history.json`, `*.api.json`, `validation/reviews/`; failure note FN-20261016-007. All eight tests across AIO and these tasks completed. Generic I2V/S2V defaults remain 2.3.

## Commands

Run from `F:/Agent_media_tools`; output must be in the user's project outside this toolbox. Serialize GPU jobs; CLI refuses a busy queue and never starts/restarts ComfyUI.

```powershell
python scripts/generate_ltx25_official.py --task t2a -p "A gentle stream flows over small rocks, no music, no speech." --seconds 2 -o F:/my_project/stream.flac
python scripts/generate_ltx25_official.py --task a2v -a F:/my_project/stream.flac -p "A shallow forest stream flows over stones; static camera." --seconds 2 --width 384 --height 256 -o F:/my_project/stream.mp4
python scripts/generate_ltx25_official.py --task ingredients -i F:/my_project/reference.png -p "Reference sheet: A red toy ball. Generated video: One continuous full-frame tabletop scene; the ball rolls slowly right; static camera." --seconds 5 --width 768 --height 448 -o F:/my_project/reference_test.mp4
```

Ingredients command is an experimental diagnostic, **not a quality-approved preset**. Minimum 121 frames; reference downscale factor1 and adapter strength1. Use exact explicit dimensions/duration above. `--export-api` writes an API envelope at `--output` without queueing or copying inputs. Every actual run writes API, history and run evidence alongside output. Completion must be followed by media review.

## Models / provenance

Base: `F:/model/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors`; encoder `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors`; separate 2.5 video/audio VAEs. A2V uses installed 2.5 spatial latent ×2 upscaler. Ingredients is single stage.

Exact adapter: `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`, 1,308,787,472 bytes, local SHA256 `ff873a5beada3c579a8137c7c53343916f78bcc9a529ba910143073fe8715e95`. User's manual download was moved from Downloads after full size/hash/header verification; only destination remains. Metadata says model_version2.5, reference_downscale_factor1. Local SHA proves move integrity; authoritative upstream SHA was not available and equality is not claimed. No authentication or license consent changed.

Pinned source UI commit: `44c8a36b7c31ee00b4271daed11dc2a4aa481140`, see [SOURCES.json](SOURCES.json). Its Ingredients JSON names a 2.3 adapter; this candidate explicitly uses the separately released 2.5 model-card recipe and is labelled accordingly. The dev base metadata does not by itself require a dev model download; the 2.5 model card demonstrates distilled inference. Existing 2.3 LoRAs are not rejected based on filename; AIO retains its original `--lora-policy quality` default. These separate task graphs are labelled baseline and do not silently change the AIO policy.

Official references: [LTX-2.5 model card](https://huggingface.co/Lightricks/LTX-2.5), [2.5 Ingredients](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients), [IC-LoRA guide](https://docs.ltx.io/open-source-model/integration-tools/ic-lo-ra-adapters#ingredients), [current model license](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x). The repository LICENSE snapshot is a separate older text and is not substituted for current model terms.

## Remaining work, priority on RTX4090 24GB

1. Review actual playback/listening and a small real use-case before production. Current runs are 2–5 seconds and offloaded; runtimes are not general throughput benchmarks.
2. Ingredients: repair reference design (remove sheet gutters/background) and isolate adapter strength/prompt effects in a separately approved experiment. Current two failures establish no root cause.
3. Test longer clips, people/identity/speech and UI import only when required. Existing AIO FML/V2V/audio variants are expanded offline but not all executed.
4. Defer Union/MotionTrack, native multishot, generated keyframes, extension, duration prediction, DFR/pixel detailing and temporal upscaling until needed. A node/model/source example is not a tested local route. No bulk model or dependency additions.
