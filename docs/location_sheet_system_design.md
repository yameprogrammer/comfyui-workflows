# 🗺️ 로케이션(세트) 시트 시스템 — 기획·설계

- **작성일**: 2026-07-11  
- **상태**: 설계 문서 (구현 대기)  
- **목적**: 영상 파이프에서 **장소 일관성**을 캐릭터 시트와 동급으로 다루기  
- **관련**: [character_sheet_system_design.md](character_sheet_system_design.md), [storyboard_pipeline_design.md](storyboard_pipeline_design.md), [production_asset_pipeline.md](production_asset_pipeline.md), [video_pipeline_roadmap.md](video_pipeline_roadmap.md)

---

## 0. 리서치 요약 (왜 이런 산출물인가)

| 출처 유형 | 핵심 교훈 |
|-----------|-----------|
| **AI 영상 커뮤니티 (X)** | 환경 일관성이 깨지면 숏폼이 “같은 배경 복붙”처럼 보인다. **Location identity board**: 동일 장소 multi-angle + 재질 스와치 + 조명 상태 + 랜드마크 + 팔레트 + (선택) 맵. 캐릭터 삽입용 **empty stage** 프레임이 중요. |
| **AI 파이프라인 (Topview 등, YT)** | **Asset cards** (character / style / **environment**) → storyboard-first → keyframe 검수 → 모션. 환경 카드를 건너뛰면 보드만 예쁘고 컷 간 세트가 붕괴. |
| **학술/실험 (DrawVideo 등)** | 장편은 shot 단위 분해. 각 샷 = 구성 조건 + **appearance(캐릭터·씬)** + motion. 장소는 appearance의 고정 축. |
| **영화·프로덕션 디자인** | Location scouting notes + set bible: establishing, reverse, detail, lighting, prop scale. 스토리보드 이전에 **세트 언어** 확정. |
| **게임/환경 아트** | Main establishing + secondary shots + lighting variants. 재질·실루엣·스케일 큐가 캐릭터 배치 품질을 좌우. |

**에이전트 함의**: 로케이션은 “배경 프롬프트 한 줄”이 아니라 **캐릭터 패키지와 대칭인 Location Pack** 이어야 한다.

---

## 1. 한 줄 정의

> **Location Pack** = 같은 장소의 **공간·재질·조명·랜드마크 언어**를 기계가 재현할 수 있게 고정한 레퍼런스 패키지.  
> 스토리보드 키프레임·I2V는 이 팩의 `approved/` 만 기본 입력으로 쓴다.

캐릭터의 L2( soft ref ) 에 대응: **L2 Location Soft Factory** (I2I + multi-view refs, 초기 LoRA 없음).

---

## 2. 영상 제작 시 실제로 필요한 결과물

### 2.1 MVP (video_ref 용 — 영상 일관성 최소)

| # | 산출물 | 용도 | 비고 |
|---|--------|------|------|
| L1 | **Hero establishing (wide)** | 장소 정체성 앵커 | 사람 없거나 작게; 공간 우선 |
| L2 | **Angle set (4~6뷰)** | 같은 장소 다른 카메라 | eye / reverse / high / low / corner / **empty stage** |
| L3 | **Lighting states (2~3)** | 시간대 연속성 | day / golden / night 등 프로젝트에 맞게 |
| L4 | **Landmark / prop lock (2~4)** | 반복 소품·간판·가구 | 클로즈업 스와치 |
| L5 | **Palette + materials text** | 프롬프트 SSOT | bible + 스와치 이미지 선택 |
| L6 | **`bible.json` + `manifest.json`** | 기계 판독 | 캐릭터 패키지와 동일 철학 |
| L7 | **`approved/` 승격 세트** | 보드·샷 입력 | draft 금지 규칙 공유 |

### 2.2 Artbook / 고해상 (선택)

