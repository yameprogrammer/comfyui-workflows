# Higgs TTS 3 — PC-HOME original ComfyUI integration

Status: `ready_experimental`. Read `TEST_MATRIX.md` for measured results and unverified scope.

Use for short multilingual character speech, official inline emotion/prosody tags and local-reference voice conditioning. Use Qwen3-TTS when you need the existing locked VoiceDesign production path; cross-engine timbre identity is not guaranteed. Long-form speech and streaming are not validated here.

## Entry points

- Original server: `http://127.0.0.1:8188`, `F:\ComfyUI_windows_portable`, ComfyUI 0.41.1.
- Node: **Higgs TTS 3 (Isolated Engine)** / class `Higgs3IsolatedTTS`.
- UI: this directory's `neutral.json`, `emotion.json`, `reference.json`. Also installed in ComfyUI `user/default/workflows/higgs3_tts`.
- API: `workflows/agent/higgs3_tts/*.api.json`.
- Factory CLI: `scripts/generate_higgs3_tts.py`. Run with the toolbox's usual default `python` from `F:\Agent_media_tools`, and put outputs in your own project. Embedded Python's `_pth` suppresses script-directory imports; use the default Python client, not `python_embeded/python.exe -I` for toolbox CLIs.

```powershell
Set-Location F:\Agent_media_tools
python scripts/generate_higgs3_tts.py -t "안녕하세요. 오늘은 새로운 이야기를 시작합니다." -o F:\my_project\voice\neutral.wav
python scripts/generate_higgs3_tts.py -t "We finally made it. I am so glad to see you." --emotion elation -o F:\my_project\voice\happy.wav
python scripts/generate_higgs3_tts.py --text-file F:\my_project\line.txt --emotion sadness --ref-audio F:\my_project\character_ref.wav --ref-text-file F:\my_project\character_ref.txt -o F:\my_project\voice\sad.wav
```

Outputs include the requested audio plus `.api.json`, `.history.json`, and `.result.json`. The result stores worker model-load/generation time, CUDA allocated/reserved peaks, duration, model revision and original server prompt ID. It does not assert listening QC. References are copied locally into ComfyUI input with unique names so API graph replay remains possible; there is no external voice upload.

The CLI checks for a busy queue before submitting through the factory `queue_prompt` helper. Do not run another GPU job concurrently or interrupt someone else's job. A client timeout does not cancel the queued server job; inspect queue/history before retrying. ComfyUI cancellation terminates only the bridge's own worker. The bridge unloads ComfyUI models before its subprocess and the subprocess exits after every request, releasing Higgs VRAM. Cold-load overhead is included in end-to-end timings.

## Prompt and reference controls

Language follows the text; there is no undocumented language token. Korean and English were selected for the local test matrix.

`--emotion neutral` adds no tag. `elation`, `sadness`, `anger` prepend their official `<|emotion:...|>` token. Other official tags may be written directly into `--text` or the text file. Avoid adding the same emotion twice via both controls.

