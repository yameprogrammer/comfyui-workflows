# docs/ — 에이전트용 설계·스펙 문서

코드보다 **문서 SSOT**를 둘 때 이 폴더를 연다.  
실행 규칙·작업 이력은 루트 `agent_rules.md` / `process.md` 를 유지한다.

## 영상 제작 — 자산 파이프 (읽기 순서)

| 순서 | 문서 | 역할 |
|------|------|------|
| 1 | [production_asset_pipeline.md](production_asset_pipeline.md) | **통합 지도** — 캐릭터·로케·룩·스토리·I2V·납품 |
| 2 | [character_impl_spec.md](character_impl_spec.md) | 캐릭터 시트 **구현 SSOT** |
| 3 | [location_sheet_system_design.md](location_sheet_system_design.md) | 로케이션 시트 설계 (구현 대기) |
| 4 | [look_style_system.md](look_style_system.md) | Look/style core (`looks/`) |
| 5 | [storyboard_pipeline_design.md](storyboard_pipeline_design.md) | 샷리스트·보드·키프레임 설계 (구현 대기) |
| 6 | [video_pipeline_roadmap.md](video_pipeline_roadmap.md) | 전체 영상 로드맵 |
| 7 | [video_delivery_and_backends.md](video_delivery_and_backends.md) | format / work·deliver / I2V 백엔드 |
| 8 | [upscale_research_and_design.md](upscale_research_and_design.md) | 업스케일 ≤4K |
| 9 | [delivery_handoff.md](delivery_handoff.md) | 사용자 납품 패키징 (`deliveries/`) |
| 10 | [commission_workflow.md](commission_workflow.md) | 수주 브리프 → 납품 순서 |
| 11 | [audio_motion_production_modes.md](audio_motion_production_modes.md) | **오디오·SI2V·production_mode / mix_policy** |

## 기타

| 문서 | 역할 |
|------|------|
| [character_sheet_system_design.md](character_sheet_system_design.md) | 캐릭터 장기 설계·리서치 |
| [moody_workflow_guide.md](moody_workflow_guide.md) | Moody T2I/I2I 운용 |

워크플로우 JSON: `../workflows/agent/`  
CLI: `../scripts/`  
데이터: `../characters/` · `../looks/` · `../locations/` · `../stories/`
