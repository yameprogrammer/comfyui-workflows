# 🎬 영상 납품 스펙 · 해상도 전략 · I2V 멀티 백엔드

- **작성일**: 2026-07-11
- **상태**: 설계 확정 (문서) / 업스케일·LTX CLI는 구현 대기
- **관련**: [video_pipeline_roadmap.md](video_pipeline_roadmap.md), [../scripts/generate_i2v.py](../scripts/generate_i2v.py), [../workflows/agent/I2V-wan22-a14b.json](../workflows/agent/I2V-wan22-a14b.json)

---

## 1. 핵심 원칙 (잊지 말 것)

### 1.1 생성 해상도 ≠ 납품 해상도

에이전트 영상 파이프라인은 **2단 해상도**를 쓴다.

| 단계 | 목적 | 해상도 감 |
|------|------|-----------|
| **Work (생성)** | 키프레임·I2V 모션 탐색/확정 | 비율 맞춤 + **작업용** 해상도 (예: 640~960 짧은 변) |
| **Delivery (납품)** | 시청·업로드·아카이브 | **선택한 종횡비**로 최소 ~1080 짧은 변 (예: 16:9→1920×1080, 9:16→1080×1920) |

```text
키프레임 (비율 맞춤, work res)
    → I2V (같은 비율, work res, 짧은 클립)
    → (선택) Frame interpolate
    → Upscale → 1080p (또는 그 이상)
    → FFmpeg 조립 + 오디오
    → final delivery
```

**하지 말 것:** 매 반복 생성마다 네이티브 1080p I2V로 돌리기 (VRAM·시간 낭비, 튜닝 루프 붕괴).  
**할 것:** 생성 단계에서 **종횡비만 최종과 동일**하게 맞추고, 픽셀 수는 나중에 올린다.

### 1.2 비율은 “프로젝트/포맷” 단위로 고르고, 생성 단계에서 고정

**납품 비율은 항상 16:9가 아니다.** 영상 종류에 따라 달라진다.

| format 프로필 | 비율 | 대표 용도 |
|---------------|------|-----------|
| `cinematic_16x9` | 16:9 | 가로 유튜브·시네마틱 (저장소 **기본값**) |
| `shorts_9x16` | 9:16 | 쇼츠·릴스·틱톡 |
| `classic_4x3` | 4:3 | 클래식/프레젠테이션 감 |
| `portrait_3x4` | 3:4 | 부드러운 세로 (9:16보다 덜 김) |
| `square_1x1` | 1:1 | 피드 정사각·스모크 |

- 한 클립/에피소드 파이프라인 안에서는 **work와 deliver가 같은 aspect**를 쓴다.  
- 키프레임 비율이 목표 format과 다르면 I2V 전에 **명시적 크롭/패드** (암묵 변환 금지).  
- 기본값이 16:9인 것은 편의일 뿐, 에이전트는 작업 브리프에 맞춰 `--format` 을 고른다.

### 1.3 모션 vs 디테일 분업

| 층 | 담당 |
|----|------|
| I2V 백엔드 (Wan / LTX 등) | 움직임, 카메라, 시간 일관성 |
| Upscale / refine | 선명도, 1080p 디테일, 얼굴 복원(선택) |
| FFmpeg | 클립 연결, 오디오, 최종 컨테이너 |

---

## 2. 납품(Delivery) 스펙 — 포맷 선택 + 기본값

에이전트는 **먼저 format(비율)** 을 정하고, 그다음 work/deliver 픽셀 프리셋을 쓴다.  
SSOT: 루트 [`video_backends.json`](../video_backends.json) 의 `formats` + `presets`.

| 키 | 기본값 (미지정 시) | 비고 |
|----|-------------------|------|
| `format` | `cinematic_16x9` | **바꿀 수 있음** — 16:9 고정 아님 |
| `aspect_ratio` | format에서 유도 | 16:9 / 9:16 / 4:3 / 3:4 / 1:1 … |
| `delivery_*` | format의 `default_deliver_preset` | 짧은 변 ~1080 급 |
| `work_*` | format의 `default_work_preset` | VRAM·속도 트레이드오프 |
| `delivery_fps` | `24` 또는 `30` | 프로젝트에서 고정 |
| `clip_seconds` | `3` ~ `6` | 길수록 identity/모션 drift |
| `codec` | `h264` / `yuv420p` | 호환성 |

### 2.1 프리셋 표 (발췌 — 전체는 JSON)

