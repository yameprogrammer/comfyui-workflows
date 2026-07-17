# Legacy mini workflows (emergency only)

These are **old mini graphs** used only when:

```bash
python scripts/generate_moody.py --legacy-mini ...
# or AGENT_T2I_BACKEND=legacy_mini / AGENT_I2I_BACKEND=legacy_mini / AGENT_CN_BACKEND=legacy_mini
```

**Production SSOT:** `workflows/agent/presets/*.api.json` via `lib/workflow_api_runner.py`.

| File | Replaced by |
|------|-------------|
| `T2I-moody.json` | `presets/lonecat_t2i_turbo.api.json` |
| `I2I-moody.json` | `presets/lonecat_i2i_identity.api.json` |
| `I2I-ControlNet-moody.json` | `presets/zimage_fun_union_controlnet.api.json` |
| `T2I-krea.json` | `presets/krea2_t2i_v10.api.json` |
| `T2I-z-image-turbo.json` | absorbed into Lonecat T2I |

Do not add new production paths that load these files.
