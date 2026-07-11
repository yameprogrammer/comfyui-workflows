# 🎞️ 프로덕션 자산 파이프라인 — 캐릭터 · 로케이션 · 스토리보드 통합

- **작성일**: 2026-07-11  
- **상태**: 설계 SSOT (통합 지도)  
- **목적**: 실제 영상을 만들 때 **어떤 결과물을 어떤 순서로** 만들어야 하는지 한 장에 고정  
- **하위 문서**:  
  - [character_sheet_system_design.md](character_sheet_system_design.md) / [character_impl_spec.md](character_impl_spec.md)  
  - [location_sheet_system_design.md](location_sheet_system_design.md)  
  - [storyboard_pipeline_design.md](storyboard_pipeline_design.md)  
  - [video_delivery_and_backends.md](video_delivery_and_backends.md)  
  - [upscale_research_and_design.md](upscale_research_and_design.md)

---

## 1. 문제 정의

에이전트가 “한 줄 프롬프트 → 영상”만 하면:

- 인물 붕괴  
- 장소 표류 (매 컷 다른 카페)  
- 비율·해상도 불일치  
- 모션 전 연출 검수 부재  

가 반복된다.  
커뮤니티·플랫폼 실무는 공통적으로 **Asset → Board → Keyframe → Motion → Finish** 를 강제한다.

---

## 2. 자산 삼각형 + 에피소드

```text
                 ┌─────────────────┐
                 │  Story/Episode  │  shots.json + keyframes + clips
                 │  (시간축)        │
                 └────────┬────────┘
            character_ids │ location_id
           ┌──────────────┴──────────────┐
           ▼                             ▼
   ┌───────────────┐             ┌───────────────┐
   │ Character Pack│             │ Location Pack │
   │ characters/   │             │ locations/    │
   └───────────────┘             └───────────────┘
```

| 팩 | 고정하는 것 | 최소 approved |
|----|-------------|---------------|
| **Character** | 얼굴·체형·의상·표정 언어 | master + 소수 표정/의상 |
| **Location** | 건축·재질·조명·랜드마크 | establishing + angles + empty_stage |
| **Story** | 샷 순서·카메라·모션·오디오 슬롯 | shots.json + approved keyframes |

세 팩 모두 **`status=approved` 자산만 본촬영(키프레임/I2V)** 에 사용.

---

## 3. 엔드투엔드 제작 순서 (권장)

```text
0. Project format 결정
   video_backends format: cinematic_16x9 | shorts_9x16 | classic_4x3 | ...

1. Character Pack (L2+)
   create → expand → approve
   품질 게이트: 마스터 identity 통과

2. Location Pack (L2+)
   create → expand → approve
   품질 게이트: multi-angle 동일 장소 인식 + empty_stage

3. Episode / Story Pack
   story_init → beats → shots.json
   (optional) board panels + contact sheet 검수

4. Production keyframes
   shot_compose per shot (char + loc + action)
   shot_approve

5. Motion
   episode_i2v @ work preset (format 비율 유지)
   optional first–last bridges

6. Finish
   upscale_video → deliver_1080 / 1440 / 2160
   assemble + audio (후속)
```

**병렬 가능**: 캐릭터와 로케 팩은 서로 독립 → 동시 제작 권장.  
**직렬 필수**: 키프레임은 두 팩 approve 이후.

---

## 4. “영상 반영”에 필요한 결과물 체크리스트

### 4.1 캐릭터 (기존 + 영상 연결)

| 결과물 | 영상에서 쓰임 |
|--------|----------------|
| `approved/master_*` | 기본 identity |
| `approved/expr_*` | 감정 샷 |
| `approved/costume_*` | 에피소드 의상 고정 |
| `positive_core.txt` | 모든 키프레임 주입 |
| turnaround (고도화 중) | multi-view·측면 샷 |

### 4.2 로케이션 (신규 설계)

| 결과물 | 영상에서 쓰임 |
|--------|----------------|
| `approved/master_wide` | establishing, 장소 앵커 |
| `approved/angle_*` | 카메라 방향 일치 |
| `approved/empty_stage` | 인물 합성 배경 |
| `approved/light_*` | 시간대 연속 |
| `approved` landmarks | insert 샷 |
| `positive_core` | 장소 블록 주입 |

### 4.3 스토리보드/에피소드 (신규 설계)

