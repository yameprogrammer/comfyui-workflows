# Wan 2.2 워크플로 구조 리서치 · 4090 효율 설계

- **작성일**: 2026-07-18  
- **환경 가정**: RTX 4090 24GB · Windows ComfyUI · agent_custom 공장  
- **관련**: [wan22_workflow_map.md](wan22_workflow_map.md) (공장 정리 맵) · [wan22_i2v_speed_research.md](wan22_i2v_speed_research.md) · [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md) · [workflows/human/wan22/AGENT_GUIDE.md](../workflows/human/wan22/AGENT_GUIDE.md)  
- **상태**: 리서치 SSOT (구현 변경 없음 — 권고만) · 공장 맵은 별도 map 문서

---

## 0. 한 줄 요약

**Wan 2.2 A14B의 “효율 본선” 구조는 항상 같다.**

```text
High-noise expert (모션·구도) → Low-noise expert (디테일·텍스처)
  + High/Low 각각 lightx2v(Lightning) distill LoRA
  + 총 4~8 step, CFG≈1, sageattn
  + GGUF Q4~Q5 (24GB) 또는 FP8
  + work 해상도 480–720 장변 · 짧은 클립 · BlockSwap 상황 조절
  + TeaCache/MagCache 는 품질 리스크 → 본선 off
```

커뮤니티·공식·YouTube가 수렴하는 효율 그래프는 **“듀얼 엑스퍼트 시퀀셜 + 4step distill”** 이고,  
우리 공장 `backend=wan22` 는 이미 이 뼈대를 갖췄다.  
**품질 본선 I2V는 LTX 2.3** (로컬 A/B 2026-07-17). Wan은 **모션 무게·텍스처·카메라 제어·LoRA/NSFW 에코** 가 필요할 때 쓰는 **2차 레인**.

---

## 1. 아키텍처 (학술·공식)

### 1.1 MoE: High-noise / Low-noise

Alibaba **Wan2.2-A14B** 계열은 diffusion denoising 타임스텝을 둘로 나눈 **Mixture-of-Experts** 다.

| Expert | 역할 | 대략 구간 |
|--------|------|-----------|
| **High-noise** | 전체 레이아웃, 큰 모션, 카메라 골격 | 초반 (높은 노이즈 / 낮은 SNR) |
| **Low-noise** | 디테일, 텍스처, 미세 보정 | 후반 (낮은 노이즈) |

- 각 엑스퍼트 ≈ **14B**, 총 파라미터 ≈ **27B** 이지만 **스텝당 활성은 14B 하나** (추론 비용 ≈ 단일 14B).  
- 전환점 `t_moe` 는 SNR 기반 (공식: `SNR_min` 의 절반 근처).  
  실무 Comfy에서는 **start/end step 경계** 또는 **sigma boundary** (`i2v_A14B.boundary ≈ 0.900` 등) 로 표현.  
