# Toolbox Index Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring tool discovery layers (intent search, human catalog, machine indexes, backends) back into one consistent story so agents pick the right CLI without reading three contradictory sources.

**Architecture:** Keep the existing layered SSOT (human catalog + intent cards + catalog.json + video_backends), but define a hard sync contract, fix known drift (high → medium), and add a cheap drift checker so future tools cannot ship half-registered. No new generation models; docs/index hygiene only (except status/path fixes that unlock already-shipped CLIs).

**Tech Stack:** Python (`lib/tool_intent.py`, optional `scripts/tool_index_check.py`), Markdown (`TOOLS.md`, `docs/tool_catalog.md`, maps), JSON (`workflows/agent/catalog.json`, `video_backends.json`).

## Global Constraints

- **Do not** change episode default I2V (still LTX) or invent new backends.
- **Do not** mass-edit unrelated 3D/VRM untracked scripts in this plan (out of scope).
- Human SSOT remains `docs/tool_catalog.md`; entry remains `TOOLS.md`.
- Intent cards must follow `docs/toolbox_card_standard.md` (when / when_not / examples / alternatives).
- Prefer fixing status/path truth over rewriting history: A/B notes stay labeled historical.
- cwd = repo root; verify with `python scripts/tool_intent.py …` (no Comfy required for discovery checks).
- After changes: short entry in `process.md` (date + what synced).

---

## File map (who owns what after this plan)

| File | Responsibility after alignment |
|------|--------------------------------|
| `docs/tool_catalog.md` | Human when/when-not · full CLI list · combination recipes |
| `TOOLS.md` | 30-second shelf table (must match catalog defaults) |
| `lib/tool_intent.py` | Searchable intent cards (must not contradict catalog defaults) |
| `scripts/tool_intent.py` | CLI only; no policy |
| `workflows/agent/catalog.json` | Machine index: status, scripts/used_by, guide paths |
| `video_backends.json` | Video backend status, cli, human_ui for motion tools |
| `docs/wan22_workflow_map.md` | Wan family map; status must match backends |
| `docs/toolbox_card_standard.md` | Card field rules (+ optional “sync checklist” section) |
| `scripts/tool_index_check.py` | **New** drift checker (intent ↔ scripts exist ↔ catalog status notes) |
| `process.md` | Changelog of alignment pass |

---

## Policy decisions (lock these before editing)

| ID | Decision | Rationale |
|----|----------|-----------|
| P1 | **SFW photoreal default CLI = `generate_krea`** (catalog already says this). Intent `still_photoreal` must point to Krea; Moody becomes alternative for I2I/control experiments. | Docs + agent_rules treat Krea2 as default still; intent currently misroutes. |
| P2 | **`wan22_animate` status = `ready`** (CLI + pack exist). Map/backends/catalog update; human_ui SSOT = `workflows/human/wan22_animate_dance/`. Old `wan22/wan22_animate.json` noted as legacy UI sample if kept. | process.md + intent already treat as toolized. |
| P3 | **Register first-class intent cards** for: `openpose_pose`, `upscale_ltx_spatial` (and optional thin cards or strong alternatives for `youtube_highlights`, `generate_yaw_wan22` if time). | Search failures confirmed. |
| P4 | **Catalog §2.4/§2.6** must mention `wan22_animate`, `extract_pose_video`, `upscale_ltx_spatial`. | Human SSOT gap. |
| P5 | Sibling tools (latentheart, redmix, nsfw i2v, boogu) stay catalog-primary; intent may keep as alternatives unless agent discoverability is poor — do not bloat intent to 50+ equal cards in pass 1. | YAGNI. |
| P6 | 3D/VRM scripts remain **non-catalog** until a separate “ASSETS_3D” plan. | Different maturity track. |

---

### Task 1: Sync contract (docs only)

**Files:**
- Modify: `docs/toolbox_card_standard.md`
- Modify: `agent_rules.md` (short pointer under tool SSOT / catalog section only)
- Optional note in: `docs/tool_catalog.md` top “이용 계약”

