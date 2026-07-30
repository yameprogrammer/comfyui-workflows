# Full Sheet + InfiniteTalk Fix Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Prefer small commits after each task’s acceptance check.

**Goal:** Restore trustworthy production paths for (1) InfiniteTalk SI2V and (2) `character_full_sheet`, and stop agents from selecting broken tools labeled “ready.”

**Architecture:** Two independent tracks sharing a reliability layer. Track IT repairs the Comfy node contract + preflight for `generate_s2v --backend infinitetalk`. Track FS fixes prompt/size/engine/approve gates in the character sheet pipeline so “approved / missing_mvp=[]” cannot mean visual garbage. Shared track H adds backend health checks and catalog honesty.

**Tech Stack:** Local ComfyUI (`F:\ComfyUI_windows_portable`), Python factory CLIs under `scripts/`, `lib/`, `characters/sheet_presets.json`, `video_backends.json`, failure notes under `failures/`.

**Related SSOT:**
- Spec / open request: [docs/FIX_REQUEST_2026-07-30_full_sheet_and_infinitetalk.md](../../FIX_REQUEST_2026-07-30_full_sheet_and_infinitetalk.md)
- Failure notes: `FN-20260729-001` (full_sheet), `FN-20260729-002` (InfiniteTalk)
- Backlog pointer: [docs/agent_video_tooling_todo.md](../../agent_video_tooling_todo.md) § P0 HOTFIX

## Global Constraints

- Production interim rules stay in force until track acceptance:
  - SI2V default path: `--backend ltx23_ia2v` (not IT)
  - `character_full_sheet.py --run` not for production cast lock
- Do not delete user package assets under `characters/green_lighter_idol_v1` (status `rejected_quality` stays until explicit re-run + QA).
- Prefer contract/preflight/defaults over new models.
- YAGNI: no full LoRA training; no native InfiniteTalk rewrite unless Track IT Option A fails.
- Every “ready” label requires a smoke that passed on this machine after the change.
- Korean user-facing status lines OK; code/comments stay English.

## Root-cause summary (why this plan exists)

| Track | Confirmed cause |
|-------|-----------------|
| **IT** | `ComfyUI-WanVideoWrapper` lives as `…\custom_nodes\ComfyUI-WanVideoWrapper.disabled` → all `WanVideo*` / `MultiTalk*` missing. Factory graph in `build_infinitetalk_api()` depends on those types. No preflight. Catalog still `ready`. Native `WanInfiniteTalkToVideo` exists but is unused. |
| **FS** | (1) cast `positive_core` injects `head-and-shoulders` into full-body/detail jobs; (2) plain `i2i` path never passes `width`/`height` (meta `size_hint` only — measured outputs e.g. costume `1024×576` vs hint `1024×1536`); (3) default engine plain `i2i` + denoise 0.78–0.92; (4) `auto_approve` = file exists; `missing_mvp` ignores quality. |

## File map

| Path | Role in this plan |
|------|-------------------|
| `F:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-WanVideoWrapper.disabled` | IT: re-enable (rename) or document conflict |
| `scripts/generate_s2v.py` | IT: preflight hook before queue; optional native path later |
| `lib/s2v_backend_health.py` *(create)* | IT+H: required nodes/models check per backend |
| `scripts/tool_health.py` *(create)* | H: CLI for agents / CI smoke |
| `video_backends.json` | H: `infinitetalk.status` honesty |
| `docs/audio_motion_production_modes.md` | H: when-not + fallback |
| `docs/tool_catalog.md` | H: when-not for IT + full_sheet |
| `TOOLS.md` | H: one-line degraded notices if listed |
| `scripts/character_expand_sheets.py` | FS: core split, size pass-through, engine defaults |
| `scripts/character_full_sheet.py` | FS: no auto L2 without gate; `--require-qa` |
| `characters/sheet_presets.json` | FS: denoise / engine / instruction / negative |
| `lib/prompt_assembly.py` or new `lib/sheet_prompt_policy.py` | FS: sheet-role core policy |
| `lib/character_package.py` | FS: status / missing_mvp semantics if needed |
| `docs/character_casting_pipeline.md` | FS: SOP — file presence ≠ quality |
| `failures/notes/FN-20260729-00{1,2}.json` | Close or attach fix refs |
| `process.md` | History line on DONE |

