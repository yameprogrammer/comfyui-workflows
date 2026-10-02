---
name: yue2-cover
description: Create short YuE2 music covers from local recordings or YouTube sources using SheetSage2 melody transcription, explicit lyrics, generated vocals, and optional reference singing voice conversion. Use for 커버곡, YuE2 cover smoke, or changing a cover singer. Not for ordinary spoken TTS or MiniMax song generation.
metadata:
  version: 1.0.0
---

# YuE2 cover

Factory CLI: `F:/Agent_media_tools/scripts/cover_music.py`. Run commands from `F:/Agent_media_tools`; all output paths belong to the caller's project. Skills are instructions, not installed CLIs. This file is agent-neutral: any agent can read it and invoke the CLI.

Read [the working guide](F:/Agent_media_tools/workflows/human/cover_music/AGENT_GUIDE.md) for exact commands, setup, and recovery. Start with `python scripts/cover_music.py doctor`.

## Choose the voice path

- Default: **generated voice**. YuE2 creates the singing from style + lyrics + reference melody. Preserve `base.flac` and export it directly. No character reference is applied.
- Only when requested: `voice --reference clean.wav` separates the **generated** cover with htdemucs, applies Seed-VC v1 SVC to the vocal, and remixes. The base stays available. A speech reference does not guarantee matching singing identity.
- If a user later asks to remove the reference voice, export the saved base; do not regenerate unnecessarily.

## Working sequence

1. `download` if needed; otherwise use the local audio. A failed download is not an unavailable song. Check downloader/runtime compatibility once, then report the real blocker. No repeated identical retries or automatic account-cookie extraction.
2. Select a coherent 20–45s vocal phrase. `prepare` creates a fresh project run, records hashes and times, and cuts it. This wrapper supports up to 60s input; full-song operation needs a separate evaluated plan.
3. `transcribe` saves SheetSage2 melody ABC. Open the score, inspect tempo/key/voice parts and obvious transcription errors. Keep the unmodified source score; pass an edited copy using `render --abc` if needed. Do not claim melodic fidelity from valid syntax alone.
4. Supply style and section-tagged lyrics matching the selected segment. Optional `captions` extracts local JSON3 automatic captions, labeled **unverified**. Inspect/correct them before quality work. Always pass explicit lyrics: the older generic CLI can otherwise substitute its demo lyrics. Do not infer that an empty lyric disables vocals.
5. `render` creates the base. Seed and graph are saved. It refuses duplicate submissions. After timeout use `collect --stage render`; a timeout does not cancel the queued job. Use a fresh run for a new candidate, not the existing job's ID.
6. Optional requested reference voice; then `export` creates WAV/MP3 and an output-review pack. Preserve the base, converted vocal, accompaniment, and metadata separately.
7. Open the probe and spectrogram; verify non-silence, no clipping, duration, and whether the output hit its ceiling. Listen for melody, lyrics, pitch, artifacts and speaker likeness where audio listening is available. Use the factory `output-review` record; leave subjective checks **pending** if you did not listen. A preview can be delivered as a pending smoke, never an approved master.

## Scope of evidence

2026-10-03: 31s input → 31.32s Japanese Sparkle cover on RTX 4090, YuE2 INT8 / 32 steps / melody mode. Generated-voice preview received positive user feedback. Reference-voice pipeline also produced a file, but speaker similarity and Japanese pronunciation were not systematically verified. This is a single smoke, not evidence that every language, melody, or full song works.

Do not hardcode the Sparkle URL, its lyrics, or the oh_minsik character into future jobs. No upload/publication is part of these commands. Models and runtimes live outside the tool repository; project artifacts stay in the requesting project.
