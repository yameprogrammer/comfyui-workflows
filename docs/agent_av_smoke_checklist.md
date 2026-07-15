# Agent AV smoke checklist (goal gate)

- **목적**: 영상 도구를 **에이전트 신뢰 수준**으로 닫기 위한 고정 검증  
- **에피소드 예**: `sonagi_cafe_smoke_v1` (로컬; stories/ 는 gitignore일 수 있음)  
- **관련**: [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md) · **육안 체크리스트 SSOT**: [image_cut_verification_gate.md](image_cut_verification_gate.md) (Rule 7.3)

---

## 0. 계약 요약 (에이전트가 외울 것)

### 0.0 공장 vs 작업대 (필수)

| 곳 | 역할 |
|----|------|
| `agent_custom` 레포 | **공장** — CLI 실행, 기본 출력 `stories/<ep>/` |
| 에이전트 프로젝트 디렉터리 | **작업대** — 편집·납품·후처리 |

생성 후 **반드시** 작업대로 가져간다:

```bash
python scripts/export_episode_to_workspace.py -e EP --dest "PATH/TO/YOUR/PROJECT/episodes/EP"
```

상세: [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md) · 루트 [AGENTS.md](../AGENTS.md)

| 프로필 | SI2V | 용도 |
|--------|------|------|
| `deliver` (default) | LTX | 일상 생성·조립 |
| `preview` | LTX | 빠른 탐색 |
| `hero` | InfiniteTalk lip (24fps/12step/1.5) | 얼굴 CU 립 **1–2컷** |

| 게이트 | 의미 |
|--------|------|
| `keyframe_status=approved` | 키프레임 **파일을 연 뒤** K* 체크리스트 OK → I2V/SI2V 허용 ([image_cut_verification_gate.md](image_cut_verification_gate.md)) |
| `clip_status=approved` | **워크 클립 육안 OK** (C* · **프리즈 패드 금지**). **assemble 하드 게이트** |
| `lip_status=approved` | SI2V 립 하위 신호 ( `--clip approved` 시 동기화 가능 ). 납품 경고/`--require-lip` |
| `episode_qa --strict` | 기계 게이트 (파일·spill·무음 등) |
| `episode_qa --require-clip` | 미승인 `clip_status` hard fail |

**클립/립 품질은 자동 점수가 없다.** 컷마다 `clips/work` 를 보고 승인한다. **합본으로 중간 컷을 대체 검수하지 말 것.**

```bash
python scripts/shot_approve.py -e EP -s S03 --clip approved
# SI2V only lip sub-gate (optional if clip already covers lips):
# python scripts/shot_approve.py -e EP -s S03 --lip approved
```

---

## 1. 빠른 게이트 (GPU 최소 / CI 가능)

```bash
# 설정·프로필·QA 구조만 (Comfy 큐 없음)
python scripts/smoke_agent_av.py -e sonagi_cafe_smoke_v1
# expect: exit 0, ok=true (또는 에피소드 없으면 code=11)
```

기대:

- `default_backend_s2v` resolve → `ltx23_ia2v`
- profiles `deliver|preview|hero` 존재
- `episode_qa` 실행 가능
- hero 기본: scale 1.5 / steps 12 / fps 24 / TeaCache off

---

## 2. 납품 경로 스모크 (Comfy 필요, 시간 중간)

전제: 키프레임 approved. Comfy `:8188` 은 CLI auto-ensure (또는 `python scripts/comfy_ensure.py`).

```bash
python scripts/episode_pipeline.py -e EP --run --from i2v --to qa --profile deliver
```

기대:

- stage 순서에 `qa` 포함, **마지막에 AGENT_RESULT 블록**
- `meta/agent_pipeline_result.json` 기록
- exit 0 이면 `ok=true` + QA hard issue 0
- SI2V 샷이 있으면 `lip_status` 미승인 시 **경고** (deliver는 soft), hero 프로필은 권장 fail

---

## 3. 히어로 립 스모크 (Comfy, ~3분/컷)

```bash
python scripts/episode_tts.py -e EP -s S03 --text "..." --bind-si2v --strict
python scripts/episode_s2v.py -e EP --shots S03 --backend infinitetalk
# 사람: clips/work/S03_s2v.mp4 확인 (얼굴·립)
python scripts/shot_approve.py -e EP -s S03 --clip approved
python scripts/assemble_video.py -e EP --stage work --mix-policy layered
# 미승인 시: exit 22 CLIP_NOT_APPROVED (우회 --force-clip-gate 는 본선 금지)
python scripts/episode_qa.py -e EP --strict --require-clip
```

기대:

- IT mild: ~3분/컷, 입 과장 심하지 않음
- **assemble 전** 컷 승인 완료
- assemble 후 대사 겹침·무음 없음
- QA ok

---

## 4. 실패 케이스 (exit ≠ 0 이어야 함)

| 케이스 | 커맨드 힌트 | 기대 |
|--------|-------------|------|
| 긴 VO + strict | `episode_tts ... --strict` | code 41 AUDIO_SPILL |
| QA hard issue | 의도적 클립 삭제 후 `episode_qa --strict` | code 42 |
| pipeline stop | stage fail + default stop | EXIT_STAGE + AGENT_RESULT ok=false |

---

## 5. 완수 판정

아래가 모두 참이면 **에이전트 AV 신뢰 목표 1차 완수**:

- [x] Safe defaults (LTX deliver / IT mild hero)
- [x] Fail loud (spill strict, QA)
- [x] One entrypoint + profile
- [x] Post-run QA + **AGENT_RESULT** envelope
- [x] Smoke checklist (본 문서) + `smoke_agent_av.py`
- [x] Lip visual gate 계약 (`lip_status`)

**비목표 (의도적):** 립 자동 점수, 대사 초 hard-cap.  
Ideogram 4 타이포는 **별도 도구** (`generate_ideogram4.py`) — AV smoke 게이트 밖.
