# 이미지·영상 업스케일 리서치 및 에이전트 설계

- **작성일**: 2026-07-11  
- **목표**: RTX **4090 (24GB)** 로컬에서 **선택 해상도 ~4K** 까지, 품질/속도 단계별 업스케일  
- **범위**: 웹·공식 문서·Reddit·X(SNS)·GitHub·로컬 인벤토리

---

## 1. 한 줄 결론 (에이전트 정책)

| 우선순위 | 용도 | 엔진 | 비고 |
|----------|------|------|------|
| **P0 품질** | 키프레임·히어로 이미지, 최종 클립 | **SeedVR2 7B** (로컬 보유) | 생성형 디테일·시간 일관성 강함 |
| **P0 속도** | 프리뷰·배치 반복 | **RTX Video Super Resolution** 또는 **ESRGAN 4x** | 초고속 / 안정 |
| **P1 단계 납품** | work → 1080 → (선택) 4K | 동일 엔진 **2-pass** | 한 번에 4K보다 안정적이라는 커뮤니티·Comfy 공식 팁 |
| **비권장(로컬 미보유/API)** | Magnific, Topaz, HitPaw 클라우드 | 품질 참고용 | 로컬 에이전트 SSOT 밖 |

**불변 규칙**

1. I2V/T2I는 **work 해상도**에서 돌리고, 업스케일은 **마감 층**.  
2. 종횡비는 **format 프로필**과 동일 유지 (16:9 / 9:16 / 4:3 / 3:4 …).  
3. 납품 픽셀은 프리셋으로 선택: **1080 / 1440 / 2160(4K)** 짧은 변 기준.  
4. AI 아티팩트(손·얼굴 붕괴)는 **업스케일 전에 고친다** — 업스케일이 구조 버그를 해결한다고 가정하지 말 것.

---

## 2. 소스별 리서치 요약

### 2.1 공식 / 벤더

