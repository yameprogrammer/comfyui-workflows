# LTX 옵션 LoRA — 에이전트 SSOT

- **작성**: 2026-08-02  
- **목적**: 에이전트가 LTX 계열 **선택 LoRA**를 언제 켜고/끄는지 한곳에서 판단  
- **코드 조회**: `python scripts/ltx_lora_status.py` · `lib/ltx_lora_catalog.py`  
- **관련**: [ltx_face_stability.md](ltx_face_stability.md) · [tool_catalog.md](tool_catalog.md) § LTX 스위치

---

## 0. 한눈에

| id | 이름 | 디스크 | 기본 주입 | 용도 한 줄 |
|----|------|--------|-----------|------------|
| **asian_face** | East Asian Facial Fidelity (Deno) | ✅ ready | **ON** (파일 있을 때) | 아시안 얼굴 드리프트·서양인화 완화 (I2V) |
| **relight** | LTX-2.3 IC-LoRA Relight (Lightricks) | ⬜ **HF gated** | 자동 아님 | **완성 클립 야외 재조명** (V2V 마감) |
| vbvr | Licon VBVR | ✅ (별도) | ON | 모션·시간축 (FaceID 아님) → face_stability 문서 |
| detailer | IC detailer | ✅ | face_stability ON 시 | 얼굴 구조 완화 |

> **에이전트 규칙:** 아래 “when / when not”을 위반한 채 만능 퀄업으로 쓰지 말 것.

---

## 1. Asian Face — `asian_face` ✅

### 무엇

