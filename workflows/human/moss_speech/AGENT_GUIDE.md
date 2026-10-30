# MOSS speech generation — Windows native

This is **speech generation**. `generate_moss_tts.py`, `generate_moss_ttsd.py` and `generate_moss_voice.py` are separate from the existing **transcription** tool `transcribe_moss.py`. Existing ComfyUI/Qwen/Higgs/Whisper environments, voice locks and project files are preserved.

Status: `ready_experimental`; actual generated samples and precise per-model evidence are linked in [the installation validation report](F:/MOSS-TTS/validation/VALIDATION_REPORT.md). Execution, automatic ASR comparison, perceptual listening, speaker similarity, and instruction/emotion following are distinct checks. No production quality promise follows from exit0.

## Installation and low-memory profile

Dedicated `F:\MOSS-TTS\.venv` Python3.12.11; official CUDA12.8 torch/torchaudio2.9.1; Transformers5.0.0; accelerate1.15.0. Full resolved lock at `F:\MOSS-TTS\requirements-lock.txt`. Source is official [MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS) commit `934d6826b084c46a0d033402174d5f8ac4ed2519`; TTSD source reference is official [MOSS-TTSD](https://github.com/OpenMOSS/MOSS-TTSD) commit `46973e425da227bfa3b315dcd7a4aba8b6be5574`, retained separately at `F:\MOSS-TTSD`. Same isolated speech-family runtime loads official HF model implementations from absolute local paths.

All four downloaded HF repositories declare Apache2.0 and were ungated when inspected. Source licenses are Apache2.0; retain notices for redistribution. No extra license-acceptance action was required. Model revisions and source/file hashes are preserved under installation `audit/`; the worker checks reviewed model Python hashes before execution and sets offline local loading.

| Model | Official HF repo | Fixed revision |
|---|---|---|
| TTS v1.5,8B | OpenMOSS-Team/MOSS-TTS-v1.5 | cdd3b911b1585e3f2dbc7775ef10f9926f58850a |
| TTSD v1.0,8B | OpenMOSS-Team/MOSS-TTSD-v1.0 | c7cd852d87aff71cab5bd2b9b05509cedc0ef1ba |
| VoiceGenerator,1.7B | OpenMOSS-Team/MOSS-VoiceGenerator | 97521ec2b6f3ec5026ac1f5751f8fc302d82c2d4 |
| Audio Tokenizer,1.6B | OpenMOSS-Team/MOSS-Audio-Tokenizer | 3cd226ba2947efa357ef453bcad111b6eafba782 |

Reviewed [official OOM issue165](https://github.com/OpenMOSS/MOSS-TTS/issues/165) and official `moss_tts_delay/llama_cpp/README.md`, staged-loading configs and C bridge source. The current bridge searches for `.so` and build script requires bash/GCC/-fPIC; a supported native Windows bridge was not established. No community binary or WSL was added. This installation instead uses the issue's official HF CPU-offload approach, plus staged GPU use for the official audio tokenizer.

1. Load processor/tokenizer on CPU; if a reference exists, move the float32 audio tokenizer to GPU only to encode, then return it to CPU.
2. Load the generation model BF16/SDPA using `device_map=auto`, GPU weight budget14GiB and CPU placement budget24GiB. Keep the audio tokenizer off GPU during generation. This is **intentional CPU offload**, not a silent CPU-only fallback. Actual device map, BF16 and SDPA settings are recorded.
3. After generation, copy raw codes to CPU, release generator and check remaining GPU allocation is below512MiB. Only then move audio tokenizer to GPU and decode.

On PC-HOME RTX4090/driver617.42/64GiB host RAM, the short TTS tests use approximately14GiB peak allocated VRAM. CPU offload makes 8B generation slower; use measured run summaries.14GiB is a weight-placement budget, not a process peak guarantee. Coordinate heavy GPU activity; an internal lock serializes this speech family only. It does not reserve the GPU against ComfyUI or the transcription environment. No existing jobs are terminated. Process exit releases the model; peak torch memory is different from total WDDM/nvidia-smi occupancy.

No CUDA Toolkit, FlashAttention, TensorRT, vLLM, WSL, driver or security-setting change was added. Native torch SDPA's cuDNN kernel is disabled in this worker as the official model card recommends; this affects only the worker process. WAV I/O uses soundfile and explicit tensor reference encoding, avoiding torchcodec. The official processor rejects a forwarded `local_files_only` kwarg; the wrapper omits it for that constructor while keeping absolute local paths and offline environment. The first failed call and fixed retry are retained.

## MOSS-TTS v1.5: Korean speech and voice reference

From toolbox root:

```powershell
python scripts/generate_moss_tts.py -t "안녕하세요. 오늘은 새로운 음성 도구를 시험합니다." --language Korean -o F:/my_project/moss_ko01
python scripts/generate_moss_tts.py -t "제 목소리로 새 문장을 읽어 봅니다." --language Korean --ref-audio F:/my_project/authorized_reference.wav -o F:/my_project/moss_clone01
```

Use a clean local reference under30seconds. The worker reads it, normalizes/resamples a tensor for the official processor and never modifies the source. v1.5 supports Korean among31languages; language tags are recommended. Documented controls include language, reference identity, punctuation and explicit `[pause X.Ys]`. **No undocumented emotion tags or guaranteed free-form emotion control are exposed for TTS/TTSD.** Emotion via reference style is not equivalent to validated explicit emotion control. For an established Qwen/Higgs production voice or explicit emotion control, retain the existing tool when appropriate.

Tests used an authorized local owner reference; source recordings and character-pack identities are not distributed. This bounded test did not change any production voice lock.

## MOSS-TTSD v1.0: two-speaker dialogue

TTSD1.0 supports Korean among20languages. Its official workflow is **continuation**: provide one clean reference and exact transcript per speaker, use ordered `[S1]`/`[S2]` target dialogue, encode each reference, encode concatenated prompt audio, prepend the tagged reference transcripts, and decode after trimming the prompt. The wrapper implements that API; it does not simply concatenate separately synthesized turns.

```powershell
python scripts/generate_moss_ttsd.py -t "[S1] 안녕하세요. 함께 이야기해 볼까요? [S2] 좋아요. 천천히 시작해 봐요." --ref-audio F:/my_project/speaker1.wav --ref-text "첫 참고 음성의 정확한 발화" --ref-audio F:/my_project/speaker2.wav --ref-text "두 번째 참고 음성의 정확한 발화" -o F:/my_project/moss_dialogue01
```

Use only voices with rights/consent. Local tests select two user-locked fictional VoiceDesign samples, with provenance and exact text. A project sample labeled “approved” but sourced from another real person's interview was excluded. Do not infer ownership from the presence of a file. Do not promise correct speaker switching or voice identity from ASR alone.

## VoiceGenerator: English/Chinese voice design

```powershell
python scripts/generate_moss_voice.py -t "Hello. This new voice was designed here, on this computer." --language English --instruction "A warm adult woman, clear medium-high pitch, gentle smile, moderately brisk American English." -o F:/my_project/moss_design01
```

VoiceGenerator's documented direct languages are **English and Chinese**. It accepts natural-language voice/style instructions (including emotion, speed and pitch). No direct Korean support is promised; the wrapper rejects Korean in design mode. A generated English voice can be passed as a local `--ref-audio` to TTS for a short Korean bridge test. That does not guarantee cross-language identity preservation. Contrasting design examples, acoustic measurements and pending listening judgments are in validation.

## Outputs, limits and review

All three commands require a new/empty **output directory** in the caller project, outside `F:/Agent_media_tools`. Validation samples are intentionally under `F:/MOSS-TTS/runs` as authorized. No existing audio or subtitles are overwritten. Outputs: `speech_<message>_<segment>.wav` (24kHz mono PCM16), `raw_generation_<n>.npy`, `run_summary.json`. TTSD can produce more than one audio segment; inspect all listed files. No automatic concatenation, mastering, loudness modification of source, video editing or upload.

The summary records source/model revisions, reference hashes, actual placement/attention, seed, generation steps, EOS, stage times, output duration/peak/RMS and peak torch VRAM. Raw generated codes and FLOAT WAV are retained in the current worker. PCM exports above0.98peak are attenuated, with gain recorded; raw overshoot beyond1.0 still warns for review. A contrast probe peaked1.031364 at2samples and was re-decoded from its preserved raw codes into a separate FLOAT plus safe PCM copy; the original failed file remains. Default max_new_tokens512; use short text first. Reaching the limit or lacking EOS warns and returns2; do not treat truncated speech as success. Exit0 means `generated_unreviewed`, not quality approval. Exit1 is runtime failure; argument/output guards return2 without inference.

Each invocation releases its worker. Inspect `run_summary.json`, actual WAV and `review_media` pack. Technical probe/spectrogram and offline ASR can support checking word content and obvious clipping/silence, but they do not establish pronunciation naturalness, timbre identity or emotional expression. Keep those pending without direct listening. No long-duration speed estimate is implied by short samples.

Measured samples and A/B references are indexed in [the listening guide](F:/MOSS-TTS/runs/LISTENING_GUIDE.md). The two contrasting English design prompts both produced5.28s clips, so this test does not establish requested speed control despite different pitch estimates. Owner-reference and repeated-clone median pitch estimates were close, but pitch is not a speaker-identity measurement. All Korean and original English sample texts matched offline CPU Whisper-medium after whitespace/punctuation normalization; this is not a human pronunciation approval.

## Reproducible setup

Installation commands (already performed with explicit approval):

```powershell
git clone https://github.com/OpenMOSS/MOSS-TTS.git F:\MOSS-TTS
git clone https://github.com/OpenMOSS/MOSS-TTSD.git F:\MOSS-TTSD
$env:UV_CACHE_DIR='F:\MOSS-TTS\.cache\uv'
uv venv --python python3.12 F:\MOSS-TTS\.venv
uv pip install --python F:\MOSS-TTS\.venv\Scripts\python.exe torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python F:\MOSS-TTS\.venv\Scripts\python.exe -e F:\MOSS-TTS transformers==5.0.0 'accelerate>=1.10.1' soundfile==0.13.1 pybase64 requests
```

Pinned model downloads, static code review and helper scripts are retained in installation `audit/` and `validation/`; they used official HF snapshots into `models/`, not user-audio upload. Source code is retained in this tool's human pack for the launcher/worker; deployed worker lives at installation root. Future updates require a fresh source review and actual WAV validation. Do not update another tool's Python environment to satisfy MOSS dependencies.


## Deployment root

The launcher accepts `MOSS_SPEECH_ROOT` to locate an existing isolated installation. Documented F-drive locations are deployment examples/defaults, not bundled local configuration. No environment, weights, source recording, validation media or machine-specific Python path is committed. Set the variable for a different installation layout; do not mix ML environments.
