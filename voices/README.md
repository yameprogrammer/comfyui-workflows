# Voice library (Qwen3-TTS clone profiles)

Register **your voice** or **talent samples** for clone TTS.

```bash
# Register — ideal 5–15s, hard max ~30s
python scripts/voice_register.py --id my_voice_v1 --name "Park" \
  --ref F:/samples/me_12s.wav \
  --ref-text "레퍼런스 오디오에서 말한 문장 그대로" \
  --language Korean \
  --instruct "calm warm narration"

python scripts/voice_register.py --list

# Clone + emotion stage direction
python scripts/generate_qwen3_tts.py --voice-id my_voice_v1 \
  --instruct "soft sad, quiet" \
  --text "이 목소리로 새 대사를 읽습니다." \
  -o out.mp3
```

UI: `workflows/human/qwen3_tts/voice_clone_qwen3_tts.json`  
Guide: `workflows/human/qwen3_tts/AGENT_GUIDE.md`  
Pipeline notes: `docs/qwen3_tts_ltx_audio_pipeline.md`

First **clone** may download **Base** into `ComfyUI/models/Qwen3-TTS/`.
