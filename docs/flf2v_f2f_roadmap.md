# FLF2V / F2F (First–Last / Frame-to-Frame) — 추가 기능 로드맵

- **작성일**: 2026-07-12  
- **상태**: **📋 PLANNED (미구현)** — 스키마·문서 예약만 있음, **실행 CLI/WF 없음**  
- **티켓**: Storyboard **S6** (first–last continuity)  
- **요청 배경**: 쇼츠 제작 시 컷이 나뉘어도 **싱글테이크처럼 이어지는 화면 연결** 필요  
  (소비자 피드백: 하드컷 + 독립 키프레임/모션만으로는 연속감·립 이질감이 큼)  
- **관련**:  
  [storyboard_pipeline_design.md](storyboard_pipeline_design.md) ·  
  [archive/research/storyboard_keyframe_community_research.md](archive/research/storyboard_keyframe_community_research.md) ·  
  [audio_motion_production_modes.md](audio_motion_production_modes.md) ·  
  [production_asset_pipeline.md](production_asset_pipeline.md)

---

## 0. 한 줄

```text
keyframe_start (S_n)  +  keyframe_end (S_n 끝 / S_{n+1} 시작)
        →  FLF2V / F2F bridge clip
        →  컷 이음이 “한 테이크를 자른 느낌”
```

**립싱크(SI2V)와 역할 분리:**

| 레이어 | 담당 | 현재 |
|--------|------|------|
| **화면 연속** | FLF2V / F2F, 키프레임 체인 | ⬜ FLF 미구현 · △ 키프레임 I2I 체인만 수동 가능 |
| **대사 립** | SI2V (`infinitetalk` / `ltx23_ia2v`) | ✅ CLI 있음 (품질은 백엔드 의존) |
| **무음 모션** | I2V (`wan22` 등) | ✅ CLI 있음 |

FLF는 **입 모양을 맞추는 도구가 아니다.**  
**자리·카메라·의상·구도가 점프하지 않게** 만드는 도구다.

---

## 1. 용어

| 이름 | 의미 | 커뮤니티 별칭 |
|------|------|----------------|
| **FLF2V** | First–Last Frame to Video — **시작 스틸 + 끝 스틸**로 중간 프레임 보간 | Wan FLF2V, first-to-last I2V |
| **F2F** | Frame-to-Frame — 컷 N 끝 ≈ 컷 N+1 시작 정렬 (공정/연속성 일반 개념) | match cut continuity |
| **`motion_driver=flf2v`** | 에피소드 샷이 FLF 경로로 렌더됨을 표시 | 스키마 enum 예약됨 |
| **`keyframe` / `keyframe_end`** | 샷의 first / last still 경로 | shots.json 필드 부분 존재 |

이 문서에서 **F2F ≈ FLF2V 계열 기능**으로 묶고, 구현 시 백엔드 이름을 `flf2v` 로 통일한다.

---

## 2. 왜 필요한가 (실무 문제)

에이전트/파이프가 흔히 하는 실패:

1. 샷마다 **다른 ref**로 키프레임 → 앉은 자세·거리·배경이 매 컷 다름  
2. 샷마다 **독립 I2V/SI2V** → 끝 프레임과 다음 시작 프레임이 무관  
3. 조립은 **하드컷** → “싱글테이크” 기대와 불일치  
4. 대사는 SI2V인데 **화면이 끊기면** 립이 맞아도 영상 전체 신뢰도가 떨어짐  

커뮤니티 관행 (요약):

- bake **keyframes first**  
- **first–last chain** 으로 컷 간 드리프트 억제  
- Wan/Comfy **FLF2V** 튜토리얼: 일관 스틸 쌍 → 브리지 클립  

---

## 3. 현재 구현 상태 (정직 표)

| 항목 | 상태 | 위치 |
|------|------|------|
| `motion_driver` enum `flf2v` | ✅ 예약 | `lib/audio_package.py` MOTION_DRIVERS |
| commission brief enum | ✅ 예약 | `docs/commission_brief.schema.json` |
| `keyframe_end` inventory | ✅ 부분 | `storyboard_export` inventory 필드 |
| `episode_i2v` flf2v 스킵 | ✅ (미구현 드라이버로 스킵) | `scripts/episode_i2v.py` |
| **`generate_flf2v.py` / `episode_flf2v.py`** | ⬜ 없음 | — |
| **FLF 전용 agent workflow JSON** | ⬜ 없음 | `workflows/agent/` |
| **video_backends `flf2v` preset** | ⬜ 없음 | `video_backends.json` |
| **연속 키프레임 I2I 체인 (수동 SOP)** | △ 운영 가능 | `shot_compose --source prev_keyframe.png` + 낮은 denoise |

**DoD (구현 완료 조건)** 는 §6.

---

## 4. 목표 공정 (구현 후 SOP 초안)

### 4.1 싱글테이크 느낌 쇼츠 (권장)

```text
0. format + look + char + loc 잠금 (9:16 등)
1. S_master 키프레임 (착석/구도 마스터 플레이트)
2. S_n keyframe = I2I from S_{n-1} keyframe (낮은 denoise, 연속성 프롬프트)
   optional: keyframe_end = next shot keyframe 또는 같은 샷의 목표 포즈
3. 브리지/본편 모션:
   A) motion_driver=flf2v  → first=keyframe, last=keyframe_end
   B) 대사 컷:            → SI2V on keyframe (립) + 끝 프레임을 다음 first에 맞춤
4. assemble: hard cut 또는 2–4f crossfade (선택)
```

