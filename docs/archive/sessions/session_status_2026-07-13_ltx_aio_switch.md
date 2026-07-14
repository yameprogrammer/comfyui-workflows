> **ARCHIVED (2026-07-14)** — 운영 SSOT 아님. 인덱스: [../../README.md](../../README.md). 활성 백로그: [../../agent_video_tooling_todo.md](../../agent_video_tooling_todo.md).

# 세션 상태 — 2026-07-13 (LTX AIO 스위치 · cafe_gomin 쇼츠)

- **채널**: 채널 주인장이 뭐해야 할지모르겠답니다  
- **팩토리**: `F:\ComfyUI_workflows\agent_custom`  
- **종료 시점**: 문서 반영 + 커밋/푸시 직전

---

## 1. 오늘 끝난 것 (Done)

### 1.1 LTX 2.3 = 실 AIO 워크플로 + 스위치/셀렉트

| 항목 | 내용 |
|------|------|
| 기본 러너 | `lib/ltx_aio_workflow_runner.build_aio_switched_api` |
| 모드 mute | `lib/ltx_aio_mode_select` — Orchestrator `[[P:]]` 표 |
| UI expand | `lib/ltx_aio_ui_expand` — subgraph, Get/Set, AE CLIP, widget 순서, NEVER 스킵 |
| CLI | `scripts/generate_s2v.py` — `ltx23_aio*` / `ltx23_ia2v` 전부 스위치 경로 |
| 미니 그래프 | **비기본** — `AGENT_LTX_FORCE_MINI_GRAPH=1` only |
| 동결 IA2V 템플릿 | 폴백 — `AGENT_LTX_FORCE_LIVE_TEMPLATE=1` |
| WF 보관 | `workflows/human|agent/ltx23AllInOne…v44(.json/_IA2V.json)` + live template |
| 매니페스트 | `workflows/agent/ltx23_aio.manifest.json` → `ready_switch_select` |

**스모크**: S02 switch 생성 OK (~100s, `runner=ltx_aio_workflow_runner`).

### 1.2 cafe_gomin_ep01 쇼츠 1편 (LTX 스위치)

| 샷 | 경로 | 비고 |
|----|------|------|
| S01 | `ltx23_aio_i2v` | establishing |
| S02–S05 | `chain_si2v_last_frame` + `ltx23_aio` | last-frame → next keyframe, 하드컷 조립 |
| 최종 | `exports/final/cafe_gomin_ep01_ltx23_switch(_playable).mp4` | ~44.5s, 544×960@24, BGM 0.18 |
| 채널 복사 | `D:\쇼츠 작업\…\exports\cafe_gomin_ep01\` | playable 포함 |

### 1.3 InfiniteTalk / Sage Attention

| 항목 | 상태 |
|------|------|
| Comfy `sageattention` 1.0.6 | 설치됨, import OK |
| LTX AIO | `GGUFLoaderKJ.attention_override=sageattn` (기존) |
| 에이전트 IT | **`attention_mode=sageattn` 기본**으로 수정 (`AGENT_IT_ATTENTION`로 폴백 가능) |

### 1.4 메모리·엔진

- `lib/comfy_engine_session.py` — 패밀리 전환 시 free 훅 (이전 세션 이슈 대응 코드 유지)

---

## 2. QA / 알려진 한계 (미해결)

1. **얼굴 붕괴 (LTX)**  
   - 장클립(S03~11s, S05~14s) + clip > audio 꼬리에서 드리프트 심함.  
   - 원본 S02 키프레임은 양호, 생성 후 무너짐.

2. **last-frame 체인 ≠ 원테이크**  
   - 생성: 이전 클립 **끝 프레임을 다음 시작 이미지**로 씀 (메타 `continuity.chain=last_frame`).  
   - 조립: **하드컷**. 샷 안에서 얼굴이 깨지면 그 망가진 last frame이 다음 seed → 붕괴 전파.  
   - FLF/크로스페이드 브릿지 없음.

3. **Wan / InfiniteTalk**  
   - 얼굴·립 쪽은 상대 우위 가능, 속도·톤 튜닝 필요.  
   - lightx2v 4–8 step / 해상 / TeaCache / sage 조합은 “쓸 만하게 빠르게”이지 LTX급은 아님.  
   - Wan 2.2 전면 채택은 **보류** (별도 벤치·튜닝).

---

## 3. 다음에 할 일 (Next)

### 공정 규칙 (2026-07-13 추가 · 완료)
- **합본 전 컷별 검수** Rule 7.2 · `clip_status` · assemble exit 22 · chain 이전 컷 승인 필수  
- 퀄리티 실험도 **컷 승인 후** 합본 — 중간 컷만 고치려고 final을 먼저 보지 말 것

우선순위 제안:

1. **LTX 얼굴/입·사물** (컷 단위) — **S02 벤치 완료**  
   - ✅ S02 A/B: baseline 6s (**채택**, 입·사물) ≫ tight 4s / IT mild  
   - ✅ Clip Length 기본 **`audio+1.5`** 유지 (`AGENT_LTX_CLIP_TIGHT=1` 실험용)  
   - ✅ 본선 `S02_s2v.mp4` = baseline (교체 없음)  
   - ⬜ S02 `shot_approve --clip approved`  
   - ⬜ S03/S05 장대사: 분할 vs 고정 KF vs 체인 (장클립 드리프트는 별 과제)  
   - 필요 시 FLF (`ltx23_aio_flf(_audio)`)

2. **IT turbo/mild 프로파일**  
   - 4step/480p vs 8–10step 1샷 벤치 (시간·얼굴)  
   - hero 대사만 IT, 나머지는 LTX 하이브리드

3. **조립** (전 컷 clip approved 후)  
   - 클립 오디오/TTS remux 정책 정리  
   - playable 24fps 조립 경로 고정

4. (후순위) Wan 2.2 / LongCat 등 신규 스택 평가

---

## 4. 핵심 파일 맵

| 역할 | 경로 |
|------|------|
| 스위치 러너 | `lib/ltx_aio_workflow_runner.py` |
| 모드 표 | `lib/ltx_aio_mode_select.py` |
| expand | `lib/ltx_aio_ui_expand.py` |
| SI2V CLI | `scripts/generate_s2v.py` |
| last-frame 체인 | `scripts/chain_si2v_last_frame.py` |
| 사용법 | `docs/ltx23_aio_ia2v_agent_usage.md` |
| 라우팅 분석 | `docs/ltx23_aio_workflow_routing_analysis.md` |
| 본 상태 문서 | `docs/session_status_2026-07-13_ltx_aio_switch.md` |

---

## 5. 환경 메모

- Comfy: `http://127.0.0.1:8188` (세션 중 가동 확인)  
- 강제 미니: `AGENT_LTX_FORCE_MINI_GRAPH=1`  
- IT attention 폴백: `AGENT_IT_ATTENTION=sdpa`  
- 에피소드 런타임 산출물(clips/exports/mp4)은 `.gitignore` — 로컬/채널 워크스페이스에만 존재

