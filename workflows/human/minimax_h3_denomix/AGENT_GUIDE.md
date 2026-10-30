# DenoMix H3 R2V Turbo 8+2

Status: `ready_experimental`. Separate opt-in CLI; existing H3 tools/defaults remain unchanged.

```powershell
python scripts/generate_minimax_h3_denomix.py --status
python scripts/tool_intent.py "denomix"
python scripts/generate_minimax_h3_denomix.py -i F:/my_project/reference.png --prompt-file F:/my_project/prompt.txt -o F:/my_project/denomix_take01.mp4 --duration 5 --seed 42 --dry-run
python scripts/generate_minimax_h3_denomix.py -i F:/my_project/reference.png --prompt-file F:/my_project/prompt.txt -o F:/my_project/denomix_take02.mp4 --duration 5 --seed 42
python scripts/generate_minimax_h3_denomix.py --status --job-id RETURNED_PROMPT_UUID
```

The existing local ComfyUI must already run. Status is read-only. Dry-run validates inputs and writes API/metadata sidecars without server access, staging images or submitting jobs. No automatic installs, downloads, service starts/restarts, queue cancellation, interrupts or global memory cleanup. An occupied queue is refused before image staging. A timeout leaves the job running; inspect its saved ID before deciding to retry.

`-o` must be a new MP4 path outside this toolbox. Existing video/sidecars are refused. Outputs, source references and audit data belong in the caller's project. Sidecars: `.api.json`, `.meta.json`, `.history.json`. Metadata preserves reference hashes, seed, requested/aligned duration, prompt ID, server output and local output. On timeout the metadata status is `pending`; a connection failure while submitting is `submission_unknown`, with no automatic resubmission.

## Duration and tested scope

Default requested duration: **5 seconds**. Local operating maximum: **10 seconds requested**. Negative, zero, NaN, infinity and values above10 are rejected before server requests or submission. This is an operational policy for this measured configuration, not the base model's capability ceiling.

Frames align upward to `17k+5` at24fps:5s becomes124frames/5.166667s;10s becomes243frames/**10.125s**. Thus the output may exceed the requested10s slightly. See `frame_count` and `aligned_duration_sec` in metadata. The raw UI Float is not bounded by this CLI; use the CLI for the guarded policy.

H3 official documentation describes up to about15s. In the measured4090/64GB desktop run,15s requested362frames but refinement node203 was deliberately interrupted after commit headroom fell to305MiB, VRAM reached23982MiB and pagefile usage grew. **No actual OOM exception, no completed15s output, no universal hardware incompatibility claim.** It was not retried. See [test matrix](TEST_MATRIX.md).

## Graph and prerequisites

896×512 first pass →1792×1024 output. Alibaba Turbo8steps, latent upscale×2, then final2steps with DMD Turbo and rank16 SoL refiner. Stage1 audio is frozen during refinement. INT8 video VAE, FP32 audio VAE, existing NVFP4 AWQ H3 encoder. The author's larger INT8 text encoder was not duplicated.

Use existing DENO Custom Nodes, H3 Latent Upscaler, KJNodes and VideoHelperSuite plus native H3/attention nodes. `--status` checks missing nodes and model dropdown paths. Models remain outside Git in the shared model library. [Manifest](MODEL_MANIFEST.json) records pinned source revisions, sizes and SHA256 for added model data. The preset uses the existing library's relative subfolders; adjust a model's relative dropdown path when deploying to a different library layout, without copying weights into the toolbox.

## Prompt and review

Apply `generation-prompt` with the H3 R2V six sections: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`. Assign every `<Picture n>` one role. English scene directions; dialogue can remain Korean, e.g. `(S1) <d>[Korean]안녕하세요. 오늘도 좋은 하루 보내세요.</d>`.

Review actual first/middle/last and consecutive frames using `output-review`. Within-shot appearance, source identity, requested motion, Korean transcription, pronunciation and lip sync are separate claims. Local MOSS transcription is optional and must run serially with GPU generation; no new ASR is installed by this CLI. ASR match alone does not approve voice quality or phoneme sync. No direct listening/full realtime playback approval was obtained in the recorded tests. No matched original-H3 baseline was generated, so do not claim superiority.

Workflow author DENO; GPL-3.0-only workflow terms are preserved in [WORKFLOW_LICENSE.txt](WORKFLOW_LICENSE.txt). Model and custom-node licenses remain separate. Source: [author workflow](https://huggingface.co/Deno2026/MiniMax-H3-DenoMix/blob/489aa1513a65fd188fd0a043c9da2eac10587910/workflows/Deno_MiniMax_H3_R2V_Turbo_8plus2.json), [NVIDIA project](https://nvlabs.github.io/Sana/Sol-Refiner/).
