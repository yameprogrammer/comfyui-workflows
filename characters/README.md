# characters/ — AI 에이전트용 캐릭터 패키지 루트

## 구조

```text
characters/
  _template/           # 새 캐릭터 복사 원본
  casts/               # Phase A 탐색 풀 (다엔진 후보, identity 미고정)
  schemas/             # bible / manifest JSON Schema
  sheet_presets.json   # 시트 생성 프리셋 SSOT (prompt/denoise/cfg)
  profiles.json        # 용도 프로필 SSOT (video_ref | artbook)
  pilots/              # 파일럿 캐릭터 브리프·샘플 프롬프트
  <character_id>/      # 정식 패키지 (promote/create 후)
```

## 캐릭터 공정 (권장)

```text
A  cast_pool   다엔진 후보 (Moody real/pro/wild, Krea…)
B  promote     고른 1장 → 패키지 + master_front 승인
C  expand      I2I 일관 시트 (표정/턴/의상)
D  video       shot_compose → I2V/SI2V
```

```bash
python scripts/character_cast_pool.py --cast heroine_cast -p "..." --engines moody_pro,krea --per-engine 3
python scripts/character_promote.py --from characters/casts/heroine_cast/candidates/....png --id hero_v1 --name "Hero" --cast heroine_cast
python scripts/character_expand_sheets.py --id hero_v1 --sheets all_mvp
```

상세: [../docs/character_casting_pipeline.md](../docs/character_casting_pipeline.md)

## 용도 프로필

| 프로필 | 용도 | 기본 해상도 감 |
|--------|------|----------------|
| **`video_ref`** (default) | 영상 일관성 첨부 팩 | ~1024² |
| **`artbook`** | 고퀄 프레젠/인쇄 지향 시트 | ~1536²+ |

상세: [../docs/character_impl_spec.md](../docs/character_impl_spec.md) §1.5, [profiles.json](profiles.json)

## 구현·운영 문서

| 문서 | 용도 |
|------|------|
| [../character_impl_spec.md](../character_impl_spec.md) | **코딩 착수 스펙** (필수) |
| [../character_sheet_system_design.md](../character_sheet_system_design.md) | 기획·리서치·장기 로드맵 |
| [../video_pipeline_roadmap.md](../video_pipeline_roadmap.md) | 영상 파이프라인 |

## 활성 트랙

`CHARACTER_L2_SOFT_FACTORY` — P2 완료 → 다음 **P2.5 프로필** 또는 ControlNet turnaround  
자세한 내용: `character_impl_spec.md` §0
