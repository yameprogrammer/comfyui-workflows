# MOSS agent CLI validation

2026-10-28, PC-HOME, existing ComfyUI 0.43.0, RTX 4090 24 GB. These are **new CLI** tests, separate from earlier direct workflow generation tests.

All seven modes passed offline dry-run, then actual `python scripts/generate_moss_image.py` end-to-end submission/upload/history/download/PNG decoding/result JSON checks. Each actual PNG was opened and independently recorded through `review_media.py pack/record`. No model downloads, dependency changes or server restarts were performed by this integration.

| Mode | PNG dimensions | Server seconds | CLI wall seconds | Result |
|---|---|---:|---:|---|
| t2i | 768 x 768 | 3.809 | 6.625 | PASS (bounded visual review) |
| layout | 768 x 768 | 5.343 | 7.984 | PASS (bounded visual review) |
| edit | 512 x 512 | 7.377 | 10.641 | PASS (bounded visual review) |
| multi-edit | 768 x 768 | 7.205 | 10.766 | PASS (bounded visual review) |
| control | 768 x 768 | 6.326 | 9.140 | PASS (bounded visual review) |
| color | 768 x 768 | 4.638 | 7.922 | PASS (bounded visual review) |
| depth | 768 x 768 | 4.705 | 8.078 | PASS (bounded visual review) |

Sampling: T2I probe 12 steps; Layout 25; Edit/Multi 30; Control/Color/Depth 25. Remaining defaults match the native mode-specific presets. Layout probe uses an explicit punctuation negative prompt because its example requests exactly MOSS.

Visual findings:
- t2i: Opened actual CLI PNG: matte blue teapot and orange fully visible on pale wood; clean ivory background, coherent materials/light. Bounded scene pass.
- layout: Opened actual CLI PNG: exact MOSS uppercase without punctuation at top; blue teapot left, orange right inside planned regions. Not pixel/font exact.
- edit: Opened actual CLI PNG and source: teapot changed blue to red; handle/spout/lid, orange/table/background broadly retained. No pixel-exact preservation claim.
- multi-edit: Opened actual CLI PNG and both references: blue teapot/orange foreground plus framed poster with legible exact 안녕하세요. Poster graphics/layout and object scale changed; identity/pixel preservation untested.
- control: Opened actual CLI PNG/maps: large gold sphere lower-left, smaller blue cube upper-right; approximate map region positions and near/far ordering followed.
- color: Opened actual CLI PNG/color map: sphere lower-left and cube upper-right follow colored regions; final gold/blue materials follow caption, not map ID colors.
- depth: Opened actual CLI PNG/depth map: large sphere lower-left appears nearer than upper-right smaller cube; bounded positional/depth pass.

Automated checks: **38 selected unit/regression tests passed**; five actual CLI invalid-input/collision/toolbox-output cases returned the expected exit codes. Static Python parsing and `git diff --check` passed. Input/model/queue/output-collision/timeout/metadata unit tests; strict shared-client submission opts out of auto-start/retry while existing caller defaults are preserved. Intent and existing H3 regressions pass. `tool_index_check.py` passes (one existing Yue2 catalog warning). All seven installed mode requirements were read from the local server without starting it.

Evidence is retained in the local caller validation workspace; decoded PNGs and `.api.json/.history.json/.result.json` under `validation/`, independent QC records under `reviews/`. API sidecars contain actual `/upload/image` returned input paths. Metadata retains `PENDING_VISUAL_REVIEW` by design; the separate review records are the visual verdict.

Scope: synthetic/generated stills only. Same installed SFT INT8/Qwen INT8/Flux2 VAE across modes. Single/multi Edit use community chinoll; Control uses community darask0. Real-person identity, 3/4-reference quality, large resolutions, arbitrary Korean paragraphs and production reliability remain untested. Original Edit weight license is not separately stated; commercial review required. Control author declares Apache-2.0 and discloses its separate training-depth source license. See AGENT_GUIDE.md.