| 소스 | 핵심 |
|------|------|
| **[ComfyUI Blog – Upscaling Handbook](https://blog.comfy.org/p/upscaling-in-comfyui)** (2026-02) | Image: SeedVR2·Magnific·HitPaw 등. Video: 품질=SeedVR2/HitPaw, 속도=FlashVSR. AI 영상은 **cleanup → 1080 → 4K 단계** 권장. 10s 720p 벤치: FlashVSR ~41s(1080), SeedVR2 ~312s(5090). |
| **[Comfy docs – video upscale](https://docs.comfy.org/tutorials/utility/video-upscale)** | 동일: fix → 1080 → gradual 4K. |
| **[numz/SeedVR2](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler)** | 이미지+영상 통합. `resolution`=짧은 변. `batch_size`는 **4n+1**. 4090: FP16/FP8 7B 품질 레인, 저VRAM은 GGUF+BlockSwap. |
| **ComfyUI native SeedVR2** (PR #14424, X 2026-07) | 코어 내장·int8 가속 논의. 우리 로컬은 아직 **custom_nodes seedvr2_videoupscaler** 중심. |
| **NVIDIA RTX VSR in ComfyUI** (공식 X) | 1K→4K 초고속 Tensor 코어. 커뮤니티: 빠른 대신 블러 입력·디테일에서 SeedVR2에 짐. |

### 2.2 Reddit / 커뮤니티

| 스레드 요지 | 함의 |
|-------------|------|
| SeedVR2가 **이미지 업스케일로도 SUPIR/LDSR 이상**이라는 평가 다수 | 사진 복원·AI 인물 디테일에 유리 |
| 7B FP8 vs FP16: FP8이 속도/품질 스윗스팟 의견 vs 개발자 FP16 권장 혼재 | 4090에서는 **기본 FP8 7B, 히어로는 FP16** |
| batch_size 높게 잡으면 OOM (5090에서도 7B 보고 있음) | 영상: batch 1→5→9 계단, 실패 시 타일/오프로드 |
| Wan 영상 업스케일: USDU+detailer vs 저 denoise t2v 논쟁 | 우리 스택은 **모션 확정 후 SeedVR2 마감**이 단순·안정 |
| “입력 깨끗하면 RTX, 블러하면 SeedVR2” (FB ComfyUI 그룹) | **tier 분기 휴리스틱** |

### 2.3 X / SNS

| 신호 | 함의 |
|------|------|
| @ComfyUI: RTX VSR Day-0 | 로컬 고속 레인 정당화 |
| SeedVR2 네이티브 환영 + 디테일 비교 논쟁 (JP 요약 계정) | 커스텀 노드 품질 레인 유지 가치 |
| Krea/Z-Image 워크플로에 SeedVR2 인라인 업스케일 유행 | Moody/Z-Image 키프레임 → SeedVR2 경로 자연스러움 |
| LTX/Wan 클립 후 RTX 업스케일 사례 | I2V work-res 후 고속 마감 패턴 검증 |

### 2.4 YouTube / 튜토리얼 컨센서스

- SeedVR2.5 vs Topaz: 오픈소스 품질 경쟁력, 특히 AI 생성 클립.  
- SeedVR2 vs SDXL tiled: **4K fidelity는 SeedVR2**.  
- 기본 권장 타깃 짧은 변 **1080**; 4K는 히어로/최종 마스터.  
- 영상 16s / 4090 대략 10–12분 사례(설정 의존).

### 2.5 로컬 PC 인벤토리 (실측)

| 항목 | 상태 |
|------|------|
| GPU | **RTX 4090** (torch CUDA OK) |
| SeedVR2 노드 | `custom_nodes/seedvr2_videoupscaler` |
| SeedVR2 가중치 | `models/SEEDVR2/seedvr2_ema_7b_fp16` + **fp8 mixed**, `ema_vae_fp16` |
| SeedVR2 CLI | `inference_cli.py` (`--resolution`, `--dit_model`, batch, VAE tile…) |
| RTX VSR | Comfy 노드 **`RTXVideoSuperResolution`** 로드됨 |
| ESRGAN 계열 | RealESRGAN_x4plus, 4xRealWebPhoto_v4_dat2, Nomos, Remacri, AnimeSharp… |
| UltimateSDUpscale | 설치됨 (확산 타일 — 모델 의존, 2차) |
| FlashVSR | Wavespeed 노드(API 키) — **로컬 기본 경로에서 제외** |
| frame-interpolation | 설치됨 (업스케일 후 RIFE 등 후속) |

---

## 3. 품질 축 정리 (에이전트 선택 가이드)

```text
속도 ──────────────────────────────────────── 품질/복원
ESRGAN 4x    RTX VSR ULTRA    SeedVR2 7B FP8    SeedVR2 7B FP16
(프리뷰)      (클린 소스 고속)   (기본 납품)        (히어로/4K 마스터)
```

| 입력 상태 | 추천 |
|-----------|------|
| work 클립 깨끗, 빠른 확인 | `rtx_vsr` 또는 `esrgan` |
| AI 생성 키프레임·인물 디테일 | `seedvr2` (이미지 batch=1) |
| AI I2V 클립 납품 | `seedvr2` + batch 5~9 + color lab |
| 심하게 뭉개진 소스 | SeedVR2 복원; 필요 시 사전 denoise/edit |
| 애니/라인아트 | ESRGAN `4x-AnimeSharp` 또는 SeedVR2 A/B |

---

## 4. 해상도 프리셋 (선택 가능, 최대 4K)

짧은 변 기준 (SeedVR2 `resolution` 과 동일 철학). format의 종횡비로 가로·세로 유도.

| 프리셋 ID | 짧은 변 | 예 16:9 | 단계 |
|-----------|---------|---------|------|
| `deliver_1080` | 1080 | 1920×1080 | 기본 납품 |
| `deliver_1440` | 1440 | 2560×1440 | 중간 |
| `deliver_2160` / **4K** | 2160 | 3840×2160 | 선택 마스터 |
| `deliver_720` | 720 | 1280×720 | 저부하 프리뷰 |

9:16이면 1080→1080×1920, 2160→2160×3840.

**2-pass 권장 (4K)**  
`work → deliver_1080 (seedvr2) → deliver_2160 (seedvr2 또는 rtx)`  
한 번에 work→4K 가능하나 VRAM·시간·아티팩트 리스크↑.

---

## 5. 에이전트 아키텍처

```text
scripts/upscale_image.py
scripts/upscale_video.py
lib/upscale_backends.py
upscale_backends.json          # 엔진·프리셋·4090 프로파일 SSOT
workflows/agent/
  UPS-image-esrgan.json        # (참고/UI) API는 코드 생성 가능
  UPS-video-rtx.json
  UPS-image-seedvr2.json       # SeedVR 예제 기반
  UPS-video-seedvr2.json
```

### 5.1 백엔드 ID

| ID | 구현 | 매체 |
|----|------|------|
| `esrgan` | Comfy API: UpscaleModelLoader + ImageUpscaleWithModel + ImageScale | image / video frames |
| `rtx_vsr` | Comfy API: RTXVideoSuperResolution | image / video frames |
| `seedvr2` | SeedVR2 **CLI** (portable python) 또는 추후 native 노드 | image / video |
| `seedvr2_max` | 동일, DiT=7B fp16 + VAE tile for 4K | hero |

### 5.2 CLI 계약

```bash
# 이미지 → 1080 짧은 변 (format 비율 유지)
python scripts/upscale_image.py -i key.png -o key_1080.png --preset deliver_1080 --backend seedvr2

# 영상 work → 4K
python scripts/upscale_video.py -i work.mp4 -o deliver_4k.mp4 --preset deliver_2160 --backend seedvr2 --two-pass

# 고속
python scripts/upscale_video.py -i work.mp4 -o preview.mp4 --preset deliver_1080 --backend rtx_vsr
```

### 5.3 4090 프로파일 (초기값)

```json
{
  "seedvr2_quality": {
    "dit_model": "seedvr2_ema_7b_fp8_e4m3fn_mixed_block35_fp16.safetensors",
    "vae_model": "ema_vae_fp16.safetensors",
    "batch_size": 5,
    "blocks_to_swap": 0,
    "vae_tiled_above_short_edge": 1440
  },
  "seedvr2_max": {
    "dit_model": "seedvr2_ema_7b_fp16.safetensors",
    "batch_size": 1,
    "vae_encode_tiled": true,
    "vae_decode_tiled": true
  },
  "esrgan_model": "4xRealWebPhoto_v4_dat2.pth",
  "rtx_quality": "ULTRA"
}
```

---

## 6. 구현 티켓

| ID | 내용 | 상태 |
|----|------|------|
| U0 | 본 리서치·설계 문서 | ✅ |
| U1 | `upscale_backends.json` + `lib/upscale_backends.py` | ✅ |
| U2 | `upscale_image.py` (esrgan / rtx / seedvr2) | ✅ |
| U3 | `upscale_video.py` (+ two-pass 4K) | ✅ |
| U4 | agent 워크플로 JSON 스냅샷 + catalog | ⬜ (API는 코드 생성; SeedVR 예제 로컬 노드 패키지 보유) |
| U5 | delivery 문서·Rule 연동 | ✅ 문서/CLI; 장기 벤치 로그는 실측 시 갱신 |

---

## 7. 참고 링크

- https://blog.comfy.org/p/upscaling-in-comfyui  
- https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler  
- https://docs.comfy.org/tutorials/utility/video-upscale  
- Reddit: r/StableDiffusion SeedVR2 image/video threads (2025–2026)  
- X: @ComfyUI RTX VSR / native SeedVR2 mentions  

로컬 경로: `F:\ComfyUI_windows_portable\ComfyUI\models\SEEDVR2\`, `custom_nodes\seedvr2_videoupscaler\`
