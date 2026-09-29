# LTX 2.5 video prompts (T2V / TA2V / I2V / IA2V / FLF / FLFA / FML / FMLA / V2V)

**CLI:** `generate_ltx25_aio` (`python scripts/generate_ltx25_aio.py --mode <mode> --prompt "..." [-i image] [-a audio]`)  
**Manifest:** `workflows/agent/ltx25_aio.manifest.json`  
**Workflow:** `workflows/agent/ltx25AllInOneWorkflowForRTX_custom.json`  
**Architecture:** 22B Distilled Transformer + Gemma 4 12B Text Encoder + Latent Video/Audio VAE  

---

## ⚠️ 핵심 하드 룰 (생성 전 필독)

| 규칙 | 내용 |
|------|------|
| **메모리 선행 해제** | 24GB VRAM 환경에서 Gemma 4 (14.6GB) + 22B DiT 동시 적재 방지를 위해 사전 `free_comfy_memory` 필수 (CLI 자동 수행) |
| **Gemma 4 자연어** | 태그 나열(tag-soup) 금지. 완전한 문장의 영화적 자연어(Natural Language) 기술 권장 |
| **프레임 상한** | 단일 생성 **49~97프레임** (24fps 기준 약 2~4초). 초과 시 프레임 간 드리프트 방지를 위해 last frame 체인 분할 |
| **I2V 프롬프트 원칙** | 이미지가 인물 외모·의상·공간을 소유. 프롬프트는 오직 **시간 축 모션 + 카메라 + 미세 액션**만 서술 |
| **단일 의도 집중** | 한 클립 = 1개의 주 카메라 무브 또는 1개의 핵심 액션 (복합 카메라 충돌 금지) |
| **오디오 태그 지원** | 오디오 동기화 모드(IA2V/TA2V 등)에서는 대사 `"dialogue in quotes"` 및 환경음(`rain sound`, `footsteps`) 묘사 가능 |

---

## 1. 프롬프트 기본 구조 (Gemma 4 12B 최적화)

Gemma 4 12B 텍스트 인코더는 문맥 이해도와 공간/시간 관계 인지력이 매우 뛰어납니다.  
기계적인 품질 수식어(`masterpiece, best quality, 8k`)는 완전히 배제하고, 장면의 물리적 변화와 감정선을 명확한 영어 산문으로 기술합니다.

### 1.1 Simple (단일 샷 기본형 — 권장)
```text
[Camera movement], [subject micro-action], [lighting/atmosphere behavior], continuous motion throughout, no warp
```
**예시:**
```text
Slow cinematic push-in toward the face, subtle breathing and gentle hair drift in the breeze, soft diffused lighting holds steady, continuous motion throughout, no warp no flicker.
```

### 1.2 Chronological (시간 순차 서술형)
LTX 2.5는 0초에서 4초 사이의 사건 전개를 문맥적으로 해석합니다.
```text
[0–2s: initial state and motion]. [2–4s: transition or subtle action shift]. [Camera and ambient cues throughout].
```
**예시:**
```text
The woman sits in silence looking down at the letter; after two seconds, she slowly lifts her gaze toward the camera with restrained emotion. Smooth static medium shot with soft window backlight holding throughout.
```

---

## 2. 9가지 모드별 프롬프트 가이드

### 2.1 T2V (Text to Video)
인물, 공간, 액션, 카메라, 조명을 모두 텍스트로 서술합니다.
```text
A young detective in a beige trench coat stands beneath flickering neon signs in a rainy alley. He slowly lifts a brass lighter to illuminate his face, shadows dancing across wet brick walls. Slow dolly in, cinematic 35mm film grain, continuous rain ambience.
```

### 2.2 TA2V (Text + Audio to Video)
대사와 인물 감정 전달이 오디오와 함께 동기화됩니다. 대사는 큰따옴표(`"..."`)로 감싸줍니다.
```text
Close-up of a radio operator speaking into a vintage microphone: "Transmission confirmed, hold your position." His lips synchronize cleanly with the speech, eyes scanning the dials, subtle head nods, warm amber cockpit illumination.
```

### 2.3 I2V (Image to Video)
**입력 이미지가 룩앤필(의상, 헤어, 인물 정체성, 배경 디테일)을 100% 결정합니다.**  
프롬프트에서 이미지를 다시 설명하지 마십시오.
- ❌ **금지:** `A pretty Korean girl with long black hair wearing a white silk blouse stands in a cafe...`
- ⭕ **권장:** `Slow elegant dolly forward, gentle breathing and subtle blinking, she slightly turns her head to the left while maintaining eye contact, continuous natural motion.`

