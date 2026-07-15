# 이미지 컷 · 키프레임 · 클립 검증 게이트 (Visual QA SSOT)

- **작성**: 2026-07-15  
- **상태**: ✅ **의무 문서 레일** (소비자·공장 에이전트 공통)  
- **문제 기원**: 상태 플래그만 `approved` 로 올리고 육안을 생략 → 정지 프레임 패딩, 구도 복붙, 사지·차량 붕괴가 본편까지 유입  
- **관련**: [agent_rules.md](../agent_rules.md) Rule **7.2** · **7.3** · **기획·컷 문법 선행**: [video_director_master_persona.md](video_director_master_persona.md) · [video_creative_director_persona.md](video_creative_director_persona.md) · [agent_av_smoke_checklist.md](agent_av_smoke_checklist.md)

---

## 0. 한 줄

```text
파일을 연다 → 체크리스트로 판정 → 기록 → 그 다음에만 approved
플래그만 올리는 승인 = 미검증 = 위반
```

`keyframe_status=approved` / `clip_status=approved` 는 **육안(또는 동등 비전 검수) 통과 증명**이다.  
생성 성공·파일 존재·CLI exit 0 만으로 승인 금지.

---

## 1. 언제 무엇을 검증하나

| 단계 | 대상 | 통과 전 금지 행위 | 통과 후 |
|------|------|-------------------|--------|
| **A. 보드** | contact / panels | 대량 `shot_compose` 본선 | 키프레임 배치 |
| **B. 키프레임** | `keyframes/Sxx.png` | `episode_i2v` / `episode_s2v` / 그록 영상 본선 편입 | `keyframe_status=approved` |
| **C. 클립** | `clips/work/Sxx*.mp4` | `assemble_video` 본선·납품 | `clip_status=approved` |
| **D. 합본** | final mp4 | 컷 품질 재평가 기대 (이미 끝났어야 함) | export / 납품 |

Grok 네이티브로 만든 키프레임·클립도 **동일 게이트**를 통과해야 공장 `keyframes/` · `clips/work/` 에 본선으로 올린다.  
프리뷰 전용 경로는 `clips/work/_preview_grok/` 등 — **approve 금지**.

---

## 2. 검증 방법 (에이전트)

1. **파일을 연다** (`read_file` 이미지 / 클립은 대표 프레임 추출 후 이미지로 검수, 가능하면 전 구간 scrub).  
2. 아래 **체크리스트**를 항목별로 Pass / Fail.  
3. Fail 1개라도 → `rejected` 또는 `draft` 유지 · **재생성·수정** · 재검증.  
   - 동시에 **`python scripts/failure_note.py add`** (Rule **7.4**) — prevention 필수.  
4. 전원 Pass → `stories/<ep>/meta/qa_Sxx_keyframe.md` 또는 에피소드 `QA_LOG.md` 에 한 줄 이상 기록 후 approve CLI.  
5. **배치 승인 스크립트로 전 샷 일괄 approved 금지** (검증 로그 없는 mass approve = 위반).  
6. **생성 전** `failure_note.py search` 로 유사 실패(freeze_pad, anatomy_*, car_geometry, same_framing 등) 확인.

### 2.1 최소 기록 포맷 (에피소드 `QA_LOG.md` 권장)

```markdown
| shot | stage | verdict | notes | at |
|------|-------|---------|-------|-----|
| S03 | keyframe | FAIL | feet deform, not insert | 2026-07-15 |
| S03 | keyframe | PASS | shoe insert only, anatomy OK | 2026-07-15 |
| S03 | clip | PASS | continuous rain, no freeze pad | 2026-07-15 |
```

---

## 3. 키프레임 체크리스트 (stage = keyframe)

**의도 대비**

| ID | 항목 | Fail 예 |
|----|------|---------|
| K1 | **shot_type 일치** | medium 지시인데 face ECU만 |
| K2 | **action / intent 일치** | “신발 insert”인데 전신+얼굴 |
| K3 | **모티프 존재** | 노란 파라솔·우산 등 지정 모티프 누락(해당 샷) |

**해부·물리**

| ID | 항목 | Fail 예 |
|----|------|---------|
| K4 | **사지·손·발 정상** | 여분 손가락, 접힌 발, 떠 있는 다리 |
| K5 | **얼굴 정체성** (캐릭 샷) | 다른 사람, 연령 붕괴, 대칭 붕괴 |
| K6 | **의상·소품 스케일** | 우산 거인화, 손과 분리된 소품 |
| K7 | **공간·건축 일관** | 문이 차체와 분리, 불가능한 차 문 프레임 |
| K8 | **반사·유리·거울 논리** | 사이드미러가 계기판, 유리 너머 파손 원근 |

**구도·연출**

| ID | 항목 | Fail 예 |
|----|------|---------|
| K9 | **프레이밍 다양성** | 직전 2컷과 **동일 렌즈 거리·동일 구도** (고의 반복 연출 제외, 메모 필수) |
| K10 | **16:9 / 9:16 캔버스** | 레터박스 막대, 잘린 필수 피사체 |
| K11 | **텍스트·로고 오염** | 읽히는 가짜 간판 난립(의도된 타이포 샷 제외) |
| K12 | **금지 미학** | Creative Pack anti-list 위반 |

