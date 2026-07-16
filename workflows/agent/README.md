# Agent-dedicated workflows

스크립트·캐릭터 파이프라인이 읽는 **프로덕션 워크플로우**입니다.  
휴먼 UI 실험 파일과 섞지 마십시오.

## Catalog (SSOT 별칭)

| 키 | 파일 | 스크립트 |
|----|------|----------|
| `t2i_moody` | `T2I-moody.json` | `scripts/generate_moody.py` |
| `i2i_moody` | `I2I-moody.json` | `scripts/generate_moody_i2i.py`, `shot_with_character.py` |
| `i2i_controlnet_moody` | `I2I-ControlNet-moody.json` | `scripts/generate_moody_controlnet.py`, expand CN |
| `i2v_wan22_a14b` | `I2V-wan22-a14b.json` | `scripts/generate_i2v.py` (default) |
| `t2i_krea` | `T2I-krea.json` | `scripts/generate_krea.py` |
| `t2i_z_image_turbo` | `T2I-z-image-turbo.json` | (베이스/참고) |
| `qwen_edit_2511` | **JSON 없음 — API inject** | `generate_qwen_edit.py` (기본 GGUF=angle과 동일 모델) · `shot_keyframe_edit --engine qwen` |
| `qwen_angle_2511` | **JSON 없음 — API inject** | `generate_qwen_angle.py` · `character_qwen_turns` (Angles LoRA 턴) |
| *(SI2V InfiniteTalk)* | **JSON 없음 — API inject** | `generate_s2v.py --backend infinitetalk` |
| *(SI2V LTX custom-audio)* | **JSON 없음 — API inject** | `generate_s2v.py --backend ltx23_ia2v` |

### Still-edit engine coexistence

| 엔진 | 스크립트 | 가중치 | 언제 |
|------|----------|--------|------|
| Moody I2I | `generate_moody_i2i` / `shot_keyframe_edit --engine moody` | Moody/ZImage | 약한 표정·톤 denoise |
| Qwen Edit | `generate_qwen_edit` / `shot_keyframe_edit --engine qwen` | **2509 Q5 GGUF** + 지시 인코더 (Angles 없음) | 물체 교체·제거 |
| Qwen Angle | `generate_qwen_angle` / `character_qwen_turns` | **2511 GGUF** + Lightning + **Angles LoRA** | 헤드/바디 멀티뷰 (`<sks>`) |

편집 기본 백엔드 `gguf_2509`. **Lightning 기본 ON** → 결과 부족 시만 `--no-lightning --steps 20 --cfg 4`.

별칭·파일 매핑은 [catalog.json](catalog.json) 이 코드와 공유하는 SSOT입니다.

SI2V는 런타임 API inject (`lib/ltx_s2v.py` / `build_infinitetalk_api`).  
참고 휴먼 WF: `F:\ComfyUI_workflows\LTX2.3\Custom-Audio\…`, Wan InfiniteTalk 예제.  
공식 LTX IC-LoRA LipDub은 V2V + gated 가중치 — 에이전트 미연동.

## Agent-friendly 설계 원칙

1. **주입 포트 안정**: 스크립트가 찾는 `class_type`(예: `KSampler`, `Prompt (LoraManager)`, `UNETLoader`)을 함부로 바꾸지 말 것.
2. **링크 우선**: 위젯 값보다 링크된 입력이 우선한다. UI에서 링크를 끊으면 스크립트 가정이 깨진다.
3. **한 그래프 한 책임**: T2I / I2I / ControlNet / I2V를 한 파일에 몰아넣지 않는다.
4. **프로모트 시 스크립트 동반**: JSON만 바꾸고 `generate_*.py` 매핑을 안 맞추면 금지 (agent_rules Rule 2).
5. **해상도**: I2V는 work 해상도 프리셋 기준. 납품 1080p는 업스케일 층 (video_delivery_and_backends.md).

## 수정 체크리스트

- [ ] `workflows/human/` 또는 UI에서 검증했는가?
- [ ] agent 디렉터리에 반영했는가?
- [ ] 해당 `generate_*.py` / convert 로직 동작 확인?
- [ ] `process.md` 기록?

## 레거시

루트 워크플로우 JSON은 제거되었다. **편집·프로모트는 여기(`workflows/agent/`)에만** 한다.
