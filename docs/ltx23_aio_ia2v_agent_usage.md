# LTX 2.3 AIO — IA2V (Image + Audio) 에이전트 사용법

- **작성일**: 2026-07-12  
- **정본 스냅샷 (스위치 상태)**:  
  - Comfy: `user/default/workflows/ltx23AllInOneWorkflowForRTX_v44_IA2V.json`  
  - agent: `workflows/human/ltx23AllInOneWorkflowForRTX_v44_IA2V.json`  
- **관련**: [ltx23_aio_IA2V_saved_snapshot.md](ltx23_aio_IA2V_saved_snapshot.md) · [ltx23_aio_workflow_routing_analysis.md](ltx23_aio_workflow_routing_analysis.md) · [ltx23_aio_pipeline_integration.md](ltx23_aio_pipeline_integration.md)

---

## 0. 한 줄

이 워크플로는 **고정 원클릭 프리셋이 아니다.**  
사람처럼 **입력 오디오·샷 목적에 맞춰 Trim / Clip Length / 해상도·aspect 를 매번 맞춘 뒤** IA2V 경로로 실행한다.

저장 파일 안의 `Trim [220,10]`, `Clip Length 15`, `Longer Edge 1920`, `16:9` 는 **예시 스냅샷**일 뿐 에이전트 기본값이 아니다.

---

## 1. IA2V 모드란

Orchestrator / mute 기준으로:

| 포트 | 상태 |
|------|------|
| First Frame `[[P:02 Image to Video]]` | ON |
| **Audio input** `[[P:Audio input]]` | ON |
| Last / Mid / V2V | OFF |

서브그래프에서 Audio encode + `SolidMask(0)` + `SetLatentNoiseMask` 경로가 살아 있는 상태가 **Image + Audio to Video**.

---

## 2. 매 실행 전 필수 파라미터 (사람 = 에이전트 동일)

### 2.1 입력 파일

| 슬롯 | 내용 |
|------|------|
| First Frame | 키프레임 PNG (쇼츠면 이미 9:16에 가깝게) |
| Audio | TTS / drive wav·mp3 (대사 구간) |

### 2.2 TrimAudioDuration

| 필드 | 규칙 |
|------|------|
| `start_index` | 쓸 구간의 시작 초. 전체 대자면 **0** |
| `duration` | **실제로 쓸 오디오 길이(초)** |

- 저장본 데모값 `220 / 10` **절대 그대로 쓰지 말 것** (짧은 TTS는 빈 오디오가 됨).  
- 보통: `duration = min(오디오 전체 길이, clip_length)`.

### 2.3 Clip Length · frames · fps

| 항목 | 규칙 |
|------|------|
| fps | AIO distilled 스택 권장 **24** |
| Clip Length (초) | 대사 길이에 맞춤 (쇼츠 한 줄 예: 3~5s, 길면 분할) |
| frames | `≈ ceil(duration_sec * fps)` 후 LTX 규칙(8k+1 등)으로 snap |

**오디오 길이 ≠ 프레임 길이** 로 두면 AV latent 불일치·VRAM 폭주 위험이 있다.  
→ **Trim duration 과 frames/fps 가 같은 시간 축**을 가리키게 한다.

### 2.4 해상도 · Aspect

| 항목 | 사람/에이전트 |
|------|----------------|
| Aspect | 쇼츠 → **9:16** (저장본 16:9 그대로 X) |
| Longer Edge | VRAM·품질 타협. 4090 쇼츠 예: **768~1024** (1920은 무거울 수 있음) |
| work 해상도 (에이전트) | 예: **544×960** 또는 Longer Edge **768~1024** + aspect **9:16** |

저장본 `Longer Edge 1920` + `Clip 15s` 는 고사양·긴 클립용 예시로 취급.

---

## 3. 실행 순서 (체크리스트)

```
1) 키프레임 · 오디오 경로 확정
2) probe 오디오 duration (초)
3) clip_sec = 쓸 구간 길이 (보통 = duration)
4) TrimAudioDuration(start=0, duration=clip_sec)
5) fps=24, frames = snap(clip_sec * 24)
6) aspect/resolution = 포맷(쇼츠 9:16) + VRAM 여유
7) IA2V 스위치 상태 확인 (Image ON, Audio ON, 나머지 OFF)
8) free 이종 엔진 직후면 Comfy free (Moody→LTX 등)
9) 생성 → 결과 오디오가 TTS와 같은지 확인
```

---

## 4. 에이전트 CLI (AIO 워크플로 + 스위치/셀렉트 — 기본)

`ltx23_aio*` / `ltx23_ia2v` 는 **축소 mini 그래프가 아니다.**  
사람용 AIO UI JSON에 **[[P:]] 포트 mute** 를 적용한 뒤 expand 해서 큐한다.

| 단계 | 모듈 |
|------|------|
| UI 로드 | `workflows/human/ltx23AllInOneWorkflowForRTX_v44_IA2V.json` (기본) |
| 모드 스위치 | `lib/ltx_aio_mode_select.py` — Orchestrator 표와 동일 |
| expand | `lib/ltx_aio_ui_expand.py` (subgraph · Get/Set 해소 · NEVER 스킵) |
| 주입 + 실행 | `lib/ltx_aio_workflow_runner.build_aio_switched_api` |

매 실행 주입: 이미지·오디오·**Trim(0, 오디오초)**·**Clip Length**·**Longer Edge**·aspect·seed·프롬프트

```bash
cd F:\ComfyUI_workflows\agent_custom

# 기본 = i2v_audio (Image + Audio 포트 ON)
python scripts/generate_s2v.py --backend ltx23_aio \
  -i stories/EP/keyframes/S02.png \
  -a stories/EP/audio/dialogue/S02_qwen3tts.mp3 \
  -o stories/EP/clips/work/S02_s2v.mp4 \
  --width 544 --height 960 \
  --timeout 1800

# First/Last + Audio
python scripts/generate_s2v.py --backend ltx23_aio_flf_audio \
  -i first.png --last last.png -a drive.wav -o out.mp4
```

| 동작 | 구현 |
|------|------|
| 그래프 | **실 AIO UI + mode mute** (half-res→upscale→2nd pass 포함) |
| Trim | `start=0`, `duration=오디오 길이` |
| Clip Length | `audio + ~1.5s` |
| Longer Edge | `max(width,height)` |
| Aspect | h≥w → **9:16** |
| fps | **24** |
| fallback | `AGENT_LTX_FORCE_LIVE_TEMPLATE=1` (동결 history) / `AGENT_LTX_FORCE_MINI_GRAPH=1` (**비권장**) |

`sageattn is not defined` 는 수동과 동일하게 pytorch fallback — 무시.

---

## 5. 금지 / 주의

1. 저장 JSON 위젯 값 그대로 Queue (Trim 220, 15s, 1920…)  
2. 오디오는 긴데 frames만 짧게 (또는 반대) 방치  
3. Moody I2I 직후 free 없이 LTX 연타 ([comfy_memory…](comfy_memory_and_model_switching.md))  
4. “AIO 저장본 = 에이전트가 이미 완벽 이식”으로 오해 (라우팅 정본 ≠ 무설정 실행)

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초판: IA2V 파라미터 규칙 · 사람/에이전트 동일 운용 · CLI 메모 |
| 2026-07-13 | 기본 러너 = `ltx_aio_workflow_runner` (실 WF 스위치). mini 기본 경로 제거 |
