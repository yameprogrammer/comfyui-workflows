# Krea2 + SeedVR2 업스케일 워크플로

- **작성**: 2026-07-19
- **목적**: Krea2로 생성한 키프레임을 SeedVR2로 enhanced 업스케일하여 납품 품질로 끌어올리는 가이드
- **관련**: upscale_research_and_design.md · Krea2_SFW_NSFW_v10_AGENT_GUIDE.md · upscale_backends.json

---

## §1. 왜 Krea2 + SeedVR2인가

- **Krea2 AI 생성 이미지와 SeedVR2 복원의 궁합**: Krea2는 고품질 AI 생성 스틸을 산출하지만 work 해상도(1024 이하)에서 작동. SeedVR2의 diffusion-based 복원은 AI 생성 소스의 디테일을 되살리는 데 최적화되어 있어 궁합이 좋다.
- **SeedVR2 특성**: 7B diffusion restore 모델, AI 생성 키프레임·인물 디테일 복원에서 ESRGAN/LDSR 대비 우위 (Reddit 커뮤니티 평가 다수).
- **커뮤니티 트렌드**: `upscale_research_and_design.md §2.3` — "Krea/Z-Image 워크플로에 SeedVR2 인라인 업스케일 유행." Moody/Z-Image 키프레임 → SeedVR2 경로가 업계 표준 패턴으로 자리잡는 중.
- **로컬 가용**: `F:\model\SEEDVR2\seedvr2_ema_7b_fp16` + `fp8 mixed` 모델이 로컬에 배치되어 있음 (4090 기준 FP8 스윗스팟).

---

## §2. 업스케일 레인 선택

목적에 맞는 백엔드를 선택한다. 기본은 `esrgan`이고, Krea2 키프레임 히어로에만 `seedvr2`를 opt-in한다.

| 목적 | 백엔드 | CLI |
|------|--------|-----|
| 배치·에피소드 기본 납품 | `esrgan --style photo` | `python scripts/upscale_image.py -i x.png --style photo --preset deliver_1080` |
| **Krea2 키프레임 히어로** | `seedvr2` | `python scripts/upscale_image.py -i x.png --backend seedvr2 --preset deliver_1080` |
| 4K 마스터 (최종 히어로) | `seedvr2_max` | `python scripts/upscale_image.py -i x.png --backend seedvr2_max --preset deliver_2160` |
| work 클립 깨끗, 빠른 납품 | `rtx_vsr` (옵션) | `python scripts/upscale_image.py -i x.png --backend rtx_vsr` |

> [!NOTE]
> `seedvr2`와 `seedvr2_max`는 **opt-in** 전용이다. 배치 기본 경로에서 자동 적용하지 않는다. 히어로 키프레임 or 최종 마스터 단계에서만 사용.

---

## §3. Krea2 인라인 SeedVR2 (워크플로 내장)

Krea2 v10 워크플로 (`krea2SFWNSFWUncensoredImageTo_v10.json`) 내부에는 SeedVR2 업스케일러 그룹이 내장되어 있다.

| 항목 | 내용 |
|------|------|
| **Bypasser 노드** | node 16 (`matchTitle: 'SeedVR2 upscaler'`) |
| **활성화 방법** | Bypasser를 **ON** 으로 설정 |
| **현재 상태** | 내장 업스케일러 그룹은 워크플로에 존재, preset 활성화 진행 중 |
| **에이전트 권장 경로** | **별도 `upscale_image.py --backend seedvr2` 호출** (더 안정적·파라미터 제어 명확) |

> [!WARNING]
> 인라인 SeedVR2 그룹이 아직 완전히 안정화되지 않았다. 에이전트는 워크플로 내장 업스케일러 대신 **별도 CLI 호출** 경로를 우선 사용한다.

---

## §4. 전체 워크플로 예

아래는 Krea2 키프레임 생성부터 I2V 입력까지의 전체 흐름이다.

