# LTX 2.3 클립 확장 가이드 — 100프레임+ 컷 제작

- **작성**: 2026-07-19
- **범위**: 단일 생성 97프레임 제한 → extend 분할 체인으로 장클립 완성
- **관련**: [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md) · [generation_prompt_craft.md](generation_prompt_craft.md) · Rule 7.6

---

## 1. 왜 97프레임인가

| 항목 | 내용 |
|------|------|
| LTX 2.3 @24fps | 97프레임 ≈ 4.04초 |
| 단일 생성 한계 | 100프레임+ 시 얼굴 drift · 모션 붕괴 · VRAM 스트레스 증가 |
| 공식 권장 | Lightricks: "5-second increments" 권장 (=120프레임, 하드 캡은 97로 설정) |
| 공장 정책 | `video_backends.json` → `ltx_quality_profiles.*.max_frames_single_clip: 97` |

> 4초 이하 단위 생성 → 체인 이어붙이기 = 단일 8초 생성보다 품질/안정성 우월

---

## 2. 파이프라인 개요

```text
컷 설계 (초수·프레임수 결정)
  ↓
분할 계획 (80–97프레임 단위)
  ↓
[1] 첫 번째 클립 생성 (generate_i2v / generate_s2v)
  ↓
[2] 마지막 프레임 추출 → 다음 클립 시작 프레임
  ↓
[3] chain_si2v_last_frame.py 로 extend 생성
  ↓
[4] 반복 (필요한 만큼)
  ↓
[5] assemble_video.py 또는 assemble_single_take.py 로 이어붙이기
```

---

## 3. 분할 계획 공식

| 목표 길이 | 분할 예 (80프레임 단위) |
|-----------|------------------------|
| 4초 (97f) | 1 클립 (단일 생성) |
| 8초 (192f) | 2 클립 × 96프레임 |
| 12초 (288f) | 3 클립 × 96프레임 |
| 16초 (384f) | 4 클립 × 96프레임 |
| 20초 (480f) | 5 클립 × 96프레임 |

권장 분할 단위: **80–97프레임** (3.3–4초)

---

## 4. CLI 사용법

### 4.1 첫 번째 클립 생성

```bash
# 기본 I2V (LTX AIO)
python scripts/generate_i2v.py \
  -i keyframe.png \
  -p "slow push-in toward face, subtle breathing, continuous, no warp" \
  --frames 97 \
  --ltx-profile work \
  -o cut01_seg01.mp4
```

### 4.2 last frame extend

```bash
# chain_si2v_last_frame: 선행 클립 마지막 프레임에서 extend
python scripts/chain_si2v_last_frame.py \
  --prev cut01_seg01.mp4 \
  -p "continuing push-in, she now faces camera, eyes hold, rain continuous, no jump cut" \
  --frames 97 \
  -o cut01_seg02.mp4
```

### 4.3 이어붙이기

```bash
# assemble_single_take: 분할 클립 → 하나의 컷 클립
python scripts/assemble_single_take.py \
  --clips cut01_seg01.mp4 cut01_seg02.mp4 cut01_seg03.mp4 \
  -o cut01_final.mp4

# 또는 episode assemble (에피소드 레일 사용 시)
python scripts/assemble_video.py -e EP --stage work
```

---

## 5. extend 프롬프트 작성 법

### 규칙

1. **선행 클립 마지막 상태를 이어받는다** — 인물 위치, 카메라 포지션 기준
2. **모션·카메라만** — 얼굴 재서술, 의상 설명 재시작 금지
3. **`continuing [X]` 또는 `as [X] continues`** 패턴 사용
4. 새 인물 도입, 장소 전환 금지 (컷 안에서)

### 예시 (3분할 16초 컷)

```text
[seg01 - 0-4s] slow push-in toward face, subtle breathing, damp hair drift, continuous
[seg02 - 4-8s] continuing push-in, she slowly lifts gaze to lens, eyes hold, rain continuous, no jump cut
[seg03 - 8-12s] push-in holds, she closes eyes briefly then opens, slight cheek tension, static frame, rain continuous
```

---

## 6. 품질 팁

| 팁 | 내용 |
|----|------|
| 마지막 프레임 안정성 | 선행 클립이 stable frame으로 끝나야 extend 품질 보장 |
| 프롬프트 연속성 | `continuous` · `no jump cut` · `identity preserved` 상용구 유지 |
| 해상도 일관 | 분할 클립 전체 동일 해상도 (`--ltx-profile work` 고정) |
| extend 실패 시 | 마지막 프레임 자체를 keyframe으로 재생성 후 다시 시도 |
| 최종 업스케일 | 이어붙인 후 `upscale_video.py`로 한 번에 업스케일 |

---

## 7. failure_note 태그

| 상황 | 태그 |
|------|------|
| 단일 생성 100프레임+ 시도 후 drift | `ltx_long_clip_drift`, `frame_cap_violation` |
| extend 프롬프트에 의상 재서술 후 불일치 | `extend_wardrobe_essay` |
| 이어붙이기 시 화질 점프 | `concat_resolution_mismatch` |

```bash
python scripts/failure_note.py add --stage clip \
  --tags ltx_long_clip_drift --symptom "..." --cause "..." \
  --fix "chain_si2v_last_frame 분할" --prevention "97프레임 하드 캡 준수" \
  --severity high
```

---

## 8. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-19 | 초안: 97프레임 하드 캡 + extend 체인 파이프라인 가이드 |
