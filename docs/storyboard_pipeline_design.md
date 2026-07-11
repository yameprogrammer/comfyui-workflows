# 🎬 스토리보드·샷리스트 파이프라인 — 기획·설계

- **작성일**: 2026-07-11  
- **상태**: 설계 문서 (구현 대기)  
- **목적**: 캐릭터·로케이션 자산을 **샷 단위 키프레임 → I2V → 조립**으로 연결  
- **관련**: [production_asset_pipeline.md](production_asset_pipeline.md), [location_sheet_system_design.md](location_sheet_system_design.md), [character_sheet_system_design.md](character_sheet_system_design.md), [video_delivery_and_backends.md](video_delivery_and_backends.md)

---

## 0. 리서치 요약

| 출처 | 핵심 |
|------|------|
| **전통 영화 프리프로** (StudioBinder, Soundstripe, Vyond 등) | 스토리보드 패널 **비율 = 납품 aspect**. 샷 번호·액션·대사·카메라/FX 주석. 샷리스트와 보드 상호 참조. |
| **AI 영상 실무** (YT / 플랫폼 Canvas 류) | **Storyboard-first**: 보드·키프레임 검수 후 모션. Asset card(캐릭터·환경·스타일) 선행. |
| **ComfyUI 커뮤니티** | multi-keyframe 스티칭, first–last frame 연속성 (LTX/Wan 계열). 스케치/보드 → 실사 키프레임 → I2V. |
| **연구 (DrawVideo 등)** | 장편 = 독립 shot. 각 shot = **구성(스케치/구도) + appearance + motion prompt**. 키프레임 파생 후 first-last I2V. |
| **SNS (X)** | 프롬프트→contact sheet로 **모션 전 미리보기**; 환경 반복 붕괴 방지 위해 로케 레퍼 강제 템플릿. Continuity matrix (scene, duration, camera, VO, SFX, master prompt). |

**에이전트 함의**:  
보드의 “예쁜 한 장”보다 **기계 판독 샷 레코드 + approved 키프레임** 이 납품 품질을 결정한다.

---

## 1. 한 줄 정의

> **Story / Episode Pack** = 샷리스트 + (선택) 보드 패널 + **승인된 키프레임** + 모션·오디오 슬롯을 묶은 제작 단위.  
> 각 샷은 **character_ids[] + location_id + format + look_id** 를 참조한다.

```text
Script / beat sheet
  → Shot list (기계 SSOT)  + episode.format + episode.look_id
  → Board panels (format 비율)
  → Production keyframes (look+char+loc, format 캔버스)
  → Approve keyframes
  → I2V clips (work res)
  → Upscale --preset deliver_1080|2160 + format → Assemble
```

### 캔버스 vs 레퍼런스 비율

| 구분 | 비율 |
|------|------|
| char/loc **approved ref 파일** | 시트 고유 (1:1·세로 허용) |
| board / **keyframe / I2V** | **항상 episode format** |
| ref 사용 시 | format 프레임 안에 배치(크롭·패드·스케일). 키프레임을 ref 비율로 내보내지 말 것. |

---

## 2. 실제 영상에 필요한 결과물 계층

### 2.1 Layer A — 기획 문서 (텍스트)

| 산출물 | 형식 | 필수 |
|--------|------|------|
| Logline / treatment | md | 권장 |
| Beat sheet (장면 단위) | md 또는 json | MVP |
| **Shot list** | **`shots.json` SSOT** | **필수** |

### 2.2 Layer B — 보드 (시각 프리비즈)

| 산출물 | 형식 | 필수 |
|--------|------|------|
| Panel images (러프 또는 포토리얼) | `boards/panels/` | 권장 |
| Contact sheet (시간순 그리드) | 1장 이미지 | 권장 (검수) |
| Animatic (패널+타이밍, 선택) | mp4 | 선택 |

보드 패널 비율 = **프로젝트 format** (`cinematic_16x9`, `shorts_9x16`, …).  
정사각 보드로 찍고 나중에 크롭하지 말 것 (StudioBinder 원칙).

### 2.3 Layer C — 프로덕션 키프레임 (I2V 직전)

| 산출물 | 형식 | 필수 |
|--------|------|------|
| Keyframe per shot | `keyframes/<shot_id>.png` | **필수** |
| Meta per shot | `keyframes/<shot_id>.json` | **필수** |
| First/last pair (연속 샷) | optional | 연장 시 권장 |

키프레임은 **look + approved character + approved location** 으로 생성.  
`shot_with_character` 의 진화형: `shot_compose.py` (look+char+loc+샷 레코드, **출력은 format 해상도**).

### 2.4 Layer D — 모션·납품

