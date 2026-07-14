# ACE-Step BGM 파이프라인 (에이전트 도구)

- **작성일**: 2026-07-12  
- **엔진**: ACE-Step 1.5 XL (turbo / base) — 사용자가 쓰던 Comfy 워크플로  
- **관련**: [audio_motion_production_modes.md](audio_motion_production_modes.md), [qwen3_tts_ltx_audio_pipeline.md](qwen3_tts_ltx_audio_pipeline.md)

---

## 1. 역할

| 용도 | 권장 |
|------|------|
| 스토리/숏폼 **무드 BGM** | ACE-Step instrumental |
| 뮤비 **원곡** | `audio/masters/` 외부 음원 (AI 대체 비권장) |
| 대사 | Qwen3-TTS (별도) |
| 립싱크 driving | **보이스만** — BGM 섞지 말 것 |

---

## 2. 모델 설치 (필수)

워크플로: `F:\ComfyUI_workflows\audio_ace_step1_5_xl_turbo.json`

다운로드: [Comfy-Org/ace_step_1.5_ComfyUI_files](https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files)

```
ComfyUI/models/
  diffusion_models/ACESTEP1.5/acestep_v1.5_xl_turbo_bf16.safetensors
  vae/ACESTEP1.5/ace_1.5_vae.safetensors
  text_encoders/ACESTEP1.5/qwen_0.6b_ace15.safetensors
  text_encoders/ACESTEP1.5/qwen_4b_ace15.safetensors
```

(optional base) `acestep_v1.5_xl_base_bf16.safetensors` + `--profile base`

로컬에 가중치가 없으면 큐는 실패합니다. 노드·WF는 이미 있습니다.

---

## 3. CLI

```bash
# 일반 BGM (인스트 기본)
python scripts/generate_bgm.py \
  --prompt "soft piano, rainy cafe ambience, lo-fi warm pads, gentle, cinematic, 85 BPM" \
  --seconds 40 --bpm 85 --engine ace --profile turbo \
  -o F:/generated_audio/cafe_bed.mp3

# 에피소드 music stem
python scripts/episode_bgm.py -e sonagi_cafe_smoke_v1 \
  --prompt "intimate Korean ballad instrumental, soft guitar piano, rainy window mood, no vocals" \
  --seconds 45 --bpm 80 --name bgm_cafe_rain

# 폴백 (ACE 모델 없을 때)
python scripts/generate_bgm.py --engine sonilo \
  --prompt "ambient soft electronic bed" --seconds 30 -o bed.mp3
```

주요 플래그:

| 플래그 | 설명 |
|--------|------|
| `--prompt` | 스타일 태그 (ACE `tags`) |
| `--lyrics` | 가사 (기본 인스트면 무시) |
| `--with-vocals` | 보컬 허용 (기본 off) |
| `--seconds` | 길이 (약 5–240) |
| `--bpm` / `--keyscale` | 템포·조성 |
| `--profile turbo\|base` | turbo=8step 빠름 |
| `--engine ace\|sonilo` | 기본 ace |
| `--audio-codes` / `--no-audio-codes` | 기본 **ON** (OFF면 클리핑 쓰레기 PCM) |

---

## 3.1 알려진 장애 & 수정 (2026-07-12 ~ 07-14, 이 머신)

| 증상 | 원인 | 대응 |
|------|------|------|
| mp3는 생기는데 **소리 없음/먹먹** | `generate_audio_codes=False` → peak 풀스케일 상수 PCM | 기본 ON 유지. `validate_bgm_audio` hard fail |
| **~16s 이상** 한 방 생성 시 동일 쓰레기 PCM | 이 환경에서 ACE LM audio-codes 단일 샷 **~15s 이하만 안정**. 더 긴 요청은 상수 PCM | `generate_bgm` 이 **15s 청크 생성 → crossfade stitch** (`AGENT_ACE_CHUNK_SEC`, 기본 15) |
| ComfyUI **프로세스 종료** | LM sampling CUDA device-side assert (과거) | `ace15.py` float32 샘플링 가드 유지. assert 후 **Comfy 재시작** |
| 긴 생성 품질 저하 가능 | `ace15.py` `max_tokens=lm_metadata["min_tokens"]` 오타 (동일 값이 default일 땐 무해) | Comfy `comfy/text_encoders/ace15.py` 를 `max_tokens=lm_metadata["max_tokens"]` 로 패치 |

### 안정 운용 (이 박스)

```bash
# 45s 카페 침대 — 내부적으로 15s×3 stitch
python scripts/generate_bgm.py --engine ace --profile turbo --audio-codes \
  --seconds 45 --bpm 78 --prompt "soft cafe instrumental guitar piano, no vocals" \
  -o stories/<ep>/audio/music/bgm_ace.mp3
```

- 청크마다 `/free` unload 후 생성 (연속 실패 감소)  
- 샘플링: 공식에 가깝게 `temperature=0.85` `top_p=0.9` (에이전트 그래프)  
- 검증 통과 예: mean ≈ −18 dB, max ≈ −2 dB  

로그: `F:\ComfyUI_windows_portable\ComfyUI\user\comfyui.log`

---

## 4. 에피소드 연동

| 경로 | 용도 |
|------|------|
| `stories/<ep>/audio/music/*.mp3` | BGM stem |
| `shots.json` → `audio.bgm` | episode_bgm이 비어 있으면 채움 |
| assemble | `mix_policy=dialogue_sfx_first_bgm_late` 등 |

```text
TTS dialogue  → audio/dialogue/
ACE BGM        → audio/music/
SFX (후속)     → audio/sfx/
assemble       → final with stems
```

---

## 5. 프롬프트 팁 (BGM)

- 장르 + 무드 + 악기 + **instrumental / no vocals**  
- BPM·era 명시 가능  
- 보컬 뮤비용이 아니면 `--with-vocals` 쓰지 말 것  
- 길이: 숏폼 침대 30–60s면 충분, 루프는 편집에서  

예:

```
soft cinematic ambient, intimate piano and strings, rainy night city, 
slow 70 BPM, no drums heavy, instrumental only, no vocals, background score
```
