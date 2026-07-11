# 🎬 AI 에이전트용 영상 제작 파이프라인 로드맵

이 문서는 `agent_custom` 작업공간에서 **AI 에이전트가 ComfyUI 도구를 이용해 멋진 영상물을 제작**하기 위한 1차 목표와, 그 목표를 달성하기 위해 필요한 워크플로우 구성을 정리한 설계 문서입니다.

- **작성일**: 2026-07-11
- **상태**: T2I/I2I/캐릭터/I2V MVP 구축, 조립·업스케일 후속
- **현재 기반**: Z-Image-Turbo (Moody) 이미지 + Wan2.2 I2V 영상

---

## 1. 목표 정의

### 1차 목표
에이전트가 이 작업공간의 도구들을 이용해 **멋진 영상물**을 만들어 낼 수 있도록, 필요한 워크플로우·스크립트·조립 도구를 준비한다.

### 현재 상태
| 도구 | 상태 | 영상에서의 역할 |
|------|------|----------------|
| **T2I-moody** | ✅ 완료 | 히어로 키프레임, 콘티 컷, 포스터성 장면 |
| **I2I-moody** | ✅ 완료 | 같은 인물로 의상·소품·조명·구도만 바꾼 샷 변형 |
| **캐릭터 팩 / shot_with_character** | ✅ MVP | 인물 일관성 + 키프레임 프로토타입 |
| **로케이션 팩** | 📐 설계 | 장소 일관성 — [location_sheet_system_design.md](location_sheet_system_design.md) |
| **스토리보드 / 에피소드** | 📐 설계 | 샷리스트·키프레임·배치 I2V — [storyboard_pipeline_design.md](storyboard_pipeline_design.md) |
| **I2V (Wan2.2 A14B GGUF)** | ✅ MVP | `generate_i2v.py` + format/preset |
| **업스케일 ≤4K** | ✅ MVP | `upscale_image/video.py` |
| **조립** | ❌ 미구축 | FFmpeg concat, 오디오 |

T2I·I2I는 영상의 **“정지 컷 공장”**이다. 영상 품질의 상한은 여기서 거의 결정된다.  
**자산 삼각형** (캐릭터·로케·스토리) 통합 지도: [production_asset_pipeline.md](production_asset_pipeline.md).

### 핵심 원칙
“멋진 영상”은 한 방 생성 모델 하나로 끝내지 않는다.  
영화/광고처럼 **파이프라인으로 쪼개야** 에이전트가 안정적으로 결과물을 뽑을 수 있다.

```
기획/샷리스트 → 캐릭터·로케 자산 → 키프레임(T2I/I2I) → 모션(I2V/T2V)
→ 연속성/연장 → 고품질화 → 오디오 → 편집 조립
```

---

## 2. 1차에 꼭 필요한 워크플로우 (우선순위)

### A. Image-to-Video (I2V) — 최우선

| 항목 | 내용 |
|------|------|
| **역할** | 키프레임 1장 → 3~10초 클립 |
| **우선순위** | P0 (최우선) |
| **이유** | 에이전트가 통제하기 가장 쉽고, 퀄리티·일관성이 T2V보다 안정적 |
| **에이전트 입력** | `image + motion prompt + duration/fps` |
| **출력** | `clip.mp4` (또는 프레임 시퀀스) |

> 멋진 영상의 핵심 루프:
> `T2I로 강한 한 장 → I2I로 샷 다듬기 → I2V로 숨 넣기`

---

### B. 캐릭터 / 아이덴티티 고정 파이프라인 — 동급 최우선

| 항목 | 내용 |
|------|------|
| **역할** | 여러 샷에서 “같은 사람 / 같은 세계관” 유지 |
| **우선순위** | P0~P1 |
| **구성 예** | 캐릭터 시트 T2I (정면/측면/3/4), 레퍼런스 기반 생성 (IP-Adapter / face lock / reference pack), face restore / detailer |
| **이유** | 영상은 컷이 여러 개라, 인물 붕괴가 바로 “싸 보이는” 원인 |

---

### C. Shot Variation / Multi-keyframe (I2I 확장)

| 항목 | 내용 |
|------|------|
| **역할** | 같은 인물·같은 장면의 연속 컷 만들기 |
| **우선순위** | P1 |
| **예시** | wide / medium / close-up, 낮→밤, 소품 교체, 포즈 변경 |
| **기반** | 기존 I2I-moody + denoise 구간 레시피 활용 |
| **에이전트 패턴** | `master frame → I2I × N → 각 키프레임 I2V` |