**Produces:** A written “new tool registration checklist” every future agent must complete.

- [ ] **Step 1: Add “Registration checklist” section** to `docs/toolbox_card_standard.md`

Add after “어디에 반영하나”:

```markdown
## Registration checklist (new or ready tool)

Ship **all** of the following in the same change set, or mark status `planned`/`experimental` consistently:

| # | Artifact | Required fields |
|---|----------|-----------------|
| 1 | `scripts/<cli>.py` | `--help` works; copy-paste example in docstring |
| 2 | `lib/tool_intent.py` card **or** explicit `alternatives` from a parent card | when, when_not, examples[0], keywords |
| 3 | `docs/tool_catalog.md` shelf row | when / when not / CLI |
| 4 | `TOOLS.md` shelf table | only if it is a **representative** shelf CLI |
| 5 | `workflows/agent/catalog.json` | `status`, `scripts`/`used_by`, `guide` path |
| 6 | Video tools: `video_backends.json` | `status`, `cli`, `human_ui`/`guide` |
| 7 | Human pack | `workflows/human/<tool>/AGENT_GUIDE.md` (or family pack) |
| 8 | `process.md` | one bullet: what shipped |

**Status vocabulary (shared):** `planned` | `ready` | `ready_experimental` | `legacy_mini` | `superseded`.  
`planned` = no agent CLI or intentionally unwired. If `scripts/generate_*.py` exists and is intended for agents → **not** `planned`.

**Drift check:** `python scripts/tool_index_check.py` (Task 6) must exit 0 before claiming done.
```

- [ ] **Step 2: One-line pointer in `agent_rules.md`** near tool catalog SSOT:

```markdown
* **도구 등록 체크리스트:** [docs/toolbox_card_standard.md](docs/toolbox_card_standard.md) § Registration checklist · drift: `python scripts/tool_index_check.py`
```

- [ ] **Step 3: Commit**

```bash
git add docs/toolbox_card_standard.md agent_rules.md
git commit -m "docs: tool registration checklist and status vocabulary"
```

---

### Task 2: Fix SFW photoreal default (intent + soft catalog cross-links)

**Files:**
- Modify: `lib/tool_intent.py` (`still_photoreal`, related alternatives on `still_nsfw` / `still_anime`)
- Touch only if wording wrong: `docs/tool_catalog.md` GENERATE Krea vs Lonecat (already correct — verify only)
- Modify: `TOOLS.md` only if needed (already lists Krea first)

**Produces:** `tool_intent search "실사 한 장"` / `"krea"` recommends `generate_krea`, not only moody/nsfw.

- [ ] **Step 1: Rewrite `still_photoreal` card** in `lib/tool_intent.py`

Target shape:

```python
{
    "id": "still_photoreal",
    "shelf": "GENERATE",
    "cli": "python scripts/generate_krea.py",
    "script": "generate_krea.py",
    "summary": "실사 시네 스틸 T2I (기본: Krea2)",
    "when": "텍스트만으로 인물/무드 한 장 — 시네·패션·키프레임 기본",
    "when_not": "애니 태그 → Illustrious · 18+ → krea_nsfw · I2I denoise 실험 → moody",
    "keywords": [
        "t2i", "still", "photo", "photoreal", "portrait", "실사", "스틸",
        "키프레임", "생성", "한장", "krea", "krea2", "시네",
    ],
    "examples": [
        'python scripts/generate_krea.py -p "cinematic portrait of a woman" -o out.png --seed 42',
    ],
    "alternatives": [
        {"if": "I2I denoise·스타일 실험", "use": "moody T2I/I2I", "cli": "python scripts/generate_moody.py -m pro -p \"...\" -o out.png"},
        {"if": "애니/일루스 태그", "use": "Illustrious XL", "cli": "python scripts/generate_illustrious_standard.py -p \"1girl, ...\" -o out.png"},
        {"if": "18+ NSFW", "use": "Krea NSFW", "cli": "python scripts/generate_krea_nsfw.py -p \"...\" -o out.png"},
        {"if": "레퍼 얼굴 유지하며 장면만", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
    ],
},
```

