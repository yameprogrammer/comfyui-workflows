# Human UI workflows

ComfyUI **웹 UI**에서 손으로 실험·튜닝한 워크플로우 내보내기를 두는 곳입니다.

- 스크립트는 **이 폴더를 기본으로 읽지 않습니다.**
- 실험이 안정되면 `../agent/presets/*.api.json` 으로 프로모트하고, 해당 `generate_*.py` 매핑을 맞춘 뒤 커밋합니다.
- 파일 이름 예: `I2I-moody__denoise085-experiment.json` (날짜·의도 suffix 권장)

에이전트 배치용 SSOT는 [../agent/](../agent/) 입니다.

## 정리된 팩

| 폴더 | 내용 |
|------|------|
| [wan22/](wan22/) | WAN 2.2 I2V / FLF / FaceEnhance / Upscale / Animate 선별본 + [AGENT_GUIDE.md](wan22/AGENT_GUIDE.md) |
| Lonecat / Krea2 / LTX / Qwen | 루트 human JSON + `*_AGENT_GUIDE.md` · `*_CAPABILITIES.json` |
