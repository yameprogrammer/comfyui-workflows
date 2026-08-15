# Agent quality guards Implementation Plan

> **For agentic workers:** Execute tasks in order. Each task is independently testable. Commit after each phase (P0 / P1 / P2).

**Goal:** Stop agents from taking the wrong tool or the wrong prompt dialect, then raise EDIT/I2V/look ceilings that we can code here.

**Architecture:** Soft docs already exist. This plan adds **fail-loud CLI gates**, **intent ranking**, and **small compiler parts**. No new engines (Revideo/Natron). No model weights.

**Tech Stack:** Python factory CLIs, `lib/tool_intent.py`, `lib/clip_quality.py`, `lib/edit_*`, unittest.

## Global Constraints

- Media writes stay outside the toolbox (`die_if_toolbox`, exit 14).
- Examples use `%AGENT_WORKSPACE%`, never `dumps/`.
- Prompt gates default ON; `--force-prompt` only for debug.
- Korean skill/catalog one-liners stay in sync with code.

---

### Task 1 — Intent ranking + YouTube example paths (P0-1, P0-4)

**Files:** `lib/tool_intent.py`, `tests/test_tool_intent.py` (create if missing)

- Phrase boosts: `(자막, 편집)`, `(훅, 자막)`, `(예능, 자막)` → `render_title` / `render_edit`
- YouTube ingest: drop lone `자막` or require `유튜브`/`youtube`/`레퍼` with it
- Replace `dumps/yt_demo` with `%AGENT_WORKSPACE%/refs/yt_demo`

Verify: `python scripts/tool_intent.py "쇼츠 자막 넣고 편집"` ranks EDIT first.

### Task 2 — Shared prompt dialect gate (P0-2, P0-3, P1-7)

**Files:** Create `lib/prompt_dialect_gate.py`  
**Wire:** `scripts/generate_anima.py`, `lib/anima_runner.py` (no default soup), `scripts/generate_i2v.py`, `scripts/generate_camera_move.py`, `scripts/generate_minimax_music.py`

- Anima: empty/`DEFAULT_POSITIVE` soup → `PROMPT_DIALECT` fail; hint `anima_2d.md`
- I2V: reuse `check_i2v_prompt`; **look-hits fail** unless `--force-prompt`
- MiniMax caption: reject visual-still language (`a woman stands`, `photoreal`, `8k`)
- Each generate CLI `--help` epilog: matrix + dialect path

### Task 3 — I2V check-prompt default + freeze (P1-5, P2-13)

**Files:** `lib/clip_quality.py` (`ok` logic), `scripts/generate_i2v.py`, `scripts/episode_i2v.py` if present, `lib/edit_compile` / assemble if freeze-pad detect exists

- Fix `check_i2v_prompt` `ok` so look-redescribe cannot pass via `or has_motion`
- Default reject; `--force-prompt` prints WARN and continues
- Strengthen default I2V negative with freeze/identity tokens if missing
- EDIT/assemble: refuse clip that is still-image padded (if a detector already exists; else skip)

### Task 4 — Caption face avoidance (P1-8)

**Files:** `lib/edit_title.py` / `lib/edit_motion.py` or skill + `compose` default  
**Skill:** `skills/video-edit/SKILL.md`

- If overlay/title has no `--y` and layout is yeonung/caption on 9:16, default `y=0.82`
- Document: CU → y≥0.82

### Task 5 — Key plate + look.amount (P1-9, P1-10)

**Files:** `lib/edit_look.py`, `lib/edit_compile_ffmpeg.py`, `tests/test_edit_look.py`

- `key.background` may be an existing image/video path → extra `-i` + overlay
- `look.amount` 0–1 lerps named look toward identity

### Task 6 — P2 leftovers

- MIDI voicing/rhythm slightly thicker (`lib/midi_arrange.py`) — small, no new SF2
- Motion `ease` (`linear` default, `out_cubic` optional) in `compose_motion` / compile
- `tool_index_check` 8 catalog warns: add missing scripts to `catalog.json`
- `docs/agent_edit_pipeline_design.md` status: v2 stagger + v3 look shipped; Revideo/Natron still later

### Task 7 — Still-QA before motion (P1-6) — warn-only on one-off

**Files:** `scripts/generate_i2v.py`

- If `--qa-record` missing and cwd looks like an episode shot folder, WARN
- Episode `episode_i2v` already has clip gates — do not invent a new hard gate for loose `-i` files

---

Execute inline in this session: Task 1 → 2 → 3 → 4 → 5 → 7 → 6. Commit per phase.