Emotion/style and speed/pitch/expressive tags belong at the sentence start. Pause tags belong at the pause location. Sound effects require the tag immediately followed by an onomatopoeia, such as `<|sfx:laughter|>Haha`. Unsupported tag names can be pronounced literally. The full catalog is in the official [PROMPTING.md](https://huggingface.co/bosonai/higgs-tts-3-4b/blob/main/PROMPTING.md).

Use clean local references you own or have permission to use, preferably a short solo speech sample with accurate transcript. Test fixture: `D:\Characters\packs\park_soft_v1\voice\samples\design_s03_explain.mp3`, an existing user-created Qwen3 VoiceDesign character sample. The owner's recorded clone fallback was not used. Converted reference, transcript and provenance hashes are under `F:\Agent_media_sandboxes\higgs3\validation`. This test does not change the character's locked Qwen3 production voice.

Default sampling is bf16/SDPA, temperature 0.8, top-p 0.95, top-k 50, seed 42, max-new-tokens 512. Approximately 25 audio token frames represent one second; the token limit is a ceiling, not a requested duration. Split long text at natural boundaries if generation hits the cap. No truncation/voice quality claim should be based only on exit code.

## Environment preservation

The original embedded Python stays on Transformers **4.57.3**, Torch **2.13.0+cu130**, and the existing audio patches. No Suite global installation or dependency upgrade was run.

Higgs runs in a separate process using `F:\Agent_media_sandboxes\higgs3\runtime` as its private dependency overlay: Transformers 5.3.0, huggingface-hub 1.3.0, tokenizers 0.22.2, numpy 2.2.6, safetensors 0.8.0; the existing Torch/torchaudio binaries are reused read-only. This is a separate engine process/dependency environment, not a second ComfyUI. `higgs3_worker.py --probe` reports import paths.

The inference implementation is a frozen copy of the already installed MIT-licensed TTS Audio Suite 5.4.16 / commit `a944650fde2cedc8791326030ea492d40384a70b` (`engine/native.py` plus codec config and LICENSE). Existing Suite nodes were not replaced. The old Suite Higgs v3 node expects a Transformers 5 main process; use the explicitly isolated node above on this PC.

Official weights: `F:\model\TTS\higgs_audio_v3\higgs-tts-3-4b`, repo `bosonai/higgs-tts-3-4b`, pinned revision `239f63fb7b02b1aa085f98d9efae5e35cc5523e8`. The inference worker uses local files with HF/Transformers offline mode and does not execute model-repository remote code. Installation metadata and private dependency lock are under the engine root.

## License

The user explicitly accepted the model license on 2026-10-16 before download/execution. The [official LICENSE](https://huggingface.co/bosonai/higgs-tts-3-4b/blob/main/LICENSE) includes a Creator Use Grant for publishing and monetizing creative audio/video on channels you control. Published creator content needs a clear **Boson AI's Higgs Audio** acknowledgment in the audio or prominently in the accompanying description. Suggested credit:

> This audio was created with Boson AI's Higgs Audio — https://www.boson.ai/higgs-audio

This grant does not cover third-party model hosting/APIs, model redistribution, or integration into externally provided products/services; those require separate commercial licensing. Keep all reference-voice rights/consents. See the full current license for its other conditions.

## Backup and recovery

Verified pre-install backup: `F:\backups\ComfyUI_env\env_20261016_232422_before_higgs3` (11.09 GiB), Manager snapshot at `F:\backups\ComfyUI_snapshots\env_20261016_232422_before_higgs3.yaml`. Source coverage: no missing files. Code/package hashes matched; only changing logs and live SQLite sidecars differed. `restore_supplement/comfyui.consistent.db` passed SQLite integrity checking; backup Python imports/CUDA were verified.

`restore_env.bat` overlays files and does not remove extra dependencies. For exact rollback, arrange an idle normal shutdown and reconstruct an empty portable destination from the backup, retaining a quarantine copy. Use the consistent DB snapshot instead of stale WAL/SHM/lock sidecars; preserve external `F:\model` and `F:\ComfyUI_data`. Full recovery notes and evidence are in backup `restore_supplement/HIGGS3_PREFLIGHT.md`. No actual live restore was performed.

To disable only this integration, arrange an idle restart after removing/disabling `ComfyUI-Higgs3-Isolated`; its private runtime and model files are separate from the original package tree. Preserve validation outputs and references until review is complete.

## QA and alternatives

After generation use `review_media pack`, open the actual probe/spectrogram, and record the checked scope. Local Whisper transcription is an imperfect check for omissions/language; acoustic pitch/mel summaries do not prove speaker identity or perceived emotion. Listening remains a separate requirement.

If you need the locked Park Soft VoiceDesign, use `generate_qwen3_tts.py --mode design` with the character pack's settings. If you need singing, use `generate_yue2_music.py` or `generate_minimax_music.py`. For lip-synced video use the established InfiniteTalk workflow after reviewing the voice output; Higgs itself produces speech audio.
