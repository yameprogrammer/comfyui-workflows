# 실패 노트 시스템 — 에이전트 간 교훈 공유

- **작성**: 2026-07-15  
- **상태**: ✅ 운영  
- **경로**: `failures/` · CLI `scripts/failure_note.py`  
- **규칙**: [agent_rules.md](../agent_rules.md) **Rule 7.4**

---

## 0. 한 줄

```text
생성 전 search → 작업 → FAIL이면 add → 다음 에이전트가 search
```

**실패를 침묵하면 조직 학습이 리셋된다.**  
에피소드 `QA_LOG` 는 작품 단위, **`failures/` 는 공장 전역 교훈**.

---

## 1. 언제 쓰나

| 상황 | 행동 |
|------|------|
| 키프레임/클립 QA **FAIL** | `add` (필수) |
| 유저가 결과 리젝·수정 요청 | `add` (필수, severity≥high) |
| CLI/Comfy 반복 에러 (OOM, timeout 패턴) | `add` |
| 같은 증상 2회째 | 기존 노트 `refs` 연결 + prevention 강화 |
| 순수 1회성 타이포 | 생략 가능 (low) |

---

## 2. 생성 전 (before-gen) — 실수 방지

영상·캐릭·로케 본선 전 **반드시** 관련 교훈을 읽는다.

```bash
# 권장: PREVENT 먼저 (mistake prevention)
python scripts/failure_note.py before "freeze OR feet OR car OR framing"
python scripts/failure_note.py before "i2v"
python scripts/failure_note.py before   # 최근 high/critical

# 키워드 검색 (전체 필드)
python scripts/failure_note.py search "freeze OR feet OR car"

# 태그
python scripts/failure_note.py search --tag freeze_pad --tag anatomy_feet

# 최근 N개
python scripts/failure_note.py list --limit 15

# 도구 고르면서 같이 보기
python scripts/tool_intent.py "키프레임 freeze"
```

에이전트는 결과의 **PREVENT** 1–3줄을 작업 메모에 남긴다 (“FN-… 예방: …”).

---

## 3. 추가 (add)

```bash
python scripts/failure_note.py add \
  --stage keyframe \
  --tags anatomy_feet,insert_failed,qa_skipped \
  --symptom "S03 intended shoe insert but got face + deformed raised leg" \
  --cause "shot_compose with character_ids forced portrait bias; no open-file QA" \
  --fix "T2I shoe-only prompt without character face block; re-QA" \
  --prevention "insert risk tag; forbid character positive_core on insert feet; Rule 7.3 open file" \
  --episode sonagi_mv_v1 \
  --shot S03 \
  --severity high \
  --agent grok \
  --path "stories/sonagi_mv_v1/keyframes/S03.png"
```

필수: `stage`, `tags`, `symptom`, `cause`(`--cause`), `fix`, `prevention`, `severity`.

---

## 4. 필드 의미

| 필드 | 내용 |
|------|------|
| symptom | 화면/유저가 본 **증상** |
| root_cause | **왜** (공정·프롬프트·툴 선택) |
| fix | **이번**에 한 조치 |
| prevention | **다음 에이전트**가 할 일 |
| tags | `failures/tags.json` 권장 태그 |
| severity | critical / high / medium / low |

---

## 5. INDEX

`failure_note.py add` 시 `failures/INDEX.md` 자동 갱신 (최신 상단).  
에이전트는 JSON을 못 읽을 때 INDEX만으로도 훑을 수 있다.

---

## 6. 에피소드 QA_LOG 와의 관계

| | QA_LOG | failures/ |
|--|--------|-----------|
| 범위 | 한 에피소드 컷 판정 | 전 공장 교훈 |
| 형식 | 표 PASS/FAIL | 구조화 JSON + INDEX |
| 의무 | Rule 7.3 | Rule 7.4 |

FAIL 한 줄은 QA_LOG **와** failures 양쪽에 남겨도 된다 (failures에 prevention 필수).