## Phased delivery

```text
Phase 0  Docs honesty + fail-loud preflight     (half day, unblocks agents)
Phase 1  InfiniteTalk restore OR explicit dead   (half–1 day)
Phase 2  full_sheet hotfixes (B1–B4)             (1–2 days)
Phase 3  full_sheet quality gates (B5–B6)        (1 day)
Phase 4  Close notes + catalog smoke policy      (half day)
```

Tracks IT and FS can run in parallel after Phase 0. **Ship Phase 0 first** even if Comfy re-enable is deferred.

---

## Phase 0 — Honesty + preflight (do first)

### Task 0.1: Backend required-node registry + preflight library

**Files:**
- Create: `lib/s2v_backend_health.py`
- Modify: `scripts/generate_s2v.py` (call before queue for `infinitetalk`)
- Test: `tests/test_s2v_backend_health.py` *(create if tests/ exists; else `scripts/_smoke_s2v_health.py`)*

**Interfaces:**
- Produces: `REQUIRED_NODES_S2V: dict[str, list[str]]`
- Produces: `def check_backend_nodes(backend: str, object_info: dict | None = None, server: str | None = None) -> dict`
  - Return shape: `{"ok": bool, "backend": str, "missing": list[str], "present": list[str], "hint": str}`
- Consumes: Comfy `/object_info` via existing `lib.comfy_client` helpers if available; else `urllib` GET

**Required nodes for `infinitetalk` (factory graph today):**

```python
INFINITETALK_REQUIRED_NODES = [
    "WanVideoClipVisionEncode",
    "WanVideoModelLoader",
    "WanVideoSampler",
    "WanVideoDecode",
    "WanVideoVAELoader",
    "WanVideoTextEncodeCached",
    "WanVideoImageToVideoMultiTalk",
    "WanVideoBlockSwap",
    "MultiTalkModelLoader",
    "MultiTalkWav2VecEmbeds",
    "DownloadAndLoadWav2VecModel",
    "CLIPVisionLoader",
    "JWLoadAudio",
    "ImageResizeKJv2",
    "VHS_VideoCombine",
    "LoadImage",
]
```

- [ ] **Step 1:** Implement `check_backend_nodes` returning missing list; empty missing → `ok=True`.
- [ ] **Step 2:** Unit test with fake `object_info` missing `WanVideoClipVisionEncode` → `ok=False`, missing contains that name.
- [ ] **Step 3:** In `generate_s2v()` when `backend == "infinitetalk"`, call check **before** `queue_prompt`; on fail return structured error:

```text
error=BACKEND_UNAVAILABLE
message=missing nodes: WanVideoClipVisionEncode, ...
hint=Re-enable ComfyUI-WanVideoWrapper (folder must not end with .disabled). See docs/superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md
```

Exit code: reuse existing non-zero queue-fail pattern or introduce explicit `EXIT_BACKEND=42` if project already has a convention — prefer existing `QUEUE_FAILED` style dict + non-zero main.

- [ ] **Step 4:** Manual: with wrapper still disabled, `python scripts/generate_s2v.py --backend infinitetalk -i <any.png> -a <any.wav> -o tmp.mp4` must fail **before** HTTP 400, message includes `BACKEND_UNAVAILABLE`.

**Acceptance:** Agents never spend length-contract prep only to hit Comfy 400 for missing node types.

---

### Task 0.2: `tool_health` CLI

**Files:**
- Create: `scripts/tool_health.py`

**Behavior:**
```bash
python scripts/tool_health.py --backend infinitetalk
python scripts/tool_health.py --all-s2v
# exit 0 if ok; exit 3 if any required missing
```

Print table: backend | ok | missing_count | missing[:5]

- [ ] **Step 1:** Wire to `lib.s2v_backend_health.check_backend_nodes`.
- [ ] **Step 2:** Document one-liner in `docs/tool_catalog.md` under SI2V / health.

