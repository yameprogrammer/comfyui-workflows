# 에이전트 영상 툴링 TODO (근시일 작업 백로그)

- **작성**: 2026-07-14  
- **상태**: Sprint A–C + P2-2 자막 ✅ 2026-07-14
- **맥락**: `cafe_gomin_ep01` 실전에서 드러난 병목 + 공장 로드맵 정합  
- **관련**: [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md) · [video_pipeline_roadmap.md](video_pipeline_roadmap.md) · [grok_build_hybrid_tooling.md](grok_build_hybrid_tooling.md) · [agent_rules.md](../agent_rules.md) Rule 7.x / Rule 8  

이 문서는 “나중에 하면 좋겠다”를 **작업 단위로 고정**한 것이다.  
구현 시 `process.md` 이력 + 해당 CLI/기본값 변경을 남긴다.

---

## 0. 설계 원칙 (합의)

1. **모델 추가보다 계약·기본값·검증**이 에이전트 효율에 먼저 온다.  
2. 공장 CLI가 본선 SSOT; Grok 네이티브는 가속·국소 수술 (Rule 8, **도구는 에이전트 자율 선택** / 유저 지정 시 우선).  
3. **립·바디 모션 ≠ 무조건 잔잔**  
   - TTS/보이스의 **감정·톤·인텐트**에 맞게 제스처·표정 강도가 따라가야 한다.  
   - 과한 디폴트 액션(큰 고개, 큰 lean, 과한 shoulder)은 피하되,  
     인사·불만·귀여움·차분 등 **감정 프로파일별 레시피**로 맞춘다.

---

## P0 — 근시일 (실전 사고 직결)

### P0-1. SI2V 오디오–길이 계약 (자동) — ✅ 2026-07-14

| 항목 | 내용 |
|------|------|
| **문제** | IT `AGENT_IT_MAX_FRAMES` 기본 129(~5.4s@24)로 긴 대사 잘림; demucs drive 길이 이상 |
| **구현** | (1) `lib/s2v_length_contract.py` — frames=ceil(audio×fps)+tail, **초과 시 hard fail** (`FRAMES_EXCEED_MAX`, 분할 힌트)<br>(2) IT 기본 max **257** (`AGENT_IT_MAX_FRAMES`)<br>(3) prep `auto` → **`center_voicey`** (demucs는 opt-in / `AGENT_DRIVE_PREP_AUTO=demucs`)<br>(4) `episode_s2v` 생성 전 drive vs TTS 비교 + `duration_sec` 동기<br>(5) `--allow-clamp` / `AGENT_S2V_ALLOW_CLAMP=1` 만 조용한 클램프 허용 |
| **건드릴 곳** | `generate_s2v.py`, `episode_s2v.py`, `lib/ffmpeg_util.resolve_driving_prep_mode` |
| **완료 기준** | 조용히 잘리지 않음 — 초과 시 실패 또는 명시적 clamp |

### P0-2. 감정 연동 모션 프로파일 (립·바디)  ← “잔잔” 재정의 — ✅ 2026-07-14

| 항목 | 내용 |
|------|------|
| **문제** | 단일 aggressive 디폴트 / 또는 “무조건 잔잔”만으로는 톤이 안 맞음. 유저 피드백: **음성 감정·느낌에 적절한 행동** |
| **구현** | (1) `lib/performance_profiles.py` — `neutral_calm` · `warm_greeting` · `mild_unsatisfied` · `thoughtful` · `cute_ask` · `sip_business`<br>(2) 프로필: `motion_prompt` · `tts_instruct` · `audio_scale` · `negative_motion`<br>(3) `episode_tts --performance` + `episode_s2v --performance` 동일 키; shot.performance / emotion 별칭<br>(4) speak/lip 마커 있으면 **still 오탐으로 덮어쓰기 금지**<br>(5) calm = 바닥, 피크만 키움 (문서) |
| **건드릴 곳** | `lib/performance_profiles.py`, `episode_s2v.py`, `episode_tts.py`, `docs/audio_motion_production_modes.md` |
| **완료 기준** | 프로필별 motion/scale/instruct 분리; lip-aware 프롬프트 보존 |

**감정 매핑 초안 (구현 시 테이블로 코드화)**

| 톤 (TTS / 씬) | performance | 바디 | audio_scale 가이드 |
|---------------|-------------|------|-------------------|
| 밝은 인사 | `warm_greeting` | 미소, 아주 작은 고개 끄덕임 | 1.3–1.4 |
| 담담 정보 | `neutral_calm` | 거의 고정 상체, 립 위주 | 1.2–1.3 |
| 가벼운 불만·당황 | `mild_unsatisfied` | 팔짱 유지, 미세 미간, 큰 흔들기 금지 | 1.25–1.35 |
| 차분 사고 | `thoughtful` | 작은 고개 기울임 정도 | 1.2–1.3 |
| 귀여운 질문 | `cute_ask` | 약한 미소, lean은 micro만 | 1.3–1.4 |
| 무대사 비지니스(sip 등) | `sip_business` / i2v | 소품 동작 명확, 얼굴 과잉 금지 | (I2V) |

