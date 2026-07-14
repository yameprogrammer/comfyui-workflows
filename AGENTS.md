# AGENTS.md — using `agent_custom` as a **tool**

This repo is a **media factory** (ComfyUI CLI tools), not your film project folder.

## Critical rule (consumer agents)

1. Run CLIs from this repo root (`python scripts/...`).
2. Outputs land under **`stories/<episode_id>/`** (and similar package dirs).
3. **Copy results into YOUR workspace** before editing/shipping.
4. If you only leave files here, the job is **incomplete**.

```bash
# After generation:
python scripts/export_episode_to_workspace.py -e YOUR_EP --dest "PATH/TO/YOUR/PROJECT/episodes/YOUR_EP"

# Or set:
#   AGENT_WORKSPACE=PATH/TO/YOUR/PROJECT
python scripts/export_episode_to_workspace.py -e YOUR_EP
```

Full contract: [docs/agent_consumer_workspace_contract.md](docs/agent_consumer_workspace_contract.md)  
AV reliability: [docs/agent_av_smoke_checklist.md](docs/agent_av_smoke_checklist.md)  
Near-term tooling backlog: [docs/agent_video_tooling_todo.md](docs/agent_video_tooling_todo.md)  
Tooling rules for **maintainers**: [agent_rules.md](agent_rules.md)  
**Grok Build only** — hybrid native image/video + factory CLI: [docs/grok_build_hybrid_tooling.md](docs/grok_build_hybrid_tooling.md) · [agent_rules.md](agent_rules.md) Rule 8.  
Default: **agent picks tools** until the user names a tool; factory remains SSOT for lips/assemble/gates.

## Video highway (short)

```bash
python scripts/smoke_agent_av.py -e EP
python scripts/episode_pipeline.py -e EP --run --from i2v --to s2v --profile deliver
# Per-cut review BEFORE assemble (hard gate — do not skip on deliver path)
python scripts/shot_approve.py -e EP -s S0x --clip approved   # each work clip
python scripts/episode_status.py -e EP                        # need_clip_approve=0
python scripts/assemble_video.py -e EP --stage work
python scripts/export_episode_to_workspace.py -e EP --dest "$AGENT_WORKSPACE/episodes/EP"
```

**Rule:** never jump to final assemble to judge middle cuts. Approve each `clips/work` clip first (`clip_status`). Assemble rejects unapproved clips (exit 22) unless `--force-clip-gate` (debug only).