### 4.2 샷 레코드 필드 (목표)

```json
{
  "shot_id": "S03",
  "motion_driver": "flf2v",
  "keyframe": "keyframes/S03.png",
  "keyframe_end": "keyframes/S04.png",
  "continuity": {
    "match_from": "S02",
    "chain": "single_take",
    "bridge_role": "dialogue_hold"
  },
  "motion_prompt": "subtle head turn only, locked seat, camera locked",
  "duration_sec": 4.0
}
```

규칙:

- `keyframe` / `keyframe_end` 모두 **episode format 캔버스** (예: 544×960)  
- `motion_prompt` 는 **모션·카메라만** (얼굴 재서술 금지 — I2V 규칙과 동일)  
- 대사 립이 필요하면 그 구간은 `si2v` 유지; FLF는 **무대사 브리지·푸시인·고개 전환**에 우선  

### 4.3 하이브리드 (현실적 1차 구현)

| 구간 | 드라이버 | 이유 |
|------|----------|------|
| S01 establishing | `i2v` | 환경 플레이트 |
| S02~S05 대사 | `si2v` (InfiniteTalk 권장) | 립 |
| 컷 이음이 약한 곳 | `flf2v` 짧은 브리지 **또는** 키프레임 체인을 더 빡세게 | 화면 연결 |

완전한 “한 클립 롱테이크”는 백엔드 길이 제한(LTX/IT 프레임 캡) 때문에 **여러 SI2V + FLF/체인 키프레임**이 실무적이다.

---

## 5. 구현 티켓 분해 (S6 하위)

| ID | 내용 | 우선 | 상태 |
|----|------|------|------|
| **S6.0** | 본 로드맵 문서 + 교차 링크 | P0 | ✅ 본 문서 |
| **S6.1** | `shots.schema.json` / story package: `keyframe_end` 검증, `motion_driver=flf2v` 문서화 | P0 | ⬜ |
| **S6.2** | Comfy agent WF: Wan (또는 보유 모델) **first-last I2V** API 그래프 | P0 | ⬜ |
| **S6.3** | `scripts/generate_flf2v.py` — first, last, motion, duration → mp4 | P0 | ⬜ |
| **S6.4** | `scripts/episode_flf2v.py` — approved 샷 중 `flf2v` 배치 | P1 | ⬜ |
| **S6.5** | `video_backends.json` flf preset + format work size 연동 | P1 | ⬜ |
| **S6.6** | `shot_compose` 옵션: `--from-prev-shot` 연속 키프레임 체인 자동화 | P1 | ⬜ |
| **S6.7** | `assemble_video` 짧은 crossfade / 끝·시작 프레임 스냅 옵션 | P2 | ⬜ |
| **S6.8** | 스모크: 2키프레임 브리지 + 9:16 비율 회귀 | P1 | ⬜ |
| **S6.9** | 에이전트 SOP: 싱글테이크 쇼츠 치트시트 (`character_casting` 급) | P1 | ⬜ |

---

## 6. Definition of Done (기능 완료)

- [ ] `python scripts/generate_flf2v.py -i first.png -e last.png -o out.mp4` 성공  
- [ ] 출력 해상도 = episode work size (예: shorts 544×960)  
- [ ] `episode_flf2v -e EP` 가 `motion_driver=flf2v` 샷만 처리, 나머지는 스킵  
- [ ] `shots.json` 에 `keyframe` + `keyframe_end` + status 게이트  
- [ ] AGENT_RESULT / meta 절대 경로  
- [ ] 육안: 시작 프레임≈first, 끝 프레임≈last, identity 급변 없음  
- [ ] docs + `process.md` 이력 갱신  

---

## 7. 구현 전 임시 SOP (에이전트·사람)

FLF CLI 나오기 전 **화면 연속** 최소 처방:

```bash
# 1) 마스터 키프레임
python scripts/shot_compose.py -e EP -s S02 --denoise 0.85 ...

# 2) 다음 컷 = 이전 키프레임 소스 + 낮은 denoise (연속성)
python scripts/shot_compose.py -e EP -s S03 --source stories/EP/keyframes/S02.png --denoise 0.45..0.55
python scripts/shot_compose.py -e EP -s S04 --source stories/EP/keyframes/S03.png --denoise 0.45..0.55
# ...

# 3) 대사는 SI2V (립 품질: infinitetalk 권장 / LTX는 속도)
python scripts/episode_s2v.py -e EP --shots S02,S03,... --backend infinitetalk
```

금지:

- 매 컷 다른 expression sheet를 **sole identity source**로 써서 자리·거리 점프  
- FLF 없이 “싱글테이크 완료” 보고  

---

## 8. 비범위 (의도적)

- 전편 1파일 무한 길이 생성 (백엔드 프레임 캡 존중)  
- FLF만으로 정확한 한국어 립 (→ SI2V)  
- 자동 시네마틱 편집 AI (Remotion/EDL 풀 스택은 OpenMontage 쪽 참고만)

---

## 9. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초안. 소비자 쇼츠 피드백(립·연속감) 반영. S6 하위 티켓·임시 SOP 고정. |
