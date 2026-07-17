# Qwen3-TTS · LTX 2.3 · 립싱크 음성 파이프라인

- **작성일**: 2026-07-12  
- **목적**: 대사/내레이션 TTS를 에이전트 CLI로 생성하고, 기존 SI2V(립싱크) 및 LTX audio-conditioned 영상과 연결  
- **관련**: [audio_motion_production_modes.md](audio_motion_production_modes.md), Rule 7.1

---

## 1. 리서치 요약 (커뮤니티 2026)

### 1.1 Qwen3-TTS (맞음 — 설계·복제 둘 다)

공식 Qwen3-TTS 패밀리:

| 모델 | 역할 |
|------|------|
| **CustomVoice** | 프리셋 화자(Vivian, Ryan, **Sohee** 등) + `instruct`로 감정/스타일 |
| **VoiceDesign** | 자연어로 **새 목소리 설계** (“차분한 20대 한국 여성 내레이터…”) |
| **Base** | 짧은 ref 오디오로 **보이스 클론** (+ ref_text 권장) |

ComfyUI: [DarioFT/ComfyUI-Qwen3-TTS](https://github.com/DarioFT/ComfyUI-Qwen3-TTS) 및 로컬 `FB_Qwen3TTS*` / `comfyui-qwen3-tts`.

실무 팁 (커뮤니티 + 이 레포):
- 클론 ref **5–15초** 이상적 · **최대 ~30초** (CLI 기본 상한; 그 이상 hang·품질 저하)
- `ref_text` 전사 있으면 유사도 상승
- CustomVoice `instruct`: `"soft sad whisper"`, `"angry short burst"` 등
- Clone 감정: (1) 감정 연기 ref (2) `--instruct` → 타깃 대본 stage direction (노드에 instruct 소켓 없음)
- UI SSOT: `workflows/human/qwen3_tts/voice_clone_qwen3_tts.json` 등 · 가이드 `…/qwen3_tts/AGENT_GUIDE.md`
- 언어: KO/EN/JA/… 10개 지원

**이 머신 상태 (프로브)**:
- 노드: `FB_Qwen3TTSCustomVoice` / `VoiceDesign` / `VoiceClone` 등 로드됨  
- 모델: `models/Qwen3-TTS/Qwen3-TTS-12Hz-1.7B-CustomVoice` 설치됨  
- VoiceDesign / Base 클론 모델은 첫 사용 시 다운로드 필요할 수 있음  

### 1.2 LTX 2.3 오디오 역할 (혼용 포인트)

커뮤니티·공식 가이드에서 LTX 쪽은 **두 겹**으로 쓰인다:

| 경로 | 무엇 | 감정 대사에 |
|------|------|-------------|
| **A. 외부 TTS → LTX audio-cond I2V** | Qwen3-TTS(또는 FishAudio 등)로 wav 생성 → LTX/IA2V/InfiniteTalk에 driving | **주력 추천** — 대본 통제 + 립싱크 |
| **B. LTX native A/V** | 한 패스에 영상+앰비언스/대사 생성 | 애드립·분위기용; 대본 정확도는 TTS 경로보다 약할 수 있음 |
| **C. LTX speech-as-model + ID LoRA** | 실험적 “standalone speech / sound ref” | 후속 실험 |

YouTube/Patreon 관행 (**Qwen3-TTS + LTX-2 talking avatar**):
1. 키프레임 이미지  
2. Qwen3-TTS로 대사 wav (clone 또는 design)  
3. LTX I2V **custom audio** / A2V 파이프에 wav 주입 → 립·표정 연동  

**우리 레포 매핑**:
- (2) = `generate_qwen3_tts` / `episode_tts`  
- (3) = 기존 **`episode_s2v`** (`ltx23_ia2v` 기본) 또는 InfiniteTalk  
- 클린 TTS가 SI2V 품질에 유리하다는 기존 실측(process.md)과 일치  

### 1.3 “감정 섞인 대사” 레시피

```text
감정 지시
  ├─ CustomVoice: --instruct "quietly sad, soft breath, intimate"
  ├─ VoiceDesign: --instruct "20대 한국 여성, 비 오는 창가, 낮은 볼륨, 슬픔"
  └─ Clone: 감정 연기가 담긴 5–12s ref 녹음

대본 품질
  ├─ 짧은 문장 단위로 잘라 TTS (한 샷 3–8초 대사)
  └─ 샷.dialogue 필드 = 립싱크 대본 SSOT

영상
  ├─ keyframe (얼굴 잘 보이는 medium/close)
  ├─ driving = TTS → center_voicey prep
  └─ episode_s2v --backend ltx23_ia2v
```

FishAudio S2 등 외부 감정 TTS도 driving wav만 맞으면 동일 SI2V 경로에 꽂을 수 있다.  
**에이전트 기본 엔진은 로컬 Qwen3-TTS**.

---

## 2. 에이전트 공정 (Production)

```text
story dialogue cut
  → episode_tts (--text / shot.dialogue, mode=custom|design|clone)
  → audio/dialogue/S0x_qwen3tts.mp3
  → prepare_driving (center_voicey|auto)
  → audio_refs.driving + motion_driver=si2v
  → episode_s2v (LTX / InfiniteTalk)
  → assemble (dialogue stem + mix_policy)
```

VO-only (입 안 움직임): TTS → `audio/vo/` 만 넣고 `motion_driver=i2v` 유지.

---

## 3. 어색함 조정

| 손잡이 | 효과 | 권장 |
|--------|------|------|
| `--instruct` | 감정·연출 | 구체적이되 과장 줄이기 |
| `--temperature` | 낮을수록 안정 | 어색하면 **0.65–0.8** |
| `--top-p` / `--top-k` | 다양성 | 기본 0.8 / 20 |
| `--repetition-penalty` | 반복 완화 | 1.05–1.15 |
| `--seed` | 재현 | 좋은 결과 고정 |
| 대본 길이 | 길면 리듬 붕괴 | **문장 단위** 분할 |
| 화자 | Sohee 등 | 캐릭 톤에 맞게 교체 |

```bash
# 기쁨이 과장되면 이렇게 부드럽게
python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee --language Korean \
  --instruct "warm gentle happy, natural smile in voice, not exaggerated" \
  --temperature 0.7 --top-p 0.75 \
  --text "오늘 정말 기뻐. 좋은 소식이 와서 설레." \
  -o out_happy_soft.mp3
```

---

## 4. CLI

```bash
# 프리셋 + 감정
python scripts/generate_qwen3_tts.py \
  --mode custom --speaker Sohee --language Korean \
  --instruct "soft sad, quiet, intimate" --temperature 0.75 \
  --text "비가 오네. 창밖이 흐려." -o line01.mp3

# Voice design (모델 첫 실행 시 다운로드 가능)
python scripts/generate_qwen3_tts.py --mode design --language Korean \
  --instruct "20대 한국 여성, 낮은 톤 내레이션" \
  --text "그날 오후…" -o narr.mp3

# --- 보이스 클론 (본인 / 타인) ---
python scripts/voice_register.py --id my_voice_v1 --name "Me" \
  --ref path/to/clean_8s.wav \
  --ref-text "레퍼런스에서 말한 문장 그대로" --language Korean

python scripts/generate_qwen3_tts.py --voice-id my_voice_v1 \
  --text "복제 목소리로 새 대사" -o clone_line.mp3

# 일회성 클론
python scripts/generate_qwen3_tts.py --mode clone \
  --ref-audio talent.wav --ref-text "…" --text "…" -o talent.mp3

# 샷 바인딩 + SI2V
python scripts/episode_tts.py -e my_ep -s S02 \
  --voice-id my_voice_v1 --text "..." --bind-si2v
python scripts/episode_s2v.py -e my_ep --shots S02
```

---

## 5. 파일 규약

| 경로 | 용도 |
|------|------|
| `voices/<id>/ref.*` + `voice.json` | 등록된 클론 프로필 |
| `stories/<ep>/audio/dialogue/S0x_qwen3tts.mp3` | 온스크린 대사 |
| `stories/<ep>/audio/vo/S0x_qwen3tts.mp3` | 내레이션 |
| `stories/<ep>/audio/exports/s2v_drive/S0x_*.wav` | SI2V driving |
| `stories/<ep>/meta/S0x_tts.json` | 시드·화자·instruct |

샷 필드: `dialogue` / `vo`, `audio_refs.tts`, `audio_refs.driving`, `motion_driver=si2v`

---

## 6. 한계 · 후속

| 항목 | 상태 |
|------|------|
| CustomVoice 로컬 | ✅ 1.7B + 튜닝 CLI |
| Clone 등록 | ✅ `voice_register` + `--voice-id` |
| Base / VoiceDesign 체크포인트 | 첫 clone·design 시 다운로드 |
| LTX native dialogue-in-one-pass | 보조; 본선 TTS→SI2V |
| 캐릭터 bible ↔ voice_id 자동 링크 | 후속 |

---

## 6. 참고

- Qwen blog: Qwen3-TTS Voice Design / Clone / CustomVoice  
- github.com/DarioFT/ComfyUI-Qwen3-TTS  
- Benji / IAMCCS: Qwen3-TTS + LTX-2 talking avatar (YouTube/Patreon)  
- HuggingFace RuneXX LTX-2 workflows: I2V + Qwen TTS voice clone  
- LTX 2.3: native A/V + A2Vid audio-conditioned talking portraits  