새 모델보다 **프롬프트·시드·denoise 레시피**를 워크플로우/스크립트로 고정하는 비중이 크다.

**참고 (기존 I2I denoise 스위트 스팟)**:
- 사물 교체: `0.70 ~ 0.73`
- 조명/분위기: `0.75 ~ 0.78`
- 포즈/의상/배경: `0.82 ~ 0.86`
- CFG: `3.5` 이상 권장

---

### D. Video Extension / Continuity (클립 이어 붙이기)

| 항목 | 내용 |
|------|------|
| **역할** | 4~5초 × N → 15~30초 이상 장면 |
| **우선순위** | P1~P2 |
| **방식** | last frame → 다음 I2V, 또는 video continuation 모델 |
| **이유** | 한 번에 긴 영상보다, 짧은 클립을 안정적으로 연장하는 쪽이 에이전트에 유리 |

---

### E. Upscale + Frame Interpolation — 마감 품질 층 (**납품 필수 경로**)

| 워크플로우 | 역할 | 우선순위 |
|-----------|------|----------|
| **Image/Video Upscale** | work-res → **deliver_1080 / 1440 / 2160** (+ format aspect) | ✅ MVP |
| **Frame Interpolation (RIFE 등)** | 12/16fps → 24/30fps, 끊김 완화 | P2 |
| **Face/Detail refine on frames** (선택) | 클로즈업 품질 | P3 |

**해상도 전략 (확정):**

- **생성(I2V)**: 최종과 **같은 종횡비**(format: 16:9 / 9:16 / 4:3 / 3:4 …) + **작업용 해상도**. 매 루프마다 네이티브 1080p 생성하지 않음.
- **납품**: 업스케일 후 해당 비율의 ~1080 짧은 변 (예: 16:9→1920×1080, 9:16→1080×1920).
- 상세 프리셋·백엔드: [video_delivery_and_backends.md](video_delivery_and_backends.md)

모델이 평범해도 이 레이어가 있으면 체감 퀄리티가 크게 올라간다.

---

### F. 조립 (Assembly) 도구 — ComfyUI 밖이어도 됨

| 항목 | 내용 |
|------|------|
| **역할** | 클립 연결, 자막, 페이드, 오디오 믹스, 최종 인코딩 |
| **권장 스택** | Python + **FFmpeg** (에이전트가 가장 다루기 쉬움) |
| **선택** | 자막 번인, 컬러 그레이딩 LUT, 인트로/아웃트로 템플릿 |
| **우선순위** | P2 (완성 영상 납품 기준) |

영상 “도구”의 절반은 **생성**이 아니라 **편집·납품**이다.

---

## 3. 2차 확장 워크플로우 (품질 / 장르)

1차 MVP가 안정화된 뒤 확장한다.

| 워크플로우 | 언제 필요 |
|-----------|----------|
| **T2V (Text-to-Video)** | 키프레임 없이 분위기/B-roll 빠르게 |
| **V2V (Video-to-Video)** | 기존 영상 스타일 변환, 톤 통일 |
| **Camera / Motion Control** | 돌리 인, 팬, 오빗 등 카메라 문법 고정 |
| **Inpaint on video / Object replace** | 로고·소품만 바꾸기 |
| **Depth / ControlNet 계열** | 구도·포즈 엄격 제어 |
| **Lip-sync / Talking head** | 나레이션·캐릭터 대사 영상 |
| **Audio** (TTS, BGM, SFX) | 완성도의 상당 부분 담당 (Comfy 외부 가능) |

---

## 4. 에이전트용 최소 툴킷 (권장 1차 MVP 세트)

에이전트가 실제로 굴릴 **MVP 6종**:

```
1) T2I-moody            ← 이미 있음
2) I2I-moody            ← 이미 있음
3) I2V (키프레임 애니)    ← 신규 핵심
4) Character ref pack     ← 신규 (일관성)
5) Upscale + Interpolate  ← 신규 (마감)
6) FFmpeg assembler       ← 신규 (최종 영상)
```

### 에이전트 표준 루프 (자산 포함)

1. **format** 고정 (`video_backends.json`)
2. **Character pack** + **Location pack** approve
3. **shots.json** (스토리보드/샷리스트) → 키프레임 생성·검수
4. 각 승인 키프레임 **I2V** (work preset)
5. **Upscale** deliver (1080/1440/4K 선택)
6. **Assemble** + 오디오