| # | 산출물 | 용도 |
|---|--------|------|
| A1 | Texture grid (벽/바닥/천) | 디테일 업스케일 전 레퍼 |
| A2 | Top-down / layout sketch | 카메라 블로킹 (정밀 맵은 후순위) |
| A3 | Scale plate (인물 실루엣 vs 문/가구) | 캐릭터 합성 시 비율 |
| A4 | Contact sheet (아트북 1장) | 사람 검수용 요약 |

### 2.3 의도적으로 넣지 않는 것 (초기)

- CAD 수준 도면, 표준 세트 블루프린트 시트 (커뮤니티: AI 일관성엔 **시네마틱 identity board**가 더 유효)
- 매 샷마다 새 배경 T2I (로케 팩 무시)
- 캐릭터가 가득한 “예쁜 장면”만 hero로 쓰기 → **공간 읽기 실패**

---

## 3. 패키지 디렉터리 규약 (초안)

캐릭터 `characters/<id>/` 와 대칭.

```text
locations/
  _template/
  schemas/
    bible.schema.json
    manifest.schema.json
  location_presets.json          # 시트별 prompt/denoise SSOT
  profiles.json                  # video_ref | artbook (해상도·MVP)
  <location_id>/
    bible.json
    manifest.json
    prompts/
      positive_core.txt          # 건축·재질·팔레트 고정 문구
      negative_core.txt
      angle_templates.json
    refs/
      master/                    # establishing 후보
      angles/                    # multi-view
      lighting/
      landmarks/
      materials/
      empty_stage/               # 캐릭터 합성용 빈 무대
    approved/
      master_wide.png
      angle_eye.png
      angle_reverse.png
      angle_high.png
      angle_low.png
      empty_stage.png
      light_day.png
      light_golden.png
      ...
    meta/
    exports/
      video_ref/
      artbook/
```

### 3.1 `bible.json` 핵심 필드 (초안)

```json
{
  "location_id": "cafe_seoul_day_v1",
  "name": "Seoul Sidewalk Cafe",
  "status": "draft",
  "level": "L2",
  "active_profile": "video_ref",
  "type": "interior_cafe",
  "atmosphere": ["warm", "quiet", "afternoon"],
  "architecture_lock": "narrow storefront, wooden facade, large window left...",
  "material_signature": ["worn wood", "matte ceramic", "brushed brass"],
  "palette": ["#C4A484", "#2F3E46", "#E9C46A"],
  "landmarks": ["round marble table", "green awning", "neon menu board"],
  "scale_notes": "door ~2.1m; table height ~75cm",
  "default_lighting": "soft window key from camera-left",
  "forbidden": ["changing storefront shape", "new skyline", "random props"],
  "sheet_index": {}
}
```

---

## 4. 생성 레시피 (엔진 관점)

### 4.1 권장 파이프 (L2)

```text
T2I establishing master (location-only, no hero character)
  → approve master_wide
  → I2I / multi-angle expand (same positive_core, camera prompt only)
  → lighting variants (denoise mid, lock architecture)
  → landmark close-ups
  → empty_stage (clear foreground for character composite)
  → human/agent approve → approved/
```

| 단계 | 엔진 | denoise 감 (Moody Flow Matching) | 메모 |
|------|------|----------------------------------|------|
| Master | T2I | — | 사람 최소화 프롬프트 |
| Angle | I2I from master | 0.78~0.85 | 구도 변경, 재료 유지 |
| Lighting | I2I | 0.75~0.80 | 건축 고정, 광만 |
| Landmark | T2I or crop+I2I | 0.70~0.78 | 소품 클로즈 |
| Empty stage | I2I | 0.72~0.80 | 전경 비우기 |

### 4.2 ControlNet / 구조 (후속 P-L4)

- 건축 각도 고정이 약하면 depth/canny/softedge 또는 스케치 가이드.
- 캐릭터 턴어라운드와 달리 **장소는 “같은 공간의 카메라 워크”** 가 목표.

### 4.3 프롬프트 조립