**Acceptance:** One command tells agent “IT usable or not” in &lt;5s.

---

### Task 0.3: Catalog / backends honesty (IT + full_sheet when-not)

**Files:**
- Modify: `video_backends.json` → `backends.infinitetalk.status`
- Modify: `docs/audio_motion_production_modes.md`
- Modify: `docs/tool_catalog.md`
- Modify: `docs/character_casting_pipeline.md` (production ban until Phase 2–3)
- Modify: `agent_rules.md` only if it still says IT ready without when-not (minimal patch)
- Modify: `docs/FIX_REQUEST_2026-07-30_full_sheet_and_infinitetalk.md` → link this plan, status PLAN READY

**Status values (pick one and use consistently):**
- While nodes missing: `"status": "degraded"` or `"blocked_missing_nodes"` (prefer **`degraded`**)
- Notes field: `"notes": "WanVideoWrapper disabled on host; use ltx23_ia2v. Preflight: tool_health --backend infinitetalk"`

**Document when-not (copy-ready):**

```markdown
### InfiniteTalk
- **When:** lip quality hero after `tool_health --backend infinitetalk` OK
- **When not:** health fail / missing WanVideo*; use `--backend ltx23_ia2v`
- **Do not** treat catalog historical “1급 대안” as runtime guarantee without health

### character_full_sheet
- **When not (until FS gates land):** production cast lock / MV identity SSOT
- **Do:** cast_pool → promote → master_front; keyframes via krea2_identity_edit
- **Note:** missing_mvp=[] means files present, not visual pass
```

- [ ] **Step 1:** Patch JSON + docs.
- [ ] **Step 2:** Grep for `infinitetalk` + `ready` in docs; fix contradictory “✅ ready” lines or add “runtime: check tool_health”.

**Acceptance:** New agent reading TOOLS/catalog alone will not pick broken IT or full_sheet for production.

---

## Phase 1 — InfiniteTalk restore

### Decision gate (run before coding graph rewrite)

```text
Option A (preferred): re-enable ComfyUI-WanVideoWrapper
  rename:
    ComfyUI-WanVideoWrapper.disabled → ComfyUI-WanVideoWrapper
  restart ComfyUI
  python scripts/tool_health.py --backend infinitetalk  → ok

Option B: if A crashes Comfy / VRAM / import conflict
  keep disabled; leave status degraded
  open spike issue for native WanInfiniteTalkToVideo graph (out of hot-fix scope unless user prioritizes)
```

### Task 1.1: Re-enable wrapper (Option A)

**Files / host:**
- Rename under `F:\ComfyUI_windows_portable\ComfyUI\custom_nodes\`
- Restart Comfy (user or existing autostart script)

- [ ] **Step 1:** Confirm no second live copy of WanVideoWrapper.
- [ ] **Step 2:** Rename `.disabled` → active folder name.
- [ ] **Step 3:** Restart Comfy; `GET /object_info` must list `WanVideoClipVisionEncode`.
- [ ] **Step 4:** `python scripts/tool_health.py --backend infinitetalk` → exit 0.
- [ ] **Step 5:** If Comfy fails to start, **revert rename immediately**, log conflict package name in FIX_REQUEST, stop Option A.

**Acceptance:** All `INFINITETALK_REQUIRED_NODES` present.

---

### Task 1.2: InfiniteTalk smoke

**Command (template):**
```bash
python scripts/generate_s2v.py --backend infinitetalk \
  -i stories/_tool_smoke/face_still.png \
  -a stories/_tool_smoke/drive_short.wav \
  -o stories/_tool_smoke/infinitetalk_smoke.mp4 \
  --format shorts_9x16
