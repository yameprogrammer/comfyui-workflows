# Pilot character brief — mina_park_v1

- **Level target**: L2 Soft Package
- **Style**: cinematic_photoreal / Moody **pro**
- **Purpose**: First E2E test of Character Factory (create → approve master → expand → approve MVP)

---

## Identity

| Field | Value |
|------|--------|
| `id` | `mina_park_v1` |
| `display_name` | Mina Park |
| Age | mid-20s |
| Presentation | female |
| Ethnicity notes | East Asian / Korean |
| Face | oval face, soft jawline, warm brown eyes, straight natural brows, natural skin texture |
| Hair | shoulder-length dark brown hair, soft natural waves, middle-ish part |
| Body | average-to-slightly-petite height, slim-athletic |
| Distinctive | small mole under left eye |
| Default wardrobe | black crew-neck t-shirt, light wash blue jeans, white sneakers, minimal jewelry |
| Alt wardrobe | light beige trench coat, white blouse, dark trousers, simple sneakers |
| Forbidden | glasses, heavy tattoos, drastic age-up, blonde hair |

## Personality (performance notes)

- Reserved, observant, warm when comfortable
- Default expression: soft neutral / slight smile
- Mannerism: tucks hair behind ear when thinking

## Locked prompt blocks

### positive_core

Use file: [samples/mina_positive_core.txt](samples/mina_positive_core.txt)

### master T2I prompt (full)

Use file: [samples/mina_positive_master.txt](samples/mina_positive_master.txt)

### negative_core

Use file: [samples/mina_negative_core.txt](samples/mina_negative_core.txt)

---

## MVP approve checklist

After generation, human should promote:

- [ ] `master_front`
- [ ] `master_full` (optional but recommended)
- [ ] `turn_front`, `turn_qf`, `turn_side`, `turn_back`
- [ ] `expr_neutral`, `expr_joy`, `expr_sad`, `expr_angry`, `expr_surprise`, `expr_think`
- [ ] `costume_default`, `costume_alt1`

Then set `bible.status` / `manifest.status` = `approved`, `manifest.level` = `L2`.

---

## Suggested CLI sequence (after P1+P2 code exists)

```bash
cd F:\ComfyUI_workflows\agent_custom

python character_create.py ^
  --id mina_park_v1 ^
  --name "Mina Park" ^
  --model pro ^
  --candidates 4 ^
  --seed-base 10001 ^
  --appearance-prompt-file characters/pilots/samples/mina_positive_master.txt

# Human picks best master candidate, then:
python character_approve.py --id mina_park_v1 --from refs/master/<chosen>.png --as master_front --set-primary

python character_expand_sheets.py --id mina_park_v1 --sheets all_mvp --model pro --candidates 2

# Approve best of each (repeat)
python character_approve.py --id mina_park_v1 --from refs/turnaround/<chosen>.png --as turn_side
# ...
```

## Manual fallback (P1 only, no character_*.py yet)

See `character_impl_spec.md` §9 and use `generate_moody.py` / `generate_moody_i2i.py` with sample prompt files.
