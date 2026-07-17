# 워크플로우 디렉터리 규약

이 저장소는 **선택 가능한 미디어 도구 모음**이다.  
프로젝트별 영상 파이프라인은 컨슈머 쪽이 정하고, 여기서는 워크플로 **특징을 보고 골라** 쓴다.

- **도구 명세 카탈로그 (읽기 시작점):** [docs/tool_catalog.md](../docs/tool_catalog.md)

휴먼 UI 실험과 에이전트 호출용 그래프를 분리한다.

| 경로 | 용도 | 누가 고치나 |
|------|------|-------------|
| **`workflows/agent/`** | CLI·캐릭터 파이프라인 **SSOT** | 에이전트 + 검증된 프로모트 |
| **`workflows/human/`** | ComfyUI UI 실험 내보내기 | 사람 / 실험 스냅샷 |

루트에 워크플로우 JSON을 두지 않는다. 스크립트는 `lib/workflow_paths.py` 로 agent 를 우선 해석한다.

## Human vs Agent

| | Human (UI) | Agent (스크립트) |
|--|------------|------------------|
| **목표** | 노드 배치·프리뷰·실험 | 안정적 API 주입·재현·배치 |
| **상태** | 위젯·좌표 자주 변경 | 주입 포트·`class_type`·링크 안정 |
| **변경** | 실험 후 human/ 저장 | 스크립트와 **함께** agent/ 커밋 |

## 프로모트 흐름

1. 실험 → `workflows/human/<이름>.json`
2. `scripts/` 노드 매핑 점검
3. `workflows/agent/` 로 복사
4. 필요 시 `catalog.json` 갱신
5. `process.md` + 관련 `scripts/generate_*.py` 동기화

## 경로 해석

```text
resolve_workflow("T2I-moody") / "t2i_moody"
  1. workflows/agent/<file>
  2. (옵션) 루트 동명 파일 — 호환용, 사용 비권장
  3. --workflow 로 명시 경로
```

* 카탈로그: [agent/catalog.json](agent/catalog.json)
* 구현: [../lib/workflow_paths.py](../lib/workflow_paths.py)
* 계약: [agent/README.md](agent/README.md)
