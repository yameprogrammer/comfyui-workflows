# OpenMontage 로컬 클론 평가 메모

- **날짜**: 2026-07-12 · **갱신**: 2026-07-12 (카탈로그 분리)  
- **목적**: agent_custom 목적에 쓸 만한 skill/tool 조각이 있는지 구조 스캔  
- **기능 전체 목록·유용도**: **[openmontage_capability_catalog.md](openmontage_capability_catalog.md)** ← 에이전트는 여기를 SSOT로  

## 위치 (gitignore — 제품 트리 아님)

| 경로 | 출처 | 내용 |
|------|------|------|
| `OpenMontage/` | [Open-Montage/OpenMontage](https://github.com/Open-Montage/OpenMontage) | **얇은** 마케팅/부분 lib + README. tools/skills **없음** |
| `OpenMontage_full/` | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | **풀 소스**. tools / skills / pipeline_defs / remotion-composer / backlot |

## 한 줄 결론

- **에이전트용 스킬+도구 monorepo** 맞음 (단독 GUI 편집기 아님).  
- **전체 import로 agent_custom 대체 ❌**  
- **후반·배포·품질게이트·자막·Remotion 조각 참고 ✅**  
- **공식 사용 단계(SOP)는 아직 미정의** — “이런 기능이 있다” 수준만 카탈로그에 고정.  
- 본선은 계속: Comfy SI2V / demucs / music_locked / 캐릭터 팩 / `assemble_video`.

## 겹치거나 가져오면 안 되는 것

- 전체 “에이전트=스튜디오” 오케스트레이션 → 우리 `episode_pipeline` / commission 과 이중 지휘  
- 클라우드 Kling/Veo 기본 경로 → 로컬 Comfy 우선 정책과 충돌  
- avatar lip-sync 도구 → demucs + LTX/IT 와 스택 중복  

## 다음 액션 (선택)

상세 우선순위·라벨은 카탈로그 §5–§8 참고.

1. `slideshow_risk` / `delivery_promise` 아이디어 → agent_custom 검수 규칙  
2. subtitle 툴 패턴 → `scripts/` 얇은 래퍼  
3. Remotion은 Node 의존 무거움 → 필요 시 별 프로젝트  
4. **공식 연동 SOP** 작성 (어느 에피소드 단계에서 OM을 쓸지) — 미착수  

**지금은 클론·지도·카탈로그.** 제품 코드 커밋에 monorepo 포함하지 않음 (`.gitignore`).
