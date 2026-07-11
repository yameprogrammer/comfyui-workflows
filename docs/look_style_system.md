# 🎨 Look / Style Core — 얇은 글로벌 룩 팩

- **작성일**: 2026-07-11  
- **상태**: 설계 + 최소 템플릿  
- **목적**: 캐릭터·로케와 별도로 **영상 전체 톤/그레이딩/매체 느낌**을 한 곳에서 고정  
- **관련**: [production_asset_pipeline.md](production_asset_pipeline.md), [storyboard_pipeline_design.md](storyboard_pipeline_design.md)

---

## 1. 왜 필요한가

커뮤니티·플랫폼의 asset card 3종:

| 카드 | 우리 대응 |
|------|-----------|
| Character | `characters/` |
| Environment | `locations/` |
| **Style / Look** | **`looks/`** (본 문서) |

룩이 없으면 샷마다 “시네마틱” 해석이 달라져 연속성이 깨진다.

**의도적으로 얇게** 둔다. 풀 아트 디렉션 시스템이 아니라 **프롬프트 코어 + 메타** 수준.

---

## 2. 결과물

| 파일 | 역할 |
|------|------|
| `prompts/positive_core.txt` | 전 샷 appearance에 붙는 룩 블록 (필름 톤, 렌즈, 색, 그레인) |
| `prompts/negative_core.txt` | 룩 붕괴 방지 (과채도, 다른 매체 스타일 등) |
| `bible.json` | look_id, 매체, 참고 키워드 |
| (선택) `refs/mood/` | 1~4장 무드 보드 이미지 |

---

## 3. 디렉터리

```text
looks/
  _template/
  cinematic_moody_v1/          # 기본 룩 예
    bible.json
    prompts/
      positive_core.txt
      negative_core.txt
    refs/mood/
```

에피소드 `shots.json` / episode meta:

```json
{
  "look_id": "cinematic_moody_v1",
  "format": "cinematic_16x9"
}
```

---

## 4. 프롬프트 조립 순서 (고정)

```text
appearance =
  look.positive_core
  + character.positive_core(s)
  + location.positive_core
  + shot action/camera
  + quality_suffix
```

negative = look.neg ∪ character.neg ∪ location.neg ∪ shot.neg

**룩은 항상 맨 앞(또는 공통 접두)** 에 두어 전역 톤을 먹인다.

---

## 5. 기본 룩 `cinematic_moody_v1`

Moody / Z-Image 실사 영상용 시작점. 에피소드가 다르면 `looks/<new_id>/` 복사 후 수정.

---

## 6. 구현 티켓

| ID | 내용 | 상태 |
|----|------|------|
| K0 | 본 문서 + template + default look | ✅ |
| K1 | shot_compose에 look_id 주입 | ⬜ (S3와 함께) |
| K2 | episode 기본 look 검증 | ⬜ |

---

## 7. 하지 말 것

- 룩마다 캐릭터/로케 패키지를 복제하지 말 것  
- 룩에 구체 인물·구체 장소를 넣지 말 것 (그건 char/loc 책임)  