| 프리셋 ID | 해상도 | aspect | stage |
|-----------|--------|--------|-------|
| `work_16x9_540` | 960×540 | 16:9 | work (cinematic 기본) |
| `deliver_16x9_1080` | 1920×1080 | 16:9 | deliver |
| `work_9x16_540` | 540×960 | 9:16 | work |
| `deliver_9x16_1080` | 1080×1920 | 9:16 | deliver |
| `work_4x3_540` | 720×540 | 4:3 | work |
| `deliver_4x3_1080` | 1440×1080 | 4:3 | deliver |
| `work_3x4_540` | 540×720 | 3:4 | work |
| `deliver_3x4_1080` | 1080×1440 | 3:4 | deliver |
| `work_1x1_smoke` | 640×640 | 1:1 | work/smoke |

```bash
python scripts/generate_i2v.py --list-formats
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format shorts_9x16
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format classic_4x3
```

---

## 3. 업스케일·보간은 “필수 마감 층”

로드맵의 Upscale + Interpolate는 선택이 아니라 **납품 경로의 기본 스테이지**로 취급한다.

| 단계 | 도구 (예정/존재) | 입력 → 출력 |
|------|------------------|-------------|
| I2V | `generate_i2v.py` (--backend) | keyframe → work-res clip |
| Interpolate (선택) | RIFE 등 / `comfyui-frame-interpolation` | 16fps → 24/30fps |
| Upscale | SeedVR2 / UltimateSDUpscale 등 (로컬 보유 시) | work → 1080p |
| Assemble | FFmpeg | clips + audio → final |

**규칙**

1. `delivery_*` 미만 해상도 클립을 “최종본”으로 아카이브하지 않는다.  
2. 업스케일 전 클립은 `work/` 또는 `clips/work/` 에 둔다.  
3. 업스케일 후는 `clips/deliver/` 또는 `final/` 에 둔다.

---

## 4. I2V 멀티 백엔드 구조 (Wan2.2 + LTX2.3)

### 4.1 왜 하나가 아닌가

로컬에 이미 다음이 있다.

- **Wan2.2 I2V A14B** (GGUF High/Low) + `ComfyUI-WanVideoWrapper` + `generate_i2v.py` / `I2V-wan22-a14b.json`
- **LTX 2.3** (GGUF distilled/dev 등) + `ComfyUI-LTXVideo`

모델마다 강점이 다르므로 **상황별 백엔드 선택**이 맞다.

### 4.2 백엔드 역할 가이드 (초안)

| 백엔드 ID | 엔진 | 잘 맞는 상황 | 비고 |
|-----------|------|--------------|------|
| **`wan22`** | Wan2.2 I2V A14B | 인물 키프레임 애니, 일반 시네마틱 모션, 현재 기본 | MVP 실측 완료 |
| **`ltx23`** | LTX 2.3 | 빠른 반복, 다른 모션 취향, distilled로 속도 우선, Wan이 약할 때 대안 | WF+CLI 연동 예정 |

정확한 품질 차이는 로컬 A/B로 갱신한다. 문서의 “언제 쓸지”는 **가이드**이며, 에이전트는 프로필/플래그로 고른다.

### 4.3 공통 CLI 계약 (목표 API)

```bash
# 가로 시네마틱 (기본 format)
python scripts/generate_i2v.py --backend wan22 -i key.png -p "slow push-in" -o work.mp4

# 세로 쇼츠
python scripts/generate_i2v.py -i key.png -p "slow push-in" -o work.mp4 --format shorts_9x16

# 4:3 / 3:4
python scripts/generate_i2v.py -i key.png -p "..." -o work.mp4 --format classic_4x3
python scripts/generate_i2v.py -i key.png -p "..." -o work.mp4 --format portrait_3x4

# 납품 업스케일 (후속) — deliver preset은 format과 같은 aspect
python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_9x16_1080
```

| 인자 | 의미 |
|------|------|
| `--format` | 종횡비 프로필 (`cinematic_16x9`, `shorts_9x16`, `classic_4x3`, `portrait_3x4`, …) |
| `--backend` | `wan22` \| `ltx23` (확장 가능) |
| `--preset` | work 해상도 프리셋 오버라이드 (format 기본 대신) |
| `-i` / `-p` / `-o` | 이미지, 모션 프롬프트, 출력 |
| `--frames` / `--fps` / `--seed` | 백엔드가 지원하는 범위 내 공통 |

