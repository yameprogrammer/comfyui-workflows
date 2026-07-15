# AGENTS.md — using `agent_custom` as a **tool**

This repo is a **media factory** (ComfyUI CLI tools), not your film project folder.

---

## 0. MANDATORY — Factory skills + Video director equip

**If you are here to make video** (music video, shorts, story film, anything with shots):

### 0.A Skills directory (portable director brain)

| Item | Path |
|------|------|
| **Skill SSOT** | **[skills/](skills/)** · equip contract [skills/README.md](skills/README.md) |
| **Director skill** | **[skills/video-direction/SKILL.md](skills/video-direction/SKILL.md)** |

**Rule:** If your agent session does **not** already have `video-direction` loaded:

```bash
python scripts/skill_equip.py list
python scripts/skill_equip.py install video-direction --target grok   # or claude / all
# Minimum if install unavailable: READ skills/video-direction/SKILL.md fully and adopt it
```

Do **not** skip to `shot_compose` / batch motion without this skill (or equivalent master persona load).

### 0.B Documents (deep SSOT — after skill load)

| Order | Document | Why |
|-------|----------|-----|
| **1** | **[skills/video-direction/SKILL.md](skills/video-direction/SKILL.md)** | **Equip first** — gated direction + handoff |
| **2** | **[skills/generation-prompt/SKILL.md](skills/generation-prompt/SKILL.md)** | **Before generate** — still/I2V/SI2V prompt packs (no tag-soup) |
| **3** | **[docs/video_director_master_persona.md](docs/video_director_master_persona.md)** | Long-form shot grammar SSOT |
| **4** | [docs/video_creative_director_persona.md](docs/video_creative_director_persona.md) | Creative Pack fields |
| **5** | [docs/image_cut_verification_gate.md](docs/image_cut_verification_gate.md) | Open-file QA before approve |
| **6** | [docs/generation_prompt_craft.md](docs/generation_prompt_craft.md) | Factory prompt SSOT (Rule 7.5) |

Paste and adopt the skill SYSTEM identity (and master persona §1 if diving deep).

### You MUST produce before factory mainline

1. **Equip** `video-direction` skill (install or full read)  
2. `CREATIVE.md` — one-image pitch, paradox, motifs×3, anti-list, thumbnail thesis  
3. `SHOT_DESIGN.md` — **size rhythm line** + per-shot type / angle / move / intent / risk  
4. **Equip** `generation-prompt` → per-shot **still + motion** prompts (quality gates)  
5. Only then: assets → keyframes → visual QA → motion → freeze gate → assemble  

### Hard bans

| Ban | Instead |
|-----|---------|
| Pipeline tables only as “planning” | Director + DP thinking first |
| Three identical framings in a row | Size/angle change every cut |
| Lyric slide-show | Visual jobs per section (chorus = event) |
| Face CU for every emotional line | Coverage: wide / medium / insert / CU |
| Freeze-pad short I2V to fake length | Full-length motion or split shots |
| Mass `approved` without opening files | QA_LOG per shot |
| Weak tag-soup prompts (`8k masterpiece…`) | [generation_prompt_craft.md](docs/generation_prompt_craft.md): Subject→Action→Light→Camera |
| I2V prompt re-describing face/wardrobe | Motion/camera only |

### Generation prompts (quality)

Before every T2I / I2I / I2V / SI2V call:

1. Equip **[skills/generation-prompt](skills/generation-prompt/SKILL.md)**  
2. Expand SHOT_DESIGN → still/i2v/si2v strings (quality gates)  
3. Follow **[docs/generation_prompt_craft.md](docs/generation_prompt_craft.md)** (Rule **7.5**): Subject→Action→Light→Camera; I2V motion-only  

Planning without prompt craft still yields poor stills/clips — **direction + prompts** both required.

### Image / cut verification

Before `keyframe_status=approved` or `clip_status=approved`:

1. `shot_qa_pack` → **open pack** (ref|current|prev) · checklist · `shot_qa_record`  
2. Fail anatomy / identity drift / freeze → regenerate — **approve without QA JSON = exit 23**  
3. 3+ keyframes: `episode_identity_sheet` + identity pass (cross-shot cast)  