**연속성 (에피소드 단위, 키프레임 contact 시)**

| ID | 항목 | Fail 예 |
|----|------|---------|
| K13 | **의상 연속** | 컷마다 다른 아우터(의도 변장 제외) |
| K14 | **시간·날씨 연속** | 맑음↔폭우 점프 무설명 |
| K15 | **사이즈 리듬** | ECU만 5컷 연속 — 스토리보드 재설계 필요 |

**K9 강제 규칙:** 같은 `shot_type`이 **3컷 연속**이면 보드 실패. medium/closeup 교대만으로 때우지 말고 wide / insert / POV / low / high 를 섞는다.

---

## 4. 클립 체크리스트 (stage = clip)

모션 생성 후, **합본 전** 필수.

| ID | 항목 | Fail 예 |
|----|------|---------|
| C1 | **전 구간 움직임 또는 의도된 정물** | 후반 N초 **프리즈/클론 패드** (tpad clone, 마지막 프레임 복제) |
| C2 | **길이 = 설계 duration** | 생성 5s + 정지 5s 로 10s 맞추기 |
| C3 | **워프·모핑** | 얼굴 녹음, 손가락 증식 애니메이션 |
| C4 | **아이덴티티 유지** | 클립 중 타인으로 변함 |
| C5 | **카메라·모션 프롬프트 일치** | push-in 지시인데 완전 고정(의도 still 제외) |
| C6 | **소품·배경 안정** | 우산 소실, 파라솔 깜빡임 |
| C7 | **SI2V** | 입↔오디오 대이탈, 이빨 붕괴 (해당 시) |
| C8 | **프레임 결함** | 깜빡임, 슬라이스, 흑프레임 |
| C9 | **오디오 정책** | music_locked 인데 클립 보컬이 섞일 계획 없음 — mute 확인 |

### 4.1 정지(프리즈) 패딩 — **본선 금지 + 기본 감지**

| 허용 | 금지 |
|------|------|
| 연출 의도 still / hold (`motion_driver=still` 또는 `--allow-freeze`) | I2V 짧게 뽑고 `tpad=clone` / freeze로 duration 채우기 |
| 합본 마지막 컷 **짧은 outro hold** (editorial, `assemble_single_take --outro-hold`) | 오디오 길이에 맞추려 중간 컷을 tpad 로 늘리기 |
| — | 전 컷 공통으로 후반 30–50% 정지 |

**기계 게이트 (2026-07-16, 기본 ON)**

| 시점 | 동작 |
|------|------|
| `episode_i2v` / `episode_s2v` / `chain_one_take` 생성 직후 | multi-point 프레임 diff → `FREEZE_PAD_SUSPECT` 시 **fail** (`clip_status=rejected`) |
| `shot_qa_record --stage clip` | freeze 검사 **기본 ON** → C1 fail / verdict fail |
| `shot_approve --clip approved` | 라이브 재검사 |
| `episode_qa` | work 클립 freeze → hard issue |
| `assemble_single_take` | video &lt; TTS 길이일 때 **tpad 거부** (`--allow-freeze-pad` 비상만) |

끄기(디버그): `AGENT_FREEZE_GATE=0` · CLI `--no-freeze-gate` / `--no-freeze-check`  
임계값: `AGENT_FREEZE_DIFF_THRESHOLD` (기본 2.5 mean abs RGB)

**본선 길이 맞추기 우선순위**

1. `duration_sec`에 맞는 **프레임 수**로 I2V/SI2V/그록 영상 생성 (6s/10s 네이티브 단위면 샷 길이를 그에 맞춤)  
2. 긴 구간은 **샷 분할** (S07a/S07b) — 각 샷 풀 모션  
3. 불가 시에만 유저 승인 하에 hold — `QA_LOG` + `--allow-freeze` 명시  

---

## 5. 스토리보드·구도 설계 게이트 (생성 전)

키프레임을 뽑기 **전** 샷 리스트에 대해:

| ID | 항목 |
|----|------|
| B1 | 각 샷에 `shot_type` + **intent 한 줄** + 예상 렌즈 거리 |
| B2 | 연속 3컷 동일 shot_type 없음 (또는 고의 반복 사유) |
| B3 | insert / wide / medium / CU / POV 중 **최소 4종**이 에피에 존재 (쇼츠 6컷 미만은 3종) |
| B4 | 차량·손·발·유리 등 고난도 샷은 프롬프트에 **해부·구조 제약** 문장 포함 |
| B5 | Creative Pack motifs 가 샷에 분배됨 |

보드 contact sheet를 보고 B2–B3 Fail이면 **재설계 후** compose.

---

## 6. 판정 → 액션

| 판정 | 액션 |
|------|------|
| PASS | QA_LOG 기록 → `shot_approve` keyframe 또는 `--clip` |
| FAIL 국소 | Grok `image_edit` 또는 `shot_keyframe_edit` 1회 → **재검증** |
| FAIL 구조 | `shot_compose` / T2I 재생성 또는 샷 intent 수정 → 재검증 |
| FAIL 클립 프리즈 | 패드 제거 · 풀 길이 재생성 · 샷 분할 |
| FAIL 구도 복붙 | 스토리보드 재설계 (해당 구간 일괄) |

