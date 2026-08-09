# LTX 2.3 얼굴 붕괴 완화 (I2V)

- **작성**: 2026-07-17  
- **관련**: [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md) · AIO Power Lora node 211  

## 왜 무너지나

LTX I2V는 **키프레임 잠금이 약하고**, 시간이 길수록 identity drift가 커지는 편이다.  
AIO v44 기본 세팅에서 **IC-LoRA detailer (`ltx-2-19b-ic-lora-detailer`)가 OFF** 였다.

## 공장 기본 완화 (자동)

`lib/ltx_aio_workflow_runner.build_aio_switched_api` — `face_stability` 기본 ON (i2v/flf/fml/v2v*)  
+ `--ltx-profile` LoRA 스택 (2026-07-18 품질 튜닝).

| 노브 | work 기본 | env |
|------|-----------|-----|
| Detailer IC-LoRA | **ON @ 0.55** | `AGENT_LTX_DETAILER_STRENGTH` |
| Distill fro09 | **0.7** (was UI 0.9 / old face 0.6) | `AGENT_LTX_DISTILL_STRENGTH` |
| Upscale IC-LoRA | **ON @ 0.45** (2-stage 지원; was hard-OFF) | `AGENT_LTX_UPSCALE_IC=0` 끄기 · `…_STRENGTH` |
| OmniNFT | **0.45** | `AGENT_LTX_OMNI_STRENGTH` |
| **VBVR** (Video Reasoning LoRA) | **ON @ 0.75** (work; file 있을 때) | `AGENT_LTX_VBVR` · `AGENT_LTX_VBVR_STRENGTH` |
| **Asian Face** (Deno East Asian Facial Fidelity) | **ON @ 1.0** (file 있을 때) | `AGENT_LTX_ASIAN_FACE` · `AGENT_LTX_ASIAN_FACE_STRENGTH` |
| 프롬프트 접미 | identity stable / no face morph | — |
| Negative | morphing face, identity shift… | — |

### VBVR (2026-07-31) — 얼굴 FaceID가 아님

Licon **VBVR** (`Ltx2.3-Licon-VBVR-I2V-240K-R32`) 는 **물리·궤적·시간 축 일관성** LoRA다.  
제목/커뮤니티에 “얼굴 일관성”으로 묶이지만 **캐릭터 FaceID 고정이 아니다**.  
detailer/Omni와 **함께** 쓰면 프레임 간 떨림·모션 이상 완화에 도움이 될 수 있다 (Mayajin LTX+VBVR WF 참고).

| profile | VBVR strength |
|---------|----------------|
| draft | 0.65 |
| **work** | **0.75** |
| hero | 0.8 |

파일: `F:\model\loras\LTX2.3\Ltx2.3-Licon-VBVR-I2V-240K-R32.safetensors`  
없으면 자동 스킵. strength **1.0은 choppy** 보고 다수 → 기본 ≤0.8.

### Asian Face (2026-08-02) — 캐릭터 ID 고정 아님

