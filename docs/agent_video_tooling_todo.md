# 에이전트 영상 툴링 TODO (근시일 작업 백로그)

- **작성**: 2026-07-14  
- **상태**: 백로그 (아직 미착수 항목 다수)  
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

### P0-1. SI2V 오디오–길이 계약 (자동)

| 항목 | 내용 |
|------|------|
| **문제** | IT `AGENT_IT_MAX_FRAMES` 기본 129(~5.4s@24)로 긴 대사 잘림; demucs drive 길이 이상 |
| **할 일** | (1) 생성 전 `tts_sec ≈ drive_sec`, frames≥ceil(tts×fps)+tail 검증, 실패 시 hard fail<br>(2) 쇼츠 기본 prepare **`center_voicey`** (demucs 자동 경로 재검토)<br>(3) `shots[].duration_sec` 를 TTS+tail 로 자동 동기<br>(4) max frames 상한 정책: 올리거나 초과 시 **샷 분할 제안** |
| **건드릴 곳** | `generate_s2v.py`, `episode_s2v.py`, `audio_prepare_driving` / `materialize_driving_audio`, `episode_status` |
| **완료 기준** | S05급 8s+ 대사가 잘리지 않거나, 잘릴 경우 사전 경고·분할 없이 조용히 잘리지 않음 |

### P0-2. 감정 연동 모션 프로파일 (립·바디)  ← “잔잔” 재정의

| 항목 | 내용 |
|------|------|
| **문제** | 단일 aggressive 디폴트 / 또는 “무조건 잔잔”만으로는 톤이 안 맞음. 유저 피드백: **음성 감정·느낌에 적절한 행동** |
| **할 일** | (1) `motion_profile` 또는 `performance` 필드 도입 예:<br>`neutral_calm` · `warm_greeting` · `mild_unsatisfied` · `thoughtful` · `cute_ask` · `sip_business`<br>(2) 프로필마다: `motion_prompt` 템플릿, 권장 `audio_scale`, 허용 제스처 강도<br>(3) TTS `instruct` / shot `emotion` / dialogue 톤과 **같은 키로 매핑** (에이전트가 TTS와 SI2V를 한 세트로 고름)<br>(4) `episode_s2v`의 `still` 키워드가 speaking 프롬프트를 **통째 덮어쓰는** 버그 수정 — lip/speak 있으면 override 금지<br>(5) 문서: “calm = 기본 바닥, 감정 피크만 키운다” |
| **건드릴 곳** | `shots.json` 스키마/관례, `episode_s2v.py` prompt 조립, (선택) `episode_tts.py` instruct 프리셋 공유 테이블, `docs/audio_motion_production_modes.md` |
| **완료 기준** | 같은 파이프에서 인사/불만/질문이 **다른 바디 강도**로 나오고, 전체가 과잉 액션으로 통일되지 않음 |

**감정 매핑 초안 (구현 시 테이블로 코드화)**

| 톤 (TTS / 씬) | performance | 바디 | audio_scale 가이드 |
|---------------|-------------|------|-------------------|
| 밝은 인사 | `warm_greeting` | 미소, 아주 작은 고개 끄덕임 | 1.3–1.4 |
| 담담 정보 | `neutral_calm` | 거의 고정 상체, 립 위주 | 1.2–1.3 |
| 가벼운 불만·당황 | `mild_unsatisfied` | 팔짱 유지, 미세 미간, 큰 흔들기 금지 | 1.25–1.35 |
| 차분 사고 | `thoughtful` | 작은 고개 기울임 정도 | 1.2–1.3 |
| 귀여운 질문 | `cute_ask` | 약한 미소, lean은 micro만 | 1.3–1.4 |
| 무대사 비지니스(sip 등) | `sip_business` / i2v | 소품 동작 명확, 얼굴 과잉 금지 | (I2V) |

### P0-3. 생성 후 자동 export (작업대)

| 항목 | 내용 |
|------|------|
| **문제** | 클립이 `stories/` 에만 있어 작업대에서 못 찾음 |
| **할 일** | `episode_i2v` / `episode_s2v` / (선택) `episode_tts` 종료 시 `--export-workspace` 또는 `AGENT_WORKSPACE` 자동 복사 |
| **완료 기준** | 생성 직후 유저 워크스페이스 `episodes/<ep>/clips/work` 에 본선 파일이 있음 |

---

## P1 — 효율·연속성·검수

### P1-1. `episode_status` 길이 헬스체크

- 샷별: `tts_sec / drive_sec / clip_sec / frames` 한 줄  
- `SHORT` / `DRIVE_MISMATCH` 플래그  

### P1-2. 원 테이크 체인 CLI

- `shot_compose --from-prev-shot` / last-frame SI2V 체인 자동화  
- 이전 컷 `clip_status=approved` 전 체인 금지 (Rule 7.2와 정합)  
- 참고: [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md)

### P1-3. 키프레임 국소 수술 슬롯

- `shot_edit` / inpaint WF 또는 Grok `image_edit` → `keyframes/S0x.png`  
- 메타 `source=surgical_edit`, status draft 재승인  
- 전 샷 픽셀 블러 금지 (실사 붕괴 사고 2026-07-13)

### P1-4. 컷 검수 보조 (자동 승인 아님)

- work 클립 첫/끝 프레임 + 소형 contact  
- (선택) 비전 soft warn: 입 움직임·잘림 의심·얼굴 붕괴  

### P1-5. TTS ↔ performance 원샷 CLI

- `episode_tts ... --performance warm_greeting` 이 instruct + 다음 s2v 프로필을 같이 세팅  

---

## P2 — 품질 상한·장르

| ID | 항목 | 메모 |
|----|------|------|
| P2-1 | Face restore 옵션 (모션 후, 약하게) | 과하면 smeary |
| P2-2 | 쇼츠 자막 SRT + soft burn | TTS 타이밍 연동 |
| P2-3 | SFX 큐 라이브러리 배치 | `shots.json` sfx |
| P2-4 | ControlNet 포즈 락 레시피 | 팔짱·잔 들기 |
| P2-5 | OpenMontage 검수/리포트 조각만 이식 | 전체 오케스트레이션 대체 금지 |

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
```

---

## 체크리스트 (착수 시 복사)

- [ ] P0-1 SI2V 길이 계약 + drive 정책  
- [ ] P0-2 performance/emotion 모션 테이블 + still-override 수정  
- [ ] P0-3 auto-export workspace  
- [ ] P1-1 episode_status duration health  
- [ ] P1-2 from-prev / last-frame chain  
- [ ] P1-3 surgical keyframe edit path  
- [ ] P1-4 clip review contact soft  
- [ ] P1-5 TTS–performance 원샷  
- [ ] P2-* 선택  

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-14 | 초안. P0–P2 백로그. “잔잔” → **음성 감정 연동 퍼포먼스** 로 정정 반영 |
