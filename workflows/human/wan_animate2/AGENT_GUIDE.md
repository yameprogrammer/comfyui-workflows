# Wan Animate 2 — 사람용 가이드

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_wan_animate2.py`  
> **Runner:** `lib/wan_animate2.py`  
> **검증:** 2026-08-14 RTX 4090 24GB · 480×832 · 81f · 6 step  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)

`generate_wan22_animate` (Wan 2.2 Animate + ViTPose)와 **다른 모델**이다.

---

## 한 줄

**캐릭터 스틸 + 드라이빙 영상 → 그 안무/제스처를 이식.** 포즈 추출 없음. 배경·카메라는 프롬프트.

---

## 언제 쓰나 / 안 쓰나

| 쓴다 | 안 쓴다 |
|------|---------|
| 댄스·퍼포먼스 영상을 다른 캐릭에 이식 | 립싱크 대사 → `generate_s2v` |
| 배경을 프롬프트로 새로 깔고 싶을 때 | 소스 배경을 유지한 교체 → `generate_wan22_animate` |
| 스켈레톤/OpenPose 없이 빠르게 | pose 플레이트만 → `extract_pose_video` |
| 4090 24GB int8 6스텝 | 에피 대량 I2V → LTX |

**저작권:** 레퍼 영상 권리 있는 것만.

---

## 빠른 시작

```bash
# 레포 루트, ComfyUI :8188. -o 는 호출 프로젝트 경로.
python scripts/generate_wan_animate2.py \
  -i character.png \
  -v dance.mp4 \
  -o F:/my_project/out/dance.mp4 \
  --seed 42

python scripts/generate_wan_animate2.py -i c.png -v d.mp4 -o o.mp4 \
  --look "pink hair, gold mechanical arms, black leather jacket" \
  --background "plain gray studio, even light" \
  --pose-prompt "energetic street dance, background stationary"
```

### 기본값 (로컬 검증 프리셋)

| 파라미터 | 기본 | 메모 |
|----------|------|------|
| size | **480×832** | 세로. 원본 비율 맞출 것 |
| frames | **81** | ≈3.4s @24fps · 4n+1 |
| steps | **6** | LightX2V + LCM |
| cache | **cpu / int8** | 24GB에서 GPU 캐시 금지 |
| unet | `wan_animate_2_int8_convrot.safetensors` | ~15.9GB |
| lora | `lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16` | |

---

## 프롬프트

- `--look` / positive: **외형만**. 동작 단어 넣지 말 것.
- `--background`: 출력 세트. 스틸 배경은 따라오지 않음.
- `--pose-prompt`: 드라이빙 영상의 동작 한 줄.

참조 스틸의 **첫 포즈 ≈ 영상 첫 포즈**, 프레이밍은 전신↔전신.

---

## 대안

| if | use | cli |
|----|-----|-----|
| 소스 배경 유지 + 얼굴 고정 | wan22_animate | `python scripts/generate_wan22_animate.py -i c.png -v d.mp4 -o o.mp4` |
| 빠른 LTX 초안 | dance_ref | `python scripts/generate_dance_ref.py -i c.png -v d.mp4 -o o.mp4` |
| 립싱크 | s2v | `python scripts/generate_s2v.py -i c.png -a line.wav -o o.mp4` |