**3회 연속 FAIL** 동일 증상 → 프롬프트/레퍼/샷 타입을 바꾸고, 같은 시드로 무한 재시도 금지.

---

## 7. 승인 문구 규약

에이전트가 사용자에게 “승인했다”고 말할 때 포함:

- 검수 샷 ID 목록  
- stage (keyframe / clip)  
- FAIL 재처리 요약  
- QA_LOG 경로  

“생성 완료 = 승인” 표현 금지.

---

## 8. CLI·경로 연동 (기계 계약 — 2026-07-16)

문서 체크리스트만으로는 에이전트가 스킵한다. **`shot_approve` 가 시각 QA JSON 을 강제**한다.

### 8.1 필수 순서 (키프레임)

```bash
# 1) 비교 팩 (identity_ref | keyframe | prev)
python scripts/shot_qa_pack.py -e EP -s S03

# 2) 팩 이미지를 연다 (read_file / 비전) → 체크리스트 판정

# 3) 구조화 기록 (verdict=pass 시 --notes 필수 + 필수 체크)
python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict pass \
  --pass-required --notes "opened pack; hands OK; matches master_front; medium OK"

# 4) 그 다음에만 approve (QA 없으면 exit 23)
python scripts/shot_approve.py -e EP -s S03 --status approved
```

### 8.2 클립

```bash
python scripts/shot_qa_pack.py -e EP -s S03 --stage clip
# first|mid|last + identity_ref 확인
python scripts/shot_qa_record.py -e EP -s S03 --stage clip --verdict pass \
  --pass-required --run-freeze-check --notes "full motion, no freeze, identity hold"
python scripts/shot_approve.py -e EP -s S03 --clip approved
```

### 8.3 에피소드 인물 일관성 (컷 간)

한 장씩 보면 통과해도, 나란히 보면 다른 사람인 경우가 많다.

```bash
python scripts/episode_identity_sheet.py -e EP
# boards/identity_contact.png 오픈
python scripts/shot_qa_record.py -e EP --stage identity --verdict pass \
  --notes "same cast/wardrobe across S01–S0N"
```

### 8.4 산출 경로

| 산출 | 경로 |
|------|------|
| QA JSON | `stories/<ep>/meta/visual_qa/<shot>_keyframe.json` · `…_clip.json` |
| Identity QA | `stories/<ep>/meta/visual_qa/episode_identity.json` |
| QA pack | `stories/<ep>/boards/qa/<shot>_keyframe_pack.png` |
| Identity sheet | `stories/<ep>/boards/identity_contact.png` |
| 로그 표 | `stories/<ep>/QA_LOG.md` |

### 8.5 필수 체크 ID (approve 시)

| stage | required |
|-------|----------|
| keyframe | `K2_action_intent` · `K4_anatomy` · `K5_identity` |
| clip | `C1_no_freeze_pad` · `C3_no_warp` · `C4_identity_hold` |
| identity | `I1_cast_consistency` |

### 8.6 게이트 동작

| 조건 | 결과 |
|------|------|
| `approved` + QA JSON 없음 / verdict≠pass | **exit 23** `QA_MISSING` / `QA_FAIL` |
| artifact sha 불일치 (재생성 후 옛 QA) | **exit 23** `QA_STALE` |
| `method=skipped` | approve 거부 |
| 디버그 우회 | `--force-approve` 또는 `AGENT_REQUIRE_VISUAL_QA=0` (경고 출력) |
| 감사 | `python scripts/episode_qa.py -e EP --require-visual-qa` |

```bash
python scripts/episode_status.py -e EP   # next=shot_qa_record | episode_identity_sheet …
python scripts/assemble_video.py -e EP --stage work   # clip 미승인 exit 22
```

---

## 9. 위반 정의 (감사 시)

다음에 해당하면 공정 위반으로 간주하고 납품 전 되돌린다.

1. 이미지/클립을 열지 않고 approve (**또는 QA JSON 없이 `--force-approve` 남용**)  
2. 전 샷 일괄 `keyframe_status=approved` 스크립트만 실행  
3. freeze pad로 duration 채운 클립을 clip approve  
4. 동일 구도 3연속을 알고도 방치  
5. 사지·차량 붕괴를 “나중에 합본에서” 미룸  
6. identity contact 없이 전 샷 모션 배치 (3+ 키프레임 에피)

---

## 10. 유지보수

- 이 문서 = **이미지 컷 검증 SSOT**. Rule 7.2는 순서·코드 게이트, **7.3은 육안 내용 + 기계 QA JSON**.  
- 구현: `lib/visual_qa.py` · `scripts/shot_qa_pack.py` · `shot_qa_record.py` · `episode_identity_sheet.py` · `shot_approve` exit 23.  
- 신규 Fail 패턴이 반복되면 §3–4 표에 행 추가 + `process.md` 한 줄.