| 결과물 | 영상에서 쓰임 |
|--------|----------------|
| `shots.json` | 전체 타임라인 SSOT |
| board panels / contact | 연출 합의 (모션 전) |
| `keyframes/Sxx.png` + meta | **I2V 입력** |
| `clips/work` | 편집 원본 |
| `clips/deliver` | 납품 해상도 |
| audio 슬롯 | 조립 |

### 4.4 납품 공통

| 결과물 | SSOT |
|--------|------|
| format / aspect | `video_backends.json` formats |
| work / deliver 해상도 | video + upscale presets |
| I2V backend | wan22 / ltx23 |
| upscale backend | seedvr2 / rtx_vsr / esrgan |

---

## 5. 데이터 흐름 (한 샷)

```text
shots.json[S01]
  character_ids → characters/mina_park_v1/approved/...
  location_id   → locations/cafe_seoul_v1/approved/...
        ↓
  appearance_prompt = char.core + loc.core + action + camera
        ↓
  keyframe S01.png  (format work size)
        ↓ approve
  motion_prompt + I2V work preset
        ↓
  clips/work/S01.mp4
        ↓ upscale
  clips/deliver/S01.mp4
```

---

## 6. 디렉터리 맵 (저장소 목표)

```text
agent_custom/
  characters/          # ✅ 존재
  locations/           # ⬜ 설계만
  stories/             # ⬜ 설계만 (에피소드)
  workflows/agent/
  scripts/
  video_backends.json
  upscale_backends.json
  docs/
    production_asset_pipeline.md   # 본 문서
    location_sheet_system_design.md
    storyboard_pipeline_design.md
    character_* 
    video_*
```

---

## 7. 티켓 로드맵 (통합)

| 단계 | 티켓 | 내용 | 상태 |
|------|------|------|------|
| 자산 | C* | 캐릭터 L2 도구 | ✅ MVP / 품질 고도화 중 |
| 자산 | **L0–L3** | 로케이션 설계→CLI→파일럿 | L0 ✅ / 구현 ⬜ |
| 서사 | **S0–S5** | 스토리 설계→샷 컴포즈→배치 I2V | S0 ✅ / 구현 ⬜ |
| 모션 | I2V D* | backend/preset/format | ✅ 상당 부분 |
| 마감 | U* / D4–D5 | upscale ≤4K, assemble | upscale ✅ / assemble ⬜ |
| 통합 | **P-E1** | 미니 에피소드 E2E (1 loc + 1 char + 6 shots) | ⬜ |

**권장 구현 순서**

1. L1–L3 로케이션 팩 (캐릭터와 대칭 CLI)  
2. S1–S3 stories + shot_compose  
3. P-E1 미니 에피소드  
4. S6 continuity + assemble  

캐릭터 턴어라운드 품질은 **병렬 트랙** (에피소드 establishing/medium 위주면 블로커 아님).

---

## 8. 에이전트 운영 규칙 (초안 → agent_rules 반영)

1. 에피소드 시작 시 **format 먼저** 고정.  
2. 키프레임/I2V 입력은 **approved 캐릭터·로케만**.  
3. 샷에 `location_id` 없이 배경 즉흥 생성 금지.  
4. 보드 검수 전 전 샷 I2V 돌리지 말 것 (storyboard-first).  
5. work 생성 → deliver 업스케일; 네이티브 4K I2V 루프 금지.  

---

## 9. 리서치 근거 (요약)

| 원칙 | 근거 |
|------|------|
| Environment asset card | AI 영상 툴·커뮤니티 (캐릭터와 대칭 환경 카드) |
| Location multi-angle + empty stage + materials | X location identity board 실무 템플릿 |
| Storyboard-first + keyframe review | YT/플랫폼 AI 영상 워크플로 |
| Panel aspect = delivery aspect | StudioBinder 등 프리프로 표준 |
| Shot = appearance + motion | DrawVideo / multi-keyframe Comfy 관행 |
| Continuity matrix / batch by location | SNS 프로덕션 프롬프트 관행 |
| Gradual upscale | Comfy upscaling handbook |

---

## 10. 다음 문서 작업 (구현 전)

- [x] location 설계  
- [x] storyboard 설계  
- [x] 통합 지도 (본 문서)  
- [ ] `locations/_template` 스캐폴드  
- [ ] `stories/_template` + shots.schema.json  
- [ ] roadmap / agent_rules 링크 동기화  