- [ ] **Step 2: Fix `still_nsfw` alternative** — SFW keyframe should recommend Krea, not moody as sole option:

```python
{"if": "SFW 키프레임", "use": "krea SFW", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
```

- [ ] **Step 3: Verify discovery (no Comfy)**

```bash
python scripts/tool_intent.py search "실사 한 장" --limit 3
python scripts/tool_intent.py search "krea" --limit 3
```

Expected: `#1 still_photoreal` with `generate_krea.py` in eg; nsfw not first for SFW queries.

- [ ] **Step 4: Commit**

```bash
git add lib/tool_intent.py
git commit -m "fix(tool_intent): SFW photoreal default is generate_krea"
```

---

### Task 3: Promote wan22_animate to ready (indexes + map + catalog prose)

**Files:**
- Modify: `workflows/agent/catalog.json` → `wan22_animate`
- Modify: `video_backends.json` → `backends.wan22_animate`
- Modify: `docs/wan22_workflow_map.md` (planned → ready rows)
- Modify: `docs/tool_catalog.md` §2.4 MOTION table + bash examples
- Modify: `TOOLS.md` MOTION row
- Optional: `docs/wan22_workflow_research_and_design.md` one-line status note (or leave as historical research)

**Produces:** Every status field agrees CLI is agent-ready; guide path = dance pack.

- [ ] **Step 1: Update `catalog.json` entry**

```json
"wan22_animate": {
  "file": null,
  "format": "native_api_graph",
  "role": "motion_transfer",
  "family": "wan22",
  "status": "ready",
  "description": "Wan2.2 Animate dance/motion retarget with face lock. Pose preprocess + animate diffusion.",
  "runner": "lib/wan22_animate.py",
  "guide": "workflows/human/wan22_animate_dance/AGENT_GUIDE.md",
  "capabilities": "workflows/human/wan22_animate_dance/CAPABILITIES.json",
  "human_ui_legacy": "workflows/human/wan22/wan22_animate.json",
  "used_by": ["scripts/generate_wan22_animate.py"],
  "notes": "Ready 2026-08-02. Prefer generate_wan22_animate CLI. Cross-cast dance; face_strength default 1.3. Not episode bulk I2V default."
}
```

- [ ] **Step 2: Update `video_backends.json` `wan22_animate`**

```json
"wan22_animate": {
  "status": "ready",
  "family": "wan22",
  "kind": "v2v_motion",
  "engine": "WAN Animate 2.2",
  "cli": "scripts/generate_wan22_animate.py",
  "runner": "lib/wan22_animate.py",
  "human_ui": "workflows/human/wan22_animate_dance/",
  "guide": "workflows/human/wan22_animate_dance/AGENT_GUIDE.md",
  "strengths": ["dance_challenge", "pose_retarget", "face_lock"],
  "notes": "Agent CLI ready. Preprocess via extract_pose_video optional. Map: docs/wan22_workflow_map.md. Fast draft: generate_dance_ref."
}
```

Also fix any summary line still saying `"wan22_animate": "planned pose/SAM2 retarget"`.

- [ ] **Step 3: Update `wan22_workflow_map.md`** tables: status **ready**, CLI `generate_wan22_animate`, guide pack path.

- [ ] **Step 4: tool_catalog §2.4** — add rows:

| CLI | 언제 | 말고 |
|-----|------|------|
| **`generate_wan22_animate`** | 댄스/제스처 레퍼 → 다른 캐릭, **얼굴 고정** 리타겟 | 빠른 초안 → `dance_ref` · 립 → s2v · 에피 대량 I2V → LTX |
| **`extract_pose_video`** | RGB 레퍼 → pose 스틱 플레이트 (Animate/Fun Control 전처리) | 이미지 한 장 포즈 → `openpose_pose` |