```bash
# ──────────────────────────────────────────
# Step 1: Krea2로 키프레임 생성
# ──────────────────────────────────────────
python scripts/generate_krea.py \
  -p "Photoreal cinematic film still, medium shot, woman in trench coat, \
      rainy night street, neon reflections, shallow DOF, 85mm lens" \
  -o keyframe_raw.png \
  --seed 42

# ──────────────────────────────────────────
# Step 2: QA 확인 (파일을 직접 열어서 검수)
# anatomy / framing / lighting / ID consistency
# → 합격 시 Step 3 진행 / FAIL 시 edit/inpaint 수정
# ──────────────────────────────────────────

# (FAIL 예: 손 결함)
python scripts/generate_qwen_inpaint.py \
  -i keyframe_raw.png \
  --mask hand_mask.png \
  --instruction "natural female hand, five fingers, correct anatomy" \
  -o keyframe_fixed.png

# ──────────────────────────────────────────
# Step 3: SeedVR2 히어로 업스케일 (1080p)
# ──────────────────────────────────────────
python scripts/upscale_image.py \
  -i keyframe_fixed.png \
  -o keyframe_hero_1080.png \
  --backend seedvr2 \
  --preset deliver_1080

# ──────────────────────────────────────────
# Step 4: (선택) 4K 마스터
# ──────────────────────────────────────────
python scripts/upscale_image.py \
  -i keyframe_hero_1080.png \
  -o keyframe_master_4k.png \
  --backend seedvr2_max \
  --preset deliver_2160

# ──────────────────────────────────────────
# Step 5: I2V 입력으로 사용
# ──────────────────────────────────────────
python scripts/generate_i2v.py \
  -i keyframe_hero_1080.png \
  -p "slow push-in, subtle breathing, rain falling continuously" \
  --ltx-profile work \
  -o clip_s01.mp4
```

---

## §5. 업스케일 하드 룰 (upscale_research_and_design.md §1 발췌)

이 규칙은 **불변**이다. 어떤 상황에서도 예외 없이 적용한다.

1. **I2V/T2I는 work 해상도**에서 돌리고, 업스케일은 **마감 층만** 진행.
2. **종횡비는 format 프로필과 동일 유지** (16:9 / 9:16 / 4:3 / 3:4 …). 업스케일이 비율을 바꾸지 않도록.
3. **납품 픽셀은 프리셋으로 선택**: `deliver_1080` / `deliver_1440` / `deliver_2160` (짧은 변 기준).
4. **손·얼굴 해부학 버그는 업스케일 전에 edit/inpaint로 수정**. 업스케일이 구조 버그를 고쳐준다고 가정하지 말 것.
5. **배치 기본 = esrgan · Krea2 히어로 = SeedVR2** — 무분별한 SeedVR2 남용은 VRAM·시간 낭비.

---

## §6. VRAM 가이드

4090 (24GB) 기준 예상치. 설정(resolution, batch_size, tile) 에 따라 달라진다.

| 백엔드 | VRAM 사용 | 예상 시간 (RTX 4090) | 비고 |
|--------|-----------|----------------------|------|
| `esrgan` (4x) | 낮음 (~2GB) | 수초 | 배치·프리뷰 기본 |
| `seedvr2` FP8 7B | 중 (~10GB) | 1–3분 / 이미지 | 히어로 스윗스팟 |
| `seedvr2` FP16 7B | 높음 (~16GB) | 3–6분 / 이미지 | 최고 품질, 4090 OK |
| `seedvr2_max` FP16 | 높음 (~18GB) | 5–10분 / 이미지 | 4K 마스터 전용 |
| `rtx_vsr` | 낮음 (Tensor 코어) | 수십초 / 이미지 | 깨끗한 소스 고속 |

> [!TIP]
> SeedVR2 OOM 발생 시: `--tile` 옵션으로 타일 처리 전환하거나 `--offload` 플래그 추가. `batch_size`는 **4n+1** 단위(1, 5, 9…)로 설정.

---

## §7. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-19 | 초안: Krea2+SeedVR2 업스케일 워크플로 가이드 |
