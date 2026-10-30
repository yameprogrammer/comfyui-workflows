# MOSS-Transcribe-Diarize — Windows native HF

Status: `ready_experimental`. Local execution verified on PC-HOME RTX 4090 (2026-10-19 UTC). Korean real-recording and multi-speaker accuracy remain unverified.

## When to use

Local speech transcription with anonymous speaker IDs and timestamps. No API, ComfyUI node, WSL, server, or shared Python package changes are required. Use an existing approved Whisper workflow when its measured accuracy is preferable; this installation does not replace it.

## Entry and example

From `F:\Agent_media_tools`:

```powershell
python scripts/transcribe_moss.py -i F:/my_project/speech.wav -o F:/my_project/moss_take01
python scripts/transcribe_moss.py -i F:/my_project/speech.wav -o F:/my_project/moss_take02 --max-new-tokens 4096
```

`-o` is a required new or empty **directory outside both the toolbox and installation**. Exit 0 means execution completed (or exact-zero silence skipped); exit 2 means output needs review (token cap, missing parsed segments, invalid timestamps), or CLI argument/output guards refused the request before inference; exit 1 means execution failed. A preflight refusal prints its reason without creating a run summary. Read `run_summary.json` and raw text before use. It does not overwrite existing subtitles or chunk recordings automatically. A single invocation uses the official processor's internal 30-second audio feature chunks, which is not transcript chunking or an identity stitching system.

The thin stdlib wrapper launches `F:\MOSS-Transcribe-Diarize\.venv\Scripts\python.exe -s F:\MOSS-Transcribe-Diarize\moss_worker.py`. It removes inherited PYTHONPATH, sets isolated F-drive HF/Numba caches and offline loading, checks reviewed source hashes, and requires CUDA:0, BF16, and SDPA on both the text and audio submodels. It raises an error instead of falling back to CPU/eager. One MOSS invocation at a time is enforced with a Windows file lock. Serialize heavy GPU jobs with other tools; this lock does not reserve or stop ComfyUI jobs.

## Outputs and checks

`raw_transcript.txt`, `segments.json`, `subtitle.srt`, `subtitle.ass`, `run_summary.json`. Raw model text is retained before subtitle parsing; no automatic text repair. Standalone ASS uses 1920x1080 layout defaults, so adjust layout in the caller project for the target video. No burn-in or original source modification occurs.

Summary records duration, versions, selected revisions, actual parameter devices/dtypes and attention configs, generated tokens, inference and total wall time, peak PyTorch allocated/reserved VRAM, and warnings. PyTorch VRAM is process allocation, not total WDDM/nvidia-smi occupancy. Check process exit and GPU state after use. Last timestamp alone does not prove complete transcription; compare speech boundaries and content. End-to-end time includes imports/loading, and varies with caches and GPU contention.

Exact zero waveform produces empty transcript/segment/subtitle content (ASS keeps its header) without loading the model. Nonzero noise/music is **not VAD filtered**; an empty parsed result is ambiguous and warns for review. No claim of general no-speech/hallucination handling. Hitting the token cap warns and returns 2; increase the limit deliberately or prepare caller-selected segments in the project. Never assume a capped transcript is complete. Anonymous S01/S02 IDs do not guarantee the same real person across files or separately processed chunks.

## Prompt

Default is the official complete transcription instruction with start timestamps, `[S01]` speaker labels, speech text and end timestamps. `--prompt` **replaces** it; retain the complete format instruction if adding domain words. There is no `--hotwords` flag or attention flag in the official CLI. The strict wrapper has fixed SDPA.

## Installation and pins

- Official source: https://github.com/OpenMOSS/MOSS-Transcribe-Diarize
- Source commit: `e3bdd93f8ad58418e04659818efd5fd87a0bc486`; contains attention fix `cb765f2b0fe6f7a298aa2002e2281ae693d1f3c3`.
- Model: https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize
- Model revision: `704aa4a9c304e8520be88901e0d1960158ef5b15`, downloaded into `F:\MOSS-Transcribe-Diarize\model` (absolute local path avoids Windows repo-ID slash conversion).
- Python 3.12.11 venv; torch/torchaudio 2.8.0+cu128 from official Windows CUDA wheel index; Transformers 5.16.1. Driver observed 617.42. CUDA Toolkit, FlashAttention, vLLM and torchcodec were not added.
- Full resolved versions: `F:\MOSS-Transcribe-Diarize\requirements-lock.txt`; provenance/hashes: `audit\code-review.json`, `audit\installation-manifest.json`.
- Reviewed all three model Python sources before remote-code execution. Strict worker verifies their SHA256 and loads locally/offline. Review again before changing source/model revision; source review is not a formal security certification.
- Python base interpreter is existing uv-managed `python3.12`. Venv is isolated; base interpreter must remain available.