| 산출물 | 도구 | 필수 |
|--------|------|------|
| Work clip | `generate_i2v.py` | 필수 |
| Deliver clip | `upscale_video.py` | 납품 시 |
| Final cut | `assemble_video.py` | 에피소드 |

---

## 3. 샷 레코드 스키마 (SSOT)

`projects/<project_id>/shots.json` 또는 `stories/<episode_id>/shots.json`

```json
{
  "episode_id": "mina_cafe_ep01",
  "format": "cinematic_16x9",
  "look_id": "cinematic_moody_v1",
  "default_fps": 24,
  "default_backend_i2v": "wan22",
  "default_work_preset": "work_16x9_540",
  "default_deliver_tier": "deliver_1080",
  "shots": [
    {
      "shot_id": "S01",
      "scene_id": "SC01",
      "order": 1,
      "duration_sec": 4,
      "shot_type": "wide",
      "camera": {
        "angle": "eye_level",
        "move": "slow_push_in",
        "lens_feel": "35mm"
      },
      "action": "Mina sits by the window, lifts a coffee cup",
      "dialogue": "",
      "vo": "",
      "sfx": ["soft cafe murmur"],
      "music_cue": "warm pad enter",
      "character_ids": ["mina_park_v1"],
      "character_refs": {
        "mina_park_v1": "approved/master_front.png"
      },
      "location_id": "cafe_seoul_v1",
      "location_ref": "approved/empty_stage.png",
      "lighting": "day_window",
      "appearance_prompt": "(assembled at runtime)",
      "motion_prompt": "gentle camera push-in, subtle steam, natural blink",
      "negative_motion": "warp, identity morph, flicker",
      "board_panel": "boards/panels/S01.png",
      "keyframe": "keyframes/S01.png",
      "keyframe_status": "draft",
      "clip_work": "clips/work/S01.mp4",
      "clip_deliver": "clips/deliver/S01.mp4",
      "seed": null,
      "continuity": {
        "screen_direction": "L_to_R",
        "matches_prev": "S00",
        "first_last_with": null
      }
    }
  ]
}
```

### 3.1 필수 필드 (에이전트 검증)

- `shot_id`, `order`, `duration_sec`  
- `format` (에피소드 또는 샷)  
- `character_ids` (0명 establishing 허용)  
- `location_id` (establishing-only도 로케 필수 권장)  
- `motion_prompt` (I2V 직전)  
- `keyframe_status` ∈ `draft | in_review | approved`

**approved 키프레임 없이 I2V 금지** (캐릭터 draft 금지 규칙과 동일).

---

## 4. 디렉터리 규약 (초안)

```text
stories/                         # 또는 projects/
  _template/
  <episode_id>/
    README.md
    bible.md                     # logline, tone
    beats.md
    shots.json                   # ★ SSOT
    boards/
      panels/
      contact_sheet.png
      animatic.mp4               # optional
    keyframes/
      S01.png
      S01.json
    clips/
      work/
      deliver/
    audio/
      vo/
      sfx/
      music/
    exports/
      final/
```

캐릭터·로케 데이터는 **복사하지 않고 id 참조** (`characters/`, `locations/`).

---

## 5. 생성 파이프 상세

### 5.1 Shot list 작성

입력: 스크립트 / 비트시트 / 사용자 브리프  
출력: `shots.json`  
에이전트 규칙:

1. 샷을 **3~6초 전후**로 쪼개기 (I2V 드리프트 대비).  
2. 같은 `location_id` 샷을 배치로 묶을 수 있게 태깅 (렌더 배치 전략 — SNS continuity matrix 관행).  
3. format을 에피소드 전역에 고정.

### 5.2 Board panels (선택 경로)

| 모드 | 설명 | 언제 |
|------|------|------|
| **Rough board** | 구도·연출만 (저비용 T2I) | 페이싱 합의 |
| **Photoreal board** | 거의 키프레임 품질 | 클라이언트/최종 연출 |
| **Contact sheet** | 전 샷 그리드 1장 | 한 장 검수 |

보드 ≠ 최종 키프레임. 보드는 **연출 합의**, 키프레임은 **I2V 입력**.

### 5.3 Production keyframe (필수 경로)

```text
for shot in shots:
  load character approved refs
  load location approved ref (angle/lighting match)
  assemble appearance_prompt = char.cores + location.core + action + camera
  generate still @ work size of episode format
  write keyframe + meta
  human/agent review → keyframe_status=approved
```

엔진: 기존 Moody T2I/I2I + (후속) 로케 empty_stage 합성.

### 5.4 Motion

```text
approved keyframe
  + motion_prompt
  + --format / work preset
  → generate_i2v.py
  → (optional) first-last with next keyframe for bridge clips
  → upscale_video.py --preset deliver_*
```