Bash block:

```bash
python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4 --duration 4
python scripts/generate_wan22_animate.py -i hero.png -v dance.mp4 -o out.mp4 --seed 42
```

- [ ] **Step 5: TOOLS.md MOTION** — append `generate_wan22_animate` · `extract_pose_video` to representative CLI list.

- [ ] **Step 6: Verify intent still lists wan22_animate**

```bash
python scripts/tool_intent.py search "댄스 얼굴 고정" --limit 3
```

Expected: `wan22_animate` near top with correct CLI.

- [ ] **Step 7: Commit**

```bash
git add workflows/agent/catalog.json video_backends.json docs/wan22_workflow_map.md docs/tool_catalog.md TOOLS.md
git commit -m "docs: mark wan22_animate ready and sync catalog paths"
```

---

### Task 4: Intent cards for openpose + LTX spatial upscale

**Files:**
- Modify: `lib/tool_intent.py` (new cards + keyword boosts if needed)
- Modify: `docs/tool_catalog.md` CAMERA (openpose already there — ensure eg matches card) + FINISH (spatial)
- Modify: `TOOLS.md` FINISH row
- Modify: `workflows/agent/catalog.json` (optional entries for openpose + ltx_spatial_upscale)
- Modify: `workflows/human/minimax_h3/AGENT_GUIDE.md` only if CLI path already correct (verify)

**Produces:** Search finds the right CLI for pose stills and MiniMax→HD spatial path.

- [ ] **Step 1: Add `openpose_pose` intent card** (CAMERA shelf)

```python
{
    "id": "openpose_pose",
    "shelf": "CAMERA",
    "cli": "python scripts/generate_openpose_pose.py",
    "script": "generate_openpose_pose.py",
    "summary": "OpenPose 맵 extract + 템플릿 포즈 생성",
    "when": "걷기/조깅 등 포즈 맵으로 스틸 키 생성 (Fun Union CN 경로)",
    "when_not": "영상 댄스 pose 플레이트 → extract_pose_video · Qwen 텍스트만으로 발 위상 교정 불가",
    "keywords": [
        "openpose", "pose map", "포즈맵", "jog", "walk cycle", "스틱피겨",
        "generate_openpose_pose", "vitpose",
    ],
    "examples": [
        "python scripts/generate_openpose_pose.py generate -i identity.png --template jog_contact -o out.png --seed 42",
        "python scripts/generate_openpose_pose.py extract -i char.png -o pose.png",
    ],
    "alternatives": [
        {"if": "저수준 CN만", "use": "moody_controlnet", "cli": "python scripts/generate_moody_controlnet.py --control pose.png -p \"...\" -o out.png -m pro"},
        {"if": "영상 pose 스틱", "use": "extract_pose_video", "cli": "python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4 --duration 4"},
        {"if": "얼굴 ID 장면", "use": "character_consistent pose", "cli": "python scripts/generate_character_consistent.py --mode pose -i face.png --pose pose.png -o out.png"},
    ],
},
```

Reduce false dominance of `controlnet_pose` for keyword `openpose` if needed (prefer openpose_pose score boost over controlnet for exact "openpose").

- [ ] **Step 2: Add `ltx_spatial_upscale` intent card** (FINISH shelf)

