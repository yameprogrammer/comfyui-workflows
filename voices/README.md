# Voice library (Qwen3-TTS clone profiles)

Register **your voice** or **talent samples** for consistent dialogue / SI2V driving.

```bash
# Register (5–15s clean speech recommended)
python scripts/voice_register.py --id my_voice_v1 --name "Park" \
  --ref F:/samples/me_8s.wav \
  --ref-text "레퍼런스 오디오에서 말한 문장 그대로" \
  --language Korean

# List
python scripts/voice_register.py --list

# Generate with clone
python scripts/generate_qwen3_tts.py --voice-id my_voice_v1 \
  --text "이 목소리로 새 대사를 읽습니다." \
  -o out.mp3

# Episode bind + lip-sync prep
python scripts/episode_tts.py -e my_ep -s S02 \
  --voice-id my_voice_v1 \
  --text "..." --bind-si2v
```

First **clone** run may download Qwen3-TTS **Base** model into  
`ComfyUI/models/Qwen3-TTS/` (CustomVoice alone is not enough for clone).

See `docs/qwen3_tts_ltx_audio_pipeline.md`.
