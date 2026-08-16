# output-review — Agent Guide

> **Shelf:** REVIEW  
> **Comfy:** 없음  
> **Specialty:** 원오프 `generate_*` 결과물을 brief에 맞춰 열고 판정한다. exit 0 ≠ 완료.

스킬 SSOT: [skills/output-review/SKILL.md](../../../skills/output-review/SKILL.md)

## When / When not

| 목표 | 도구 | 쓰지 말 때 |
|------|------|------------|
| 원오프 스틸/클립/오디오 평가 | **`review_media`** | 에피소드 샷 → `shot_qa_*` |
| fail 다음 CLI | `review_media lever <ID>` | 같은 프롬프트 재생성 |
| 에피 키프레임/클립 | `shot_qa_pack` | 원오프 `-o` 한 장 |
| 편집 마스터 | `edit_qa_pack` | 생성 직후 스틸 |

## CLI

```bash
python scripts/review_media.py pack -i hero.png --intent "medium, yellow parasol" -o "%AGENT_WORKSPACE%/reviews/hero"
python scripts/review_media.py record --pack "%AGENT_WORKSPACE%/reviews/hero" --verdict pass --opened --notes "opened; hands OK"
python scripts/review_media.py lever S4_anatomy
```

pass 에 `--opened` 없으면 exit 23.