- 출처: [Wan-AI HF model card](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B), [ComfyUI Wan2.2 docs](https://docs.comfy.org/tutorials/video/wan/wan2_2), DeepLearning.AI The Batch 해설.

### 1.2 제품 라인 (공식 Comfy)

| 모델 | 용도 | 24GB 현실 |
|------|------|-----------|
| **I2V-A14B** | 키프레임→클립 (공장 메인 관심) | GGUF/FP8 + lightx2v 필수급 |
| **T2V-A14B** | 텍스트→영상 | 동일 VRAM 압력 |
| **TI2V-5B** | 하이브리드 경량 | 저VRAM·초안용 (품질 본선 아님) |
| **FLF2V** | first+last frame | I2V와 동일 듀얼 로드 + end image |

### 1.3 Distill: LightX2V / Lightning (Phased DMD)

[ModelTC / lightx2v Wan2.2-Lightning](https://github.com/ModelTC/Wan2.2-Lightning):

- **4 NFE (4 steps)** · **CFG trick 불필요** (CFG=1) → 주장 최대 ~**20×** vs 풀 스텝 베이스  
- High/Low **각각** 전용 distill LoRA (또는 체크포인트)  
- 권장 재현 힌트 (이슈·README 합의): **Euler 계열 + shift≈5, CFG=1, steps=4**, LoRA strength 1.0  
- 한계: **극단 모션** 에서 아티팩트·방향 반전 등 (공식 badcase)

학술 기반: **Phased DMD** (distillation 계열; lightx2v T2V V2 노트).

---

## 2. 커뮤니티가 수렴한 “효율 워크플로 구조”

### 2.1 표준 그래프 토폴로지 (거의 모든 효율 템플릿)

```text
[umt5 / T5 text encode] ──► text embeds
[start image] ──► Wan I2V encode (CLIP-vision 계열 포함 가능)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
  HighNoise UNet              LowNoise UNet
  + high lightx2v LoRA        + low lightx2v LoRA
  + BlockSwap (optional)      + BlockSwap
        │                           │
        ▼                           ▼
  Sampler pass A              Sampler pass B
  (high steps / end@bound)    (start@bound / end@total)
        │                           │
        └──────────► latent ────────┘
                      │
                      ▼
                 VAE decode → VideoCombine
```

**필수 축 5개**

1. **Dual model load** (High + Low) — 단일 UNet으로 “Wan2.2 A14B 정석”이 아님  
2. **Dual LoRA** (high/low distill 쌍)  
3. **Boundary** (steps//2 또는 SNR/sigma 스위치)  
4. **CFG≈1** when lightx2v on  
5. **Attention accel** (SageAttention) + **VRAM swap/offload**

### 2.2 세 가지 효율 티어 (커뮤니티 관행)

| 티어 | steps (high+low) | 해상도 | 용도 | 비고 |
|------|------------------|--------|------|------|
| **Lightning pure** | **4** (2+2) | 480p-class | 초고속 스카우트 | 공식 lightx2v 재현; 모션 약할 수 있음 |
| **Work / daily** | **6–8** (3+3 ~ 4+4) | 540–720 long edge | 에피소드 work | YouTube CG Pixel: 4 가능, **8 권장** for quality |
| **Hero / LoRA-heavy** | **10–12** (예: 4 high + 6–8 low) | 720p | 히어로·스타일 LoRA | Civitai favorites: low에 더 많은 step |

### 2.3 샘플러·스케줄 합의 (2025 후반–2026)

| 소스 | 설정 |
|------|------|
| lightx2v 공식 힌트 | Euler, shift=5, CFG=1, 4 step |
| Civitai “workflow favorites” | **res_multistep / sgm_uniform**, CFG=1, high 4 / low 6–8 |
| Kijai wrapper 기본 다수 | dpm++_sde 또는 uni_pc 계열, shift 5–8 |
| YouTube (Lightx2v 튜토리얼) | high LoRA strength를 1.0→**0.3** 로 낮춰 슬로모/과다 distill 완화 시도 다수 |
| HF discussions | 모션 개선 임시책: high LoRA **0.6–0.8**, low **1.0**, CFG high 2–3.5 / low 1, **8 steps (4+4)** |

**실무 결론:**  
- distill on → **CFG 1 고정**이 기본. CFG 올리면 종종 블러·불안정.  
- 샘플러는 **한 패밀리로 A/B** 할 것 (res_multistep vs dpm++_sde vs euler). “커뮤니티 만능 하나”는 없음.  
- **High/Low step 비대칭** (예: 4+8) 은 style LoRA를 low에만 실을 때 유리.

### 2.4 VRAM / 4090 실전 노하우

| 기법 | 효과 | 리스크 |
|------|------|--------|
| **GGUF Q4_K_M / Q5** | 24GB에서 A14B dual 가능 | Q4 디테일·텍스처 손실 |
| **FP8 scaled** | GGUF보다 품질↑, VRAM↑ | OOM 시 swap↑ |
| **BlockSwap / offload** | OOM 방지 | 속도 ↓ (로컬: swap20→0 ≈ −37% 시간 이득 스모크) |
| **SageAttention** | 스텝 시간 ↓ | 설치·수치 이슈 드묾 |
| **TeaCache / MagCache** | 큰 가속 보고 | **우리 팩토리 육안 탈락** (grain) → 본선 off |
| **TorchCompile** | 반복 배치 2샷부터 | 첫 런 워밍업 |
| **frames↓ + 후 RIFE** | 긴 클립 비용 절감 | 보간 위화 |
| **TI2V-5B** | 진짜 저VRAM | 품질·에코 약함 |

24GB에서 “풀 FP16 dual 14B + 720p + 긴 프레임” 은 비현실적.  
**효율 = 양자화 + distill + 짧은 work 해상도 + swap 튜닝.**

### 2.5 LTX 2.3 대비 (외부 + 로컬 A/B)

| 축 | Wan 2.2 | LTX 2.3 |
|----|---------|---------|
| 속도 | 1× (기준) | 커뮤니티 **~10–18×** 체감 (조건 의존) |
| 텍스처/시네마 무게 | 종종 우위 (Reddit/블로그) | 부드럽고 빠름, 가끔 floaty |
| 모션 (로컬 S01 A/B) | micro-wobble / freeze-adjacent | **living take 승** |
| 오디오 | 보통 후처리 | 네이티브 오디오 강점 |
| LoRA / NSFW / 에코 | **두꺼움** | 성장 중 |
| 공장 기본 | fallback | **default I2V** |

외부 블로그는 “프로토타입 LTX → 마감 Wan” 을 권하는 경우 많음.  
**우리 로컬 A/B는 그 반대 결론 (LTX work 품질 승)** — 시드·샷·프롬프트 한 케이스지만 **정책에 반영됨**.  
→ 공장은 **LTX 본선 + Wan 선택적 재시도** 가 합리적.

---

## 3. 우리 환경 매핑 (있는 것 / 없는 것)

### 3.1 이미 올바른 뼈대

| 구성 | 경로 / 값 |
|------|-----------|
| Dual GGUF High/Low Q4_K_M | `generate_i2v.py` inject |
| lightx2v HIGH/LOW 4step LoRA rank64 | `Wan2.2\Wan_2_2_I2V_A14B_*_lightx2v_4step_*` |
| steps 6, boundary = steps//2 | deliver 프로필 |
| CFG schedule / cfg=1 | API preset |
| sageattn 기본 | `AGENT_WAN_ATTENTION` |
| BlockSwap CLI/프로필 | preview 8 / deliver·quality 10 |
| Tea/Mag **기본 off** | 품질 게이트 후 확정 |
| profiles preview / deliver / quality | 4 / 6 / 8 steps |
| FLF | `wan22_flf` + LTX flf 본선 |
| Human pack | `workflows/human/wan22/*` (i2v, flf, face, upscale, animate) |
| Easy MoE UI | `generate_yaw_wan22` (YAW v0.50) |
| 정책 | `video_backends.json` quality default = LTX |

### 3.2 커뮤니티 “최고 효율” 대비 갭

| 갭 | 커뮤니티 관행 | 우리 상태 | 우선도 |
|----|---------------|-----------|--------|
| **Scheduler** | res_multistep/sgm_uniform 또는 euler+shift5 | **dpm++_sde + shift=8** 고정 | P2 A/B |
| **LoRA strength 비대칭** | high 0.3–0.8 / low 1.0–1.5 | 양쪽 **1.0 고정** 추정 | P2 (모션 약할 때) |
| **비대칭 step** | 4 high + 6–8 low | **항상 steps//2** | P2 (LoRA 쓸 때) |
| **GGUF 티어** | Q5/Q6 quality lane | **Q4 only** | P2 hero |
| **T5** | 종종 fp8 | bf16 + offload | P3 |
| **TorchCompile** | 배치 시 | 노드 off | P3 |
| **lightx2v V2 / MoE distill 파일명** | 최신 Seko/MoE rank 변형 | `260412` rank64 고정 | 버전 추적 |
| **Native Comfy vs Kijai** | 둘 다 공존 | **Kijai WanVideoWrapper API** | 유지 (에이전트 친화) |
| **3-pass polish** | low 끝 2step LoRA 없이 클린업 | 없음 | P3 실험 |
| **TI2V-5B draft** | 초저VRAM | 미연동 | 불필요 (LTX draft 있음) |

### 3.3 공장 내 Wan 역할 (도구 박스)

```text
[에피소드 기본 모션]     → LTX AIO i2v / flf / s2v
[Wan 명시 요청 / 폴백]   → generate_i2v --backend wan22
[FLF Wan 실험]          → --backend wan22_flf
[YAW 쉬운 MoE UI]       → generate_yaw_wan22
[얼굴 스미어 후처리]     → wan22_face_enhance (FINISH 레인)
[Wan 확산 업스케일]     → wan22_upscale (opt-in, SeedVR2/RTX VSR 본선 아님)
[댄스 모션 리타겟]       → wan22_animate (planned wire)
```

---

## 4. 우리 환경 “가장 효율적인” 권장 구조

### 4.1 에이전트 기본 레시피 (변경 없이 지금 쓸 것)

```bash
# 폴백 / 명시 Wan I2V — deliver 프로필 (이미 효율 스택)
python scripts/generate_i2v.py -i KEY.png -p "MOTION ONLY..." -o out.mp4 \
  --backend wan22 --profile deliver

# 초고속 스카우트
python scripts/generate_i2v.py ... --backend wan22 --profile preview

# 히어로 모션 (Wan으로 갈 때)
python scripts/generate_i2v.py ... --backend wan22 --profile quality

# VRAM 여유 시 속도
python scripts/generate_i2v.py ... --backend wan22 --block-swap 0

# OOM / 긴 클립
python scripts/generate_i2v.py ... --backend wan22 --block-swap 20
```

| 노브 | 권장 (4090) |
|------|-------------|
| Model | High/Low **Q4_K_M** (현행) · hero 시 Q5 후보 |
| Distill | lightx2v high+low **on**, strength 1.0 출발 |
| Steps | preview 4 / deliver 6 / quality 8 |
| Boundary | steps//2 (현행) |
| CFG | **1** |
| Attention | **sageattn** |
| Cache | **none** |
| BlockSwap | 10 출발 · 짧게 0 · 길게 20 |
| Resolution | work 540-class (쇼츠 544×960) · 납품은 upscale 레인 |
| Frames | 짧은 샷 우선 (4n+1); 긴 establishing은 LTX 또는 분할 |
| Prompt | **모션/카메라 only** (generation-prompt skill · I2V 규칙) |

### 4.2 “효율 그래프” 규범 구조 (설계 기준)

에이전트·휴먼 모두 이 레이어를 깨지 말 것.

```text
Layer A  MODELS     High GGUF + Low GGUF (or FP8 pair)
Layer B  DISTILL    lightx2v HIGH + LOW LoRA (pairs only)
Layer C  MEMORY     BlockSwap + load offload (not quality hacks)
Layer D  SAMPLE     dual WanVideoSampler + shared steps/boundary
Layer E  ATTN       sageattn (sdpa fallback)
Layer F  IO         I2V encode ← image · VAE · VHS combine
Layer G  OPTIONAL   FLF end_image | face_enhance post | upscale post
```

**금지 (비효율·품질 함정)**

- distill 없이 4-step  
- Tea/Mag를 deliver 기본으로  
- High에 Wan2.1 스타일 LoRA 과다 (커뮤니티: high는 2.2 high 전용)  
- work 1080p+ dual 14B로 “한 번에 납품” (업스케일 레인 무시)  
- freeze-pad로 짧은 I2V 늘리기 (Agents.md hard ban)

### 4.3 언제 Wan / 언제 LTX (공장 의사결정)

| 상황 | 선택 |
|------|------|
| 에피소드 기본 work 클립 | **LTX** `ltx23_aio_i2v` |
| 빠른 변주·오디오 포함 초안 | **LTX** |
| LTX 모션이 가볍거나 카메라 무게 부족 | **Wan** `--backend wan22` 재시도 |
| 텍스처·실사 클로즈업 디테일 | Wan quality 프로필 후보 |
| 두꺼운 Wan LoRA / 특수 장르 | Wan (+ 비대칭 low steps 실험) |
| 저VRAM 강제 | Wan Q4 + swap20 또는 LTX quant |
| First–last bridge 품질 본선 | **LTX flf**; Wan flf = 실험 |
| 댄스 포즈 리타겟 | `wan22_animate` (장르 도구) |

### 4.4 개선 백로그 → 구현 상태 (2026-07-18)

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| **W-A** | scheduler CLI (`--wan-scheduler` / `--wan-shift`) | ✅ | 기본 그래프는 유지; euler 시 shift auto 5 |
| **W-B** | LoRA strength CLI | ✅ | `--lora-strength-high/low` |
| **W-C** | 비대칭 boundary | ✅ | `--wan-boundary` |
| **W-D** | Q5 옵션 | ✅ CLI | 디스크에 Q5 없으면 로드 실패 — 파일 추가 후 사용 |
| **W-CFG** | High CFG scalar=1 (스케줄 링크 제거) | ✅ | 프리셋 정리 + inject 강제 |
| **W-ROLE** | High/Low 로더 = 샘플러 배선 판별 | ✅ | `lib/wan22_i2v_inject.py` |
| **W-DEAD** | dead CLIP 경로 제거 | ✅ | API 프리셋 + runtime strip |
| **W-E** | lightx2v 최신 MoE distill 파일 동기화 | ⬜ | 파일 교체+재벤치 |
| **W-F** | TorchCompile profile=batch | ⬜ | 다컷 루프 |
| **W-G** | T5 fp8 | ⬜ | 로드 약간 |

**코드:** `lib/wan22_i2v_inject.py` · `scripts/generate_i2v.py`  
**맵:** [wan22_workflow_map.md](wan22_workflow_map.md) §3  
**기본값 변경은 로컬 동일 키프레임 A/B 후에만.**  
(이미 LTX 본선이므로 Wan 튜닝이 전체 에피소드 처리량을 바꾸진 않음.)

---

## 5. YouTube / 튜토리얼에서 반복되는 실수

1. **단일 모델만 로드**하고 “Wan2.2” 라 부름 → MoE 이득 상실  
2. lightx2v 없이 steps=4 → 미완성/블러  
3. CFG를 3.5+ 로 올린 채 distill 유지 → 불안정  
4. Sage 없이 “느리다”고만 불평  
5. 720p+81f+dual 14B+swap0 로 OOM 루프  
6. High/Low LoRA 파일을 뒤바꿔 장착  
7. TeaCache 켠 채 “품질 괜찮겠지” (우리 벤치: 탈락)

---

## 6. 참고 소스 (리서치 시점 2026-07-18)

| 종류 | 링크 / 위치 |
|------|-------------|
| 공식 Comfy 튜토리얼 | https://docs.comfy.org/tutorials/video/wan/wan2_2 |
| 아키텍처 (HF / GitHub Wan2.2) | Wan-AI/Wan2.2-T2V-A14B model card MoE 절 |
| Distill | https://github.com/ModelTC/Wan2.2-Lightning · lightx2v HF |
| Comfy LightX2V 통합 노트 | blog.comfy.org Wan2.2 Fun + Lightning |
| Civitai favorites | civitai.com/articles/23316 (high 4 / low 6–8, res_multistep) |
| LTX vs Wan 실사용 | ltxworkflow.com / Reddit r/comfyui 2026 스레드 |
| 로컬 속도 벤치 | docs/wan22_i2v_speed_research.md |
| 로컬 품질 A/B | docs/wan_vs_ltx_i2v_ab_2026-07-17.md |
| YouTube 계열 | CG Pixel Sage+lightx2v · FoxtonAI Lightx2v settings · ArtOfficial dual-sampler 해설 |

---

## 7. 결론 (에이전트용)

1. **Wan2.2 효율 구조의 정석 = Dual expert + dual lightx2v + 4–8 step CFG1 + sage + GGUF + 상황별 BlockSwap.**  
2. **우리 `wan22` 백엔드는 이미 정석 위에 있다** (추가 “마법 그래프” 불필요).  
3. **에피소드 본선은 LTX**; Wan은 폴백·카메라/텍스처/LoRA 특수 레인.  
4. 다음 품질 레버는 구조 교체가 아니라 **scheduler / LoRA strength / Q5 / 비대칭 steps** 의 작은 A/B.  
5. Face/Upscale/Animate 는 **생성 본체와 분리된 FINISH·장르 도구**로 유지 (All-in-one 거대 그래프 재도입 금지).