---

## 5. 확정 스펙 (해상도 · 백엔드)

상세 전문: **[video_delivery_and_backends.md](video_delivery_and_backends.md)**

| 항목 | 확정 |
|------|------|
| **납품 비율** | **format별** (기본 cinematic 16:9; 쇼츠 9:16, 4:3, 3:4 등) |
| **납품 해상도** | 비율 유지 + **짧은 변 ~1080** |
| **생성 해상도** | 동일 비율의 **work 프리셋** (권장 960×540). 1080p는 업스케일 단계 |
| **I2V 백엔드** | 멀티: 기본 **`wan22`**, 상황별 **`ltx23`** (LTX 연동 예정) |
| **일관성** | 주연은 캐릭터 팩 + 키프레임 고정 후 I2V |

### I2V 멀티 백엔드 (개요)

```text
generate_i2v.py --backend wan22|ltx23 --preset work_16x9_540 ...
        → work clip
upscale_video.py --preset deliver_1080 --format cinematic_16x9 ...
        → deliver clip
assemble_video.py ...
        → final
```

| 백엔드 | 상태 | 메모 |
|--------|------|------|
| **wan22** | ✅ MVP CLI | `I2V-wan22-a14b.json`, GGUF A14B |
| **ltx23** | ⬜ 설계 | 로컬 LTX2.3 GGUF + ComfyUI-LTXVideo 존재, WF 연동 예정 |

---

## 6. 권장 구축 순서 (갱신)

| 단계 | 할 일 | 상태 |
|------|------|------|
| **P0** | I2V 1개 (Wan) + CLI | ✅ |
| **P1** | 캐릭터 팩 + shot_with_character | ✅ MVP |
| **P1b** | format / I2V preset / multi-backend SSOT | ✅ |
| **P1c** | 업스케일 multi-backend ≤4K | ✅ |
| **P-L** | 로케이션 팩 설계 → CLI → 파일럿 | CLI ✅ / 파일럿 ⬜ |
| **P-S** | 스토리보드·샷·배치 I2V/업스케일/조립 | ✅ |
| **P-E1** | 미니 에피소드 E2E (1 char + 1 loc + 6 shots) | ⬜ |
| **P3** | LTX2.3 백엔드 연동 | ⬜ |
| **P4** | FFmpeg 조립 + 오디오 | ✅ assemble_video (BGM 옵션) |
| **P5** | T2V/V2V/립싱크 등 | ⬜ |

---

## 7. 결론 (요약)

| 층 | 구성 | 상태 |
|----|------|------|
| **생성의 뼈대** | T2I + I2I + I2V(Wan) + 캐릭터 | ✅ MVP |
| **장소의 뼈대** | 로케이션 팩 | 📐 설계 |
| **서사의 뼈대** | 샷리스트 + 키프레임 보드 | 📐 설계 |
| **연속성의 뼈대** | 캐릭터+로케 고정 + 클립 연장 | 부분 |
| **룩의 뼈대** | `looks/` style core | ✅ 템플릿 |
| **퀄리티의 뼈대** | 업스케일 ≤4K | ✅ MVP |
| **완성의 뼈대** | FFmpeg 조립 + BGM | ✅ MVP |
| **백엔드 확장** | LTX2.3 등 | ⬜ |

---

## 8. 다음 액션 후보

1. `locations/` 템플릿 + create/expand/approve CLI (L1–L3)
2. `stories/` + `shot_compose` (S1–S3)
3. 미니 에피소드 P-E1
4. LTX 백엔드 / 실 미니 에피소드 파일럿

---

## 관련 문서

- [production_asset_pipeline.md](production_asset_pipeline.md) — **캐릭터·로케·스토리 통합 지도 (필독)**
- [location_sheet_system_design.md](location_sheet_system_design.md) — 로케이션 시트 설계
- [storyboard_pipeline_design.md](storyboard_pipeline_design.md) — 스토리보드·샷 파이프 설계
- [video_delivery_and_backends.md](video_delivery_and_backends.md) — 납품 스펙 · format · Wan/LTX
- [upscale_research_and_design.md](upscale_research_and_design.md) — 업스케일 리서치
- [character_sheet_system_design.md](character_sheet_system_design.md) / [character_impl_spec.md](character_impl_spec.md)
- [../agent_rules.md](../agent_rules.md) — 에이전트 협업 규칙
- [process.md](process.md) — 작업 이력 로그
