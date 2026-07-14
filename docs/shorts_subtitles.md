# 쇼츠 자막 (P2-2)

- **CLI**: `python scripts/episode_subtitles.py -e <ep>`
- **SRT**: `stories/<ep>/exports/final/<ep>.srt` (UTF-8 BOM)
- **타이밍**: 샷 순서 누적 — work 클립 길이 우선, 없으면 `duration_sec`
- **대사 소스**: `dialogue` → `vo` → `subtitle` → `caption`
- **소프트 번인**:
  ```bash
  python scripts/episode_subtitles.py -e EP --burn \
    --video stories/EP/exports/final/EP_final_1080.mp4
  ```
  → `*_subs.mp4` (libass force_style, 하단 중앙)

Grok/YouTube 업로드용 SRT와 번인본을 분리 제공 가능.
