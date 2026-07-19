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

## 에이전트 루프

```text
tool_intent "의도"
  → #1 카드 eg: 실행
  → 실패/부적합
  → 카드 alternatives 중 맞는 if → cli 실행
  → 상세는 AGENT_GUIDE
```

생성은 Comfy; **이 표준은 발견·전환 UX**다.
