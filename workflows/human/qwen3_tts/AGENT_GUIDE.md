# Qwen3-TTS 도구 가이드 (음성 복제 · 감정 · 프리셋)

ComfyUI **Qwen3-TTS** 노드를 에이전트 CLI로 호출합니다.  
이 레포의 다른 도구와 같이 **골라 쓰는 TTS 도구**이며, 영상 파이프라인 전체가 필수이지 않습니다.

## UI 원본 (`workflows/human/qwen3_tts/`)

| 파일 | 역할 |
|------|------|
| **`voice_clone_qwen3_tts.json`** | **음성복제** — `LoadAudio` + `FB_Qwen3TTSVoiceClone` + `SaveAudio` |
| `custom_voice_qwen3_tts.json` | 프리셋 화자 + instruct 감정 (`FB_Qwen3TTSCustomVoice`) |
| `voice_design_qwen3_tts.json` | 자연어 보이스 디자인 (`FB_Qwen3TTSVoiceDesign`) |
| `custom_voice_loader_qwen3_tts.json` | 별 로더 팩 (참고) |

소스 이름 예: Comfy `user/default/workflows/음성복제TTS-Qwen3-TTS.json`

## CLI

```bash
# --- 음성 복제 (핵심) ---
python scripts/generate_qwen3_tts.py --mode clone \
  --ref-audio sample_20s.wav \
  --ref-text "샘플에서 말한 문장 그대로" \
  --language Korean \
  --instruct "quietly sad, soft, intimate" \
  --text "비가 오네. 창밖이 흐려." \
  -o out_clone.mp3

# 등록 보이스 재사용
python scripts/voice_register.py --id hero_v1 --name "Hero" \
  --ref sample_20s.wav --ref-text "..." --language Korean \
  --instruct "calm warm narration"
python scripts/generate_qwen3_tts.py --voice-id hero_v1 \
  --instruct "angry short burst" \
  --text "지금 당장 나가." -o line.mp3

# --- 감정 + 프리셋 화자 (클론 아님) ---
python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee \
  --instruct "soft happy, natural smile in voice" \
  --text "오늘 정말 기뻐." -o happy.mp3

# --- 보이스 디자인 ---
python scripts/generate_qwen3_tts.py --mode design \
  --instruct "20대 한국 여성, 낮은 톤, 비 오는 창가 내레이션" \
  --text "그날 오후…" -o design.mp3
```

## 감정(emotion) 구조

| 모드 | 감정 넣는 방법 |
|------|----------------|
| **custom** | `--instruct` → 노드 **instruct** 필드 (1순위 추천) |
| **design** | `--instruct` 필수 (보이스 성격+감정) |
| **clone** | (1) **감정 연기된 ref 샘플** 권장 · (2) `--instruct` → 타깃 대본 앞에 stage direction `(instruct) text` (노드에 instruct 소켓 없음) |

클론에서 감정이 약하면:
- ref를 같은 감정으로 짧게 다시 녹음 (5–15s)
- 또는 custom + 비슷한 speaker로 감정 잡고, 음색만 clone 비교

## 샘플 길이 (중요)

| | 권장 |
|--|------|
| **이상적** | **5–15초** 클린 스피치 (잡음·음악 최소) |
| **실무 상한** | **~30초** — 이 레포 CLI 기본 거부 한도 |
| **너무 김** | hang · 클론 품질 저하 · VRAM 부담 |

```bash
# 30초 초과 시 기본 FAIL (REF_TOO_LONG)
# 강제: --allow-long-ref  (비권장)
```

`--ref-text`에 **샘플이 말한 문장을 정확히** 넣으면 유사도가 올라갑니다.

## 튜닝

| 손잡이 | 효과 |
|--------|------|
| `--temperature` | 0.6–0.8 안정 · 높을수록 과장 |
| `--top-p` / `--top-k` | 다양성 |
| `--repetition-penalty` | 반복 완화 1.05–1.15 |
| `--x-vector-only` | 클론 음색 위주 (대사 누수 완화 시도) |
| `--unload-after` | 생성 후 모델 언로드 (VRAM) |
| 대본 길이 | 문장 단위로 자르기 (한 줄에 장문 비권장) |

## 다른 도구와 연결 (선택)

```text
TTS wav
  → scripts/audio_prepare_driving.py (center_voicey)
  → generate_s2v / episode_s2v  (립·오디오 연동 I2V)
```

필수 아님 — 오디오만 필요하면 TTS 단독 완료.

## 카탈로그

- 도구 표: [docs/tool_catalog.md](../../../docs/tool_catalog.md)
- 장문 파이프 메모: [docs/qwen3_tts_ltx_audio_pipeline.md](../../../docs/qwen3_tts_ltx_audio_pipeline.md)
- `voices/` 등록: [voices/README.md](../../../voices/README.md)