Recorded install commands (installation was explicitly approved):

```powershell
git clone https://github.com/OpenMOSS/MOSS-Transcribe-Diarize.git F:\MOSS-Transcribe-Diarize
$env:UV_CACHE_DIR='F:\MOSS-Transcribe-Diarize\.cache\uv'
uv venv --python python3.12 F:\MOSS-Transcribe-Diarize\.venv
uv pip install --python F:\MOSS-Transcribe-Diarize\.venv\Scripts\python.exe torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python F:\MOSS-Transcribe-Diarize\.venv\Scripts\python.exe -e F:\MOSS-Transcribe-Diarize transformers==5.16.1
$env:HF_HOME='F:\MOSS-Transcribe-Diarize\.cache\huggingface'
F:\MOSS-Transcribe-Diarize\.venv\Scripts\hf.exe download OpenMOSS-Team/MOSS-Transcribe-Diarize --revision 704aa4a9c304e8520be88901e0d1960158ef5b15 --local-dir F:\MOSS-Transcribe-Diarize\model
```

Official CLI alternative (its loader can fall back; inspect actual execution):

```powershell
F:\MOSS-Transcribe-Diarize\.venv\Scripts\mtd-subtitle.exe F:/my_project/speech.wav --backend hf --model F:/MOSS-Transcribe-Diarize/model --device cuda:0 --dtype bf16 --max-new-tokens 4096 --out-dir F:/my_project/moss_official01
```

Keep `--out-dir` new/empty yourself for the official CLI. Prefer the strict wrapper for routine use. The official Chinese default prompt is complete; omitting `--prompt` preserves it. User audio must remain local; do not send it to APIs, Hub repositories or Library.

## Measured validation and remaining limits

- 1s exact-zero WAV: silent skip, empty segments, no GPU model loading. First direct worker run exposed console cp949 printing failure after files were saved; UTF-8 console fix added, retest recorded separately.
- 15.382375s synthetic English, Windows Microsoft Zira Desktop, known text: CUDA:0 / all floating parameters BF16 / model+text+audio SDPA; 119 tokens, 6 segments, last end 14.72s; no cap, bounds violation or structural warning. Inference 4.222s, total 10.830s; peak allocated 1,896,364,032 bytes, reserved 1,992,294,400 bytes. Transcript misrecognized “stays” as “stage”; content accuracy is not perfect. This is a synthetic execution test, not Korean or real-world diarization validation. No direct listening evaluation was performed.
- GPU occupancy returned near prior baseline after the worker exited (observed 6697MiB vs 6564–6680MiB before; other desktop/ComfyUI usage varies). Existing ComfyUI PID 3612 remained running. No MOSS worker process retained.
- Thin wrapper retest: same 119 tokens / 6 segments; inference 3.640s, total 9.827s, same peak allocation and transcript. UTF-8 silence retry exit 0; deliberate 8-token cap exit 2 with raw output retained and truncation warning; existing output and toolbox-output guards exit 2. Intent search finds MOSS; tool index check has 0 errors and one unrelated existing `generate_yue2_music.py` catalog warning. `uv pip check` passed all 68 installed packages.
- Historical source-dependent tests were initially blocked by an unavailable private recording; no source recording or private filename is included in this tool repository. See the later bounded validation state below.
- No measured 90-minute result or performance extrapolation. General multi-speaker attribution, Korean accuracy, long-recording omissions and timing quality remain unverified.

Validation evidence is retained in the caller workspace, outside this repository. Do not publish private recordings or transcripts.

## Work stopped — 2026-10-19 latest direction

User clarified the intended task is TTS/TTSD/voice generation. Further transcription validation is stopped; preserve this installation and completed results. It is not a TTS solution. Already-started Korean30s and full264.149s inference completed before stop; CUDA/BF16/SDPA passed, full inference58.996s, peak allocated3.97GiB,2141/4096tokens,last timestamp264.11s. No reference-comparison or listening quality approval was completed. See [durable stop/result report](F:/MOSS-Transcribe-Diarize/validation/20261019/STOP_REPORT.md). Prior missing-original paragraph is historical; follow-up explicitly allowed existing edited source for these runs. No new TTS installation authorized.


## Deployment root

The launcher accepts `MOSS_TRANSCRIBE_ROOT` to locate an existing isolated installation. Documented F-drive locations are deployment examples/defaults, not bundled local configuration. No environment, weights, source recording, validation media or machine-specific Python path is committed. Set the variable for a different installation layout; do not mix ML environments.