### 2.4 IA2V (Image + Audio to Video)
입력 이미지의 인물이 전달된 음성 오디오에 맞춰 립싱크 및 표정 연기를 수행합니다.
```text
The character speaks naturally with realistic lip movement, slight eyebrow twitches matching vocal emphasis, natural blinking and micro head tilts, stable camera, identity locked.
```

### 2.5 FLF & FLFA (First–Last Frame Interpolation)
시작 프레임과 종료 프레임 사이를 자연스럽게 이어주는 **브리지(Bridge) 모션**만 기술합니다. (새로운 인물이나 엉뚱한 사건 삽입 금지)
```text
Smooth continuous transition from opening posture to the ending pose, gradual camera pull-back, seamless interpolation with no morphing or sudden pops, preserving subject identity throughout.
```

### 2.6 FML & FMLA (First–Middle–Last Frame)
중간 키프레임을 거치는 2단계 전환 모션입니다.
```text
Continuous flowing motion: moving smoothly through the middle action and resolving into the final pose, steady pan left matching subject movement, clean temporal consistency.
```

### 2.7 V2V (Video to Video)
기존 영상의 모션 구조를 유지하면서 스타일, 조명, 텍스처를 변환합니다.
```text
Retain source motion and camera trajectory exactly, transform visual grade into moody neo-noir cinema, high contrast shadows, wet asphalt reflections, no ghosting.
```

---

## 3. 카메라 무브 어휘 (Camera Lexicon)

카메라 무브는 **1샷당 1개만** 사용하는 것이 드리프트 방지에 가장 좋습니다.

| 의도 | 권장 어휘 | 비고 |
|------|-----------|------|
| 전진 (줌인/달리) | `slow cinematic push-in`, `gentle dolly forward` | 피사체 집중, 인물 클로즈업 |
| 후진 (줌아웃/달리) | `slow pull-back`, `gentle dolly out` | 공간 확장, 고립감 |
| 수평 이동 | `steady lateral track left/right`, `slow horizontal pan` | 걷기, 시선 이동 |
| 고정 샷 | `locked-off tripod shot`, `static medium frame` | 연기 집중, 잔잔한 대화 |
| 틸트 | `slow tilt up to sky`, `gentle downward tilt` | 높이감, 인물 전신 스캔 |
| 원형 회전 | `gentle orbital arc around subject` | 극적 긴장감 |
| 미세 핸드헬드 | `subtle natural handheld drift` | 현실감, 다큐멘터리 무드 |

---

## 4. 미세 액션 및 환경 어휘 (Micro-actions & Atmosphere)

- **호흡/미세 동작:** `subtle chest micro-rise`, `gentle rhythmic breathing`, `relaxed posture`
- **시선/표정:** `slow natural blink`, `gaze shifts softly to the side`, `subtle smirk playing on lips`, `repressed tension in jaw`
- **헤어/의류 펄럭임:** `soft wind flutter in hair`, `gentle fabric drift`, `loose strands swaying lightly`
- **환경 이펙트:** `floating dust motes in sunbeam`, `continuous gentle drizzle`, `subtle steam rising from coffee cup`

---

## 5. Negative Prompt (네거티브 프롬프트 표준)

LTX 2.5는 네거티브 프롬프트 민감도가 높습니다. 과도한 문장형보다는 결함 토큰을 명확히 전달합니다.

```text
warp, identity morph, face melt, sudden jump cut, teleportation, distorted limbs, flickering lighting, extra fingers, text overlay, watermark, plastic skin texture, stuttering motion
```

---

## 6. 품질 검수 체크리스트 (Quality Gate)

생성 명령 실행 전 다음 사항을 확인하십시오:
- [ ] 실행 모드가 의도에 부합하는가? (예: 단일 이미지→`i2v`, 음성 포함→`ia2v` 또는 `ta2v`)
- [ ] 단일 생성 프레임 수가 **97프레임 이내**인가?
- [ ] I2V/IA2V에서 외모·의상 재서술이 없고 모션에 집중되어 있는가?
- [ ] 충돌하는 카메라 무브가 섞여 있지 않은가? (`push-in and quick pan` 등 금지)
- [ ] 사전 VRAM 언로드가 준비되어 있는가? (`generate_ltx25_aio.py` 실행 시 자동 수행)
