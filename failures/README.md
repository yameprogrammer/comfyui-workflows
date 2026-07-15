# failures/ — 에이전트 공유 실패 노트 (Learn from failure)

에이전트가 **같은 실수를 반복하지 않도록** 실패 원인·수정·예방을 남기는 공유 저장소다.

| 경로 | 역할 |
|------|------|
| `notes/*.json` | 기계 판독 노트 (SSOT 1건 = 1파일) |
| `INDEX.md` | 최신순 요약 (사람이 훑기) |
| `tags.json` | 권장 태그 목록 |
| `schema.json` | 필드 스키마 |
| CLI | `python scripts/failure_note.py` |

**규칙:** [agent_rules.md](../agent_rules.md) Rule **7.4** · [docs/failure_notes_system.md](../docs/failure_notes_system.md)

## 에이전트 의무

1. **생성 전** — 관련 태그로 `failure_note.py search` (또는 INDEX 훑기)  
2. **QA FAIL / 유저 리젝 / 재생성 필요** — 같은 세션에 `failure_note.py add`  
3. **성공만 남기고 실패 침묵** — 위반  

에피소드 로컬 `QA_LOG.md` 와 별개다.  
QA_LOG = 이번 작품 컷 판정 · **failures/** = 전 에이전트 공통 교훈.