- **Deno2026** Civitai: [East Asian Facial Fidelity \| LTX-2.3 I2V](https://civitai.com/models/2816700)  
- YT: https://youtu.be/9Dkd3JwkJWo  
- **표준 LoRA** (IC-LoRA 아님). 캐릭터 ID 고정 **아님**.  
- 카메라 이동 시 LTX가 **서양인 이목구비로 기우는 편향**을 줄이는 **얼굴 prior**.

### 파일

```text
F:\model\loras\LTX2.3\LTX2.3_EastAsian_Facial_Fidelity_v1.safetensors
(= ltx-face-prior-f1-profile-correction-step11019.safetensors)
```

### When (써야 함)

| 상황 | 예 |
|------|-----|
| 아시안 주연 I2V / FLF / SI2V (LTX AIO) | 뮤비·쇼츠 히어로 |
| 옆/오빗 시 눈·코·턱이 서양형으로 변하는 증상 | 리서치·Deno 설명과 동일 |
| 공장 기본 작업 (파일 있으면) | **자동 ON** |

### When not (끄기)

| 상황 | 조치 |
|------|------|
| 서양인·비아시안 주연 | `--no-ltx-asian-face` 또는 `AGENT_LTX_ASIAN_FACE=0` |
| 이미 캐릭 ID LoRA / 강한 FaceID로 고정 중 + 충돌 의심 | 끄고 A/B |
| 조명·안무·텍스처만 이슈 | 다른 도구 (relight / animate / upscale) |

### 에이전트 호출

```bash
# 기본: 파일 있으면 auto ON @ strength 1.0
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow head turn"
python scripts/generate_s2v.py --backend ltx23_aio_i2v ...

# 끄기
python scripts/generate_s2v.py --no-ltx-asian-face ...
set AGENT_LTX_ASIAN_FACE=0

# strength
python scripts/generate_s2v.py --ltx-asian-face-strength 1.0 ...
set AGENT_LTX_ASIAN_FACE_STRENGTH=1.0
```

- **Trigger word:** 없음 (`woman` 등 일반 서술)  
- **권장 strength:** **1.0**  
- **주입 위치:** LTX AIO Power Lora node 211 (`apply_ltx_asian_face_lora`)  
- **스택:** detailer / VBVR / distill 과 병행 가능  

### 기대치

- ✅ 프로필·3/4 각도 얼굴 안정 향상  
- ❌ 특정 연예인 FaceID / 댄스 안무 재현 / 해상도 업스케일  

---

## 2. Relight IC-LoRA — `relight` ⬜ 가중치 게이트

### 무엇

- **Lightricks** 공식: [LTX-2.3-22b-IC-LoRA-Relight](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Relight)  
- 리뷰/소개: 소이랩 https://youtu.be/OJkNlT5B-5M  
- **IC-LoRA**: 소스 영상 + **라이트 방향 구(ball)** 조건으로 **야외 클립 재조명**  
- 생성 본선 품질 업이 아니라 **룩/연출 마감 패스**.

### 파일 (설치 후 기대 경로)

```text
F:\model\loras\LTX2.3\ltx-2.3-22b-ic-lora-relight-1.0.safetensors
F:\model\loras\LTX2.3\LTX2.3_IC-LoRA_Relight_v1.safetensors   # alias 권장
```

**현재 상태 (2026-08-02):** HF **gated** + 로컬 토큰 무효 → **자동 다운로드 실패**.  
에이전트는 `ltx_lora_status.py` 가 `missing` 이면 **호출하지 말 것**.

### 수동 설치 (사람 1회)

1. HF 로그인 + 모델 페이지 **Agree and Access**  
2. 유효 토큰:

```bash
hf auth login --force
python scripts/ltx_lora_status.py download-relight
# 또는
hf download Lightricks/LTX-2.3-22b-IC-LoRA-Relight ltx-2.3-22b-ic-lora-relight-1.0.safetensors \
  --local-dir F:/model/loras/LTX2.3
```

3. 공식 WF: 리포의 `LTX-2.3_Relight_ICLoRA_SingleStage_Distilled.json` →  
   `workflows/human/ltx23_relight/` 에 복사  
4. Sphere-Light-Render 노드 등 WF 의존 설치 (공식 README)

### When (써야 함)

| 상황 | 예 |
|------|-----|
| **이미 나온 LTX 야외 클립**의 햇빛 방향·매직아워·역광 재연출 | 히어로 컷 룩 통일 |
| 낮 촬영 느낌 → 골든아워/측면광 | 프롬프트로 룩 지정 |
| 에피소드 **FINISH / 룩 패스** (모션 승인 후) | 생성 본선 아님 |

### When not

| 상황 | 대신 |
|------|------|
| 댄스 안무·아이덴티티 문제 | `generate_wan22_animate` / Asian Face / detailer |
| **실내** 토킹·카페 | 범위 밖 (공식 exterior only) |
| 빈 화면에서 첫 생성 | `generate_i2v` 본선 |
| 파일 없음 / status missing | 스킵 · 설치 요청만 |

### 제어 신호 (에이전트 필수 이해)

- 입력 = **소스 영상 전 프레임** + 우상단 **라이트 방향 구** 합성  
- 공식 Comfy WF는 Sphere-Light-Render로 구를 자동 합성  
- 프롬프트 형식:

```text
relight the video to match the light-direction ball. <look> from <direction>
```

`<look>` 예: `hard directional sunlight` · `warm golden low side sun` · `soft diffused daylight` …  
`<direction>` 예: `the right` · `the left` · `behind` · `the front` …

- **LoRA strength:** 1.0  
- **권장 geometry:** 1280×704 · ~121f · 24fps (공식 sweet spot)  
- **single-stage** (2-stage Stage2는 레퍼 유실)

**12 trained looks** (이 목록 밖 자유 문장은 약함):

```
hard directional sunlight | hard high-angle sunlight | hard low-angle sunlight
soft diffused daylight | soft warm afternoon light | cool soft daylight
dim overcast light | strong backlight with rim light | soft hazy backlight
warm golden low front sun | warm golden low side sun | frontal sunlight
```

**Directions:** `the front` · `the front-right` · `the right` · `the back-right` · `behind` · `the back-left` · `the left` · `the front-left`

### 에이전트 호출 (가중치 ready 후)

```bash
# 상태 확인
python scripts/ltx_lora_status.py

# CLI (가중치 있을 때만; 없으면 exit non-zero + 안내)
python scripts/generate_ltx_relight.py \
  -v exterior_clip.mp4 \
  -o relit.mp4 \
  --look "warm golden low side sun" \
  --direction "the left" \
  --seed 42
```

구현 상태: 카탈로그·가이드·status CLI 우선.  
`generate_ltx_relight.py` 는 가중치 없으면 설치 안내 후 실패; 있으면 공식 WF/API 경로로 확장.

### 기대치

- ✅ 야외 클립 조명 방향·분위기 변경  
- ❌ 안무 개선 · 실내 릴라이트 · 씬 내용 편집 · “무조건 고퀄 업스케일”

---

## 3. 에이전트 의사결정 트리

```text
LTX로 클립 만드는 중?
  ├─ 아시안 얼굴 드리프트 걱정 → asian_face ON (기본)
  ├─ 서양인 주연 → asian_face OFF
  └─ 모션 떨림 → VBVR (별도)

클립이 이미 나왔고 야외 룩만 바꾸고 싶다?
  ├─ relight status == ready → generate_ltx_relight / UI Relight WF
  └─ missing → 설치 요청, 본선 생성에 relight 끼워 넣지 말 것

댄스 크로스 캐스트?
  └─ asian_face는 LTX 경로에만 해당; 본선은 wan22_animate
```

---

## 4. 상태 조회

```bash
python scripts/ltx_lora_status.py
python scripts/ltx_lora_status.py --json
```

| status | 의미 |
|--------|------|
| `ready` | 파일 있음 · 에이전트 사용 가능 |
| `missing` | 파일 없음 · 해당 도구 호출 금지 |
| `gated` | HF 동의·로그인 필요 (relight) |

---

## 5. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-08-02 | asian_face 설치·AIO 자동 주입 · relight 문서화 (HF gate로 가중치 미수신) · status CLI · tool_intent/catalog · generate_ltx_relight fail-closed |