### P0-3. 생성 후 자동 export (작업대) — ✅ 2026-07-14

| 항목 | 내용 |
|------|------|
| **문제** | 클립이 `stories/` 에만 있어 작업대에서 못 찾음 |
| **구현** | `lib/workspace_export.py` · `episode_i2v` / `episode_s2v` / `episode_tts` 종료 시<br>`AGENT_WORKSPACE` 설정 시 **자동** 복사, 또는 `--export-workspace` / `--export-dest`<br>`--no-export-workspace` 로 끄기 · `AGENT_EXPORT_WORKSPACE=0` |
| **완료 기준** | 생성 직후 유저 워크스페이스 `episodes/<ep>/clips/work` (또는 audio) 에 본선 파일 |

---

## P1 — 효율·연속성·검수

### P1-1. `episode_status` 길이 헬스체크 — ✅ 2026-07-14

- 샷별: `tts_sec / drive_sec / clip_sec / frames_est_24` + `length_flags`  
- 플래그: `SHORT` (클립 < 오디오) · `DRIVE_MISMATCH` (drive < TTS) · `DURATION_SHORT`  
- `episode_status` 텍스트/JSON · overall_next `fix_driving_length` / `regen_s2v_longer`

### P1-2. 원 테이크 체인 CLI — ✅ 2026-07-14

- `lib/one_take.py` 공유 헬퍼 + `shot_compose --from-prev-shot`  
- `chain_one_take.py`: performance 프로필 · 길이 계약 · clip_status 게이트(재조회) · workspace export  
- 이전 컷 `clip_status=approved` 전 체인 금지 (exit 22; `--force-clip-gate` 디버그)  
- 참고: [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md) · SI2V 전용 `chain_si2v_last_frame.py` 유지

### P1-3. 키프레임 국소 수술 슬롯 — ✅ 2026-07-14

- `scripts/shot_keyframe_edit.py` — Moody I2I surgical (denoise default 0.35)  
- 메타 `keyframe_source=surgical_edit`, `keyframe_status=draft` 재승인  
- 전 샷 글로벌 블러 프롬프트 거부 · `_history/` 백업  

### P1-4. 컷 검수 보조 (자동 승인 아님) — ✅ 2026-07-14

- `scripts/clip_review_sheet.py` — work 클립 first/last + contact grid  
- 자동 승인 없음 · `shot_approve --clip` 는 사람이  

### P1-5. TTS ↔ performance 원샷 CLI — ✅ (P0-2)

- `episode_tts ... --performance warm_greeting`

---

## P2 — 품질 상한·장르

| ID | 항목 | 메모 |
|----|------|------|
| **VQ-1** | **Visual QA hard gate** | ✅ 2026-07-16 — `lib/visual_qa.py` · `shot_qa_pack` · `shot_qa_record` · `shot_approve` exit 23 · QA_LOG |
| **VQ-1.5** | **Episode identity sheet** | ✅ `episode_identity_sheet.py` · identity QA JSON · status/episode_qa |
| VQ-2 | Clip freeze **detect** default ON + ban tpad length-fill | ✅ 2026-07-16 multi-point gate post-gen + QA + assemble ban |
| VQ-3 | Face embedding identity score (보조) | 선택 · 자동 승인 금지 |
| P2-1 | Face restore 옵션 (모션 후, 약하게) | 과하면 smeary |
| P2-2 | 쇼츠 자막 SRT + soft burn | ✅ episode_subtitles.py · lib/subtitles.py |
| P2-3 | SFX 큐 라이브러리 배치 | `shots.json` sfx |
| P2-4 | ControlNet 포즈 락 레시피 | 팔짱·잔 들기 · **댄스 모드와 공유 가능** |
| P2-5 | OpenMontage 검수/리포트 조각만 이식 | 전체 오케스트레이션 대체 금지 |

---

## P3 — 장르 파이프 (토킹 에피와 별 트랙)

### P3-1. 댄스 챌린지 쇼츠 공정 (`dance_challenge`)

| 항목 | 내용 |
|------|------|
| **의도** | 특정 댄스 **레퍼런스** → 채널 캐릭으로 정교한 9:16 챌린지 쇼츠. **지금 cafe 토킹 에피와 분리** |
| **합의** | 파이프를 설계·구현하면 그 장르를 **체계적으로·더 정교하게** 제작 가능 (1:1 완벽 복제 보장은 모델 한계) |
| **설계 문서** | **[dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md)** |
| **핵심 스테이지** | 레퍼 ingest → 키 포즈/구간 → 캐릭 키프레임 → I2V(포즈 가이드) → 음악 락 assemble → 1080 |
| **모드** | `production_mode=dance_challenge` · mix `music_locked` · SI2V 립 비주력 |
| **착수 시기** | 토킹 파이프 P0–P1 안정화 **이후** 권장 |
| **하위 티켓** | D0–D6 — 설계 문서 §4 |

