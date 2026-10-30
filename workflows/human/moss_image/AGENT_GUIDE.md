# MOSS-Image native agent tool

Status: `ready_experimental`. Use `python scripts/generate_moss_image.py` from the toolbox root. This is image generation, separate from MOSS speech and transcription.

When: local text-to-image, literal typography with visual review, pixel-box Layout, single/multiple reference editing, or color/depth composition control. When not: lossless masked editing, guaranteed face identity, exact font/layout reproduction, or production-guaranteed Korean paragraphs. Alternatives: existing Qwen inpaint for masks, existing locked character workflows for approved identities, Flux3/Krea2 for their established production routes.

## Discover and validate first

```powershell
python scripts/generate_moss_image.py --status
python scripts/generate_moss_image.py --help
python scripts/tool_intent.py "moss image edit"
```

Status reads local server/node/model listings only; it does not hash large weights or establish image quality. The CLI never downloads models, installs dependencies, starts/restarts ComfyUI, clears a queue, cancels a job, or changes security settings. Start a compatible native ComfyUI manually if unavailable. Default server: `127.0.0.1:8188`; local unauthenticated HTTP only. Existing shared model paths are used by the server.

## Seven modes

```powershell
python scripts/generate_moss_image.py --mode t2i -p 'Studio photograph of a blue ceramic teapot beside one orange on a pale oak table, soft window light, eye-level medium shot.' -o F:/my_project/moss.png
python scripts/generate_moss_image.py --mode layout --layout workflows/human/moss_image/layout_example.json -o F:/my_project/moss_layout.png
python scripts/generate_moss_image.py --mode edit -i F:/my_project/source.png -p 'Change only the blue teapot to red. Preserve its shape, the orange, background, lighting and framing.' -o F:/my_project/moss_edit.png
python scripts/generate_moss_image.py --mode multi-edit -i F:/my_project/scene.png -i F:/my_project/poster.png -p 'Image 1 supplies the foreground objects. Place a framed print of Image 2 behind them.' -o F:/my_project/moss_multi.png
python scripts/generate_moss_image.py --mode control --color-map F:/my_project/color.png --depth-map F:/my_project/depth.png -p 'Studio photograph of a gold sphere and a blue cube on a neutral gray floor, soft studio light.' -o F:/my_project/moss_control.png
python scripts/generate_moss_image.py --mode color --color-map F:/my_project/color.png -p 'A gold sphere and a blue cube on a neutral gray floor, studio photograph.' -o F:/my_project/moss_color.png
python scripts/generate_moss_image.py --mode depth --depth-map F:/my_project/depth.png -p 'A gold sphere and a blue cube on a neutral gray floor, studio photograph.' -o F:/my_project/moss_depth.png
```

Use `--prompt-file` for UTF-8 multiline captions; `--negative`, `--seed`, `--steps`, `--cfg`, and paired `--width/--height` override their preset fields. Seed 0 and empty negative prompts are valid. Dimensions must be multiples of 16; this local batch-1 profile limits dimensions to 4096 and area to 4 MiPixels. This is a resource bound, not a quality promise at extreme sizes.

| Mode | Preset defaults | Inputs |
|---|---|---|
| t2i | 1024², 25 steps, CFG 2.5, er_sde/simple | Full final-scene caption |
| layout | Dimensions from JSON, 25, CFG 2.5, er_sde/simple, SLG 22 early-half | Pixel-box JSON, optional caption override |
| edit | About 512² pixels, 30, CFG 4, Euler/normal, SLG 22 | Exactly one source |
| multi-edit | About 768² pixels, 30, CFG 4, Euler/normal, SLG 22 | 2-4 ordered references; 3/4-reference quality untested |
| control/color/depth | Map dimensions, 25, CFG 3, er_sde/simple | Both maps / color only / depth only |

Native model shift is 5; do not insert the plugin workflow's `ModelSamplingSD3` because its timestep scale differs. Edit uses `edit_format=Moss-Image-Edit` and the same ordered reference latents on both positive and negative branches. The CLI preserves reference aspect ratio, aligns to 16 and caps the long edge at 512 by default (`--reference-max-edge 256..1024`). Default output aspect follows the first reference at the preset pixel area. No denoise-based source preservation is implied: native editing still samples from noise with reference conditioning.

## Prompts and Layout

T2I: describe the finished visible scene in English with medium, subject, materials, spatial composition and lighting. Quote requested on-image wording exactly in its original language. Do not add quality tag spam. Edit: state the change and what must remain; for multi-edit explicitly assign each image's role. Control: describe the intended objects and surfaces; map colors are region IDs, not final object colors.

