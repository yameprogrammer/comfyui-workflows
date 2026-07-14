# LTX 2.3 All-in-One → agent_custom 파이프라인 편입

- **작성일**: 2026-07-12  
- **상태**: **⚠️ approx only** — 축소 API 그래프 동작 / **AIO Orchestrator parity 미완**  
- **소스 UI**: `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json`  
- **라우팅 분석 (아카이브)**: [archive/ltx23_debug/ltx23_aio_workflow_routing_analysis.md](archive/ltx23_debug/ltx23_aio_workflow_routing_analysis.md)  
- **IA2V 사용법**: [ltx23_aio_ia2v_agent_usage.md](ltx23_aio_ia2v_agent_usage.md) (Trim·Clip·해상도 매 실행 조정)  
- **관련**: `lib/ltx_s2v.py` · `scripts/generate_s2v.py` · `workflows/agent/ltx23_aio.manifest.json`

---

## 0. 한 줄

사용자 AIO **모드 이름**을 agent 백엔드 alias 로 옮겼고, **LoRA/TE/fps 등 스택만 맞춤**.  
**ComfySwitch / OrchestratorNodeMuter / `[[P:]]` mute / 서브그래프 분기** 는 아직 이식하지 않았다.  
→ Image+Audio 포함 “기능 정합” 은 **미완**. 반드시 라우팅 분석 문서를 볼 것.

---

## 1. 모드 매핑 (approx vs parity)

| AIO 테이블 (Orchestrator 옵션) | agent `--backend` | 입력 | approx | AIO parity |
|--------------------------------|-------------------|------|--------|------------|
| Image to Video | `ltx23_aio_i2v` | `-i first` | △ 축소 I2V | ❌ |
| Image + Audio | `ltx23_aio` | `-i first -a wav` | △ 단순 AV concat | ❌ (Audio input 스위치 경로 아님) |
| First/Last Frame | `ltx23_aio_flf` | `-i first --last last` | △ AddGuide | ❌ |
| First/Last + Audio | `ltx23_aio_flf_audio` | `+ -a wav` | △ | ❌ |
| First/Mid/Last | `ltx23_aio_fml` | `-i --mid --last` | △ | ❌ |
| First/Mid/Last + Audio | `ltx23_aio_fml_audio` | `+ -a` | △ | ❌ |
| Video to Video | `ltx23_aio_v2v` | `-i last_of_prev.png` [ `-a` ] | △ last-frame continue | ❌ (ExtendSampler 아님) |

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
| TE | **`gemma-3-12b-it-UD-Q4_K_XL.gguf`** via `DualClipLoaderGGUF` + text_projection (user AIO 정합; 구 fp8 기본 폐기) |
| FPS | default **24** for aio* |
| 출력 | yuv420p re-encode for players |
| **오디오** | LTX AV decode 음성은 **환청/엉뚱한 대사** 가능 → `generate_s2v`가 **driving/TTS로 트랙 교체** (립 가이드만 LTX) |
| 빌더 | `lib.ltx_s2v.build_ltx_aio_mode_api` |

---

## 4. 아직 안 한 것 (우선순위)

1. **AIO 라우팅 parity** — Orchestrator 옵션 → `[[P:]]` mute → 서브그래프 활성 컷 추출·실행  
   ([routing analysis archive](archive/ltx23_debug/ltx23_aio_workflow_routing_analysis.md) §8)  
2. Text to Video / Text+Audio pure T2V (테이블 `01 …`)  
3. **풀 latent Video→Video ExtendSampler**  
4. Spatial upscale · multi-IC-LoRA 스택  
5. **이종 엔진 전환 free** — [comfy_memory_and_model_switching.md](comfy_memory_and_model_switching.md)

### 4.1 운영 주의 (2026-07-12 사고)

- 스모크(동일 544×960·89f)는 정상.  
- **I2I(ZImage) 연타 직후 free 없이** `ltx23_aio` 체인 → VRAM full + 시스템 RAM ~60GB private thrash → 샘플러 로그 없이 hang.  
- 조치: interrupt → 종료 후 unload free → 메모리 회복. 재실행 전 Comfy free 또는 재시작 권장.

---

## 5. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 문서 PLANNED → MVP i2v_audio |
| 2026-07-12 | **모드 이식**: i2v, flf, flf_audio, fml, fml_audio, v2v(+agent 매핑) |
| 2026-07-12 | I2I→LTX 전환 hang 기록 · 메모리 문서 링크 |
| 2026-07-12 | 상태 **approx only** 로 정정 · 라우팅 분석 문서 링크 (AIO switch parity 미완) |