```

Use any existing short face still + &lt;5s wav if smoke assets differ; keep output under `stories/_tool_smoke/`.

- [ ] **Step 1:** Run smoke; exit 0; mp4 exists; duration ~ audio length.
- [ ] **Step 2:** Visual open: mouth moves; no freeze-only clip.
- [ ] **Step 3:** On success set `video_backends.json` infinitetalk `status` back to `ready` **only if** health+smoke both pass; add `"last_smoke": "ISO-date"`.
- [ ] **Step 4:** Append `process.md` history line.

**Acceptance:** FN-20260729-002 fix path verified; IT-1/IT-2 from FIX_REQUEST done.

---

### Task 1.3: (Optional / deferred) Native graph spike

Only if Option A fails permanently.

**Scope note:** Native `WanInfiniteTalkToVideo` requires different loaders (model_patch, audio_encoder_output). This is a **new backend implementation**, not a rename. Schedule as separate plan if needed: `2026-07-XX-infinitetalk-native-graph.md`.

---

## Phase 2 — full_sheet hotfixes (quality root causes)

### Task 2.1: Sheet-role prompt policy (kill head-and-shoulders on full/detail)

**Files:**
- Create: `lib/sheet_prompt_policy.py` *(preferred)*  
  or extend `lib/prompt_assembly.py` if thin enough
- Modify: `scripts/character_expand_sheets.py` where `core_prefix=positive_core` is passed
- Modify: expression vs costume/pose/detail source of core

**Policy:**

| sheet / view | core_prefix behavior |
|--------------|----------------------|
| `expression`, `head`, source_pref `face` | full `positive_core` (face lock OK) |
| `costume` with `view` full / alt | **identity-only core**: face traits, hair, age, ethnicity — **strip framing** (`head-and-shoulders`, `portrait`, `85mm`, `casting portrait`) |
| `costume` detail_* | identity-only + **do not** lead with face framing; prefer empty face prose weight or short identity tags |
| `pose`, `turnaround` | identity-only + wardrobe from bible |
| product_plate / t2i design | no character face core (already) |

**Suggested API:**
```python
def core_for_preset(positive_core: str, preset: dict, *, preset_id: str = "") -> str:
    """Return core_prefix appropriate for this sheet preset."""
    ...

def strip_framing_clauses(core: str) -> str:
    """Remove portrait/headshot framing phrases; keep identity descriptors."""
    ...
