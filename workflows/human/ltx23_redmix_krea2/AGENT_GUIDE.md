# LTX2.3 REDMix Krea2 I2V — Agent 가이드

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_ltx23_redmix_i2v.py`  
> **Alternatives:** general I2V → `generate_i2v` · still from Krea/Ideogram/Boogu first then any I2V  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.4

**출처 컬렉션:** [[NEW] Krea2 & LTX2.3 & ideogram 4 WF](https://civitai.red/models/579280/newkrea2-and-ltx23-and-ideogram-4-wf-in-collection)  
**이 파일 버전:** **LTX2.3REDMixKrea2** (`NEWKrea2LTX23Ideogram4_ltx23redmixkrea2.json`)  
**제작 계열:** RedCraft / AiMetatron 컬렉션  

**CLI:** `python scripts/generate_ltx23_redmix_i2v.py`  
**원칙:** 실 UI(서브그래프 포함) · 포트/로더 스왑만 · 미니그래프 금지 · 카탈로그 자유 선택

---

## 1. 이게 뭔가 (컬렉션 vs 이 JSON)

컬렉션에는 여러 WF가 있습니다 (Boogu+Ideogram, Ideogram4, Krea2 등).  
**지금 편입한 파일은 “이미지→영상(LTX 2.3 I2V)” 한 장**입니다.

```text
LoadImage (보통 Krea2/Ideogram 스틸)
  → 서브그래프 Image to Video (LTX-2.3)  2-pass low→upscale→high
  → SaveVideo
```

- **Krea2 / Ideogram4 생성은 이 그래프 안이 아님**  
  스틸은 기존 도구로: `generate_krea` / `generate_krea_nsfw` / `generate_ideogram4` / `generate_boogu_typo`  
  그 결과를 **이 도구의 `-i` 로 넣어 애니메이트**.

---

## 2. 팩 모델 vs 로컬

| 역할 | 팩 기본 | 로컬 | 에이전트 |
|------|---------|------|----------|
| Diffusion | `REDGTA1.1_LTX23-int4-convrot.safetensors` | **없음** | **GGUF 대체** (아래) |
| Distilled LoRA | `LTX2\…fro09…` | `LTX2.3\…fro09…` | 경로 리맵 |
| Style LoRA yoyo | `LTX2.3\LTX-2.3-yoyo` | 없음 | 패스스루(스킵) |
| Audio LoRA clapping | `LTX2.3\clapping-cheeks…` | 없음 | 패스스루 |
| CLIP | heretic gemma int8 | `gemma_3_12B_it_fp8_e4m3fn` | 로컬 이름 |
| Projection | ltx-2.3_text_projection_bf16 | 있음 | 유지 |
| Video/Audio VAE | LTX23_*_bf16 | 있음 | AE 깨진 링크 재배선 |

### GGUF (메모리)

| backend | 파일 |
|---------|------|
| **`gguf_distilled` (기본)** | `LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf` |
| `gguf_10eros` | `LTX2.3\10Eros_v1-Q4_K_M.gguf` |
| `gguf_dev` | `LTX2.3\ltx-2.3-22b-dev-Q4_K_M.gguf` |
| `pack_redgta` | 팩 UNET (파일 있을 때만) |

`UNETLoader` → **`UnetLoaderGGUF`** 스왑 (그래프 구조 유지).  
REDGTA와 스타일은 다를 수 있음 — 팩 전용 미설치 시 동작용 대체.

---

## 3. 서브그래프 포트

| 라벨 | 용도 | CLI |
|------|------|-----|
| first_frame | 시작 이미지 | `-i` |
| prompt | 모션/장면 프롬프트 | `-p` |
| prompt_enhance | TextGenerateLTX2Prompt | (내부; 기본 유지) |
| width / height | 해상도 | `--width` `--height` |
| duration | 프레임 수 | `--frames` |
| fps | FPS | `--fps` |
| seed | noise seed | `--seed` |
| Diffusion_Model | UNET/GGUF | `--backend` / `--unet-name` |
| distilled_lora | 증류 LoRA | 자동 리맵 |
| text_encoder | CLIP | 자동 리맵 |
| latent_upscale_model | spatial x2 | 팩 기본 |

내부: low-res sample → latent upscale → high-res sample → decode → CreateVideo → SaveVideo.

---

## 4. CLI

```bash
python scripts/generate_ltx23_redmix_i2v.py --list-backends

# 스틸 → 영상 (GGUF distilled)
python scripts/generate_ltx23_redmix_i2v.py \
  -i still.png \
  -p "she smiles and turns slowly, cinematic natural motion" \
  -o out.mp4 --seed 42 --frames 49

# 10Eros GGUF
python scripts/generate_ltx23_redmix_i2v.py -i still.png -p "..." \
  --backend gguf_10eros -o out.mp4
```

**권장 파이프 (에이전트 조합, 강제 아님):**

```text
generate_krea / ideogram / boogu  → still.png
generate_ltx23_redmix_i2v -i still.png  → clip.mp4
```

---

## 5. 스모크

| 항목 | 값 |
|------|-----|
| backend | gguf_distilled |
| seed | 42 |
| frames | 49 · 768×512 |
| output | `stories/_tool_smoke/ltx23_redmix_gguf_smoke.mp4` |
| status | **OK** |

---

## 6. 다른 컬렉션 형제 (미편입)

| 버전 이름 | 역할 | 상태 |
|-----------|------|------|
| Boogu + Krea2 / Ideogram | 스틸 타이포 파이프 | 이미 `generate_boogu_typo` 등 |
| Ideogram4 단독 | 구조화 캡션 T2I | `generate_ideogram4` |
| **LTX2.3REDMixKrea2** | **I2V (이 도구)** | 편입됨 |

---

## 7. 실패 시

1. VAE “missing” → Anything Everywhere 링크 깨짐 — 러너가 VAELoader로 재배선  
2. REDGTA missing → 기본 GGUF 사용 (의도됨)  
3. yoyo/clapping LoRA missing → 스킵(패스스루)  
4. 미니그래프로 재작성 금지  
