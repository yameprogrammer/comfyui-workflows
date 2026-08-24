# MiniMax H3 — Agent 가이드

> **Toolbox shelf:** MOTION (Seedance-class local T2V / I2V / R2V + polish + **native stereo audio**)  
> **CLI:** `python scripts/generate_minimax_h3.py`  
> **Alternatives:** episode I2V default → `generate_i2v` (LTX) · Wan easy T2V → `generate_yaw_wan22` · **클론 VO 파형 립** → `generate_s2v` (IT)  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.4 MOTION  
> **Official docs:** [ComfyUI MiniMax H3](https://docs.comfy.org/tutorials/video/minimax/minimax-h3) · [HF Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)  
> **Deno recipes:** [A2V](https://youtu.be/puBAu9qt5qM) · [MultiRef + polish](https://youtu.be/s7JDBLfTGKI)

**엔진:** MiniMax H3 open weights (pruned int8) · ComfyUI ≥ **0.30.0** native nodes  
**CLI:** `python scripts/generate_minimax_h3.py`  
**Runner:** `lib/minimax_h3_runner.py` · family `minimax_h3`

> **실 노드 유지** (`MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo`). 미니 그래프 재작성 금지.  
> T2V/I2V: H3가 대사·SFX·음악을 **같이 생성** (`<d>[Korean] …</d>`). R2V `-a` = 음색 레퍼(먹스 아님).  
> **A2V Simple / AudioToVideo = Deno 먹스 트릭. 공식 아님. 호스트 본선 금지.** SSOT: vault `decisions/2026-08-17-a2v-lipsync-chain.md`.

---

## 1. 언제 / 언제 말고

| **언제** | **말고** |
|----------|----------|
| 시네마틱 애니/실사 **텍스트→영상** (시댄스급 품질 목표) | 에피소드 본선 I2V 대량 (기본은 LTX 720p) |
| 키프레임 **I2V** + 샷/카메라/오디오를 한 프롬프트에 | 저지연 2–4초 초안만 필요 → LTX draft |
| **멀티 레퍼**로 캐릭·스타일·모션 고정 (R2V) | 15초 초과의 안정 체인 → LTX last-frame chain |
| 키프레임 + `<d>` 로 **H3가 말하게** (I2VA) | 클론 VO를 입에 그대로 → `s2v` / IT. `--task a2v` 먹스 금지 |
| work 클립 **폴리시** (VSR+RIFE 24→48) | 일반 납품 업스케일만 → `upscale_video` / LTX spatial |

---

## 2. CLI 예

```bash
# T2V work (DEFAULT ~864x480, 5s) — RTX 4090 ≈ 2분
python scripts/generate_minimax_h3.py -p "Anime cinematic, silver-haired heroine on cliff at sunset..." -o out.mp4 --seed 42

# Native canvas (~1344x768) — RTX 4090 ≈ 6분 / 5s
python scripts/generate_minimax_h3.py -p "..." -o out_native.mp4 --profile native --seed 42

# Draft scout
python scripts/generate_minimax_h3.py -p "..." -o scout.mp4 --profile draft

# I2V / first-last frame
python scripts/generate_minimax_h3.py --task i2v -i start.png -p "slow orbit, wind in cloak, soft score" -o i2v.mp4
python scripts/generate_minimax_h3.py -i start.png --last end.png -p "continuous motion between frames" -o flf.mp4

# R2V multi-ref (ref2va weights) — agent path = stock LoadImage×N
python scripts/generate_minimax_h3.py --task r2v --ref-image hero.png --ref-image style.png \
  -p "Use <Picture 1> as identity. <Picture 2> sets the city style. She walks toward camera." -o r2v.mp4

# I2VA — H3 speaks (official). Do NOT pass -a
python scripts/generate_minimax_h3.py --task i2v -i face.png --profile native \
  -p "The host (S1) says: <d>[Korean] 안녕하세요. 야매플머입니다.</d>" -o speak.mp4

# R2V timbre only (official). Different-sentence wav. H3 audio kept
python scripts/generate_minimax_h3.py --task r2v --ref-image face.png -a other_line.wav \
  --profile native -p "<Audio 1> is voice-timbre only. (S1) says: <d>[Korean] 오늘은 솔직하게 가겠습니다.</d>" \
  -o timbre.mp4

# A2V mux (Deno, unofficial) — host talking-head 금지. MV 실험만
# python scripts/generate_minimax_h3.py --task a2v ...

# Post-polish (RTX VSR×2 + RIFE×2 → 48fps; auto-fallback rife-only)
python scripts/generate_minimax_h3.py --task polish -i work.mp4 -o polished.mp4
python scripts/generate_minimax_h3.py --task polish -i work.mp4 -o polished.mp4 --polish-mode rife

python scripts/generate_minimax_h3.py --list-profiles
python scripts/generate_minimax_h3.py --list-models
```

---

## 3. 프로필 (해상도 티어)

| profile | megapixels | 대략 16:9 | steps | 용도 | 4090 5s 벤치 |
|---------|------------|-----------|-------|------|--------------|
| `draft` | 0.3 | ~736×416 | 16 | 프롬프트 탐색 | 더 빠름 |
| **`work`** | **0.4** | **~864×480** | **20** | **에이전트 기본** | **~113s** |
| `native` | 0.98 | ~1344×768 | 20 | H3 네이티브 캔버스 | **~378s** |
| `hero` | 0.98 | ~1344×768 | 24 | 소수 히어로 컷 | native+ |

H3 단변 목표 ≈ **768px**, 최대 그리드 32 배수. 세로 쇼츠: `--aspect 9:16`.

---

## 4. 모델 (로컬)

`extra_model_paths.yaml` → `F:\model`

| 역할 | 파일 |
|------|------|
| T2V/I2V DiT | `diffusion_models/MinimaxH3/minimax_h3_fl2va_pruned_int8_convrot.safetensors` (~21GB) |
| R2V DiT | `diffusion_models/MinimaxH3/minimax_h3_ref2va_pruned_int8_convrot.safetensors` (~21GB) |
| Text encoder | `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (~15GB) |
| Video VAE | `vae/minimax_h3_video_vae_fp16.safetensors` (~5GB) |
| Audio VAE | `vae/minimax_h3_audio_vae_fp32.safetensors` (~0.6GB) |

ComfyUI 콤보 이름: `MinimaxH3\minimax_h3_…` (서브폴더 포함).

---

## 5. 프롬프트 팁

1. **한 블록**에 장면 개요 + 타임라인 샷 + 카메라 + **오디오**(대사/SFX/음악).  
2. 타임라인 예: `[0s-1.5s] Shot 1: ...`  
3. R2V: 연결 순서대로 `<Picture 1>`, `<Video 1>`, `<Audio 1>` 태그 + **각 레퍼 역할** 명시.  
4. length는 24fps에서 **17프레임 블록 그리드**로 스냅됨 (duration 초 입력).

공식 가이드:  
- Base: [VIDEO_PROMPT_WRITING_GUIDE_base_en.md](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)  
- Ref: [VIDEO_PROMPT_WRITING_GUIDE_ref_en.md](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)

---

## 6. 인간 UI 워크플로 (로드용)

| 파일 | 모드 | 에이전트 대응 |
|------|------|----------------|
| `MiniMax_H3_T2V_TextToVideo.json` | T2V | `--task t2v` |
| `MiniMax_H3_I2V_ImageToVideo.json` | I2V / FL | `--task i2v` / flf |
| `MiniMax_H3_R2V_ReferenceToVideo.json` | R2V stock | `--task r2v` |
| **`MiniMax_H3_R2V_MultiRef_Deno.json`** | Multi-ref Deno 로더 | `--task r2v` (API는 stock; UI가 편함) |
| **`MiniMax_H3_A2V_Simple.json`** | Deno 먹스 (비공식) | `--task a2v` — **호스트 본선 금지** |
| `MiniMax_H3_A2V_AudioToVideo.json` | Deno 먹스 + Whisper/LLM | UI 전용. 공식 아님 |
| **`MiniMax_H3_PostPolish_Upscale60fps.json`** | RTX VSR + RIFE | **`--task polish`** |
| **`MiniMax_LTX_Spatial_Full_Upscale.json`** | work → HD 생성형 업스케일 | `upscale_ltx_spatial.py` |
| `MiniMax_H3_README.md` | 로컬 설치·레시피 메모 | — |

ComfyUI 템플릿 라이브러리 **Video → MiniMax H3** 와 동일 계열 (로컬 `MinimaxH3\` 경로 패치됨).  
휴대 설치 복제본: `F:\ComfyUI_windows_portable\ComfyUI\workflows\MiniMax_H3_*`

### 6.1 MiniMax → LTX Full Spatial Upscale

스모크 테스트 통과 그래프 (spatial x2 + **upscale IC-LoRA refine**, CRT UnifiedSampler V2V Upscale).

**Comfy 로드 경로 (둘 중 하나):**
- Workflows 메뉴 → `MiniMax_LTX_Spatial_Full_Upscale`
- 파일: `ComfyUI\user\default\workflows\MiniMax_LTX_Spatial_Full_Upscale.json`  
  (복제본: `ComfyUI\workflows\…`, 에이전트 팩: 이 폴더)

**사용법:**
1. 소스 mp4를 Comfy **input** 폴더에 넣기
2. **Load MiniMax / source video** 에서 선택
3. (선택) prompt / seed / steps / megapixels_target (1.5 ≈ 1632×896)
4. Queue Prompt

**기본값 (4090, 5s 클립 ≈ 3분):** steps=4 · guide=0.45 · IC-LoRA 0.75 · megapixels=1.5

**Agent CLI:**
```bash
python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full
```

필요 custom nodes: **ComfyUI-LTXVideo** + **crt-nodes** + **ComfyUI-GGUF** + **VideoHelperSuite**

### 6.2 Official speak vs A2V mux (2026-08-17)

- **공식 말하기:** I2V 템플릿 / `--task i2v` + `<d>[Korean]`. `-a` 넣지 말 것.  
- **공식 음색:** R2V / MultiRef + `ref_audios`. CreateVideo는 `VAEDecodeAudio`.  
- **A2V Simple/Full:** H3 생성음을 버리고 원본 wav를 얹음. 운이 좋으면 립처럼 보임. 호스트 금지.  
- **PostPolish:** VSR Medium ×2 → RIFE ×2 (24→**48**fps). RTX VFX 없으면 `--polish-mode rife`.

스모크 (4090): A2V 0.2MP 5s ~50s · MultiRef ~110s · polish RTX+RIFE ~25s → 1216×704@48.

---

## 7. 한계 / 주의

- **VRAM:** pruned int8 + dynamic load. 4090 24GB OK. 3060급은 draft/work + 짧은 duration.  
- **속도:** LTX lightx2v 초안보다 느림. 품질 히어로·오디오 포함 쇼츠에 적합.  
- **에피 본선:** `video_backends.json` default I2V는 여전히 **LTX**. MiniMax는 의도적 품질/오디오 도구.  
- **R2V**는 fl2va와 **다른 unet** (`ref2va`).  
- 클론 VO 파형 립은 `s2v`/IT. MiniMax A2V 먹스는 공식 립싱크가 아님.  
- Sage Attention 옵션 시 약 2× 가속 가능 (공식 문서; 미기본).

---

## 8. Alternatives

| if | use | cli |
|----|-----|-----|
| 에피 키프레임 모션 대량 | LTX I2V | `python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4` |
| MiniMax work → HD 생성형 | LTX spatial full | `python scripts/upscale_ltx_spatial.py -i work.mp4 -o hd.mp4 --path full` |
| MiniMax work → 빠른 선명+보간 | polish | `python scripts/generate_minimax_h3.py --task polish -i work.mp4 -o p.mp4` |
| 빠른 Wan T2V 실험 | YAW | `python scripts/generate_yaw_wan22.py --task t2v -p "..." -o out.mp4` |
| 클론 VO 파형을 입에 그대로 | s2v | `python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4` |
| H3가 말하게 | minimax i2v | `python scripts/generate_minimax_h3.py --task i2v -i face.png -p "... <d>[Korean] …</d>"` |
| 카메라 의도만 | camera_move | `python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4` |
