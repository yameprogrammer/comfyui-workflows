# MIDI Skeleton Rearrangement Implementation Plan

Canonical copy of the session plan. Execute task-by-task.

See the approved plan in the session `plan.md` for full TDD steps.

**Goal:** Comfy-free VOICE/INGEST chain: harmonic skeleton → new-genre MIDI bed → optional WAV preview → MiniMax/Suno handoff pack.

**CLIs:** `extract_music_skeleton.py` · `generate_midi_arrangement.py` · `generate_midi_render.py` · `generate_midi_cover_bed.py`

**Default keep:** `harmony_only`. No Suno API, no MidiPilot, no Omnizart, no basic-pitch hard dep.
