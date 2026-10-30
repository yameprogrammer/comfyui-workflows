
<!-- IMAGE-TOOL-PRIORITY-20261018 -->
## 이미지 도구 선택 — 최신 사용자 지침 (2026-10-18)

> 로컬 도구들이 텍스트가 포함된 뭔가를 만들 때는 좀 성능이 떨어지니까 텍스트가 포함된 뭔가를 만드는건 보조관의 이미지 도구를 사용하고 그외에는 Flux3나 Krea2 모델을 사용해서 작업 하는걸로 합시다.

- **이미지 안에 글자가 포함되면 보좌관 이미지 생성 도구를 사용한다.** 로컬 모델의 글자 표현 한계를 고려한 선택이다. 생성 후 실제 이미지를 열어 철자·문구·누락·가독성을 검수한다.
- **글자 없는 이미지는 로컬 FLUX3 또는 Krea2를 사용한다.** FLUX3는 full-caption, Krea2는 해당 모델의 자연어 프롬프트 규칙을 따른다.
- 이번 지침은 이전 **“텍스트가 있으면 Flow 또는 보좌관 이미지 도구”**보다 최신이며 이미지 선택 시 우선 적용한다. **Flow 전면 금지를 뜻하지 않는다.**
- 정확한 자막·타이틀·광고 문구는 기존대로 Remotion/Blender 등의 별도 텍스트 소스·레이어로 후반 합성할 수 있다. 글자 없는 배경·원화 생성은 위 로컬 모델을 사용한다.
- 적용 범위는 이미지 생성 도구 선택이다. **영상·TTS·Blender·Remotion 도구 선택과 기존 편집 워크플로우는 변경하지 않는다.**

[공장 이미지 선택 가이드](../../../docs/agent_native_capability_autonomy.md). 아래 모델 표는 기능·방언 참고이며 최신 사용자 선택 지침을 대체하지 않는다.

<!-- /IMAGE-TOOL-PRIORITY-20261018 -->

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
| FLUX3 T2I / reference edit / layout | `generate_flux3` | Read [flux3_still.md](flux3_still.md) directly; no registered prompt_dialect id | Full scene caption + quoted literal text; not the FLUX.2 recipe |
| SDXL / Lightning 스카우트 | `generate_sdxl` | `sdxl` | short NL or Pony scores |
| 문장 편집 | `generate_qwen_edit` | `qwen_edit` | one imperative + keep rest |
| 화면 글자 히어로 | `generate_ideogram4` | `ideogram` | `--text` / exactly reading |

Full recipes live in the `ref` of `python scripts/prompt_dialect.py show <id>`.
