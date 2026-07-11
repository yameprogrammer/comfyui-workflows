# locations/ — Location packs (L2 Soft Factory)

Agent-facing set/location consistency packs. Design: [docs/location_sheet_system_design.md](../docs/location_sheet_system_design.md).

```bash
python scripts/location_create.py --id cafe_seoul_v1 --name "Seoul Cafe" --architecture "narrow wooden cafe..."
python scripts/location_expand_sheets.py --id cafe_seoul_v1 --sheets all_mvp
python scripts/location_approve.py --id cafe_seoul_v1 --from refs/master/<file>.png --as master_wide --set-primary
```