```

Implementation note: start with regex/phrase strip list:

```python
FRAMING_PHRASES = [
    "head-and-shoulders",
    "head and shoulders",
    "casting portrait",
    "eye-level 85mm",
    "85mm feel",
    "portrait crop",
    "close-up portrait",
]
```

Plus: for `view` in `full` / pose full body, **prepend** a hard framing lock once:

```text
full body head-to-toe visible, feet in frame, not a close-up, not headshot
```

- [ ] **Step 1:** Implement `core_for_preset` + unit tests on sample GREEN core string → no `head-and-shoulders` for `costume.default`.
- [ ] **Step 2:** Wire expand path for i2i / i2i_lock / ipadapter / controlnet.
- [ ] **Step 3:** Dry-run one costume preset: printed prompt must not start with casting portrait framing.

**Acceptance:** Meta prompt for costume.default no longer contains `head-and-shoulders`.

---

### Task 2.2: Pass width/height into plain i2i (and lock/ipa)

**Files:**
- Modify: `scripts/character_expand_sheets.py` `else` branch `generate_i2i_image(...)` and `generate_i2i_lock` / `generate_i2i_ipadapter` calls

**Change pattern:**
```python
result = generate_i2i_image(
    ...
    width=w,
    height=h,
    timeout_sec=args.timeout,
)
```

Same for `generate_i2i_lock` / `generate_i2i_ipadapter` if signatures support width/height; if not, extend those generators to forward ports like `generate_moody_i2i.py` already does.

- [ ] **Step 1:** Confirm `generate_i2i_lock` / ipadapter accept width/height; add if missing.
- [ ] **Step 2:** Wire all non-t2i paths that currently ignore `w,h`.
- [ ] **Step 3:** Smoke single `costume.default` expand; output pixel size must match `size_for_sheet` (allow divisible-by-8 snap ±16).

**Acceptance:** costume full body output ≈ 1024×1536 (or profile size), not 1024×576.

---

### Task 2.3: Engine + denoise defaults in `sheet_presets.json`

**Files:**
- Modify: `characters/sheet_presets.json`

| Preset group | Change |
|--------------|--------|
| `costume.default`, `costume.alt1` | `engine`: `i2i_lock` (or `ipadapter` if IPA proven stable); denoise **≤ 0.55** for default, **≤ 0.62** alt |
| `costume.detail_*` | denoise **≤ 0.50**; strengthen instruction “crop POI only”; negative already has face — keep + `portrait, headshot` |
| `expression.*` | keep face source; denoise joy/etc **≤ 0.72** (was 0.84); neutral can stay ~0.55–0.65 |
| `pose.*` | denoise **≤ 0.72**; control_strength keep ~0.55–0.65; add negative `multiple people, twins, crowd, second person` |

Also set profile `candidates_sheet_default` to **2** in `characters/profiles.json` for `full_sheet` (optional but recommended).

- [ ] **Step 1:** Edit JSON presets.
- [ ] **Step 2:** `character_expand_sheets --dry-run` shows new engine/denoise.
- [ ] **Step 3:** One real costume.default generation; compare face to master_front visually.

**Acceptance:** Default path uses lock engine; denoise no longer ≥0.84 on costume.

---

### Task 2.4: Disable silent auto L2

**Files:**
- Modify: `scripts/character_full_sheet.py`

**Behavior change:**
- Default: **do not** call `auto_approve` on `--run` completion **unless** `--auto-approve` flag is passed (opt-in, debug only).
- Or: `--require-qa` default ON: after expand, write review grids, set `manifest.status = "pending_review"`, print next steps; never set approved aliases from junk without human/agent `character_approve.py`.
- Mid-phase design/costume mid-approve may remain for **pipeline chaining** (costume_default source) but must not imply L2 complete.

**Recommended CLI:**
```text
--auto-approve     # explicit opt-in (default off)
--approve-only     # existing; still maps refs→approved but print WARN pending visual QA
```

On successful expand without auto-approve:
```text
manifest.status = "pending_review"   # if field exists / use notes
missing_mvp still computed from approved only
print: NEXT: open exports/full_sheet/review_*.png then character_approve.py
```

- [ ] **Step 1:** Invert default; add flag.
- [ ] **Step 2:** Ensure `missing_mvp=[]` cannot happen solely via silent auto path after `--run`.
- [ ] **Step 3:** Update `docs/character_casting_pipeline.md` SOP.

**Acceptance:** `character_full_sheet --run` does not fill all approved aliases without `--auto-approve`.

---

## Phase 3 — full_sheet quality gates

### Task 3.1: Framing heuristic (lightweight)

**Files:**
- Create: `lib/sheet_qa_heuristics.py`
- Modify: expand or full_sheet post-step

**Checks (no heavy ML required for v1):**
1. **Aspect / size:** abs(output_w - expected_w) &gt; 32 or height mismatch → fail framing
2. **Full-body feet proxy (optional v1):** if preset view `full` and image is landscape (w &gt; h) → fail
3. **Detail footwear:** if face detector available use it; else skip to manual — **optional**. Minimum: reject if prompt meta still contains framing conflict (dev assert)

Integrate:
```python
def check_sheet_output(path: str, preset: dict, size_hint: tuple[int,int]) -> dict:
    return {"ok": bool, "reasons": list[str]}