```python
{
    "id": "ltx_spatial_upscale",
    "shelf": "FINISH",
    "cli": "python scripts/upscale_ltx_spatial.py",
    "script": "upscale_ltx_spatial.py",
    "summary": "LTX latent spatial x2 (core 빠름 / full IC-LoRA 품질)",
    "when": "MiniMax·저해상도 클립 → LTX spatial HD (오디오 패스스루)",
    "when_not": "일반 납품 ESRGAN/SeedVR2 → upscale_video · 스틸만 → upscale_image",
    "keywords": [
        "ltx spatial", "spatial upscale", "latent upsampler", "minimax upscale",
        "full path", "IC-LoRA upscale", "ltx_spatial",
    ],
    "examples": [
        "python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full",
        "python scripts/upscale_ltx_spatial.py -i work.mp4 -o preview.mp4 --path core",
    ],
    "alternatives": [
        {"if": "일반 영상 납품", "use": "upscale_video", "cli": "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080"},
        {"if": "엔진 모름", "use": "upscale_recommend", "cli": "python scripts/upscale_recommend.py --media video --goal hero --source normal"},
        {"if": "야외 조명만", "use": "ltx_relight", "cli": "python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look \"warm golden low side sun\" --direction \"the left\""},
    ],
},
```

- [ ] **Step 3: Catalog + TOOLS FINISH**

`tool_catalog` §2.6 add row for `upscale_ltx_spatial` (core vs full, MiniMax companion).  
`TOOLS.md` FINISH: append `upscale_ltx_spatial`.

- [ ] **Step 4: catalog.json entries** (minimal)

```json
"openpose_pose": {
  "status": "ready",
  "role": "pose_extract_and_generate",
  "guide": "workflows/human/openpose_controlnet/AGENT_GUIDE.md",
  "used_by": ["scripts/generate_openpose_pose.py"]
},
"ltx_spatial_upscale": {
  "status": "ready",
  "role": "video_spatial_upscale",
  "family": "ltx",
  "runner": "lib/ltx_spatial_upscale.py",
  "guide": "workflows/human/minimax_h3/AGENT_GUIDE.md",
  "used_by": ["scripts/upscale_ltx_spatial.py"],
  "notes": "core = fast latent x2; full = CRT + IC-LoRA refine. Requires ComfyUI-LTXVideo + crt-nodes."
}
```

- [ ] **Step 5: Verify**

```bash
python scripts/tool_intent.py search "openpose" --limit 3
python scripts/tool_intent.py search "spatial upscale" --limit 3
python scripts/tool_intent.py search "minimax 업스케일" --limit 3
```

Expected: openpose_pose #1 or top-2 with `generate_openpose_pose`; spatial → `upscale_ltx_spatial`.

- [ ] **Step 6: Commit**

```bash
git add lib/tool_intent.py docs/tool_catalog.md TOOLS.md workflows/agent/catalog.json
git commit -m "feat(tool_intent): openpose_pose and ltx_spatial_upscale cards"
```

---

### Task 5: Thin sync leftovers (discovery honesty)

**Files:**
- Modify: `lib/tool_intent.py` (alternatives / optional thin cards)
- Modify: `docs/tool_catalog.md` if any row still claims planned wrongly
- Modify: `video_backends.json` `i2v_quality_policy` note only

**Produces:** No more “planned” lies for shipped tools; historical A/B clearly labeled.

- [ ] **Step 1: `youtube_highlights`** — either thin INTENT card or strengthen `youtube_ref_ingest.alternatives` with cut example (already partial). Prefer **strengthening alternatives + keywords** over new card if search already finds ingest.

- [ ] **Step 2: `generate_yaw_wan22`** — add as alternative under `minimax_h3` and `i2v_generic`/`ltx_i2v` (already one path). Ensure keyword boost so “yaw” does not map only to wan22_animate:

```python
# in _KEYWORD_BOOSTS or equivalent
(("yaw",), "yaw_wan22", 6.0),  # only if card exists
```

If no full card this pass: add one-line alternative on `i2v_generic` and document in catalog only (already has row).

- [ ] **Step 3: Label historical A/B** in `video_backends.json`:

```json
"i2v_quality_policy": {
  "note": "Historical A/B 2026-07-17 at work_16x9_540-class. Current default work preset is work_16x9_720 (see default_work_preset).",
  "target_work_at_test": "960x544 (work_16x9_540)",
  ...
}
```

Do not change verdict; only prevent “current default is 540p” misread.

- [ ] **Step 4: Catalog audit grep** (manual)

