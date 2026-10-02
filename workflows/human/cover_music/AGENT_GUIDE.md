# Cover music working guide

Status: ready_experimental. Local 31-second generation and optional reference SVC were measured; perceptual quality is a separate review.

Use for reference-melody music covers. For new songs use `generate_yue2_music.py`; for spoken lines use the TTS tools. Existing YuE2 files may contain other agents' changes: the staged wrapper reuses their graph builder without replacing it.

## Local setup

- Toolbox: `F:/Agent_media_tools`
- ComfyUI: `127.0.0.1:8188`, `yue2_3b_int8_convrot.safetensors`, `sheetsage2_bf16.safetensors`.
- Main CLI: standard Python 3.11, FFmpeg/FFprobe, Node for yt-dlp.
- Shared downloader: `F:/model/tools/cover-youtube`, yt-dlp 2026.8.19 + EJS 0.8.0. Passed through a child PYTHONPATH; the system Python installation is unchanged. `download --yt-packages` overrides it.
- SVC Python: `F:/ComfyUI_windows_portable/python_embeded/python.exe` (observed torch 2.13.0+cu130, transformers 4.57.3). Override with `voice --audio-python`.
- Shared Seed-VC: `F:/model/tools/seed-vc`, revision `51383efd921027683c89e5348211d93ff12ac2a8`. Override with `voice --seed-vc-repo`. Public model checkpoints download on first use if absent. These dependencies are not required for the generated-voice path.
- Shared runtime copies were created from the tested project cache; no existing portable packages were upgraded.

`doctor` reads server node/model availability and local paths. It does not prove a GPU run will succeed or install missing dependencies. Missing runtime on another machine: set the overrides, install the needed dependencies in that machine's isolated environment and smoke test. Do not blindly run Seed-VC's legacy pinned requirements against a working ComfyUI environment.

## Generated voice smoke (PowerShell)

Run from the toolbox. Choose new run/export directory names each time. Use an available local source and prepare matching style/lyrics text files in the project.

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/cover_music.py doctor
# Optional download; create a new source directory
python scripts/cover_music.py download --url 'https://www.youtube.com/watch?v=VIDEO_ID' --out 'D:/my_music/sources/song' --caption-language ja-orig
# 31-second example; choose a phrase after inspecting the actual song
python scripts/cover_music.py prepare --audio 'D:/my_music/sources/song/source.wav' --start 19 --seconds 31 --run 'D:/my_music/runs/take01'
python scripts/cover_music.py transcribe --run 'D:/my_music/runs/take01'
# Optional: extract matching automatic captions, then inspect/correct the file
python scripts/cover_music.py captions --run 'D:/my_music/runs/take01' --input 'D:/my_music/sources/song/source.ja-orig.json3'
python scripts/cover_music.py render --run 'D:/my_music/runs/take01' --style 'D:/my_music/style.txt' --lyrics 'D:/my_music/lyrics.txt' --lyrics-status user_supplied --seed 20261003 --ceiling 40
python scripts/cover_music.py export --audio 'D:/my_music/runs/take01/base.flac' --out 'D:/my_music/exports/take01_original'
```

A suitable style describes vocal range, genre, instruments and production. Example: `Japanese orchestral piano pop ballad, mature male baritone, warm resonance, expressive sustained singing, grand piano, acoustic guitar, restrained strings, intimate studio production`. Match language/style to the user; do not always choose Japanese or baritone. Lyrics use separate section tags such as `[Verse]` on their own line. `--lyrics-status automatic_unverified` preserves uncertainty if a smoke deliberately uses raw captions.

The ceiling is an upper bound, not an exact target. Do not pad music to disguise an early ending. Review any result whose duration reaches the ceiling. The wrapper saves `source_melody.abc`, the exact rendered ABC/style/lyrics, their hashes, graphs, prompt IDs, history and basic metrics.

## Optional requested reference voice

```powershell
python scripts/cover_music.py voice --run 'D:/my_music/runs/take01' --reference 'D:/Characters/packs/CHARACTER/voice/ref/clean.wav'
python scripts/cover_music.py export --audio 'D:/my_music/runs/take01/reference_voice/mix.wav' --out 'D:/my_music/exports/take01_reference'
```

Use 1–30 seconds of clean voice. Read the pack's `voice.json` to locate the actual reference and its provenance. No training required in this tested route. htdemucs → Seed-VC 44.1kHz SVC (`f0_condition=True`, 30 diffusion steps, CFG .7, auto F0 adjustment off, zero semitone shift) → RMS-matched vocal + accompaniment. The worker refuses >100ms duration mismatch rather than stretching blindly; sub-100ms tail differences are recorded. Output stays in the run. The original generated vocal is never overwritten.

Seed-VC warnings in the measured run included unused old checkpoint layers and rebuilt position/frequency buffers. Inspect unexpected missing **active learned weights**, silent output, model-load failures or new warnings instead of declaring success. The known audit is in `D:/cover-music/runs/yue2/sparkle_smoke/seed_checkpoint_audit.json`.

## Recovery and review

- Timeout: `python scripts/cover_music.py collect --run 'D:/my_music/runs/take01' --stage render --timeout 900`. For transcription use `--stage transcribe`. Poll the saved job instead of queueing another.
- Failed job: preserve its history/error and inputs; correct the cause and use a fresh run. Never interrupt another user's queue.
- HTTP 403: tested old yt-dlp 2026.07.04 failed; 2026.8.19 + Node/EJS succeeded. This is a compatibility finding, not a guarantee or an access-control workaround. If the current downloader fails, use a supplied local recording.
- Wrong lyrics: correct the exact segment's text. Wrong melody: inspect/fix the ABC before spending another render. Changed lyrics/score/settings need a new candidate.
- `export` refuses silent/clipped inputs and existing filenames, writes 24-bit WAV/192k MP3 and `review/`. It does not approve perceptual quality.
- Open `review/probe.json` and `review/spectrogram.png`; inspect actual audio when playback/listening is available. `python scripts/review_media.py record --pack 'D:/my_music/exports/take01_original/review' --verdict pending --opened --notes 'Technical checks done; melody and pronunciation require listening'`.

Report generation status, voice path, duration and unverified limitations. Give the user the playable MP3 and WAV link. Do not expose downloaded caption lyrics unnecessarily in chat or commit source media/models.