### Failure notes (shared across agents)

Learn from prior agents — **do not repeat known mistakes**.

```bash
# BEFORE generating / storyboarding
python scripts/failure_note.py search "freeze OR framing OR car OR feet"
python scripts/failure_note.py list --limit 10

# AFTER any FAIL or user rejection
python scripts/failure_note.py add --stage keyframe --tags ... \
  --symptom "..." --cause "..." --fix "..." --prevention "..." \
  --severity high --agent <you> -e EP -s S0x
```

Docs: [docs/failure_notes_system.md](docs/failure_notes_system.md) · folder [failures/](failures/) · Rule **7.4**.

Rules: [agent_rules.md](agent_rules.md) **7.0** (persona) · **7.2** (order) · **7.3** (visual QA) · **7.4** (failure notes) · **7.5** (prompts) · **8.0** (your tools).

### Use YOUR tools and skills (do not wait for the user to name them)

The user **cannot** know every agent’s private tools, skills, MCP servers, or plugins.  
For video work you **must proactively** pick anything you can actually call that improves **quality or speed**, while keeping factory gates.

| Do | Don’t |
|----|--------|
| Inventory your session capabilities and use them | Ask “which tool?” every step |
| Research, edit stills, preview motion, vision-QA, subagents… when useful | Only run bare `scripts/*` when better options exist |
| Hand off files into `stories/<ep>/` and pass approve/assemble | Skip QA because a native tool “looked fine” |
| Obey user if they lock a tool (“Comfy only”) | Invent tools you don’t have |

Full rule: [docs/agent_native_capability_autonomy.md](docs/agent_native_capability_autonomy.md) · Rule **8.0**  
Grok mapping: [docs/grok_build_hybrid_tooling.md](docs/grok_build_hybrid_tooling.md) · Rule **8.1**

---

## Critical rule (consumer agents)

1. Run CLIs from this repo root (`python scripts/...`).
2. Outputs land under **`stories/<episode_id>/`** (and similar package dirs).
3. **Copy results into YOUR workspace** before editing/shipping.
4. If you only leave files here, the job is **incomplete**.

```bash
python scripts/export_episode_to_workspace.py -e YOUR_EP --dest "PATH/TO/YOUR/PROJECT/episodes/YOUR_EP"
# Or: set AGENT_WORKSPACE=PATH/TO/YOUR/PROJECT
```

Full contract: [docs/agent_consumer_workspace_contract.md](docs/agent_consumer_workspace_contract.md)  
AV reliability: [docs/agent_av_smoke_checklist.md](docs/agent_av_smoke_checklist.md)  
Tooling backlog: [docs/agent_video_tooling_todo.md](docs/agent_video_tooling_todo.md)  
Planning SOP: [docs/creative_brief_autonomy_design.md](docs/creative_brief_autonomy_design.md)  
Maintainers: [agent_rules.md](agent_rules.md)  

Default: **agent picks factory + its own tools/skills** until the user names a tool; factory remains SSOT for lips/assemble/gates (Rule **8.0**).

## Video highway (short)

```bash
# 0) LOAD master persona + write CREATIVE.md + SHOT_DESIGN.md  (Rule 7.0)
# ComfyUI :8188
python scripts/smoke_agent_av.py -e EP
# keyframe open+QA → approve, then motion, then clip open+QA → approve
python scripts/shot_qa_pack.py -e EP -s S0x
python scripts/shot_qa_record.py -e EP -s S0x --stage keyframe --verdict pass --pass-required --notes "..."
python scripts/shot_approve.py -e EP -s S0x --status approved
python scripts/shot_approve.py -e EP -s S0x --clip approved   # after clip QA record
python scripts/episode_status.py -e EP
python scripts/assemble_video.py -e EP --stage work
python scripts/export_episode_to_workspace.py -e EP --dest "$AGENT_WORKSPACE/episodes/EP"
```

**Rule:** never jump to final assemble to judge middle cuts. Approve each work clip first. Assemble rejects unapproved clips (exit 22) unless `--force-clip-gate` (debug only).
