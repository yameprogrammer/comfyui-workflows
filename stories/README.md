# stories/ — Episode / storyboard packs

```bash
# 수주 브리프 → 에피소드 (권장)
python scripts/commission_start.py --brief stories/examples/commission_brief_example.json

python scripts/story_init.py --id mina_cafe_ep01 --format cinematic_16x9 --look cinematic_moody_v1
python scripts/shot_edit.py --episode mina_cafe_ep01 --shot S02 --action "..." --motion "..."
python scripts/shot_compose.py --episode mina_cafe_ep01 --shot S01 --dry-run
python scripts/shot_approve.py --episode mina_cafe_ep01 --shot S01
python scripts/episode_i2v.py --episode mina_cafe_ep01 --dry-run
python scripts/episode_upscale.py --episode mina_cafe_ep01 --preset deliver_1080 --dry-run
python scripts/assemble_video.py --episode mina_cafe_ep01 --stage auto --dry-run

# 상태 + 파이프
python scripts/episode_status.py --episode mina_cafe_ep01
python scripts/episode_pipeline.py --episode mina_cafe_ep01 --run --from i2v --to package
python scripts/episode_contact_sheet.py --episode mina_cafe_ep01
python scripts/package_delivery.py --episode mina_cafe_ep01
```

Design: [docs/storyboard_pipeline_design.md](../docs/storyboard_pipeline_design.md) · [docs/commission_workflow.md](../docs/commission_workflow.md)
