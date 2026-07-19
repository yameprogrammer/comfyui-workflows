# 개선 작업 종합 계획서
### `agent_custom` 미디어 공구함 — 5개 요구사항 분석 및 실행 계획

> **작성일**: 2026-07-19  
> **기준**: 현 파악된 도구 인벤토리 + 리서치 결과 기반

---

## 📋 현황 요약

| 항목 | 현재 상태 |
|------|-----------|
| **기본 이미지 생성** | Lonecat Z-Image(Moody)가 카탈로그 §2.1 헤드라인, Krea2는 NSFW/언센서드 포지션 |
| **Krea2 프롬프트 가이드** | `skills/generation-prompt/references/krea2_still_prompts.md` 존재, but 피상적 — 에이전트가 제대로 따르지 않음 |
| **이미지 편집/합성 가이드** | z-image·qwen 도구 카드 존재, 에이전트 자체 도구 사용 가이드 없음 |
| **키프레임 업스케일 (Krea2 강화)** | SeedVR2가 HERO 레인이지만 Krea2 워크플로 내 SeedVR2 모듈은 "planned" 상태, 통합 워크플로 없음 |
| **LTX2.3 영상 생성** | 기본값 `ltx23_aio_i2v`, Q6모델, `chain_si2v_last_frame.py` 스크립트 존재 — 프롬프트 가이드와 100프레임 제한 룰 미정립 |

---

## 🔴 요구사항별 작업 분석

---

### 요구사항 1 — Krea2를 기본 이미지 생성 모델로

**현재 구조 파악:**
- `TOOLS.md` §GENERATE 선반: `moody · illustrious_standard · krea*` 순서 (Krea가 3번째)
- `docs/tool_catalog.md` §2.1: Lonecat이 헤드라인 "실사 기본", Krea2는 "SFW/NSFW 스틸 · 패션/바디"
- `skills/generation-prompt/references/model_prompt_matrix.md`: Krea2 열 존재
- `generate_krea.py` (13KB), `generate_krea_nsfw.py` (4KB) 스크립트 완비
- 워크플로: `Krea2_SFW_NSFW_v10_AGENT_GUIDE.md` + CAPABILITIES 완비

**필요한 변경:**

| 파일 | 변경 내용 |
|------|-----------|
| `docs/tool_catalog.md` §1.A + §2.1 | Krea2를 "실사 기본" 포지션으로 격상. Lonecat은 대안 옵션으로 재편 |
| `TOOLS.md` §GENERATE 선반 | `generate_krea`를 선반 첫 번째로 재배치 |
| `docs/generation_prompt_craft.md` | Krea2 섹션을 §2(메인)로 이동, Moody는 §3으로 |
| `docs/README.md` (docs 내) | 키 이미지 기본 모델 항목 갱신 |
| `skills/generation-prompt/SKILL.md` | Dialect map에서 `generate_krea*` 첫 번째 행으로 이동 |

**작업량:** 중 (문서 수정 5개 파일, 스크립트 변경 없음)

---

### 요구사항 2 — Krea2 최적화 프롬프트 작성 가이드

**현재 파악:**
- `skills/generation-prompt/references/krea2_still_prompts.md` 존재 (7KB) — 기본 구조 있으나:
  - Krea2 12B DiT 구조(Qwen3-VL 4B 텍스트 인코더) 특성 미반영
  - Turbo vs RAW 모드 차이 설명 없음
  - Krea 공식 `expansion.txt` 시스템 프롬프트 스타일 미반영
  - "Aesthetic-first" 모델 특성 활용 전략 없음
  - 스타일/매체 레이어 전략 미비
  - 에이전트 실패 패턴 대응 미비

**신규 작성/대폭 확장 필요 항목:**

| 파일 | 내용 |
|------|------|
| `skills/generation-prompt/references/krea2_still_prompts.md` | 완전 재작성: Krea2 12B DiT 아키텍처 특성, RAW vs Turbo 운용법, 프롬프트 레이어 전략 (Subject/Style/Medium/Context/Composition/Lighting), 품질 극대화 체크리스트 |
| `docs/krea2_prompt_guide.md` (신규) | 에이전트용 심층 가이드: 공식 expansion.txt 기반 LLM 확장 전략, 재현성 확보법, 스타일 레이어 조합, 실패 패턴 → 교정 레시피 |
| `skills/generation-prompt/references/model_prompt_matrix.md` | Krea2 행에 RAW/Turbo 구분, 최적 토큰 길이 업데이트 |

