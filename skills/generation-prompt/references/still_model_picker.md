# Still model picker → official prompt dialect

**When:** before any still `generate_*`.  
**CLI:** `python scripts/prompt_dialect.py pick "…"` · `show <id>`  
**Which tool:** `python scripts/tool_intent.py "…"` first if the CLI is unknown.

Do **not** write one prompt and spray it across models.

| Need | CLI | Dialect id | Official form |
|------|-----|------------|---------------|
| 시네·패션 실사 키프레임 | `generate_krea` | `krea` | NL paragraph 90–140w, materials |
| Z-Image I2I / 실험 | `generate_moody` | `zimage` | clause stack; positives not negatives |
| 애니 Danbooru XL | `generate_illustrious_standard` | `illustrious` | quality tags + Danbooru |
| 2D 애니 초고속 | `generate_anima` | `anima` | tags + short pose; replace CLI soup |
| Flux 추종 / 짧은 글자 | `generate_flux` | `flux1` | NL 30–80w; no negatives |
| 마스크 인페 (실사) | `generate_flux_fill` | `flux_fill` | hole contents only |
| Klein 빠른 T2I/I2I | `generate_flux2_klein` | `flux2_klein` | NL; I2I = one change |
| SDXL / Lightning 스카우트 | `generate_sdxl` | `sdxl` | short NL or Pony scores |
| 문장 편집 | `generate_qwen_edit` | `qwen_edit` | one imperative + keep rest |
| 화면 글자 히어로 | `generate_ideogram4` | `ideogram` | `--text` / exactly reading |

Full recipes live in the `ref` of `python scripts/prompt_dialect.py show <id>`.
