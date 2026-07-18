# Story / episode package

Created by `scripts/story_init.py`.  
SSOT: `shots.json`. Design: [docs/storyboard_pipeline_design.md](../../docs/storyboard_pipeline_design.md).

**Optional (toolbox, not required):**

| Field | Where | Use |
|-------|--------|-----|
| `motion_preset` | each shot | I2V intent (`push_in`, `idle`, …) → `episode_i2v` |
| `default_motion_preset` | root of `shots.json` | fallback for all shots |
| `motion_prompt` | each shot | extra motion text (composes with preset) |

```bash
python scripts/generate_i2v.py --list-motion-presets
python scripts/episode_i2v.py -e THIS_EP --motion-preset push_in
```

Docs: [toolbox_shot_fields.md](../../docs/toolbox_shot_fields.md) · [tool_catalog.md](../../docs/tool_catalog.md).