**작업량:** 중-대 (심층 리서치 기반 가이드 문서 작성)

---

### 요구사항 3 — 이미지 편집/합성 파이프라인 가이드 (키프레임 제작)

**현재 파악:**
- **로컬 도구**: `generate_qwen_edit.py`, `generate_qwen_inpaint.py`, `generate_qwen_angle.py`, `generate_moody_i2i.py`, `generate_moody_controlnet.py` 등 다수 완비
- **z-image I2I 워크플로**: `image_z_image_turbo_fun_union_controlnet.json` 존재
- **qwen 멀티앵글**: `멀티앵글생성-qwen-image.json`, `generate_qwen_angle.py` 완비
- **에이전트 자체 도구**: `generate_image` 기능 보유 (현재 가이드에서 명시적 언급 없음)
- **가이드 갭**: 키프레임 제작 워크플로(T2I → edit → 합성 → 키프레임 확정) 시퀀스 가이드 없음

**필요한 작업:**

| 파일 | 내용 |
|------|------|
| `docs/keyframe_production_pipeline.md` (신규) | 키 이미지 제작 전체 파이프라인: Krea2 T2I → Qwen 편집 → z-image I2V → 멀티앵글(qwen_angle) → 합성/인페인트 → 확정. 에이전트 자체 generate_image 도구 병행 사용 지침 포함 |
| `docs/tool_catalog.md` §2.2 TRANSFORM | 에이전트 자체 이미지 도구(`generate_image`) 명시적 추가, 키프레임 제작 워크플로 조합 예시 강화 |
| `docs/agent_native_capability_autonomy.md` | 이미지 생성 도구 자율 사용 지침 강화 |

**작업량:** 중 (신규 문서 1개 + 기존 문서 2개 보완)

---

### 요구사항 4 — Krea2 Enhanced 업스케일링 도구

**현재 파악:**
- `scripts/_build_krea2_capabilities.py`: `krea2_seedvr2` feature_id 존재, 상태 **"planned"**
- `Krea2_SFW_NSFW_v10_AGENT_GUIDE.md`: §SeedVR2 upscaler 그룹 문서화됨, bypasser 확인됨
- 워크플로 JSON: `krea2SFWNSFWUncensoredImageTo_v10.json` 내 SeedVR2 upscaler 그룹 존재
- `upscale_backends.json`: `seedvr2`, `seedvr2_comfy` ready 상태
- **갭**: Krea2 인라인 SeedVR2 업스케일 preset이 "planned" → 실제 API preset 미완성

**필요한 작업:**

| 작업 | 내용 |
|------|------|
| Krea2 + SeedVR2 통합 preset 활성화 | `workflows/agent/presets/krea2_t2i_seedvr2_v10.api.json` 생성 (SeedVR2 bypasser ON 상태) |
| `_build_krea2_capabilities.py` 갱신 | `krea2_seedvr2` feature status → "ready", preset 등록 |
| `Krea2_SFW_NSFW_v10_AGENT_GUIDE.md` 갱신 | §SeedVR2 활성화 방법 + 언제 쓰는지 가이드 |
| `upscale_recommend.py` 연동 | `--domain krea2` 또는 Krea2 출력 인식 시 SeedVR2 우선 추천 |
| `docs/tool_catalog.md` §2.6 FINISH | Krea2 키프레임 → SeedVR2 업스케일 경로 명시 |
| 신규 문서 `docs/krea2_upscale_workflow.md` | Krea2 생성 → SeedVR2 enhanced 업스케일 전체 가이드 |

**작업량:** 중-대 (스크립트 수정 + 신규 preset + 문서)

---

### 요구사항 5 — LTX2.3 프롬프트 가이드 + 100프레임 제한 + Extend 워크플로

