# EDIT — Agent Guide

> **Shelf:** EDIT  
> **Comfy:** 없음  
> **스킬:** `skills/video-edit/SKILL.md` — 렌더 전 EDIT_PLAN 필수

사용자는 말만 한다. concat으로 납품하지 마라.

---

## When / When not

| 목표 | 도구 | 말고 |
|------|------|------|
| 클립+자막+룩 → 마스터 | **`edit_pack`** | concat / assemble_video 납품 |
| 클립을 타임라인에 | `edit_timeline from-clips` | 에피 디버그 concat → assemble_video |
| 한글 훅/이름 | `render_title` | 가사 전부 올리기 |
| 이미 있는 timeline | `render_edit` | 처음부터면 edit_pack |
| 열어보기 | `edit_qa_pack` + record | 생성 샷 QA → shot_qa_* |

---

## CLI

```bash
python scripts/edit_pack.py -i a.mp4 -i b.mp4 --xfade 0.25 \
  --text "포기하지 마" --text "조금만 더" --font yeonung --motion pop --stagger 0.06 \
  --look night --audio bed.wav --vo line.wav \
  --width 1080 --height 1920 \
  -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"

python scripts/edit_timeline.py from-clips -i a.mp4 -i b.mp4 --xfade 0.25 \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"

python scripts/setup_edit_fonts.py
python scripts/render_title.py --list-fonts
python scripts/render_title.py --list-parts
python scripts/render_title.py --text "조금만 더" --font yeonung --layout caption \
  --color cyan --size xl --bubble yellow --tilt -4 --y 0.82 \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/cap.png"
python scripts/render_title.py --preset yt_hook --text "포기하지 마" \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/hook.png"

# overlays: path + start/end + motion parts (or shortcut pop|fade|slide)
#   fade_in fade_out move scale_from scale_to direction distance dx dy
python scripts/edit_timeline.py list-motions
python scripts/render_title.py --split glyphs --text "포기하지 마" --font yeonung \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/cap.png"
python scripts/edit_timeline.py stagger --timeline t.json \
  --glyphs "%AGENT_WORKSPACE%/edits/s01/cap.glyphs.json" \
  --start 0.4 --end 3.6 --stagger 0.06 --motion pop -o t.json
python scripts/comp_shot.py --list-looks
python scripts/comp_shot.py --look night -i clip.mp4 -o "%AGENT_WORKSPACE%/graded.mp4"
# timeline "look": {"name":"night"} 또는 clip.key
python scripts/render_edit.py --timeline "%AGENT_WORKSPACE%/edits/s01/timeline.json" \
  -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"

python scripts/edit_qa_pack.py -i "%AGENT_WORKSPACE%/edits/s01/master.mp4" \
  -o "%AGENT_WORKSPACE%/edits/s01/qa"
python scripts/edit_qa_record.py --pack "%AGENT_WORKSPACE%/edits/s01/qa" \
  --verdict pass --notes "hook reads"
```

`-o` 는 프로젝트. 이 레포에 쓰면 exit 14.

---

## 게이트

E0 말 → E1 EDIT_PLAN → E2 timeline → E3 titles → E4 render → E5 QA → E6 deliver

문서: `docs/agent_edit_pipeline_design.md`