캐릭터와 동일 패턴:

```text
positive = positive_core + angle_or_lighting_clause + shot_clause + quality_suffix
negative = negative_core + "different building, relocated landmarks, style shift..."
```

**Spatial lock 규칙 (커뮤니티 합의 반영)**  
동일 건축 실루엣, 동일 팔레트, 동일 랜드마크 상대 위치, 동일 조명 논리, 스케일 관계 유지.

---

## 5. 프로필

| 프로필 | 목표 | MVP 시트 |
|--------|------|----------|
| **`video_ref`** (기본) | 영상 레퍼 최소 | establishing + 4 angle + 1 empty + 1 lighting alt |
| **`artbook`** | 아트 디렉션·고해상 | + materials grid, scale plate, full lighting set, contact sheet |

해상도: 기존 `characters/profiles.json` 과 정렬하되 **납품 format 비율**은 프로젝트 format 따름 (16:9/9:16/…). 로케 마스터는 최종 format에 맞춘 work 비율로 생성하는 것을 권장.

---

## 6. CLI 계약 (구현 시)

| 스크립트 | 역할 |
|----------|------|
| `scripts/location_create.py` | 패키지 + establishing 후보 |
| `scripts/location_expand_sheets.py` | angles/lighting/landmarks |
| `scripts/location_approve.py` | refs → approved |
| (공유) `lib/location_package.py` | 캐릭터 패키지 미러 |

```bash
python scripts/location_create.py --id cafe_seoul_v1 --name "Seoul Cafe" --profile video_ref
python scripts/location_expand_sheets.py --id cafe_seoul_v1 --sheets all_mvp
python scripts/location_approve.py --id cafe_seoul_v1 --from refs/master/... --as master_wide --set-primary
```

---

## 7. 스토리보드·샷과의 연결

| 보드 필드 | 로케 팩 소스 |
|-----------|--------------|
| `location_id` | 패키지 id |
| `location_ref` | `approved/master_wide` 또는 shot별 angle |
| `lighting` | `approved/light_*` 또는 bible default |
| `empty_stage` | 캐릭터 합성 시 배경 우선 |
| `positive_core` 주입 | 키프레임 생성 시 장소 블록 |

**금지**: 보드 샷이 선언한 `location_id` 없이 자유 배경 T2I.

---

## 8. 구현 티켓

| ID | 내용 | 의존 | 상태 |
|----|------|------|------|
| **L0** | 본 설계 문서 | — | ✅ |
| **L1** | `locations/_template` + schemas + presets | L0 | ✅ |
| **L2** | create / expand / approve CLI | L1 | ✅ |
| **L3** | video_ref 파일럿 1곳 (e.g. mina 카페) | L2 + Comfy 실생성 | ⬜ |
| **L4** | ControlNet/depth 각도 강화 | L2 | ⬜ |
| **L5** | artbook export + contact sheet | L2 | ⬜ |
| **L6** | storyboard CLI 연동 (`location_id` 필수) | L2 + S* | ⬜ |

---

## 9. 성공 기준 (파일럿)

1. 같은 `location_id` 로 만든 3개 키프레임에서 **건축·랜드마크가 사람 눈으로 동일 장소**로 읽힘.  
2. empty_stage + character approved 합성 시 스케일이 크게 어긋나지 않음.  
3. lighting variant 전환 시 구조가 무너지지 않음.  
4. 보드→I2V 경로에서 배경 표류가 “프롬프트만” 때보다 감소.

---

## 10. 참고

- X: cinematic LOCATION identity board 템플릿 (multi-angle, materials, lighting, landmarks, empty stage)  
- StudioBinder / 스토리보드 비율 가이드: 패널·로케 레퍼 모두 **납품 aspect** 정렬  
- DrawVideo / multi-keyframe 커뮤니티: shot-level appearance 고정  
- 기존 캐릭터 시스템: [character_impl_spec.md](character_impl_spec.md) 패턴 재사용
