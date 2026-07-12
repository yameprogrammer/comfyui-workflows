# Look / Style Core — Production v1

- **작성일**: 2026-07-11 · **갱신**: 2026-07-12  
- **상태**: **Production v1 READY**  
- **목적**: 캐릭터·로케와 별도로 **영상 전체 톤**을 고정  
- **관련**: production_asset_pipeline, shot_compose, character_casting

---

## 0. 한 줄

```text
looks/<look_id>/prompts/positive_core.txt  →  모든 키프레임 appearance 접두
```

룩이 없으면 샷마다 “시네마틱” 해석이 갈라진다.

---

## 1. 공정 (실무)

```text
1) look_create   — 새 룩 패키지 (또는 cinematic_moody_v1 사용)
2) look_status   — cores 검증 · --approve
3) episode       — shots.json look_id 지정 (story_init / commission)
4) shot_compose  — look 코어 자동 주입 (이미 연동)
```

### CLI

```bash
# 목록 / 검증
python scripts/look_status.py --list
python scripts/look_status.py --id cinematic_moody_v1

# 새 룩 (기본 룩 시드)
python scripts/look_create.py --id noir_rain_v1 --name "Noir Rain" \
  --from-default \
  --positive "wet asphalt reflections, cool teal-orange grade, anamorphic bokeh, night rain, film still" \
  --keywords "noir,rain,teal-orange" \
  --status draft
python scripts/look_status.py --id noir_rain_v1 --approve

# 에피소드에서 사용
# shots.json: "look_id": "noir_rain_v1"
python scripts/shot_compose.py -e <ep> --shot S01 --look noir_rain_v1
```

---

## 2. 디렉터리

```text
looks/
  _template/
  cinematic_moody_v1/     # 기본 승인 룩
    bible.json
    prompts/
      positive_core.txt   # 전역 톤 (필수, 충분히 구체적)
      negative_core.txt
    refs/mood/            # 선택 무드보드 1~4장
```

**하지 말 것:** 룩에 구체 인물명·구체 장소명 넣기 (char/loc 책임).

---

## 3. 프롬프트 조립 (고정)

```text
appearance =
  look.positive_core
  + character.positive_core
  + location.positive_core
  + shot action / camera / framing
  + quality_suffix
```

`shot_compose` 가 이 순서로 조립한다 (K1 ✅).

---

## 4. Definition of Done (v1)

| 항목 | 상태 |
|------|------|
| template + default look | ✅ |
| look_create / look_status | ✅ |
| shot_compose look 주입 | ✅ |
| episode_status look 검증 | ✅ |
| 얇은 bible + cores | ✅ |
| mood ref 필수 | ❌ 선택 (의도적) |
| ControlNet 스타일 전용 엔진 | ⬜ 후속 |

---

## 5. 캐릭터 공정과의 관계

| 공정 | 역할 |
|------|------|
| Character A/B/C | **누구** (identity) |
| Look | **어떤 필름/그레이드** (global tone) |
| Location | **어디** |

룩은 캐릭터 시트를 대체하지 않는다. C expand identity 엔진과도 독립 (look = 톤, char = 누구).

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안 템플릿 |
| 2026-07-12 | Production v1: create/status + episode look check |