### 4.4 디렉터리·설정 SSOT (예정)

```text
agent_custom/
  video_backends.json              # 백엔드·프리셋 SSOT ✅
  lib/video_backends.py            # 로드·resolve_i2v_job ✅
  workflows/agent/I2V-wan22-a14b.json
  workflows/agent/I2V-ltx23.json   # LTX 예정
  scripts/generate_i2v.py          # --backend / --preset (Wan ready, LTX planned)
  scripts/upscale_video.py         # 예정
  scripts/assemble_video.py        # 예정
```

`video_backends.json` 초안 스키마:

```json
{
  "default_backend": "wan22",
  "default_work_preset": "work_16x9_540",
  "default_deliver_preset": "deliver_16x9_1080",
  "presets": {
    "work_16x9_540": { "width": 960, "height": 540, "aspect": "16:9", "stage": "work" },
    "deliver_16x9_1080": { "width": 1920, "height": 1080, "aspect": "16:9", "stage": "deliver" }
  },
  "backends": {
    "wan22": {
      "workflow": "I2V-wan22-a14b.json",
      "runner": "generate_i2v.py",
      "strengths": ["character_i2v", "general_cinematic"],
      "notes": "GGUF dual high/low + lightx2v 4step"
    },
    "ltx23": {
      "workflow": "I2V-ltx23.json",
      "runner": "generate_i2v.py",
      "strengths": ["fast_iteration", "alt_motion"],
      "status": "planned",
      "notes": "ComfyUI-LTXVideo + local GGUF"
    }
  }
}
```

### 4.5 에이전트 선택 휴리스틱 (초안)

```text
if 인물 키프레임 일관성 중시 and wan22 사용 가능 → backend=wan22
elif 빠른 프리뷰 / wan 실패·품질 불만 → backend=ltx23
elif 세로 쇼츠 → preset work_9x16_* + 동일 백엔드 선택
always: work preset으로 생성 → deliver preset으로 업스케일 후 납품
```

---

## 5. 키프레임 ↔ I2V 비율 정합

| 키프레임 소스 | I2V 입력 전 처리 |
|---------------|------------------|
| 이미 16:9 | 그대로 work 해상도로 리사이즈 |
| 1:1 (현재 많은 Moody 샷) | **센터 크롭 16:9** 또는 상단/얼굴 가중 크롭 정책 선택 |
| 9:16 쇼츠 | work_9x16 프리셋 |

`shot_with_character` 향후: `--aspect 16:9` 로 Empty latent / 리사이즈 출력 지원 (티켓).

---

## 6. 구현 티켓

| ID | 내용 | 상태 |
|----|------|------|
| D0 | 본 문서 (납품 스펙 + 멀티 백엔드 설계) | ✅ |
| D1 | `video_backends.json` SSOT + generate_i2v `--backend`/`--preset` | ✅ |
| D2 | I2V 기본 프리셋을 16:9 work로 변경 (640×640 스모크는 `--preset work_1x1_smoke`) | ✅ |
| D3 | `I2V-ltx23.json` + LTX 러너 연동 | ⬜ |
| D4 | `upscale_video.py` (work → deliver_16x9_1080) | ⬜ |
| D5 | `assemble_video.py` (concat + audio) | ⬜ |
| D6 | shot_with_character 비율 옵션 | ⬜ |

---

## 7. 현재 코드와의 관계

| 구성 | 지금 |
|------|------|
| Wan2.2 I2V | ✅ `scripts/generate_i2v.py --backend wan22` + agent WF |
| 프리셋 | ✅ 기본 `work_16x9_540` (960×540); 스모크 `work_1x1_smoke` |
| LTX2.3 I2V | 모델·노드 로컬 존재, **에이전트 워크플로 미연동** (`BACKEND_NOT_READY`) |
| 업스케일 1080p | 로드맵만, CLI 없음 |
| 16:9 work 기본 | ✅ 코드 기본 프리셋 반영 |

---

## 8. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안: 2단 해상도, 16:9/1080p 납품, Wan+LTX 멀티 백엔드, 구현 티켓 |
| 2026-07-11 | D1/D2: `video_backends.json` + `--backend`/`--preset`, 기본 work_16x9_540 |
| 2026-07-11 | 비율은 format 프로필 (16:9/9:16/4:3/3:4/1:1). 16:9는 기본값일 뿐 고정 아님 |