**현재 파악:**
- 기존 가이드: `skills/generation-prompt/references/ltx23_video.md` (3KB) — 기초만 있음
- `docs/ltx23_quality_research_and_improvement.md`: G2 갭 "긴 SI2V/장 I2V → max clip 캡 · 분할" 백로그 존재 (L6 항목), **미구현**
- `scripts/chain_si2v_last_frame.py` (11KB): last_frame extend 스크립트 존재
- `scripts/chain_one_take.py` (15KB): one-take 체인 스크립트 존재
- `video_backends.json` `ltx_quality_profiles.work.max_pure_i2v_sec`: 5.0 (120 프레임 = 5s@24fps) — 이미 설정되어 있으나 에이전트 강제 룰 미정립
- 공식 LTX 가이드: "5초 단위 extend" 권장, last_frame extend 방식 확인

**100프레임 = 약 4.17초@24fps 계산 (24fps 기준 정확히 97프레임 ≈ 4s)**

**필요한 작업:**

| 파일 | 내용 |
|------|------|
| `skills/generation-prompt/references/ltx23_video.md` | 완전 강화: LTX2.3 최적화 프롬프트 공식(chronological beats / 시간축 모션 서술법) + 에이전트 실패 예시 → 교정 예시 + 96프레임 이내 하드 룰 명시 |
| `docs/ltx23_quality_research_and_improvement.md` | L6 백로그 → **완료 처리**, 100프레임 제한 룰 §7 에이전트 운용 규칙에 추가 |
| `docs/ltx23_clip_extend_guide.md` (신규) | 100프레임 이상 클립 제작 전체 가이드: 분할 전략, last_frame extend 방식, `chain_si2v_last_frame.py` 사용법, `assemble_video.py` 이어붙이기, 프롬프트 연속성 유지법 |
| `docs/tool_catalog.md` §2.4 MOTION | 100프레임 제한 룰 + extend 체인 방법 명시 |
| `video_backends.json` | `max_frames_per_clip: 97` 필드 추가 (hard cap reference) |
| `agent_rules.md` | Rule 7.x LTX 클립 길이 제한 추가 |

**작업량:** 중 (신규 문서 1개 + 기존 문서 4개 수정)

---

## 📊 전체 작업 목록 (우선순위별)

| 우선 | 항목 | 파일 | 종류 |
|------|------|------|------|
| **P0** | Krea2 기본 모델 지정 | `TOOLS.md`, `tool_catalog.md`, `generation_prompt_craft.md` | 문서 수정 |
| **P0** | LTX 100프레임 제한 룰 공식화 | `ltx23_quality_research_and_improvement.md`, `tool_catalog.md`, `video_backends.json` | 문서+JSON 수정 |
| **P1** | Krea2 프롬프트 가이드 강화 | `krea2_still_prompts.md` 재작성, `krea2_prompt_guide.md` 신규 | 대형 문서 작업 |
| **P1** | LTX 프롬프트 가이드 강화 | `ltx23_video.md` 강화, `ltx23_clip_extend_guide.md` 신규 | 중형 문서 작업 |
| **P1** | 키프레임 제작 파이프라인 가이드 | `keyframe_production_pipeline.md` 신규 | 중형 문서 작업 |
| **P2** | Krea2+SeedVR2 업스케일 preset 활성화 | preset JSON 생성, capabilities 스크립트 갱신 | 스크립트+JSON |
| **P2** | Krea2 업스케일 워크플로 문서 | `krea2_upscale_workflow.md` 신규 | 소형 문서 |
| **P2** | agent_rules.md LTX 규칙 추가 | `agent_rules.md` | 문서 수정 |

---

## 🏗️ 신규 생성 파일 목록

| 파일 경로 | 크기 예상 | 역할 |
|-----------|-----------|------|
| `docs/krea2_prompt_guide.md` | ~15KB | Krea2 심층 프롬프트 가이드 |
| `docs/ltx23_clip_extend_guide.md` | ~10KB | LTX 클립 확장 파이프라인 |
| `docs/keyframe_production_pipeline.md` | ~12KB | 키프레임 제작 전체 워크플로 |
| `docs/krea2_upscale_workflow.md` | ~6KB | Krea2→SeedVR2 업스케일 가이드 |

