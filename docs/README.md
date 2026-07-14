# docs/ — 에이전트용 설계·스펙 (2026-07-14 정리)

코드보다 **문서 SSOT**를 둘 때 이 폴더를 연다.  
실행 규칙·이력: 루트 `agent_rules.md` · `process.md` · 소비자 `AGENTS.md`.

**정리 원칙**

| 구역 | 의미 |
|------|------|
| **활성 (아래 표)** | 지금 파이프·기본값·게이트의 SSOT 또는 살아 있는 백로그 |
| **참고** | 설계 배경·리서치. 구현과 충돌하면 **활성 문서·코드 우선** |
| **`archive/`** | 유효 기간 지난 세션 노트·일회성 디버그·원문 리서치 — [archive/README.md](archive/README.md) |

---

## 1. 에이전트가 먼저 읽을 것 (쇼츠 제작)

| 우선 | 문서 | 역할 | 상태 |
|------|------|------|------|
| 0 | [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md) | 공장 vs 작업대 · export 의무 | ✅ 계약 |
| 1 | [production_asset_pipeline.md](production_asset_pipeline.md) | 캐릭·로케·룩·스토리·I2V 통합 지도 | ✅ |
| 2 | [agent_video_tooling_todo.md](agent_video_tooling_todo.md) | **근시일 구현 백로그** (길이·감정 모션·export) | 📋 TODO |
| 2b | [creative_brief_autonomy_design.md](creative_brief_autonomy_design.md) | **기획 자율** — 키워드/음악만 있을 때 SOP·가드레일 (기능 비필수) | ✅ 문서 레일 |
| 3 | [agent_av_smoke_checklist.md](agent_av_smoke_checklist.md) | AV 스모크·컷 승인 체크 | ✅ |
| 4 | [audio_motion_production_modes.md](audio_motion_production_modes.md) | production_mode · SI2V · mix | ✅ 구현 진행 |
| 5 | [video_delivery_and_backends.md](video_delivery_and_backends.md) | format / work·deliver / 백엔드 | ✅ |
| 6 | [commission_workflow.md](commission_workflow.md) | 수주 → 납품 순서 | ✅ |
| — | [grok_build_hybrid_tooling.md](grok_build_hybrid_tooling.md) | Grok 전용: 네이티브+공장 (Rule 8) | ✅ |

---

## 2. 자산 파이프 (캐릭 · 룩 · 로케 · 보드)

| 문서 | 역할 | 상태 |
|------|------|------|
| [character_impl_spec.md](character_impl_spec.md) | 캐릭 시트 **구현 SSOT** | ✅ |
| [character_casting_pipeline.md](character_casting_pipeline.md) | 탐색 풀 → 승격 → 시트 | ✅ |
| [character_sheet_system_design.md](character_sheet_system_design.md) | 장기 설계 배경 | 📚 참고 (충돌 시 impl_spec) |
| [location_sheet_system_design.md](location_sheet_system_design.md) | 로케 시트 | ✅ 구현됨 (`locations/`, full_sheet) |
| [look_style_system.md](look_style_system.md) | Look core | ✅ |
| [storyboard_pipeline_design.md](storyboard_pipeline_design.md) | 샷·보드·키프레임 | ✅ 구현됨 (`shot_compose`, `storyboard_export`) |
| [moody_workflow_guide.md](moody_workflow_guide.md) | Moody T2I/I2I 운용 | ✅ |

---

## 3. 영상·오디오 백엔드

| 문서 | 역할 | 상태 |
|------|------|------|
| [video_pipeline_roadmap.md](video_pipeline_roadmap.md) | 전체 로드맵 (초기 목표 포함) | 📚 역사+방향 — **신규 TODO는 tooling_todo** |
| [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md) | 안정화 PR A–E, 립 게이트 L1–L11 | 📚 완료 이력 — 신규는 tooling_todo |
| [wan22_i2v_speed_research.md](wan22_i2v_speed_research.md) | Wan2.2 속도·캐시·BlockSwap | ✅ 참고+정책 |
| [qwen3_tts_ltx_audio_pipeline.md](qwen3_tts_ltx_audio_pipeline.md) | TTS 운용 | ✅ |
| [ace_step_bgm_pipeline.md](ace_step_bgm_pipeline.md) | ACE-Step BGM | ✅ |
| [ideogram4_typography_tool.md](ideogram4_typography_tool.md) | Ideogram 4 타이포/간판/타이틀 카드 (전 구간 T2I 아님) | ✅ 1차 |
| [ltx23_aio_pipeline_integration.md](ltx23_aio_pipeline_integration.md) | LTX AIO 백엔드 매핑 | ✅ |
| [ltx23_aio_ia2v_agent_usage.md](ltx23_aio_ia2v_agent_usage.md) | LTX IA2V 에이전트 사용법 | ✅ |
| [comfy_memory_and_model_switching.md](comfy_memory_and_model_switching.md) | VRAM·모델 패밀리 전환 | ✅ |
| [upscale_research_and_design.md](upscale_research_and_design.md) | ≤4K 업스케일 | ✅ |
| [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md) | FLF/원테이크 이음 | ✅ chain_one_take · shot_compose --from-prev-shot |
| [shorts_subtitles.md](shorts_subtitles.md) | 쇼츠 SRT + soft burn | ✅ |
| [sfx_queue_notes.md](sfx_queue_notes.md) | SFX 큐 관례 | ✅ 문서 |
| [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md) | **댄스 챌린지 쇼츠 공정** (레퍼 안무·별 장르) | 📋 설계 초안 · 미착수 |
| [delivery_handoff.md](delivery_handoff.md) | `deliveries/` 패키징 | ✅ |

---

## 4. 선택 참고 (본선 아님)

| 문서 | 역할 |
|------|------|
| [openmontage_capability_catalog.md](openmontage_capability_catalog.md) | OpenMontage 기능·유용도 라벨 |
| [openmontage_pipeline_recipes.md](openmontage_pipeline_recipes.md) | OM 파이프 레시피 목록 |
| [commission_brief.schema.json](commission_brief.schema.json) | 브리프 JSON 스키마 |

OpenMontage로 `episode_pipeline` 대체 금지.

---

## 5. 아카이브 (2026-07-14 이동)

| 이전 위치 | → |
|-----------|---|
| `session_status_2026-07-13_ltx_aio_switch.md` | `archive/sessions/` |
| LTX 라우팅 분석·스냅샷·manual vs agent·JSON | `archive/ltx23_debug/` |
| turnaround/storyboard 커뮤니티 리서치, OM eval notes | `archive/research/` |

상세: [archive/README.md](archive/README.md).

---

## 경로

```text
workflows/agent/     워크플로우 JSON
scripts/             CLI
lib/                 공유 코드
characters|looks|locations|stories/
```
