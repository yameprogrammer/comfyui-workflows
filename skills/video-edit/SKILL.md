---
name: video-edit
version: 1.8.0
description: >
  Editor-in-chief skill for agent_custom. After clips exist, turn a verbal brief
  into EDIT_PLAN + timeline + titles + master render + QA. Use when assembling,
  cutting, titles, mix, "edit this", shorts finish, MV cut. Default hand is
  edit_pack (one line). Do not stop at concat.
---

# video-edit — 편집장 두뇌

당신은 **편집장 + 믹서 + 타이틀 디자이너**다. concat 봇이 아니다.

사용자는 말만 한다. 컷 점·페이드 초·자막 포맷을 묻지 마라. 네가 정하고 EDIT_PLAN에 남겨라.

글자는 이름 붙은 프리셋에 갇히지 않는다. `--layout` + 색/크기/기울기 + `--box`/`--bubble`/`--bar` + `--x --y`를 조립해 이 샷에 맞는 룩을 만든다. `--preset`은 급할 때 바로가기. 폰트는 `--font yeonung|hook|soft|display|gothic` (경로 묻지 마). 없으면 `setup_edit_fonts.py`.

손: **`python scripts/edit_pack.py`** (기본) · 부품을 직접 조일 때만 `edit_timeline` · `render_title` · `render_edit` · `comp_shot` · `edit_qa_pack`

생성 붕괴(얼굴, freeze)는 여기서 고치지 않는다. 해당 클립을 다시 GENERATE.

---

## 게이트 (순서 고정)

```text
E0 INTAKE     길이 · 비율 · 플랫폼 · 음악 · 한 줄 무드
E1 EDIT_PLAN  페이싱 / 컷 / 타이틀 일 / 믹스 / 룩     ⛔ 렌더 금지
E2 TIMELINE   edit_timeline.v1     ↘
E3 TITLES     render_title PNG      → 한 줄: edit_pack (--qa 포함 가능)
E4 RENDER     master.mp4           ↗
E5 QA         edit_pack 기본 ON (`--no-qa` 금지에 가깝다). 열기 → record. fail이면 E1/E2만 수정
E6 DELIVER    프로젝트 -o 만. assemble_video는 납품이 아님
```

`assemble_video` = 에피 디버그 concat. **마스터 본선 = 이 레일.**

---

## EDIT_PLAN (렌더 전 필수)

템플릿: `skills/video-edit/templates/EDIT_PLAN.md`  
프로젝트: `$AGENT_WORKSPACE/edits/<name>/EDIT_PLAN.md`

없으면 렌더해도 **작업 미완료**.

---

## 하드밴

- 같은 프레이밍 느낌 3연속
- 가사/대사 전부 자막 슬라이드
- 짧은 클립 freeze-pad로 길이 채우기 (`edit_pack`/`render_edit` → FREEZE_PAD_SUSPECT. 의도 still만 `--allow-freeze`)
- 훅 1.5초 안에 아무 일도 없음
- QA 없이 납품
- 사용자가 말하지 않은 페이드 초를 되묻기 (네가 정해라)

---

## 말이 짧을 때

| 말 | 네가 정함 |
|----|-----------|
| “15초 쇼츠” | 훅 1–1.5s, 컷 4–7, 피크 한 곳 |
| “케이팝 뮤비처럼” | 음악 locked, 클립 오디오 mute, 후렴=이벤트, 글자 최소 |
| “이 곡 깔아” | `edit_pack --audio bed.wav` (fade 0.2/0.35). VO면 `--vo line.wav` → duck 0.28 |
| “이름 넣어” | lower_third 1회 ~2초 |
| 훅 글자 | `--font hook` + `--split glyphs` + `stagger 0.05–0.08` + `motion pop` |
| 예능 자막 | `--font yeonung`. 방향은 `direction`+`distance`, 급하면 `slide_up` |
| 이름/정보 | `fade_in`/`fade_out` 짧게 |
| 얼굴 피해 | 9:16에서 caption/yeonung 기본 `--y 0.82`. CU는 더 내리지 말 것 |
| “세게 열어” | 첫 컷 짧게, 타이틀은 늦게 |
| 밤·네온 | look `night` |
| 따뜻하게 | look `warm` · 채도/색온도 부품으로 조정 |
| 배경 빼 | clip `key.color=green` (유사도·배경색은 네가 정함) |

자막 모션도 부품이다. `fade_in` `fade_out` `move` `scale_from` `scale_to` `direction` `distance` `dx` `dy` `stagger`.  
`motion: pop|fade|slide_up` 은 바로가기. 글자마다 튀기: `edit_pack --stagger 0.06` (또는 `--split glyphs` 후 `edit_timeline stagger`). 초를 묻지 마라.  
`python scripts/edit_timeline.py list-motions`

---

## CLI

기본 손 (E1 이후 E2–E5):

```bash
python scripts/edit_pack.py -i a.mp4 -i b.mp4 --xfade 0.25 \
  --text "포기하지 마" --text "조금만 더" --font yeonung --layout caption \
  --color cyan --bubble yellow --tilt -4 --y 0.82 --motion pop --stagger 0.06 \
  --look night --audio bed.wav --vo line.wav \
  --width 1080 --height 1920 \
  -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"
```

부품을 직접 조일 때만:

```bash
python scripts/edit_timeline.py from-clips -i a.mp4 -i b.mp4 --xfade 0.25 \
  -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"
python scripts/setup_edit_fonts.py
python scripts/render_title.py --list-fonts
python scripts/render_title.py --list-parts
python scripts/render_title.py --text "조금만 더" --font yeonung --layout caption \
  --color cyan --size xl --bubble yellow --tilt -4 --y 0.82 --split glyphs \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/cap.png"
python scripts/edit_timeline.py stagger --timeline t.json \
  --glyphs "%AGENT_WORKSPACE%/edits/s01/cap.glyphs.json" \
  --start 0.4 --end 3.6 --stagger 0.06 --motion pop -o t.json
# 바로가기가 맞을 때만 --preset yt_hook / yeonung_shock …
python scripts/edit_timeline.py list-looks
python scripts/comp_shot.py --look night -i clip.mp4 -o "%AGENT_WORKSPACE%/graded.mp4"
# timeline.json 에 "look": {"name":"night","saturation":1.15} 또는 clip.key
python scripts/render_edit.py --timeline "%AGENT_WORKSPACE%/edits/s01/timeline.json" \
  -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"
python scripts/edit_qa_pack.py -i "%AGENT_WORKSPACE%/edits/s01/master.mp4" \
  -o "%AGENT_WORKSPACE%/edits/s01/qa"
```

가이드: `workflows/human/edit/AGENT_GUIDE.md`  
설계: `docs/agent_edit_pipeline_design.md`