### P3-2. 기획 자율 모드 (키워드 / 음악만 입력)

| 항목 | 내용 |
|------|------|
| **의도** | 풀 시놉 없이 키워드·음악 정보만으로 에이전트가 기획→시놉→보드→공장 진행 |
| **필수 구현** | **없음** — 문서 가드레일·SOP면 운용 가능 |
| **SSOT 문서** | **[creative_brief_autonomy_design.md](creative_brief_autonomy_design.md)** |
| **선택 이후** | Brief 템플릿 자동 생성, `episode_init_from_brief` 등 얇은 CLI (반복 실수 시) |
| **상태** | ✅ 문서 레일 기록 완료 · 기능 코드 미착수(불필요 시 유지) |

### P3-3. (예약) 기타 장르 템플릿

- 예: pure_mv_hook, product_ugc — 필요 시 동일 패턴으로 문서화  

### P3-4. V2V 의도 파이프 (camera / motion / style)

| 항목 | 내용 |
|------|------|
| **의도** | 레퍼 비디오로 카메라 연출·모션 리타겟·스타일 트랜스퍼 (본선 SI2V와 분리) |
| **SSOT** | **[v2v_intent_pipeline_design.md](v2v_intent_pipeline_design.md)** |
| **P0** | `generate_v2v.py` · AIO `-v` inject · `ltx23_aio_v2v_true` · schema enum |
| **P1** | `episode_v2v.py` 배치 강화 · status flags · length hard contract |
| **하지 않음** | 대사 본선 대체 · FLF를 V2V에 흡수 |

---

## 하지 않음 (의도적)

- 클라우드 Kling/Veo 를 본선 생성 경로로  
- OpenMontage 전체로 `episode_pipeline` 대체  
- TeaCache 기본 ON (그레인 품질 이슈)  
- 그록 영상으로 IT 립 대체  

---

## 구현 스프린트 제안 (순서)

```text
Sprint A (P0):  P0-1 길이 계약 → P0-2 감정 모션 프로파일 → P0-3 auto-export
Sprint B (P1):  P1-1 status 헬스 → P1-5 TTS-performance 연동 → P1-2 원테이크 체인
Sprint C (P1):  P1-3 국소 수술 → P1-4 검수 보조
Sprint D (P2):  필요 시 자막/SFX/face restore
Sprint E (P3):  dance_challenge 파이프 설계 확정 → D1–D4 구현
```

---

## 체크리스트 (착수 시 복사)

- [x] P0-1 SI2V 길이 계약 + drive 정책  
- [x] Ideogram4 타이포 1차 (`generate_ideogram4.py` + schema fix)
- [x] P0-2 performance/emotion 모션 테이블 + still-override 수정  
- [x] P0-3 auto-export workspace
- [x] P1-1 episode_status duration health
- [x] P1-2 from-prev / last-frame chain
- [x] P1-3 surgical keyframe edit path  
- [x] P1-4 clip review contact soft  
- [x] P1-5 TTS–performance 원샷 (`episode_tts --performance`, thin)
- [x] P2-2 subtitles SRT+burn  
- [x] **VQ-1 / VQ-1.5 Visual QA hard gate + identity sheet** (2026-07-16)
- [x] **VQ-2 freeze detect default ON + tpad length-fill ban** (2026-07-16)
- [ ] VQ-3 face embedding (선택)
- [ ] P2-1 face restore / P2-3 SFX lib / P2-4 pose lock / P2-5 OM 이식 (선택)
- [ ] **P3-1 댄스 챌린지 파이프** — [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md)  
- [x] **P3-2 기획 자율** — 문서 레일 [creative_brief_autonomy_design.md](creative_brief_autonomy_design.md) (기능 코드 비필수)  
- [x] **P3-4 V2V 의도 P0** — [v2v_intent_pipeline_design.md](v2v_intent_pipeline_design.md) · `generate_v2v` / `episode_v2v`  
- [ ] **P3-4 V2V P1** — status/length 계약·실 스모크 클립  

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-16 | **VQ-2 freeze gate** — post-gen detect default ON · assemble tpad ban · multi-point heuristic |
| 2026-07-16 | **VQ-1 Visual QA hard gate** — pack/record/approve exit 23 · identity sheet · episode_status/qa |
| 2026-07-15 | **P3-4 V2V intent** 설계 + P0 CLI (camera/motion/style) |
| 2026-07-14 | 초안. P0–P2 백로그. “잔잔” → **음성 감정 연동 퍼포먼스** 로 정정 반영 |
| 2026-07-14 | **P3-1 댄스 챌린지** 백로그 + 설계 초안 링크. 토킹 에피와 별 트랙 명시 |
| 2026-07-14 | **P0-2 performance** 테이블 + episode_tts/s2v 연동 + still 오탐 수정 |
| 2026-07-14 | **P0-1** 길이 계약 · **Ideogram4** 타이포 1차 |
| 2026-07-14 | **P3-2 기획 자율** 문서 레일. 기능 필수 아님·가드레일 SOP 합의 반영 |
