# characters/ — AI 에이전트용 캐릭터 패키지 루트

## 구조

```text
characters/
  _template/           # 새 캐릭터 복사 원본
  schemas/             # bible / manifest JSON Schema
  sheet_presets.json   # 시트 생성 프리셋 SSOT (prompt/denoise/cfg)
  pilots/              # 파일럿 캐릭터 브리프·샘플 프롬프트
  <character_id>/      # 실제 패키지 (create 후 생성)
```

## 구현·운영 문서

| 문서 | 용도 |
|------|------|
| [../character_impl_spec.md](../character_impl_spec.md) | **코딩 착수 스펙** (필수) |
| [../character_sheet_system_design.md](../character_sheet_system_design.md) | 기획·리서치·장기 로드맵 |
| [../video_pipeline_roadmap.md](../video_pipeline_roadmap.md) | 영상 파이프라인 |

## 활성 트랙

`CHARACTER_L2_SOFT_FACTORY` — P1 기존 CLI 패치 → P2 create/expand/approve  
자세한 내용: `character_impl_spec.md` §0