---

## 📝 수정 파일 목록

| 파일 경로 | 변경 규모 |
|-----------|-----------|
| `TOOLS.md` | 소 (GENERATE 선반 순서 + Krea2 강조) |
| `docs/tool_catalog.md` | 중 (§1.A, §2.1, §2.2, §2.4, §2.6 수정) |
| `docs/generation_prompt_craft.md` | 중 (섹션 재배치 + Krea2 강화) |
| `docs/ltx23_quality_research_and_improvement.md` | 소 (§7 운용 규칙 + L6 완료 처리) |
| `skills/generation-prompt/SKILL.md` | 소 (dialect map 순서 변경) |
| `skills/generation-prompt/references/krea2_still_prompts.md` | 대 (완전 재작성) |
| `skills/generation-prompt/references/ltx23_video.md` | 중-대 (강화) |
| `skills/generation-prompt/references/model_prompt_matrix.md` | 소 (행 순서 + Krea2 업데이트) |
| `video_backends.json` | 소 (max_frames 필드 추가) |
| `agent_rules.md` | 소 (LTX 클립 길이 룰 추가) |

---

## ⏱️ 작업 공수 추정

| 요구사항 | 예상 토큰/시간 | 복잡도 |
|----------|---------------|--------|
| 1. Krea2 기본 모델 | 중 | 문서 수정 위주 |
| 2. Krea2 프롬프트 가이드 | 대 | 리서치 통합 신규 작성 |
| 3. 이미지 편집 파이프라인 가이드 | 중 | 신규 문서 작성 |
| 4. Krea2 업스케일 | 중 | 스크립트 수정 + 문서 |
| 5. LTX 프롬프트 + 100프레임 제한 | 중-대 | 가이드 강화 + 신규 문서 |
| **합계** | **대** | **~15–20개 파일 작업** |

---

## 🔑 핵심 판단 포인트

### 요구사항 1, 2 (Krea2 기본화 + 프롬프트):
- Krea2는 12B DiT + Qwen3-VL 4B 텍스트 인코더로, NL 산문형 프롬프트에 최적화
- 기존 `krea2_still_prompts.md`는 뼈대만 있어 **완전 재작성** 필요
- 기본 모델 지정은 **문서 순서 + 카탈로그 업데이트**로 해결 (스크립트 변경 불필요)

### 요구사항 3 (편집 파이프라인):
- 로컬 도구(z-image I2I, qwen angle/edit/inpaint)는 이미 완비됨
- **에이전트 자체 `generate_image` 도구 병행 사용** 가이드가 핵심 추가 사항
- 순서도(T2I → edit → 합성 → 확정) 형태의 신규 문서가 필요

### 요구사항 4 (Krea2+SeedVR2 업스케일):
- Krea2 워크플로 내 SeedVR2 bypasser ON 상태 API preset 파일 생성이 핵심
- `_build_krea2_capabilities.py` status 갱신 필요
- 독립 `upscale_image.py --backend seedvr2` 경로로도 동작 가능 (이미 ready)

### 요구사항 5 (LTX 100프레임 제한):
- 24fps 기준 100프레임 ≈ 4.17초, 97프레임 ≈ 4.0초
- `video_backends.json` work 프로파일 `max_pure_i2v_sec: 5.0` 이미 존재 → 강제 룰로 격상 필요
- `chain_si2v_last_frame.py`가 이미 구현됨 → 가이드 문서화만 필요
- LTX 공식 권장: 5초(=120프레임) 이내 단위 생성 후 체인

---

## ✅ 승인 요청

위 계획서를 검토 후 진행 범위와 우선순위를 알려주시면 작업을 시작하겠습니다.

**전체 진행 시 예상 순서:**
1. P0 항목 (Krea2 기본화 + LTX 프레임 룰) → 문서 즉시 수정
2. P1 항목 (심층 가이드 문서 작성) → 신규 파일 생성
3. P2 항목 (Krea2+SeedVR2 preset 활성화) → 스크립트+JSON 작업
