# Toolbox card standard — 한 줄 예시 + 실패 시 대안

에이전트가 도구를 **고르고 → 실행하고 → 틀리면 전환**할 수 있게,  
모든 도구 카드(문서·`tool_intent` 인덱스)에 아래를 넣는다.

---

## 필수 필드

| 필드 | 의미 | 예 |
|------|------|-----|
| **when** | 언제 이 도구 | 레퍼 얼굴 있고 장면만 변경 |
| **when_not / alternatives** | 언제 말고 · 실패·부적합 시 | 부위만 → inpaint |
| **eg (examples[0])** | **복붙 가능한 CLI 한 줄** | `python scripts/… -i … -o …` |
| **CLI** | 엔트리 스크립트 | `generate_character_consistent.py` |

---

## 한 줄 예시 규칙

1. 레포 루트에서 동작하는 완전한 커맨드  
2. 필수 플래그 포함 (`-i` / `-p` / `-o` / 모드)  
3. placeholder는 짧고 명확 (`face.png`, `out.png`)  
4. 위험 도구는 제한 명시 (18+, mask 등)

```bash
# good
python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4 --seed 42

# bad (불완전)
generate_camera_move --preset push_in
```

---

## 대안 (alternatives) 규칙

각 대안:

| 키 | 의미 |
|----|------|
| `if` | 이 상황이면 (실패 원인 / when not) |
| `use` | 짧은 도구 이름 |
| `cli` | **한 줄 예시** (대안도 복붙 가능) |

3–4개면 충분. 무한 링크 금지.

```text
if fail / wrong tool → try:
  · 마스크 부위만: qwen_inpaint
    python scripts/generate_qwen_inpaint.py -i img.png --mask m.png -p "..." -o out.png
```

---

## 어디에 반영하나

| 위치 | 내용 |
|------|------|
| `lib/tool_intent.py` | `examples` + `alternatives` (검색 결과) |
| `docs/tool_catalog.md` | 카드 when / when not + 코드 블록 |
| `workflows/human/**/AGENT_GUIDE.md` | 상단 Alternatives + CLI 예 |
| 새 도구 추가 시 | 위 전부 + `tool_intent` 인덱스 1행 |

---

## Registration checklist (new or ready tool)

에이전트가 **검색 → 실행**할 수 있게, 같은 변경 세트에 아래를 맞추거나  
상태 어휘를 **일관되게** `planned` / `experimental`로 둔다.

| # | Artifact | Required fields |
|---|----------|-----------------|
| 1 | `scripts/<cli>.py` | `--help` 동작 · docstring에 복붙 예 |
| 2 | `lib/tool_intent.py` 카드 **또는** 부모 카드의 `alternatives` | when, when_not, examples[0], keywords |
| 3 | `docs/tool_catalog.md` 선반 행 | when / when not / CLI |
| 4 | `TOOLS.md` 선반 표 | **대표** CLI일 때만 |
| 5 | `workflows/agent/catalog.json` | `status`, `scripts`/`used_by`, `guide` path |
| 6 | 영상 도구: `video_backends.json` | `status`, `cli`, `human_ui`/`guide` |
| 7 | Human pack | `workflows/human/<tool>/AGENT_GUIDE.md` (또는 family pack) |
| 8 | `process.md` | 한 줄: 무엇을 실었는지 |

**Status vocabulary (shared):** `planned` | `ready` | `ready_experimental` | `legacy_mini` | `superseded`.

- `planned` = 에이전트 CLI 없음, 또는 **의도적으로** 미배선.
- `scripts/generate_*.py` 등이 있고 에이전트 사용 대상이면 → **`planned` 금지** (`ready` 또는 `ready_experimental`).

**Drift check (Comfy 불필요):**

```bash
python scripts/tool_index_check.py
```

exit 0 이 아니면 등록 미완료.

---

## 에이전트 루프

```text
tool_intent "의도"
  → #1 카드 eg: 실행
  → 실패/부적합
  → 카드 alternatives 중 맞는 if → cli 실행
  → 상세는 AGENT_GUIDE
```

생성은 Comfy; **이 표준은 발견·전환 UX**다.
