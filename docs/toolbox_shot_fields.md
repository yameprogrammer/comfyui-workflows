# Toolbox — optional shot / episode fields

에이전트가 **에피 레일을 쓸 때만** 참고. 고정 공정 아님.  
의도 선반 SSOT: [tool_catalog.md](tool_catalog.md).

---

## I2V motion intent

| Where | Field | Example |
|-------|--------|---------|
| shot | `motion_preset` | `"push_in"` |
| shot | `i2v_motion_preset` | alias |
| shot | `motion_prompt` | extra action only |
| shot | `negative_motion` | extra neg |
| episode root | `default_motion_preset` | applies if shot omits |
| CLI | **`generate_camera_move --preset`** | one-off camera-move tool (recommended) |
| CLI | `generate_i2v --motion-preset` | same ids, low-level I2V |
| CLI | `episode_i2v --motion-preset` | batch default |

List ids:

```bash
python scripts/generate_camera_move.py --list-presets
python scripts/generate_i2v.py --list-motion-presets
```

Implementation: `lib/motion_presets.py` · compose order in `episode_i2v.py`.

Related SI2V emotion (different key): `performance` → `lib/performance_profiles.py` · [audio_motion_production_modes.md](audio_motion_production_modes.md).

---

## Shot size / identity helpers (no episode required)

| CLI | Field N/A | Role |
|-----|-----------|------|
| `generate_reframe` | — | wide/MCU/CU crop |
| `generate_ref_pack --profile quick\|default\|full` | — | face board without `characters/` |
| `generate_character_consistent` | — | ID lock scenes |

```bash
python scripts/generate_ref_pack.py --list-profiles
python scripts/generate_reframe.py --list-sizes
```

---

## Commission brief schema

`motion_preset` / `i2v_motion_preset` / `negative_motion` are optional properties on shots in  
[commission_brief.schema.json](commission_brief.schema.json).
