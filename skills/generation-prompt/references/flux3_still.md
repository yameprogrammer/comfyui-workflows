# FLUX3 Klein — full scene captions, references and typography

Applies only to `generate_flux3.py`. FLUX.1/Fill/FLUX.2 remain in [flux_still.md](flux_still.md); their short-prompt and Fill rules do not apply here.

## Local profile (static code/workflow inspection, 2026-10-18)

- Distilled INT8 loader: `flux3/flux3_image_klein_sd_int8_convrot.safetensors`; `CLIPLoader` type `flux3`, `qwen3vl_4b_int8_convrot.safetensors`; `flux2-vae.safetensors`. These are local loader filenames, not a claim that the current public download uses the same spelling.
- Default 16 steps, CFG 1, euler/simple. No prompt-upsample node: the caller supplies the expanded caption through `-p` or UTF-8 `--prompt-file`. No dedicated `--text`, `--negative` or upsampler CLI option exists here.
- Modes: `t2i`, `single_edit`, `multi_reference`, `character_consistency`, `style_consistency`, `box_layout`. Read [usage and measured limits](F:/Agent_media_tools/workflows/human/flux3/AGENT_GUIDE.md); strict style QC is still experimental.

## Official guidance and sources (checked 2026-10-18)

1. [BFL Comfy model card — Prompting / Limitations](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy): use a prompt upsampler or another LLM to write a complete final-scene caption. References anchor content, not a locked composition; describe style through palette, stroke and texture. Text can be rendered but may be distorted or wrong. Up to 10 references; boxes guide placement, not a hard mask.
2. [BFL external-VLM caption instructions — t2i / i2i](https://github.com/black-forest-labs/flux-3-image-klein/blob/main/src/flux3/pup_prompts_external_vlm.json): use continuous English prose led by the medium, concrete spatial relations and visible details. Its t2i guidance describes typical captions as **200–350 words**, with complex scenes reaching 500. This is writing guidance, not a token limit or mandatory minimum; do not pad simple scenes. This replaces the older local 100–350 claim.
3. [ComfyUI official tutorial — Prompting and reference tips](https://docs.comfy.org/tutorials/flux/flux-3-klein): edits describe the finished image; reference order uses `<ref_image_0>`, `<ref_image_1>`, etc. Distilled sampling uses CFG 1. The local API attaches references to both conditionings and sets output size independently via `EmptyFlux2LatentImage`; do not assume the first reference fixes the output aspect ratio.

## Caption structure and reference editing

Write one prose block: medium → framing/viewpoint → subjects, count and positions → materials/action → lighting → background. For editing, describe the final scene with the requested change folded in, and name what must remain. Describe each reference's role using its zero-based input order; these tokens identify images, not a face-ID guarantee. Do not send only a short edit command or substitute FLUX.2's 30–80-word recipe.

The [model card's layout format](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy#prompting) appends a JSON list after the caption: `{"id":"cup","bbox":[480,100,800,350],"desc":"A white cup on the left"}` inside an array, paired with `<cup>` in prose. Coordinates are `[top,left,bottom,right]` on a 0–1000 grid. The local CLI accepts that caption verbatim; it does not expose a separate box parser or hard regional mask. Do not confuse this prompt format with the upstream Python CLI's normalized 0–1 box input. No ControlNet/Fill/LoRA support is established by this documentation.

## On-image text: official caption convention

The external-VLM instructions specify literal wording inside double quotes, retaining the original script, capitalization and punctuation; surrounding prose stays English. Describe type, color and location. For a multiline text block, they encode line breaks as literal backslash+n characters inside the quotes, e.g. `"NIGHT\nMARKET"`; a plain UTF-8 prompt file should contain those two characters, not a real line break. This is a caption convention, not a special text-rendering API or correctness guarantee. Do not translate quoted user copy. Do not invent text or logos when the request calls for none.

## Practical typography advice (editorial recommendations, not model guarantees)

- Start with a short headline and one subordinate line. Specify exact copy, upper/lower placement, relative size and hierarchy, alignment, letter style and foreground/background contrast in ordinary prose. A requested percentage or size is a visual target, not a pixel constraint or font engine.
- Reserve a plain, uncluttered area around letters; keep illustration, texture, shadows and props outside that reading area. Avoid tiny fine print, overlapping letters and elaborate distortion when legibility matters.
- For an existing sign, bind the source to `<ref_image_0>` and describe the final sign plus the unchanged scene. Review the rest of the frame too: reference edits can drift outside the target.
- Inspect every character, punctuation mark, line break, clipping and hierarchy at delivery size. If exact copy or a specific typeface is essential, generate a blank text area and typeset in a normal graphics/video editor afterward. Do not report a prompt example as a rendered pass.

## Draft examples — not generated or visually validated

These are complete prose examples; simpler layouts can be shorter than the typical caption guidance. They add no custom tokens beyond documented reference syntax.

### T2I poster

```text
Flat graphic poster on cream paper. Across the upper third, a centered headline reads "NIGHT MARKET" in large dark-navy uppercase sans-serif letters. The headline spans about three quarters of the poster width and has broad cream margins above and on both sides. A second centered line directly below reads "SATURDAY 18:00" in the same navy lettering at about one third of the headline height. The two lines sit on a plain cream field with generous space between them. The middle band is an uninterrupted cream gap separating the type from the illustration. In the lower third, three orange lanterns hang at different heights above a small navy silhouette of a market stall. The stall has a rectangular orange awning, two thin supports and an empty counter. The lantern cords descend vertically and stop within the illustration area. All illustration marks stay below the cream gap. A narrow navy rule sits near the bottom margin. The paper has a matte surface; the lettering uses solid flat fills and straight, open letterforms. The view is straight on, with the entire rectangular sheet inside the frame. The remaining paper margins are blank cream.
```

### Single-reference sign edit

```text
Full-color outdoor photograph of the storefront in <ref_image_0>, preserving the building facade, doorway, camera viewpoint and daylight. Above the doorway, the same rectangular sign now has a plain cream face. Its centered main line reads "OPEN DAILY" in large dark-navy uppercase sans-serif letters, with even spacing and wide margins. A smaller centered line below reads "09:00–18:00" at half the main line's letter height. Both lines lie flat on the sign face and remain separated by a clear cream gap. The sign's original frame and mounting brackets retain their positions. The doorway, window reflections, wall materials and pavement retain the appearance and arrangement of the reference. The area immediately around each line is plain cream, while the surrounding facade keeps the lighting of the source photograph.
```

### Blank-area fallback

Replace the two lettering sentences in the poster example with: `The upper third is a flat blank cream panel, wide enough for a headline and one smaller line; all printed marks and illustration sit below it.` Add approved copy afterward in a graphics editor. This is an alternative production plan, not a promise that the model leaves pixels untouched.

## Unverified scope

The examples above, literal `\n` behavior, exact font/position reproduction, Korean/Hangul and other language-specific accuracy have not been tested in this local INT8 profile. Existing six-mode execution/QC evidence does not establish typography quality. No image generation or model/workflow change was performed for this documentation update.
