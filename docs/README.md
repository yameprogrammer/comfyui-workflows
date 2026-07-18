# docs/ — 설계·스펙 · 도구 문서

`agent_custom` = ComfyUI **미디어 공구함** (의도별 도구를 골라 조합).  
고정 양산 공정 문서 모음이 **아님**.  
실행 규칙·이력: 루트 `README.md` · `AGENTS.md` · `agent_rules.md` · `process.md`.

**정리 원칙**

| 구역 | 의미 |
|------|------|
| **도구 명세 (1순위)** | [tool_catalog.md](tool_catalog.md) — **의도 선반** · 무엇을 골라 쓸지 |
| **활성** | 도구 계약·백엔드 SSOT |
| **참고** | 설계 배경. 충돌 시 **코드 + tool_catalog** 우선 |
| **옵션 레일** | 에피소드/`stories/` · 캐릭 패키지 — **쓸 때만** |
| **`archive/`** | 만료 세션·일회성 — [archive/README.md](archive/README.md) |

---

## 1. 에이전트가 먼저 읽을 것

| 우선 | 문서 | 역할 | 상태 |
|------|------|------|------|
| **0** | **[tool_catalog.md](tool_catalog.md)** · [../TOOLS.md](../TOOLS.md) | **의도→CLI 공구함 SSOT** (GENERATE/TRANSFORM/MOTION…) | ✅ **입구** |
| 0b | [toolbox_shot_fields.md](toolbox_shot_fields.md) | 옵션 샷 필드 (`motion_preset` 등) · ref_pack/reframe | ✅ |
| 0c | [style_transfer_research.md](style_transfer_research.md) | 스타일 전이 리서치 → `generate_style_transfer` | ✅ |
| 0d | [toolbox_card_standard.md](toolbox_card_standard.md) | 한 줄 예시 + 실패 시 대안 카드 표준 | ✅ |
| 1 | [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md) | 공구함 vs 프로젝트 작업대 · export | ✅ |
| 2 | [video_delivery_and_backends.md](video_delivery_and_backends.md) | format / work·deliver / I2V 백엔드 | ✅ |
| 3 | [generation_prompt_craft.md](generation_prompt_craft.md) | 프롬프트 품질 (쓸 때) | ✅ |
| 4 | [failure_notes_system.md](failure_notes_system.md) | 실패 노트 공유 | ✅ |
| 5 | [agent_native_capability_autonomy.md](agent_native_capability_autonomy.md) | 자체 툴 자율 (Rule 8.0) | ✅ |
| 6 | [comfy_memory_and_model_switching.md](comfy_memory_and_model_switching.md) | VRAM · 모델 전환 | ✅ |
| — | [agent_video_tooling_todo.md](agent_video_tooling_todo.md) | 툴 백로그 | 📋 |

### 옵션 — 에피소드/`stories/` 레일 또는 장기 자산을 **쓸 때만**

| 문서 | 역할 |
|------|------|
| [../skills/video-direction/SKILL.md](../skills/video-direction/SKILL.md) | 연출 스킬 (장편·뮤비 기획 시) |
| [video_director_master_persona.md](video_director_master_persona.md) | 컷 문법 |
| [image_cut_verification_gate.md](image_cut_verification_gate.md) | 키프레임·클립 QA |
| [production_asset_pipeline.md](production_asset_pipeline.md) | 캐릭·로케·스토리 통합 지도 |
| [audio_motion_production_modes.md](audio_motion_production_modes.md) | SI2V · mix |
| [creative_brief_autonomy_design.md](creative_brief_autonomy_design.md) | 기획 SOP (선택) |
| [character_casting_pipeline.md](character_casting_pipeline.md) | 캐릭 패키지 A→B→C (자산 쌓을 때) |

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
| [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md) | LTX 품질 리서치·갭·프로필 백로그 | ✅ |
| [ltx_face_stability.md](ltx_face_stability.md) | LTX 얼굴 붕괴 완화 | ✅ |
| [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md) | Wan vs LTX I2V A/B | ✅ |
| [comfy_memory_and_model_switching.md](comfy_memory_and_model_switching.md) | VRAM·모델 패밀리 전환 | ✅ |
| [upscale_research_and_design.md](upscale_research_and_design.md) | ≤4K 업스케일 | ✅ |
| [youtube_ref_ingest_research.md](youtube_ref_ingest_research.md) | 유튜브 레퍼 인제스트 · CLI 구현 | ✅ |
| [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md) | FLF/원테이크 이음 | ✅ chain_one_take · shot_compose --from-prev-shot |
| [v2v_intent_pipeline_design.md](v2v_intent_pipeline_design.md) | **V2V 의도** camera/motion/style · generate_v2v | 📋 P0 · experimental |
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
