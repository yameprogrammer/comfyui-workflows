# LTX 2.3 All-in-One → agent_custom 파이프라인 편입

- **작성일**: 2026-07-12  
- **상태**: **✅ multi-mode READY**  
- **소스 UI**: `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json`  
- **관련**: `lib/ltx_s2v.py` · `scripts/generate_s2v.py` · `workflows/agent/ltx23_aio.manifest.json`

---

## 0. 한 줄

사용자 AIO 테이블의 주요 영상 모드를 **agent 백엔드 alias** 로 이식했다.  
전체 Orchestrator UI는 돌리지 않고, 동일 계열 LTX 그래프 + AIO LoRA/24fps 로 구현.

---

## 1. 이식된 모드 (요청 반영)

| AIO 테이블 | agent `--backend` | 입력 | 상태 |
|------------|-------------------|------|------|
| Image to Video | `ltx23_aio_i2v` | `-i first` | ✅ |
| Image + Audio | `ltx23_aio` | `-i first -a wav` | ✅ |
| First/Last Frame | `ltx23_aio_flf` | `-i first --last last` | ✅ |
| First/Last + Audio | `ltx23_aio_flf_audio` | `+ -a wav` | ✅ |
| First/Mid/Last | `ltx23_aio_fml` | `-i --mid --last` | ✅ |
| First/Mid/Last + Audio | `ltx23_aio_fml_audio` | `+ -a` | ✅ |
| Video to Video | `ltx23_aio_v2v` | `-i last_of_prev.png` [ `-a` ] | ✅ **agent 매핑** |

**V2V 주의:** 에이전트 V2V는 AIO의 풀 latent `ExtendSampler` 연장이 아니라,  
**이전 클립 마지막 프레임을 first로 이어서 생성** (원테이크 last-frame 체인과 동일 철학).  
풀 인코드 연장은 후속.

또는 `--backend ltx23_aio --ltx-mode flf_audio` 처럼 **mode 오버라이드** 가능.

---

## 2. CLI 예시

```bash
cd F:\ComfyUI_workflows\agent_custom

# Image only
python scripts/generate_s2v.py --backend ltx23_aio_i2v -i first.png -o out.mp4 --width 544 --height 960 --frames 73

# Image + Audio (대사)
python scripts/generate_s2v.py --backend ltx23_aio -i first.png -a drive.wav -o out.mp4 --width 544 --height 960

# First / Last (원테이크 브리지)
python scripts/generate_s2v.py --backend ltx23_aio_flf -i first.png --last last.png -o bridge.mp4 --frames 49

# First / Last + Audio
python scripts/generate_s2v.py --backend ltx23_aio_flf_audio -i first.png --last last.png -a drive.wav -o out.mp4

# First / Mid / Last
python scripts/generate_s2v.py --backend ltx23_aio_fml -i first.png --mid mid.png --last last.png -o out.mp4 --frames 73

# V2V continue (last frame of previous clip)
python scripts/generate_s2v.py --backend ltx23_aio_v2v -i prev_last.png -a drive.wav -o cont.mp4

# last-frame chain default backend = ltx23_aio
python scripts/chain_si2v_last_frame.py -e EP --backend ltx23_aio_flf_audio   # if wiring last/first pair
```

---

## 3. 구현 메모

| 항목 | 내용 |
|------|------|
| First 프레임 | `LTXVImgToVideoInplace` on empty latent |
| Mid / Last | `LTXVAddGuide` at `frame_idx` mid / length-1 |
| Audio | `LTXVAudioVAEEncode` + `LTXVConcatAVLatent` when mode has audio |
| LoRA | AIO dynamic fro09 @ **0.9** |
| FPS | default **24** for aio* |
| 출력 | yuv420p re-encode for players |
| 빌더 | `lib.ltx_s2v.build_ltx_aio_mode_api` |

---

## 4. 아직 안 한 것

- Text to Video / Text+Audio pure T2V  
- OrchestratorNodeMuter 자동 스위치  
- **풀 latent Video→Video ExtendSampler** (원본 영상 전체 인코드 후 연장)  
- Spatial upscale · multi-IC-LoRA 스택  

---

## 5. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 문서 PLANNED → MVP i2v_audio |
| 2026-07-12 | **모드 이식**: i2v, flf, flf_audio, fml, fml_audio, v2v(+agent 매핑) |
