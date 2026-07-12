# OpenMontage 로컬 클론 평가 메모

- **날짜**: 2026-07-12  
- **목적**: agent_custom 목적에 쓸 만한 skill/tool 조각이 있는지 구조 스캔  
- **위치** (gitignore — 제품 트리 아님):

| 경로 | 출처 | 내용 |
|------|------|------|
| `OpenMontage/` | [Open-Montage/OpenMontage](https://github.com/Open-Montage/OpenMontage) | **얇은** 마케팅/부분 lib + README. tools/skills **없음** |
| `OpenMontage_full/` | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | **풀 소스** (~2000 files). tools / skills / pipeline_defs / remotion-composer |

릴리스 번들: `OpenMontage-x64.7z` (~67MB installer) — 소스 리뷰용으로 풀 클론이 더 유용.

---

## 한 줄 결론

- **에이전트용 스킬+도구 monorepo** 맞음 (단독 GUI 편집기 아님).  
- **전체 import로 agent_custom 대체 ❌**  
- **후반·배포·품질게이트·Remotion 조각 참고 ✅**  
- 본선은 계속: Comfy SI2V / demucs / music_locked / 캐릭터 팩.

---

## 우리 목적에 쓸 만한 후보 (우선순위)

| 우선 | 조각 | 경로 (full) | 우리 쓰임 |
|------|------|-------------|-----------|
| 1 | slideshow / delivery promise 품질 게이트 | `lib/slideshow_risk.py`, `lib/delivery_promise.py` | 납품 전 “슬라이드쇼 티” 차단 아이디어 |
| 2 | post-render 검수 패턴 | AGENT_GUIDE + analysis tools | ffprobe + 프레임 + 오디오 레벨 (우리는 부분 구현) |
| 3 | 자막 SRT/VTT | `tools/subtitle/` | 숏폼 자막 — 현재 약함 |
| 4 | clip-factory / 롱→숏 | `pipeline_defs/clip-factory.yaml` + video tools | 배포 리퍼포즈 |
| 5 | documentary corpus | `lib/corpus.py`, `tools/analysis/` | B-roll 실사 몽타주 (뮤비 배경) |
| 6 | Remotion 캡션 모션 | `remotion-composer/` | 타이포·워드 레벨 캡션 |
| 7 | media profiles | `lib/media_profiles.py` | 플랫폼 해상도 표 (우리는 format SSOT 있음) |
| 8 | ComfyUI 브리지 | `tools/_comfyui/` | 연동 참고 (우리 스택이 더 깊음) |
| 9 | Wav2Lip / SadTalker | `tools/avatar/` | **비권장 중복** — SI2V(LTX/IT) 유지 |
| 10 | scored provider selection | `lib/scoring.py` | 클라우드 다공급자 쓸 때만 |

---

## 겹치거나 가져오면 안 되는 것

- 전체 “에이전트=스튜디오” 오케스트레이션 → 우리 `episode_pipeline` / commission 과 이중 지휘
- 클라우드 Kling/Veo 기본 경로 → 로컬 Comfy 우선 정책과 충돌
- avatar lip-sync 도구 → demucs + LTX/IT 와 스택 중복

---

## 다음 액션 (선택)

1. `slideshow_risk` / `delivery_promise` 아이디어만 agent_custom 검수 규칙으로 이식  
2. subtitle 툴 1개 스모크 후 `scripts/` 얇은 래퍼  
3. Remotion은 Node 의존 무거움 → 필요 시 별 프로젝트  

**지금은 클론·지도만.** 제품 코드 커밋에 monorepo 포함하지 않음 (`.gitignore`).