`layout_example.json` contains `width`, `height`, `prompt`, and `boxes`. Each box has integer pixel `x`, `y`, `width`, `height`, plus `type`, `description` and, for text, `text`. Native canvas `metadata: {type, desc, text}` is also accepted. Types: `object`/`obj`, `text`, `character`. Boxes must remain inside the canvas. No implicit coordinate or canvas rescaling occurs. All three native canvas/conditioning/latent sizes are kept equal. The CLI uses Create Bounding Boxes → MOSSImageLayoutPrompt, not a prompt enhancer that could erase the layout. Array literals are serialized using ComfyUI's supported `__value__` representation.

Keep actual typography review separate from spatial success. One measured Layout probe added an unwanted period; explicit punctuation wording/negative and a new seed corrected that example, not every possible string.

Control maps must be single PNG/JPEG/WebP frames matching the output size. Color maps use one flat RGB ID per region, black for unspecified; depth is grayscale near=white replicated to RGB. `--control-end 0.5` is the synthetic-map default; `--control-strength` defaults to 1. Edit/Control `--lora-strength` defaults to 1. No depth estimator or segmentation package is installed by this tool.

## Outputs, recovery and review

`-o` must point outside this repository. Output and `.api.json`, `.history.json`, `.result.json` sidecars are refused if any already exists. Explicit `--overwrite` preserves prior artifacts as `.previous.<run_id>` backups; dry-run does not move an existing PNG. Inputs cannot be overwritten even with that flag. Unique hashed image names are uploaded through the supported local `/upload/image` API; no direct copy into guessed Comfy input folders. Submitted API graphs are the actual uploaded paths and include all sampling parameters.

```powershell
python scripts/generate_moss_image.py --mode edit -i F:/my_project/source.png -p 'Change the teapot to red.' -o F:/my_project/plan.png --dry-run
python scripts/review_media.py pack -i F:/my_project/moss.png --intent 'blue teapot medium studio still' -o F:/my_project/reviews/moss
```

Dry-run is offline: validates inputs and writes the planned API/result sidecars, with explicit `DRY_RUN` upload placeholders. It does not check installed models; combine with `--status`. Metadata records task/mode, model filenames, prompt/negative, seed, references and hashes, processed sizes, actual uploaded names, prompt ID, server output, output hash/dimensions and timings. `visual_qc=PENDING_VISUAL_REVIEW` remains until an agent opens the image and records output-review independently.

Queue busy → fail without submitting/cancelling. Timeout → the server job may still run; inspect the recorded prompt ID before retrying. A lost submission response is **not retried**; status becomes `submission_uncertain` with client ID so the caller can inspect history before another submission. Per-output and MOSS-family locks serialize tool callers; never blindly remove a stale lock while its job might still be active. This CLI does not unload other model families or rewrite shared memory/session policy.

Exit codes: 0 success/status-ready/dry-run; 2 bad inputs or output collision; 10 server/upload unavailable; 11 missing native node/model; 12 busy/locked; 13 uncertain submission; 14 toolbox output blocked; 124 timeout with possible running job; 1 other inference/output failure. Normal output is JSON; brief queue/error logs go to stderr.

## Models and community limits

- Native SFT INT8: `moss_image_sft_int8_convrot.safetensors`, Qwen encoder `qwen3.5_9b_int8_convrot.safetensors`, existing `flux2-vae.safetensors`.
- Edit: community chinoll `moss_image_edit_lora_rank_64_bf16.safetensors`, not an OpenMOSS-authored extension. The original weight license is not separately stated; GPLv3 covers its project code, not automatically the weights. Commercial use needs license review. Repack Apache labeling is not automatically extended to the original weights.
- Control: community darask0 `moss_image_color_depth_control.safetensors`; the author declares Apache-2.0 and separately discloses Depth Anything V2 Large CC-BY-NC-4.0 as a training-depth source.

Only tiny synthetic/generated examples were reviewed. Pixel-exact preservation, real-person face identity, exact font/design copying and arbitrary Korean paragraphs are not guaranteed. Multi-reference scene content can combine while the poster design and object scale change. No new base model is downloaded on incompatibility.

Sources: [native integration](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/README.md), [Comfy-Org models/workflows](https://huggingface.co/Comfy-Org/MOSS-Image), [Edit author](https://huggingface.co/chinoll/Moss-Image-Edit), [Control author](https://huggingface.co/darask0/MOSS-Image-color-depth-control). [CLI validation matrix](TEST_MATRIX.md).
