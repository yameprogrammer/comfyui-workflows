# Wan Animate 2 — 로컬 (RTX 4090 24GB)

유튜브 [Wan Animate 2 리뷰](https://youtu.be/P3I-w-7CgJs)의 **Wan-Animate-2**(2026-08-07)입니다.
이미 있던 **Wan 2.2 Animate**(포즈 추출 + 캐릭터 스왑)와는 다른 모델입니다.

| | Wan 2.2 Animate (기존) | Wan Animate 2 (이번) |
|---|---|---|
| 모션 입력 | YOLO + ViTPose + SAM2 전처리 | 드라이빙 영상을 **그대로** DiT에 넣음 |
| 배경 | 소스 영상 배경을 유지/교체 | 프롬프트로 **새 배경·카메라** |
| 워크플로 | `character_swap_wan_animate_v2v` | `wan_animate2_motion_transfer` |

## 24GB에서 왜 이 조합인가

공식 bf16은 31GB라 4090에 안 들어갑니다.

| 파일 | 크기 | 24GB |
|---|---|---|
| `wan_animate_2_bf16.safetensors` | 31.3 GB | 불가 |
| `wan_animate_2_int8_convrot.safetensors` | **15.9 GB** | **사용 중** |
| Distill TURBO GGUF Q4_K_M | 10.8 GB | 여유는 더 있음 (커스텀 로더 필요) |

크기가 크다고 느린 게 아닙니다. 속도는 **스텝 수**입니다.

- 이 워크플로: LightX2V LoRA + LCM **6 step**, CFG 1.0
- 캐시는 **CPU / int8** (GPU에 올리면 16GB 모델과 같이 못 씀)
- 해상도 480×832, 81프레임 (~3.4초 @ 24fps)

더 가볍게 가려면 나중에 `realrebelai/Wan-Animate-2_GGUFs` 의 `Distilled/Wan-Animate-2-14B-TURBO-Q4_K_M.gguf` (10.8GB)를 쓰면 됩니다. 단, 기본 GGUF 로더는 `animate2`로 인식 못 해서 모션이 무시됩니다.

## 파일 위치

워크플로

- Workflows 패널: `wan_animate2_motion_transfer` (권장, 평탄화)
- 공식 서브그래프 원본: `wan_animate2_motion_transfer_official` (캐시 CPU로 패치됨)

모델 (`F:\model`)

- `diffusion_models/wan_animate_2_int8_convrot.safetensors`
- `loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors`
- `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` (기존)
- `clip_vision/clip_vision_h.safetensors` (기존)
- `vae/wan_2.1_vae.safetensors` + 별칭 `Wan2_1_VAE_bf16.safetensors`

샘플 입력 (`F:\ComfyUI_data\input`)

- `pink_hair_mech_arms_ref.png`
- `street_dance_drive.mp4`

출력: `F:\ComfyUI_data\output\wan_animate2\WanAnimate2_*.mp4`

## 사용

1. ComfyUI Workflows → `wan_animate2_motion_transfer`
2. 모델 목록이 비면 노드에서 Refresh, 그래도 없으면 ComfyUI 재시작
3. 참조 이미지 / 드라이빙 영상 교체 가능
4. Positive = **외형 + 배경만**. 동작 설명은 Pose prompt
5. Queue

## 품질 팁

- 참조 첫 포즈 ≈ 영상 첫 포즈 (전신↔전신)
- 프롬프트에 움직임을 쓰지 말 것
- 영상이 너무 고fps면 16–24fps로 리샘플
- VRAM 부족 시 480×720 또는 length 49
