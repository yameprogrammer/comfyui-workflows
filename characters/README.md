# characters/ — AI 에이전트용 캐릭터 패키지 루트

## 구조

```text
characters/
  _template/           # 새 캐릭터 복사 원본
  schemas/             # bible / manifest JSON Schema
  sheet_presets.json   # 시트 생성 프리셋 SSOT (prompt/denoise/cfg)
  profiles.json        # 용도 프로필 SSOT (video_ref | artbook)
  pilots/              # 파일럿 캐릭터 브리프·샘플 프롬프트
  <character_id>/      # 실제 패키지 (create 후 생성)
```

## 용도 프로필 (planned CLI: `--profile`)

| 프로필 | 용도 | 기본 해상도 감 |
|--------|------|----------------|
| **`video_ref`** (default) | 영상 일관성 첨부 팩 | ~1024² |
| **`artbook`** | 고퀄 프레젠/인쇄 지향 시트 | ~1536²+ |

상세: [../character_impl_spec.md](../character_impl_spec.md) §1.5, [profiles.json](profiles.json)

## 구현·운영 문서

| 문서 | 용도 |
|------|------|
| [../character_impl_spec.md](../character_impl_spec.md) | **코딩 착수 스펙** (필수) |
| [../character_sheet_system_design.md](../character_sheet_system_design.md) | 기획·리서치·장기 로드맵 |
| [../video_pipeline_roadmap.md](../video_pipeline_roadmap.md) | 영상 파이프라인 |

## 활성 트랙

`CHARACTER_L2_SOFT_FACTORY` — P2 완료 → 다음 **P2.5 프로필** 또는 ControlNet turnaround  
자세한 내용: `character_impl_spec.md` §0
