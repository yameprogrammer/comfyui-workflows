# Script archive (one-off probes / failed experiments)

| Folder | Contents |
|--------|----------|
| `tmp/` | `_tmp_*` investigation scripts and smoke logs from Lonecat/Qwen/LTX conversion |
| `probes/` | One-shot analyzers and debug exporters |

**Keep in `scripts/` (active):**

- `_bootstrap.py` — path bootstrap for all CLIs  
- `_build_*_preset.py` / `_build_*_capabilities.py` — regenerate agent presets  
- `_lonecat_export_api.mjs` — full Lonecat graphToPrompt export  
- `_export_lonecat_feature_presets.mjs` — feature preset snapshots (detailer / upscale)

Do not import from `_archive` in production CLIs.
