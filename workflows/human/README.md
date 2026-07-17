# Human UI workflows

ComfyUI **웹 UI**에서 실험·튜닝한 워크플로 원본입니다.  
에이전트는 보통 프리셋/expand 러너로 호출하고, **특징 명세는** [docs/tool_catalog.md](../../docs/tool_catalog.md).

- 안정되면 `../agent/presets` + `generate_*.py` + **tool_catalog 한 블록** 갱신.
- 파일 이름 예: `image_qwen_image_instantx_inpainting_controlnet.json`

## 정리된 팩

| 폴더 | 내용 |
|------|------|
| [illustrious_standard_v37/](illustrious_standard_v37/) | Legendaer Illustrious XL Standard_V37 + [AGENT_GUIDE.md](illustrious_standard_v37/AGENT_GUIDE.md) · feature 스위치 메뉴 |
| [yaw_wan22/](yaw_wan22/) | YAW Wan 2.2 MoE v0.50 T2V/I2V 실 UI + GGUF · [AGENT_GUIDE.md](yaw_wan22/AGENT_GUIDE.md) |
| [wan22/](wan22/) | WAN 2.2 I2V / FLF / FaceEnhance / Upscale / Animate 선별본 + [AGENT_GUIDE.md](wan22/AGENT_GUIDE.md) |
| [qwen3_tts/](qwen3_tts/) | Qwen3-TTS 음성복제·커스텀·디자인 + [AGENT_GUIDE.md](qwen3_tts/AGENT_GUIDE.md) |
| [ltx23_nsfw/](ltx23_nsfw/) | Kenpechi LTX NSFW I2V/Director |
| Lonecat / Krea2 / LTX / Qwen image | 루트 human JSON + `*_AGENT_GUIDE.md` · `*_CAPABILITIES.json` |