```

On fail: do not mid-approve; mark asset `qa_fail` in manifest assets entry.

- [ ] **Step 1:** Implement size/aspect checks.
- [ ] **Step 2:** Wire after successful generation in expand.
- [ ] **Step 3:** Unit test with fake sizes.

**Acceptance:** 1024×576 cannot be auto-accepted as full-body costume.

---

### Task 3.2: Solitary / multi-person hard fail (pose)

**Files:**
- `lib/sheet_qa_heuristics.py`
- pose path in expand after controlnet

**v1 approach (pick first available):**
1. If `comfyui-impact` / face count utility already used elsewhere in repo, reuse.
2. Else: document manual gate + negative prompts (Task 2.3) as interim; add `status=needs_visual_qa` on pose sheets.

Do not block Phase 2 on perfect person detector.

- [ ] **Step 1:** Search repo for face/person count helpers.
- [ ] **Step 2:** Wire or document skip with FIX_REQUEST checkbox.

**Acceptance:** Documented path to reject multi-person; automated if helper exists.

---

### Task 3.3: Phase human/agent gate hooks

**Files:**
- `scripts/character_full_sheet.py`

Between phases when `--phases all`:
- After design / costume / turns / rest: if `--stop-between-phases`, exit 0 with message to review grids.
- Default can remain continuous for batch, but **without auto-approve** (Task 2.4) continuous is safer.

- [ ] **Step 1:** Add `--stop-between-phases` flag.
- [ ] **Step 2:** Document in casting pipeline.

**Acceptance:** Operator can run design → review → costume without pollution.

---

## Phase 4 — Close-out

### Task 4.1: Failure notes + process

- [ ] Attach fix refs on `FN-20260729-001` / `002` (paths to commits or plan tasks) via `failure_note` refs field or close note in FIX_REQUEST.
- [ ] `process.md` entry: date, what fixed, smoke paths.
- [ ] FIX_REQUEST status → `DONE` only when acceptance list below green.
- [ ] `docs/agent_video_tooling_todo.md` P0 HOTFIX rows → ✅

### Task 4.2: Regression checklist (manual)

| # | Check | Pass criteria |
|---|--------|----------------|
| R1 | `tool_health --backend infinitetalk` | matches reality |
| R2 | IT smoke mp4 | exit 0 + lips move |
| R3 | costume.default expand | size ~profile; prompt no head-and-shoulders |
| R4 | full_sheet --run without --auto-approve | no full approved dump |
| R5 | catalog when-not | agent-readable |
| R6 | ltx23_ia2v still works | no regression |

---

## Acceptance (whole project DONE)

Mirror of FIX_REQUEST §5, refined:

- [ ] InfiniteTalk: preflight + (smoke exit 0 **or** permanent degraded + native spike filed)
- [ ] full_sheet: sheet-role core + size pass-through + lower denoise/lock engine + no silent auto L2
- [ ] Framing heuristic blocks wrong aspect on full-body
- [ ] Catalog / video_backends / casting SOP updated
- [ ] FN-001 / FN-002 referenced or closed
- [ ] `process.md` history line

## Out of scope (unchanged)

- GREEN LIGHTER lyric timing re-slice
- Subtitle burn-in / 1080 upscale
- Character LoRA training
- Full rewrite of casting T2I models
- Native IT graph unless Option A fails and user prioritizes Option B

## Risk register

| Risk | Mitigation |
|------|------------|
| Re-enabling WanVideoWrapper breaks Comfy boot | Rename back; keep degraded; don’t leave half-state |
| i2i width/height ports ignored by workflow graph | Verify ports in moody i2i workflow; fix inject if no-op |
| i2i_lock too tight for costume change | denoise band 0.48–0.58; allow per-preset override |
| IPA unavailable | Prefer i2i_lock default; IPA optional |
| Agents ignore docs | preflight hard-fail + backends status |

## Suggested implementation order (single engineer)

1. Task 0.1 → 0.2 → 0.3  
2. Task 1.1 → 1.2 *(or skip to degraded if A fails)*  
3. Task 2.1 → 2.2 → 2.3 → 2.4  
4. Task 3.1 → 3.3 → 3.2  
5. Task 4.1 → 4.2  

## Estimate

| Phase | Effort |
|-------|--------|
| 0 | 0.5 day |
| 1 | 0.5–1 day |
| 2 | 1–2 days |
| 3 | 0.5–1 day |
| 4 | 0.5 day |
| **Total** | **~3–5 days** calendar |

## Execution handoff

When implementing:

1. **Inline** in one session for Phase 0 (high value, low risk).  
2. Phase 1 needs Comfy restart — coordinate with user if UI sessions open.  
3. Phase 2–3 can use subagent-driven tasks (expand vs full_sheet vs docs).

Do not mark FIX_REQUEST DONE until R1–R6 pass.
