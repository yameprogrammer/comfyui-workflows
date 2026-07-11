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

## 2. 자산 구조 + 에피소드

```text
                 ┌─────────────────┐
                 │  Story/Episode  │  shots.json + keyframes + clips
                 │  look_id + format│
                 └────────┬────────┘
     character_ids │ location_id │ look_id
    ┌──────────────┼─────────────┼──────────────┐
    ▼              ▼             ▼              │
┌─────────┐  ┌──────────┐  ┌──────────┐         │
│Character│  │ Location │  │ Look/Style│◄───────┘
│characters│ │locations │  │ looks/    │  (전역 톤)
└─────────┘  └──────────┘  └──────────┘
```

| 팩 | 고정하는 것 | 최소 산출 |
|----|-------------|-----------|
| **Character** | 얼굴·체형·의상·표정 | `approved/` masters |
| **Location** | 건축·재질·조명·랜드마크 | establishing + angles + empty_stage |
| **Look** | 그레이드·매체·필름 느낌 | `positive_core` / `negative_core` |
| **Story** | 샷 순서·카메라·모션 | `shots.json` + approved keyframes |

캐릭터·로케는 **`status=approved` 자산만** 본촬영. 룩은 텍스트 코어가 본체(이미지 mood ref는 선택).

---

## 3. 엔드투엔드 제작 순서 (권장)

```text
0. Project format + look_id 결정
   format: cinematic_16x9 | shorts_9x16 | …
   look:   looks/cinematic_moody_v1 (기본)

1. Character Pack (L2+)
   create → expand → approve

2. Location Pack (L2+)
   create → expand → approve

3. Episode / Story Pack
   story_init (format + look_id) → beats → shots.json
   (optional) board panels + contact sheet 검수

4. Production keyframes  ★ format 캔버스
   shot_compose: look + char + loc + action → keyframe @ format work size
   shot_approve

5. Motion
   episode_i2v @ work preset (format 비율)
   optional first–last bridges

6. Finish
   upscale_video --preset deliver_1080|1440|2160  (+ format aspect)
   assemble + audio (후속)
```

**병렬 가능**: 캐릭터·로케·룩 준비.  
**직렬 필수**: 키프레임은 char+loc approve 이후.

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

### 4.4 Look (글로벌 톤)

| 결과물 | 영상에서 쓰임 |
|--------|----------------|
| `looks/<id>/prompts/positive_core.txt` | 전 샷 appearance 접두 |
| `negative_core.txt` | 룩 붕괴 방지 |
| `bible.json` | look_id 메타 |

상세: [look_style_system.md](look_style_system.md)

### 4.5 납품 공통 (프리셋 이름 규칙)

| 개념 | ID 예 | SSOT |
|------|-------|------|
| **format** (비율) | `cinematic_16x9`, `shorts_9x16` | `video_backends.json` → `formats` |
| **work 픽셀** | `work_16x9_540`, `work_9x16_540` | `video_backends.json` → `presets` (stage=work) |
| **deliver 티어** (짧은 변) | `deliver_1080`, `deliver_2160` | **`upscale_backends.json` only** |
| 구 이름 | `deliver_16x9_1080` 등 | **deprecated** → `deliver_aliases` → `deliver_1080` |

```bash
# 올바른 납품 호출
python scripts/upscale_video.py -i work.mp4 -o out.mp4 \
  --preset deliver_1080 --format cinematic_16x9 --backend seedvr2
```

### 4.6 키프레임 비율 규칙 (compose)

| 자산 | 비율 | 비고 |
|------|------|------|
| Character / location **시트 ref** | 스튜디오·시트 고유 (1:1, 세로 등 OK) | identity/set 언어용 |
| Board panel / **production keyframe** / I2V | **에피소드 format 캔버스만** | 납품 aspect와 동일 |
| 합성 | ref는 크롭·스케일·패드하여 **format 프레임 안에 배치** | 암묵 비율 변환 금지 — 정책 명시 |

---

## 5. 데이터 흐름 (한 샷)

```text
shots.json[S01]
  look_id       → looks/cinematic_moody_v1/prompts/...
  character_ids → characters/mina_park_v1/approved/...
  location_id   → locations/cafe_seoul_v1/approved/...
        ↓
  appearance = look.core + char.core + loc.core + action + camera
        ↓
  keyframe S01.png  @ format work size (not ref native aspect)
        ↓ approve
  motion_prompt + I2V work preset
        ↓
  clips/work/S01.mp4
        ↓ upscale --preset deliver_1080 + format
  clips/deliver/S01.mp4
```

---

## 6. 디렉터리 맵 (저장소 목표)

```text
agent_custom/
  characters/          # ✅
  locations/           # ⬜ 설계
  looks/               # ✅ 템플릿 + cinematic_moody_v1
  stories/             # ⬜ 설계
  workflows/agent/
  scripts/
  video_backends.json  # format + work presets
  upscale_backends.json# deliver_1080/2160 tiers
  docs/
```

---

## 7. 티켓 로드맵 (통합)

| 단계 | 티켓 | 내용 | 상태 |
|------|------|------|------|
| 자산 | C* | 캐릭터 L2 도구 | ✅ MVP / 품질 고도화 중 |
| 자산 | **L0–L3** | 로케이션 | L0 ✅ / 코드 ⬜ |
| 자산 | **K0–K1** | Look 코어 | K0 ✅ / compose 주입 ⬜ |
| 서사 | **S0–S5** | 스토리·샷 컴포즈 | S0 ✅ / 코드 ⬜ |
| 모션 | I2V | backend/format/work | ✅ |
| 마감 | U* | upscale ≤4K | ✅ |
| 마감 | D5 | assemble | ⬜ |
| 통합 | **P-E1** | 미니 에피소드 E2E | ⬜ |

**권장 구현 순서**

1. L1–L3 로케이션 팩  
2. S1–S3 stories + shot_compose (**look_id + format 캔버스 포함**)  
3. P-E1 미니 에피소드  
4. assemble  

캐릭터 턴어라운드 품질은 **병렬 트랙**.

---

## 8. 에이전트 운영 규칙

1. 에피소드 시작 시 **format + look_id** 고정.  
2. 키프레임/I2V 입력은 **approved 캐릭터·로케만**.  
3. 샷에 `location_id` 없이 배경 즉흥 생성 금지.  
4. Storyboard-first: 키프레임 검수 전 전 샷 I2V 금지.  
5. work → deliver 티어 업스케일; 네이티브 4K I2V 루프 금지.  
6. deliver ID는 **`deliver_1080` 형태** (aspect는 format이 담당).  
7. **멀티 트랙 허용**: 로케/스토리/I2V/업스케일은 캐릭터 L2와 병행 가능. **L3 LoRA 학습만** 캐릭터 트랙과 한 PR에 섞지 말 것.

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