### 5.5 Continuity 패턴

| 패턴 | 방법 |
|------|------|
| 동일 장소 연속 컷 | 동일 `location_id` + 다른 angle ref |
| 액션 연결 | shot N last frame ≈ shot N+1 first (또는 explicit first-last I2V) |
| 화면 방향 | `screen_direction` 필드 유지 |
| 의상 | character costume approved alias 고정 |

---

## 6. 샷 타입 프리셋 (초안)

`stories/shot_type_presets.json` (구현 시)

| shot_type | 기본 구도 | 로케 ref 우선 | 캐릭터 framing |
|-----------|-----------|---------------|----------------|
| `establishing` | wide | master_wide | 없음/극소 |
| `wide` | full body in set | empty_stage or angle_eye | full |
| `medium` | waist-up | angle_eye | medium |
| `closeup` | face | soft bokeh / landmark blur | close |
| `insert` | prop | landmark | none |
| `pov` | subjective | angle matching | partial |

---

## 7. CLI 계약 (구현 시)

| 스크립트 | 역할 |
|----------|------|
| `scripts/story_init.py` | 에피소드 폴더 + template shots.json |
| `scripts/story_from_beats.py` | 비트시트 → 샷 초안 (LLM 에이전트 또는 규칙) |
| `scripts/storyboard_panels.py` | 패널/컨택시트 생성 |
| `scripts/shot_compose.py` | 캐릭터+로케 → 키프레임 (**shot_with_character 대체/확장**) |
| `scripts/shot_approve.py` | keyframe_status 승격 |
| `scripts/episode_i2v.py` | approved 샷 배치 I2V |
| `scripts/episode_upscale.py` | work→deliver 배치 |

```bash
python scripts/story_init.py --id mina_cafe_ep01 --format cinematic_16x9
python scripts/shot_compose.py --episode mina_cafe_ep01 --shot S01
python scripts/shot_approve.py --episode mina_cafe_ep01 --shot S01
python scripts/episode_i2v.py --episode mina_cafe_ep01 --shots all_approved
python scripts/episode_upscale.py --episode mina_cafe_ep01 --preset deliver_1080 --backend seedvr2
```

---

## 8. 검수 체크리스트

### 보드 단계
- [ ] 패널 비율 = 에피소드 format  
- [ ] 샷 순서·누락 없음  
- [ ] 각 샷에 location_id / character_ids 명시  

### 키프레임 단계
- [ ] 캐릭터 identity 유지  
- [ ] 로케 랜드마크 유지  
- [ ] 화면 방향·의상 연속  
- [ ] work 해상도·비율 일치  

### I2V 전
- [ ] `keyframe_status=approved`  
- [ ] motion_prompt에 카메라 동사 명확  
- [ ] duration이 백엔드 한계 내  

### 납품 전
- [ ] upscale preset 일관  
- [ ] 오디오 슬롯 매칭 (후속)  
- [ ] draft 클립을 final로 보관하지 않음  

---

## 9. 구현 티켓

| ID | 내용 | 의존 | 상태 |
|----|------|------|------|
| **S0** | 본 설계 문서 | — | ✅ |
| **S1** | `stories/_template` + shots.schema.json | S0 | ✅ |
| **S2** | `story_init` + shots.json | S1 | ✅ |
| **S3** | `shot_compose` (look+char+loc → keyframe) | S2, L2, character L2 | ✅ |
| **S4** | `shot_approve` (+ contact sheet later) | S3 | ✅ approve / contact ⬜ |
| **S5** | `episode_i2v` 배치 | S4, generate_i2v | ✅ |
| **S6** | first–last continuity 옵션 | S5 | ⬜ |
| **S7** | board panels / animatic | S2 | ✅ contact_sheet / animatic ⬜ |
| **S8** | episode upscale + assemble 연동 | S5, D4/D5 | ✅ |

---

## 10. 성공 기준 (미니 에피소드)

1. 샷 4~8개, **한 location + 한 character**, format 고정.  
2. 키프레임 전량 approve 후 I2V.  
3. 사람 평가: “같은 카페·같은 인물” 유지.  
4. work→deliver_1080 업스케일까지 한 경로로 재현 가능.

---

## 11. 참고

- StudioBinder: storyboard dimensions = project aspect ratio  
- Soundstripe / Vyond: shot image + number + action + dialogue + FX  
- DrawVideo: sketch + appearance + motion per shot; Wan first-last  
- Comfy/SNS: storyboard-first, contact sheet preview, environment asset cards  
- 본 저장소: `shot_with_character.py` (S3의 프로토타입), `video_backends.json`, `upscale_backends.json`
