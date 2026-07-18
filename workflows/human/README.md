# Human UI workflows

ComfyUI **웹 UI** 실험·튜닝 원본.  
에이전트는 보통 `scripts/generate_*` + 프리셋으로 호출한다.

**무엇을 고를지 (의도 선반):** [docs/tool_catalog.md](../../docs/tool_catalog.md) · 입구 [TOOLS.md](../../TOOLS.md)

```text
안정 UI → agent/presets 또는 expand 러너 → generate_*.py → tool_catalog 카드 갱신
```

---

## 선반별 팩 · 가이드

### GENERATE / TRANSFORM (스틸)

| 경로 | 선반 | 내용 |
|------|------|------|
| [Lonecat_AIO…_AGENT_GUIDE.md](Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md) | GENERATE · TRANSFORM | Z-Image T2I/I2I AIO |
| [Krea2…_AGENT_GUIDE.md](Krea2_SFW_NSFW_v10_AGENT_GUIDE.md) | GENERATE | Krea2 SFW/NSFW |
| [illustrious_standard_v37/](illustrious_standard_v37/) | GENERATE | Illustrious XL Standard |
| [character_consistency/](character_consistency/) | TRANSFORM | ID 유지 오케스트레이션 |
| [style_transfer/](style_transfer/) | TRANSFORM | 스타일 전이 (Qwen multi-ref / preset) |
| [viewpoint/](viewpoint/) | CAMERA | 깊이·시점 과장 (Qwen multi-angle h/v/zoom) |
| [ref_pack/](ref_pack/) | TRANSFORM / ASSETS-lite | 원샷 레퍼 팩 (face→board, no characters/) |
| [camera_move/](camera_move/) | MOTION | 카메라 무빙 의도 I2V (`generate_camera_move`) |
| [idle_loop/](idle_loop/) | MOTION | 아이들·루프 (`generate_idle_loop`) |
| [dance_ref/](dance_ref/) | MOTION | 댄스/레퍼 모션 (`generate_dance_ref`) |
| [Qwen_InstantX_Inpaint_AGENT_GUIDE.md](Qwen_InstantX_Inpaint_AGENT_GUIDE.md) | TRANSFORM | 마스크 인페 |
| [NEWKrea2BooguIdeogram4_AGENT_GUIDE.md](NEWKrea2BooguIdeogram4_AGENT_GUIDE.md) | GENERATE | 타이포·잡지 파이프 |
| `image_qwen_image_edit_2509.json` 등 | TRANSFORM | Qwen edit UI 원본 |
| `멀티앵글생성-qwen-image.json` | CAMERA | Qwen multi-angle UI |
| `image_z_image_turbo_fun_union_controlnet.json` | CAMERA | Fun Union CN |

### MOTION

| 경로 | 내용 |
|------|------|
| [LTX23_AIO_v44_AGENT_GUIDE.md](LTX23_AIO_v44_AGENT_GUIDE.md) | LTX AIO I2V/FLF/S2V… |
| [ltx23_latentheart_aio/](ltx23_latentheart_aio/) | Director 모듈 |
| [ltx23_redmix_krea2/](ltx23_redmix_krea2/) | REDMix I2V |
| [ltx23_nsfw/](ltx23_nsfw/) | NSFW I2V/Director **18+** |
| [wan22/](wan22/) | Wan I2V / FLF / face / upscale |
| [yaw_wan22/](yaw_wan22/) | YAW MoE T2V/I2V |

### VOICE · FINISH

| 경로 | 선반 | 내용 |
|------|------|------|
| [qwen3_tts/](qwen3_tts/) | VOICE | TTS clone/custom/design |
| [image_upscale_dual/](image_upscale_dual/) | FINISH | 스틸 듀얼 레인 업스케일 |

---

## 에이전트 가이드 공통 헤더

새/갱신 `*_AGENT_GUIDE.md` 상단 + 본문에 **한 줄 예시** 필수.  
표준: [docs/toolbox_card_standard.md](../../docs/toolbox_card_standard.md)

```markdown
> **Toolbox shelf:** TRANSFORM · CAMERA · …  
> **CLI:** `python scripts/…`  
> **Example:** `python scripts/… -i in.png -o out.png`  
> **Alternatives:** if X → `other_cli …` · if Y → `…`  
> **Catalog:** [docs/tool_catalog.md](../../docs/tool_catalog.md)

## Quick start
```bash
python scripts/… -i … -o …
```
```

검색 인덱스: `python scripts/tool_intent.py "…"` → `eg` + `if fail → try`
