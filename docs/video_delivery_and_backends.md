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
| **Delivery (납품)** | 시청·업로드·아카이브 | **최소 1080p**, 기본 **16:9 = 1920×1080** |

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

### 1.2 비율은 생성 단계에서 고정

- 기본 납품 비율: **16:9 (가로)**  
- 쇼츠 등 예외: **9:16** 프로필을 별도 정의  
- 키프레임이 1:1이면 I2V 전에 **16:9 크롭/패드 정책**을 명시적으로 적용 (암묵 변환 금지)

### 1.3 모션 vs 디테일 분업

| 층 | 담당 |
|----|------|
| I2V 백엔드 (Wan / LTX 등) | 움직임, 카메라, 시간 일관성 |
| Upscale / refine | 선명도, 1080p 디테일, 얼굴 복원(선택) |
| FFmpeg | 클립 연결, 오디오, 최종 컨테이너 |

---

## 2. 납품(Delivery) 스펙 — 기본값

에이전트·스크립트가 기본으로 가정하는 값.

| 키 | 기본값 | 비고 |
|----|--------|------|
| `aspect_ratio` | `16:9` | 가로 유튜브/시네마틱 |
| `delivery_width` | `1920` | |
| `delivery_height` | `1080` | **최소 1080p** |
| `delivery_fps` | `24` 또는 `30` | 프로젝트 프로필로 고정 |
| `work_long_edge` (I2V) | `640` ~ `960` | VRAM·속도 트레이드오프 |
| `work_short_edge` | 비율에서 유도 | 16:9 → 예: 640×360, 960×540 |
| `clip_seconds` | `3` ~ `6` | 길수록 identity/모션 drift |
| `codec` | `h264` / `yuv420p` | 호환성 |
| `audio` | 별도 슬롯 | TTS/BGM은 조립 단계 |

### 2.1 작업용 16:9 프리셋 (권장)

| 프리셋 ID | 해상도 | 용도 |
|-----------|--------|------|
| `work_16x9_360` | 640×360 | 초고속 스모크 |
| `work_16x9_540` | 960×540 | **기본 작업용 (권장)** |
| `work_16x9_720` | 1280×720 | VRAM 여유 시 |
| `deliver_16x9_1080` | 1920×1080 | 업스케일 목표 |
| `work_9x16_540` | 540×960 | 세로 쇼츠 작업 |
| `deliver_9x16_1080` | 1080×1920 | 세로 납품 |

현재 `generate_i2v.py` 기본 `640×640`은 **정사각 MVP 스모크용**이다.  
**프로덕션 기본은 `work_16x9_*` 로 옮긴다** (구현 티켓: I2V 프리셋).

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
# 백엔드 선택 — 기본 wan22
python scripts/generate_i2v.py --backend wan22 -i key.png -p "slow push-in" -o work.mp4 --preset work_16x9_540

python scripts/generate_i2v.py --backend ltx23 -i key.png -p "slow push-in" -o work.mp4 --preset work_16x9_540

# 납품 업스케일 (후속 스크립트)
python upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_16x9_1080
```

| 인자 | 의미 |
|------|------|
| `--backend` | `wan22` \| `ltx23` (확장 가능) |
| `--preset` | work/deliver 해상도 프리셋 ID |
| `-i` / `-p` / `-o` | 이미지, 모션 프롬프트, 출력 |
| `--frames` / `--fps` / `--seed` | 백엔드가 지원하는 범위 내 공통 |

### 4.4 디렉터리·설정 SSOT (예정)

```text
agent_custom/
  video_backends.json          # 백엔드·프리셋 SSOT (구현 시)
  I2V-wan22-a14b.json          # Wan 백엔드 WF (있음)
  I2V-ltx23.json               # LTX 백엔드 WF (예정)
  generate_i2v.py              # 멀티 백엔드 엔트리 (Wan 구현, LTX 확장)
  upscale_video.py             # 예정
  assemble_video.py            # 예정
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
| D1 | `video_backends.json` SSOT + generate_i2v `--backend`/`--preset` | ⬜ |
| D2 | I2V 기본 프리셋을 16:9 work로 변경 (640×640 스모크는 `--preset work_1x1_smoke` 등) | ⬜ |
| D3 | `I2V-ltx23.json` + LTX 러너 연동 | ⬜ |
| D4 | `upscale_video.py` (work → deliver_16x9_1080) | ⬜ |
| D5 | `assemble_video.py` (concat + audio) | ⬜ |
| D6 | shot_with_character 비율 옵션 | ⬜ |

---

## 7. 현재 코드와의 관계

| 구성 | 지금 |
|------|------|
| Wan2.2 I2V | ✅ `generate_i2v.py` + `I2V-wan22-a14b.json` (스모크 640² 성공) |
| LTX2.3 I2V | 모델·노드 로컬 존재, **에이전트 워크플로 미연동** |
| 업스케일 1080p | 로드맵만, CLI 없음 |
| 16:9 강제 | 문서 확정, 코드 기본값은 아직 정사각 MVP |

---

## 8. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안: 2단 해상도, 16:9/1080p 납품, Wan+LTX 멀티 백엔드, 구현 티켓 |