**Deno2026** [East Asian Facial Fidelity | LTX-2.3 I2V](https://civitai.com/models/2816700)  
YT: [LTX2.3 아시안 얼굴 Lora 공유](https://youtu.be/9Dkd3JwkJWo)

| | |
|--|--|
| 역할 | LTX가 카메라 이동 시 **서양인 이목구비로 드리프트**하는 편향을 줄이는 **얼굴 prior** |
| 아님 | 특정 인물 FaceID / 일관성 앵커 (키프레임·detailer·ID LoRA가 1번 축) |
| strength | **1.0** (권장, trigger word 없음) |
| 파일 | `F:\model\loras\LTX2.3\LTX2.3_EastAsian_Facial_Fidelity_v1.safetensors`  
| | (= `ltx-face-prior-f1-profile-correction-step11019.safetensors`) |

서양인 주연 컷은 `AGENT_LTX_ASIAN_FACE=0` 또는 `--no-ltx-asian-face`.

**에이전트 SSOT (when/when-not · status):** [ltx_loras_agent.md](ltx_loras_agent.md) · `python scripts/ltx_lora_status.py`

끄기 / 튜닝:

```bash
# env
set AGENT_LTX_FACE_STABILITY=0
set AGENT_LTX_DISTILL_STRENGTH=0.7
set AGENT_LTX_UPSCALE_IC=1
set AGENT_LTX_UPSCALE_IC_STRENGTH=0.45
set AGENT_LTX_DETAILER_STRENGTH=0.55
set AGENT_LTX_VBVR=0
set AGENT_LTX_VBVR_STRENGTH=0.75
set AGENT_LTX_ASIAN_FACE=0
set AGENT_LTX_ASIAN_FACE_STRENGTH=1.0

# CLI
python scripts/generate_s2v.py --backend ltx23_aio_i2v --no-face-stability ...
python scripts/generate_s2v.py --detailer-strength 0.7 --ltx-profile hero ...
python scripts/generate_s2v.py --no-ltx-vbvr ...          # VBVR off
python scripts/generate_s2v.py --ltx-vbvr-strength 0.6 ...
python scripts/generate_s2v.py --no-ltx-asian-face ...    # Asian Face off
python scripts/generate_s2v.py --ltx-asian-face-strength 0.8 ...
```

## 연출/프롬프트 (더 중요)

| 할 것 | 하지 말 것 |
|------|------------|
| 얼굴이 큰 MS/MCU (wide면 얼굴 픽셀 부족) | 와이드+작은 얼굴로 긴 클립 |
| I2V 프롬프트 = **모션만** + 안정 절 | 얼굴/의상 장문 재서술 |
| 클립 **짧게** (2–4s) 후 컷 분할 | 한 테이크 10s+ 에 identity 기대 |
| 키프레임 얼굴 선명·정면 쪽 | 블러/옆얼굴만 있는 still |
| 대사 컷 = **SI2V/InfiniteTalk** 히어로 | 립 컷을 pure I2V에 맡기기 |

## 2차 수단 (필요 시)

| 수단 | 언제 |
|------|------|
| **InfiniteTalk** (hero) | 대사·얼굴 CU 품질 최우선 |
| SeedVR2 / face polish | 모션 승인 후 마감 (얼굴 스미어 잔여) |
| Dual-Character IC-LoRA | 2인 대화 (AIO 슬롯 수동/추가 export) |
| 키프레임 재생성 | 소스 얼굴이 이미 약할 때 |
| **Best Face ID / char LoRA** | 진짜 인물 고정이 필요할 때 (별 티켓; VBVR 대체 아님) |

## A/B (2026-07-17, S01 동일 seed)

| | OFF (`--no-face-stability`) | ON (detailer@0.55) |
|--|----------------------------|---------------------|
| 파일 | `F:\generated_videos\ab_ltx_face_detailer\S01_ltx_detailer_OFF.mp4` | `…\S01_ltx_detailer_ON.mp4` |
| 비교 시트 | `compare_f12_off_vs_on.png`, `compare_last_off_vs_on.png` | |
| 중간 프레임 얼굴 | 고개 숙임·윤곽 부드러움/흐림 경향 | **정면 쪽 가독성·눈/입 구조 더 또렷** |
| 끝 프레임 | 시선 아래, 얼굴 부분 가림 | 얼굴이 카메라 쪽으로 더 읽힘 |
| 비고 | 모션 연출은 살아 있음 | 아이덴티티 “고정”은 아님, **붕괴 완화** |

**판정:** detailer ON 유지 (기본값). 완전 고정은 불가, 얼굴 가독성·구조 안정에 유리.

## 한계

완전 고정 아이덴티티는 보장되지 않는다.  
**좋은 키프레임 + 짧은 클립 + detailer + (필요 시) 립 전용 백엔드** 조합이 현실적인 상한이다.
