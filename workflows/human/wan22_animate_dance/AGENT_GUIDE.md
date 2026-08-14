# Wan 2.2 Animate Dance Retarget — 사람용 가이드

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_wan22_animate.py`  
> **Human UI WF (풀팩 참고):** `../wan22/wan22_animate.json`  
> **검증 파일럿:** `stories/_tool_smoke/dance_prettygirl_test/out/D2_male_animate_headroom.mp4`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)

---

## 한 줄

**내 캐릭터 전신 스틸 + 남의(또는 내) 댄스 RGB 영상 → 같은 안무, 캐릭 룩 유지.**

크로스 캐스트(여자 댄스 → 남자 캐릭 등)에서 LTX V2V / Fun Control보다 **재현·아이덴티티가 훨씬 낫다** (2026-08-02 파일럿).

---

## 언제 쓰나 / 안 쓰나

| 쓴다 | 안 쓴다 |
|------|---------|
| 댄스·제스처 레퍼를 **다른 캐릭**에 이식 (소스 배경 유지) | 립싱크 대사 → `generate_s2v` / InfiniteTalk |
| | 포즈 없이 / 새 배경 → `generate_wan_animate2` |
| 안무 뼈대가 중요 (K-pop 훅 등) | 카메라만 → `generate_camera_move` |
| 짧은 훅 (≈3–5초, LTX 4s 캡과 비슷한 운영) | 비트 완벽 상용 커버 보장 기대 |
| pose 플레이트만 필요 → `extract_pose_video` | |

**저작권:** 레퍼 영상 권리 있는 것만. 쇼츠 재업로드 금지. 결과물은 생성 캐릭+모션.

---

## 빠른 시작 (CLI · 권장)

```bash
# 레포 루트, ComfyUI :8188
python scripts/generate_wan22_animate.py \
  -i character_fullbody.png \
  -v dance_ref.mp4 \
  -o out_dance.mp4 \
  --seed 42

# 머리 잘림 완화(기본 ON) — 끄려면
python scripts/generate_wan22_animate.py -i c.png -v d.mp4 -o o.mp4 --no-headroom

# 얼굴 더 고정 / 포즈 약화
python scripts/generate_wan22_animate.py -i c.png -v d.mp4 -o o.mp4 \
  --face-strength 1.4 --pose-strength 0.9
```

### 기본값 (파일럿 검증 프리셋)

| 파라미터 | 기본 | 메모 |
|----------|------|------|
| size | **544×960** | 9:16 · 헤드룸 여유 |
| frames | **49** | ≈3s @16fps · 4n+1 |
| steps | **8** | lightx2v LCM |
| face_strength | **1.3** | 아이덴티티 |
| pose_strength | **1.0** | 안무 |
| headroom | **on** | 상단 여백 전처리 |
| block_swap | **30** | 4090 24GB 근처 |
| retarget_padding | **48** | pose 스틱 축소 → 잘림↓ |

---

## 파이프라인 (내부)

```text
[캐릭 전신 스틸] ──CLIP Vision + ref_images──┐
                                              ├─► WanVideoAnimateEmbeds ─► Sampler ─► mp4
[댄스 RGB] ─► ViTPose pose + face crops ─────┘
              (retarget_image = 캐릭 스틸)
```

- **얼굴 고정:** `face_images` + `face_strength` + CLIP ref  
- **몸 안무:** `pose_images` + `pose_strength`  
- SAM2 마스크: v1 CLI **미사용** (bbox/video 불안정 → 생략해도 동작)

관련 도구:

```bash
# pose 플레이트만 보고 싶을 때
python scripts/extract_pose_video.py -v dance.mp4 -i character.png -o pose.mp4 --duration 4
```

---

## ComfyUI UI로 돌리기 (사람)

1. **필수 노드**
   - `ComfyUI-WanVideoWrapper` (kijai)
   - `ComfyUI-WanAnimatePreprocess` (kijai)
   - Video Helper Suite  
2. **모델 (공유 `F:\model`)**
   - `diffusion_models/Wan2.2/Wan2.2-Animate-14B-Q4_K.gguf`
   - `vae/wan_2.1_vae.safetensors`
   - `text_encoders/umt5-xxl-enc-bf16.safetensors` (또는 fp8)
   - `clip_vision/clip_vision_h.safetensors`
   - `loras/Wan2.2/lightx2v_T2V_...` + `WanAnimate_relight_lora_fp16.safetensors`
   - `detection/yolov10m.onnx` + `vitpose-l-wholebody.onnx`
3. **워크플로 열기**
   - 풀팩: `workflows/human/wan22/wan22_animate.json` (서브그래프 포함, 무겁다)
   - 또는 CLI가 쓰는 검증 그래프 설명: 이 문서 + `RECIPE.md`
4. **입력**
   - LoadImage = 캐릭 전신 (가급적 중립/댄스 준비 포즈)
   - VHS_LoadVideo = 댄스 RGB (전신이 보이는 구간이 유리)
5. **권장 노브**
   - AnimateEmbeds: `face_strength` 1.2–1.4 · `pose_strength` ~1.0  
   - `retarget_padding` 40–64 (머리 잘림 시 ↑)  
   - 해상도 544×960, frames 49, steps 8, scheduler lcm  

**UI 팁:** 레퍼가 상반신 위주면 미리 ffmpeg로 레터박스(상단 여백) 넣거나 CLI `--headroom` 사용.

---

## 품질 기대

| 잘 됨 | 약함 |
|------|------|
| 크로스 캐스트 안무 뼈대 | 손가락·비트 프레임 단위 |
| 얼굴/의상 대체로 유지 | 과격 회전 시 손 뭉개짐 |
| 짧은 훅 실험 | 18초 원테이크 한 방 |

비교 이력 (같은 Pretty Girl 훅):

| 경로 | 결과 |
|------|------|
| LTX `dance_ref` V2V | 레퍼 외형으로 붕괴 |
| Fun Control + pose | 남자이지만 심하게 뭉개짐 |
| **Animate + face** | **재현·아이덴티티 최선** |
| + headroom 544×960 | 머리 잘림 완화 |

---

## 의존 / 설치 체크

```bash
# 노드 존재 (Comfy 켜진 상태)
# DownloadAndLoadSAM2Model optional — CLI v1 미사용
# WanVideoAnimateEmbeds, PoseAndFaceDetection, OnnxDetectionModelLoader 필수
```

SAM2 풀 마스크 경로는 별도 안정화 예정. 지금 사람용 본선은 **pose+face+CLIP ref**.

---

## 관련

| 문서/도구 | 역할 |
|-----------|------|
| `generate_dance_ref.py` | LTX V2V 초안 (크로스 캐스트 비추) |
| `extract_pose_video.py` | pose 플레이트만 |
| `../wan22/SETUP_animate_fun_control.md` | 모델 설치 메모 |
| `docs/dance_challenge_pipeline_design.md` | 에피소드급 댄스 공정 (나중) |