```bash
# From repo root — list planned vs scripts that exist
python -c "import json;from pathlib import Path;c=json.loads(Path('workflows/agent/catalog.json').read_text(encoding='utf-8'));
for k,v in c['workflows'].items():
  if v.get('status')=='planned':
    print(k, v.get('used_by') or v.get('scripts') or v.get('human_ui'))"
```

Any `planned` with a working agent CLI → fix status or remove CLI claim.

- [ ] **Step 5: Commit**

```bash
git add lib/tool_intent.py video_backends.json docs/tool_catalog.md
git commit -m "docs: honesty pass for planned backends and discoverability"
```

---

### Task 6: Drift checker CLI

**Files:**
- Create: `scripts/tool_index_check.py`
- Optional: wire mention in `TOOLS.md` quick section
- Test: run script exit codes

**Produces:** Single command that fails CI-local / agent preflight when indexes diverge.

- [ ] **Step 1: Implement `scripts/tool_index_check.py`**

Behavior (keep simple, no network, no Comfy):

1. Load `INTENT_TOOLS` from `lib.tool_intent`.
2. For each card with `script`: assert `scripts/<script>` exists.
3. For each card `examples[0]` / `cli`: if contains `scripts/foo.py`, file must exist.
4. Load `catalog.json` workflows: if `status == "planned"` and any `used_by`/`scripts` path exists as file → **warn or fail** (default **fail** for agent CLIs matching `generate_*.py` / `upscale_*.py` / `extract_*.py`).
5. Load `video_backends.json` backends: if `status == "planned"` but `cli` file exists → fail.
6. Optional soft checks (warn only): intent script not listed in any catalog `scripts`/`used_by`.
7. Exit 0 if no hard failures; print summary counts.

Sketch:

```python
#!/usr/bin/env python3
"""Drift check: tool_intent scripts exist; planned status cannot hide ready CLIs."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.tool_intent import INTENT_TOOLS  # noqa: E402

def main() -> int:
    errors: list[str] = []
    warns: list[str] = []
    for t in INTENT_TOOLS:
        script = t.get("script") or ""
        if script:
            p = ROOT / "scripts" / script
            if not p.is_file():
                errors.append(f"intent {t['id']}: missing scripts/{script}")
    cat = json.loads((ROOT / "workflows/agent/catalog.json").read_text(encoding="utf-8"))
    for name, ent in cat.get("workflows", {}).items():
        if ent.get("status") != "planned":
            continue
        for key in ("scripts", "used_by"):
            for rel in ent.get(key) or []:
                path = ROOT / rel
                if path.is_file() and path.name.startswith(("generate_", "upscale_", "extract_")):
                    errors.append(f"catalog {name}: status=planned but CLI exists: {rel}")
    vb = json.loads((ROOT / "video_backends.json").read_text(encoding="utf-8"))
    for name, ent in (vb.get("backends") or {}).items():
        if ent.get("status") == "planned":
            cli = ent.get("cli")
            if cli and (ROOT / cli).is_file():
                errors.append(f"video_backends {name}: planned but cli exists: {cli}")
    for e in errors:
        print("ERROR:", e)
    for w in warns:
        print("WARN:", w)
    print(f"intent_cards={len(INTENT_TOOLS)} errors={len(errors)} warns={len(warns)}")
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Expand after Tasks 2–5 so checker is green against fixed indexes.

- [ ] **Step 2: Run checker**

```bash
python scripts/tool_index_check.py
```

Expected: exit 0 after Tasks 2–5.

- [ ] **Step 3: Mention in TOOLS.md** under 빠른 검색:

```bash
python scripts/tool_index_check.py   # intent/catalog/backends drift
```

- [ ] **Step 4: Commit**

```bash
git add scripts/tool_index_check.py TOOLS.md
git commit -m "feat: tool_index_check drift guard for toolbox indexes"
```

---

### Task 7: Close the loop (process + smoke report)

**Files:**
- Modify: `process.md` (top entry 2026-08-09)
- Optional: short note in `docs/agent_video_tooling_todo.md` — “Toolbox index alignment ✅”

**Produces:** Future agents see the pass as done and how to re-check.

- [ ] **Step 1: `process.md` bullet list**

```markdown
## 2026-08-09 — Toolbox index alignment
- Policy: SFW photoreal default = generate_krea (intent fixed)
- wan22_animate: planned → ready (catalog, video_backends, wan22 map, tool_catalog, TOOLS)
- New intent cards: openpose_pose, ltx_spatial_upscale; catalog rows extract_pose_video + spatial
- Registration checklist in toolbox_card_standard.md
- Drift guard: scripts/tool_index_check.py
- Out of scope: 3D/VRM scripts, full intent cards for every catalog sibling
```

- [ ] **Step 2: Final verification matrix**

| Check | Command / method | Expected |
|-------|------------------|----------|
| Photoreal | `tool_intent search "실사"` | krea CLI |
| Openpose | `tool_intent search "openpose"` | generate_openpose_pose |
| Dance face | `tool_intent search "댄스 얼굴"` | wan22_animate |
| Spatial | `tool_intent search "spatial upscale"` | upscale_ltx_spatial |
| Drift | `tool_index_check.py` | exit 0 |
| Backends | JSON `wan22_animate.status` | `ready` |

- [ ] **Step 3: Commit**

```bash
git add process.md docs/agent_video_tooling_todo.md
git commit -m "docs: record toolbox index alignment pass"
```

---

## Out of scope (explicit)

| Item | Why later |
|------|-----------|
| Hunyuan3D / VRM / Blender script toolization | Separate shelf; not in intent model yet |
| Full intent parity for latentheart, redmix, nsfw director, boogu, face_enhance | Catalog-first is enough for pass 1 |
| Automated CI gate in GitHub | Local/agent script first; wire CI if repo has CI later |
| Changing LTX default work resolution or MiniMax episode policy | Unrelated product policy |
| Deleting legacy `wan22/wan22_animate.json` | Keep as legacy sample; just stop pointing SSOT at it |

---

## Suggested execution order & effort

| Phase | Tasks | Effort (est.) | Risk |
|-------|-------|---------------|------|
| 0 | Task 1 contract | 15–20 min | low |
| 1 | Task 2 Krea default | 20–30 min | low (behavior change for agents only) |
| 2 | Task 3 wan22 ready | 30–45 min | low |
| 3 | Task 4 openpose + spatial | 30–45 min | low |
| 4 | Task 5 leftovers | 20–30 min | low |
| 5 | Task 6 checker | 30–40 min | low |
| 6 | Task 7 process | 10 min | none |

**Total:** ~2.5–4 hours one focused session.  
**No Comfy required** for completion criteria (discovery + file existence only). Optional smoke of animate/spatial not required for “index aligned.”

---

## Success criteria

1. No known **high** drift items remain (Krea default, wan22 planned-lie, openpose search, spatial discoverable).
2. `python scripts/tool_index_check.py` → exit 0.
3. `TOOLS.md` shelf table matches `tool_catalog` defaults for GENERATE + MOTION + FINISH representatives.
4. New tools have a written registration path so drift is harder to reintroduce.

---

## Self-review (plan vs earlier mismatch list)

| Earlier gap | Task |
|-------------|------|
| A1 Krea vs moody | Task 2 |
| A2 openpose | Task 4 |
| A3 wan22 planned | Task 3 |
| B1 intent without catalog (animate, extract_pose) | Task 3–4 |
| B2 spatial not in intent | Task 4 |
| B3 siblings weak intent | Task 5 (thin) / out of scope full |
| C1 path dual | Task 3 |
| C2 catalog scripts missing | Tasks 3–4 + checker warn |
| C3 A/B 540 metadata | Task 5 |
| Process / prevention | Tasks 1, 6, 7 |
