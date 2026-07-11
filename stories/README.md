# stories/ — Episode / storyboard packs

```bash
python scripts/story_init.py --id mina_cafe_ep01 --format cinematic_16x9 --look cinematic_moody_v1
# edit stories/mina_cafe_ep01/shots.json
python scripts/shot_compose.py --episode mina_cafe_ep01 --shot S01 --dry-run
python scripts/shot_approve.py --episode mina_cafe_ep01 --shot S01
```

Design: [docs/storyboard_pipeline_design.md](../docs/storyboard_pipeline_design.md)
