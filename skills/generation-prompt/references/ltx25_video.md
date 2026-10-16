# LTX-2.5 prompt contract: user input, enhancer output, production policy

Updated 2026-10-16. CLI: `generate_ltx25_aio` (ten declared modes; GPU/QC pending).
Do not infer 2.5 from generic `generate_i2v`/`generate_s2v`: their defaults remain 2.3.

## 1. User input (official current guidance)

T2V: describe shot size/viewpoint, subject and space/light, chronological visible actions, camera motion or explicit static camera, and a concrete soundscape. Quote exact dialogue in its original language; specify voice/language/accent when relevant. Natural English prose for scene direction; preserve Korean dialogue in Korean.

I2V: the image supplies appearance/composition. Concentrate on what happens next, camera relative to the subject, and audio. Do not contradict the first image or invent a wardrobe change. Avoid repeating a long appearance essay in the user's motion input.

```text
T2V: A medium shot frames [subject] from [viewpoint] in [setting/light]. [Action], then [next action/pause]. The camera [movement/remains static]. [Synchronized ambience]. [Speaker] says in [language/voice], "[exact dialogue]".
I2V: The subject [action], then [next action or pause]. The camera [movement relative to subject/remains static]. [Sound or exact dialogue consistent with the shot].
A2V: [Visual scene, subject performance and camera]. The input audio drives timing; do not request conflicting new dialogue/music.
FLF/FML: [Motion between supplied opening, optional middle, and ending states], [camera], [audio].
```

Reference inputs are task-specific. Ingredients uses a reference sheet/static reference video and its adapter-specific `Reference sheet: ... / Generated video: ...` description. Motion Transfer, sparse tracks, V2V and H3 R2V are not interchangeable, and H3 `<Picture>`/audio tags are not LTX syntax.

## 2. Gemma4 enhancement output (different from the user's short input)

The official Gemma3 I2V system prompt says to describe changes only in a concise paragraph. The Gemma4 I2V system prompt instead asks for a detailed caption faithfully grounded in the exact first image: same subject, clothing, lighting and composition, then chronological motion in a continuous take. Accurate image description is allowed here; invented appearance is not.

Gemma4 requests an explicit shot size, camera movement/static state, viewpoint, integrated sound, objective physical cues, and one rich paragraph (roughly 150–220 words for the enhancer's output). This is not a mandatory length for every user's short input.

The official local templates use **Gemma4 E2B as enhancer**, separately from the LTX-specific **Gemma4-12B text encoder**. Short/rough/cross-model prompts can benefit; detailed controlled prompts can leave enhancement off. Inspect the effective rewritten prompt. The AIO currently forces raw prompt passthrough and exposes no verified E2B enhancement option; do not claim enhancement ran just because the node exists.

## 3. Multi-shot and timing

LTX-2.5 supports native multi-shot. In a chronological prose paragraph, name each cut, re-establish framing and recurring identity, and say whether audio continues or changes. Official guidance suggests 2–4 shots. For first-frame I2V and precise lip performance, a continuous take remains the safer choice. The Gemma4 I2V enhancer's default no-hard-cut instruction means deliberately designed multi-shot should not be blindly passed through that single-take enhancer.

An optional duration predictor can set length; actual pauses must be written into the action. A timestamp in prose is not an exact timing guarantee. The local AIO does not currently wire automatic duration prediction.

## 4. Negative prompts and conservative house rules

- The existing 2.3 guide's CFG 2–4, 97-frame cap, auto-face prompt suffixes and PrunaVAE policy must not be copied into 2.5 distilled configuration.
- Distilled reference graphs use CFG=1 and a fixed sigma schedule. Negative-input availability does not guarantee negative conditioning changes the output. No official evidence was found for a universal 2.5-specific increase in negative-prompt sensitivity.
- Put desired behavior positively into the main prompt. Do not append `no warp`, `identity locked` or a defect list as a substitute for concrete action and appropriate conditioning.
- One primary move, simple action and an approximately ten-second limit are conservative production choices, not official 2.5 feature restrictions. Video frame grid is `8n+1`.
- The input image does not guarantee 100% identity preservation. Inspect frames and motion under output-review.

## Sources and change evidence

- Previous official LTX-2 guide (2025-12-11): https://ltx.io/blog/prompting-guide-for-ltx-2
- Current user/multi-shot/enhancer guide: https://docs.ltx.io/open-source-model/usage-guides/prompting-guide
- I2V input: https://docs.ltx.io/open-source-model/usage-guides/image-to-video
- A2V: https://docs.ltx.io/open-source-model/usage-guides/audio-to-video
- Gemma3: https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-core/src/ltx_core/text_encoders/gemma/encoders/prompts/gemma3_i2v_system_prompt.txt
- Gemma4: https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-core/src/ltx_core/text_encoders/gemma/encoders/prompts/gemma4_i2v_system_prompt.txt
- Explicit 2.5/Gemma4 change record (2026-08-11): https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md

The model card/release record explicitly establishes 2.5 capabilities. Current documentation recommendations do not by themselves establish the exact date a wording first changed. Local short production templates are house recommendations, not quotations from the enhancer system prompt.

## LoRA compatibility review — 2026-10-16 correction

The official LTX-2.5 model card says the large majority of LTX-2.3 LoRAs and IC-LoRAs run on 2.5 unchanged, with some exceptions requiring validation. A 2.3 filename is not grounds for disabling an adapter. https://huggingface.co/Lightricks/LTX-2.5#training--fine-tuning

Restored the pre-change runtime default: `--lora-policy quality --ltx-profile work`. This enables `LTX2.3\ltx-2.3-22b-distilled-1.1_lora-dynamic_fro09_avg_rank_111_bf16.safetensors` at 0.7 and `LTX2.3\ltx2.3_upscale_ic-lora_06250.safetensors` at 0.45. The former is a distilled/speed/model-behavior LoRA; the latter is an upscale IC-LoRA (header reference_downscale_factor=2). They are not interchangeable with identity/Union/Ingredients adapters. The retained Cameraman slot is OFF@0.7 and was not affected. Detailer and Omni were not slots in this 2.5 graph; VBVR was already explicitly off before the change.

`--lora-policy workflow` preserves the saved UI on/off/strength settings (all three current slots off); `--lora-policy none` explicitly disables all Power LoRA slots for a controlled baseline comparison. Neither setting is a compatibility verdict. Active filenames/strengths/policy are recorded in run metadata. Files and UI settings have never been deleted or replaced.

Exact two-adapter-on-LTX2.5 quality/runtime evidence has not been found. The local July-17 detailer A/B supports the old 2.3 detailer use only, not these exact two files on 2.5. GPU remains pending parent coordination. The original automatic stack is preserved as requested; compare quality/workflow/none after the basic paths run.
