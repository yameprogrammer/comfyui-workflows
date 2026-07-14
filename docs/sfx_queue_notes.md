# SFX 큐 배치 노트 (P2-3 · 선택)

- **상태**: 관례 문서 (전용 CLI 없이 assemble `layered` / `dialogue_sfx_first_bgm_late` 로 운용)
- **경로**: `stories/<ep>/audio/sfx/*.wav|mp3`

## shots.json 예

```json
{
  "shot_id": "S03",
  "audio_refs": {
    "dialogue": { "path": "audio/dialogue/S03_qwen3tts.mp3" },
    "driving": { "path": "audio/exports/s2v_drive/S03_drive_center_voicey.wav" },
    "sfx": [
      { "path": "audio/sfx/cup_clink.wav", "at_sec": 1.2, "gain": 0.8 }
    ]
  }
}
```

- `at_sec`: **샷 시작 기준** 타임라인 오프셋 (assemble layered 믹스)
- 파일은 에피소드 `audio/sfx/` 에 두고 짧은 원샷 큐만 넣기
- BGM은 `audio/music/` + `mix_policy=bgm_under` (Suno 등 외부 생성 OK)

## 라이브러리 시드 (직접 채움)

| 파일 예 | 용도 |
|---------|------|
| `cup_clink.wav` | 잔 부딪힘 |
| `soft_whoosh.wav` | 컷 전환 |
| `page_turn.wav` | UI/텍스트 |

저작권 있는 상용팩 대신 직접 녹음·무료 라이선스 샘플 권장.
