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
| *(SI2V InfiniteTalk)* | **JSON 없음 — API inject** | `scripts/generate_s2v.py` / `episode_s2v.py` |

별칭·파일 매핑은 [catalog.json](catalog.json) 이 코드와 공유하는 SSOT입니다.

SI2V는 WanVideoWrapper 노드 그래프를 `generate_s2v.build_infinitetalk_api` 가 런타임에 조립한다.  
human UI 예제(`ComfyUI-WanVideoWrapper/example_workflows/*InfiniteTalk*`)를 수정할 때 러너 노드 타입과 동기화할 것.

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
