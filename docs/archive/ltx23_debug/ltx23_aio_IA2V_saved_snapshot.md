> **ARCHIVED (2026-07-14)** — 운영 SSOT 아님. 인덱스: [../../README.md](../../README.md). 활성 백로그: [../../agent_video_tooling_todo.md](../../agent_video_tooling_todo.md).

# 저장본 분석: `ltx23AllInOneWorkflowForRTX_v44_IA2V.json`

- **경로 (Comfy)**: `ComfyUI/user/default/workflows/ltx23AllInOneWorkflowForRTX_v44_IA2V.json`  
- **복사본 (agent)**: `workflows/human/ltx23AllInOneWorkflowForRTX_v44_IA2V.json`  
- **분석 시각**: 2026-07-12  
- **기계 맵**: `docs/_ltx23_aio_IA2V_saved_diff.json`

---

## 1. 이 저장본이 의미하는 모드

| 포트 | mode | 해석 |
|------|------|------|
| First Frame `[[P:02 Image to Video]]` | **ALWAYS** | I2V 켜짐 |
| **Audio input** `[[P:Audio input]]` | **ALWAYS** | **오디오 입력 켜짐** |
| Last Frame | NEVER | FLF 꺼짐 |
| Mid Frame | NEVER | FML 꺼짐 |
| Video to Video | NEVER | V2V 꺼짐 |

→ 테이블상 **「Image to Video + Audio input」(IA2V)** 상태와 일치합니다.

서브그래프에서도 Audio 태그 노드가 **ALWAYS**:

- `1495` `LTXVAudioVAEEncode [[P:Audio input]]`
- `1496` `SolidMask [[P:Audio input]]` (value=0)
- `1499` `SetLatentNoiseMask [[P:Audio input]]`

---

## 2. 로더 / 스택 (이 저장본)

| 역할 | 설정 |
|------|------|
| TE | **`DualClipLoaderGGUF`** + `gemma-3-12b-it-UD-Q4_K_XL.gguf` + text_projection (fp8 DualCLIP은 BYPASS) |
| UNet | `GGUFLoaderKJ` 경로 (dev Q4 / 스위치) + Power Lora: **fro09 @ 0.9**, upscale IC, OmniNFT 등 |
| Video VAE | `LTX23_video_vae_bf16` |
| Audio VAE | `LTX23_audio_vae_bf16` |
| Clip Length 슬라이더 | **15 초** |
| Longer Edge | **1920** |
| Aspect | **16:9** (저장 위젯 기준; 쇼츠는 UI에서 9:16로 바꿔야 함) |

---

## 3. 오디오 트림 (중요)

루트 `TrimAudioDuration` (id 1792) **ALWAYS**:

```text
widgets = [220, 10]
→ start_index = 220 초, duration = 10 초
```

AIO 데모 음원용으로 보이는 값입니다.  
**우리 TTS(3초 안팎)를 그대로 넣으면 220초부터 자르려 해서 빈/이상 오디오**가 될 수 있습니다.

에이전트가 이 WF를 쓸 때는 반드시:

- `start_index = 0`
- `duration = clip_length` (또는 프레임 수 / fps)

로 **덮어써야** 합니다.

---

## 4. Orchestrator 위젯

| 파일 | widgets |
|------|---------|
| 예전 agent 카피 | `[F, null, F, null, F, T, F, F, F, F]` 등 |
| **IA2V 저장본** | **`[]` 비어 있음** |

스위치 결과는 이미 **노드 mode에 반영**된 상태로 저장된 것으로 보입니다.  
(위젯 배열이 비어도 포트 mode가 IA2V와 맞음.)

---

## 5. 에이전트 축소 그래프와의 차이 (재확인)

| | 이 IA2V 저장본 | 에이전트 mini 그래프 |
|--|----------------|---------------------|
| Orchestrator / mute | 이미 IA2V로 고정 | 없음 |
| Audio encode + **SolidMask0 + SetLatentNoiseMask** | 있음 (ALWAYS) | 한때 잘못 넣었다가 제거 |
| TrimAudioDuration | 있음 (값 주의) | 최근 duration=frames/fps 추가 |
| Longer Edge 1920 / 15s | UI 기본 | 544×960·짧은 프레임 (VRAM 절약) |
| TE | GGUF DualClip | 한때 fp4 safetensors로 변경 |

**전체 서브그래프를 그대로 돌리면** 해상도·15초 설정 때문에 4090에서도 무거울 수 있습니다.  
저장본의 **모드 라우팅(뭐가 ALWAYS인지)** 은 정본으로 쓰되,  
에이전트 실행 시에는 **해상도·clip length·trim** 을 쇼츠용으로 줄여야 합니다.

---

## 6. 다음 작업 제안

1. 이 저장본을 SSOT 스냅샷으로 유지 (`workflows/human/..._IA2V.json`)  
2. API 실행 시 주입:
   - First Frame / Audio 경로 입력
   - Trim: start=0, duration=대사 길이
   - Clip Length / Longer Edge / Aspect = 쇼츠 프리셋 (예: 9:16, 768~1024 long edge, 3~5s)
3. 전체 206노드 실행 vs 활성 컷만 추출 실행 중 택일 (VRAM)

---

## 7. 한 줄

**저장본은 Image+Audio(IA2V)로 올바르게 켜진 상태**입니다.  
특히 Audio 포트·서브그래프 Audio 인코드/마스크가 ALWAYS.  
다만 **Trim 220/10** 과 **15s·1920** 은 쇼츠 TTS용으로 반드시 재설정해야 합니다.

