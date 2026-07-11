# docs/ — 에이전트용 설계·스펙 문서

코드보다 **문서 SSOT**를 둘 때 이 폴더를 연다.  
실행 규칙·작업 이력은 루트 `agent_rules.md` / `process.md` 를 유지한다 (에이전트 핸드오프 습관).

| 문서 | 역할 |
|------|------|
| [character_impl_spec.md](character_impl_spec.md) | 캐릭터 시트 **구현 SSOT** (코딩 시 우선) |
| [character_sheet_system_design.md](character_sheet_system_design.md) | 캐릭터 장기 설계·리서치 |
| [video_pipeline_roadmap.md](video_pipeline_roadmap.md) | 영상 파이프라인 로드맵 |
| [video_delivery_and_backends.md](video_delivery_and_backends.md) | 납품 1080p / work 해상도 / I2V 멀티 백엔드 |
| [moody_workflow_guide.md](moody_workflow_guide.md) | Moody T2I/I2I 운용 가이드 |

워크플로우 JSON: `../workflows/agent/`  
CLI 스크립트: `../scripts/`
