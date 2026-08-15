# 설계 — 에이전트 영상 편집 레일 (EDIT)

- **작성**: 2026-08-15
- **상태**: v1 구현 (2026-08-15). v2/v3 미착수
- **기획**: [agent_edit_pipeline_brief.md](agent_edit_pipeline_brief.md)
- **패턴 원본**: MIDI 레일 (`music_skeleton.v1` → CLI → 렌더) · FluidSynth `setup_*.py`

---

## 1. 한 줄 구조

```text
사용자 말 (길이·무드·음악·플랫폼)
    → video-edit 스킬 (판단)
    → EDIT_PLAN.md
    → edit_timeline.v1
    → compile (FFmpeg)     ← v1 손
    → (Revideo / MLT)      ← v2
    → (grade / key)        ← v3
    → master.mp4
    → edit_qa_pack → 열기 → 고치고 재렌더
```

에이전트는 FFmpeg 필터나 MLT XML을 직접 쓰지 않는다.  
**EDIT_PLAN + timeline JSON**이 편집 판단의 SSOT다. 엔진은 손이다.

`assemble_video`는 그대로 둔다. 에피소드 “샷 순서 concat + mix_policy”.  
EDIT는 원오프·뮤비·쇼츠처럼 **컷을 다시 짜는** 작업.

---

## 2. 선반

새 선반 **EDIT**. BUNDLE(에피 옵션) / FINISH(업스케일)와 분리.

| CLI | 역할 |
|-----|------|
| `edit_timeline.py` | JSON 생성·검증·샷 목록 import |
| `render_title.py` | 타이틀/로어서드 스틸 (폰트 고정) |
| `render_edit.py` | timeline → master.mp4 |
| `edit_qa_pack.py` / `edit_qa_record.py` | 마스터 프레임 팩 + 판정 |
| `setup_edit_runtime.py` | (v2) melt / 폰트. v1은 ffmpeg + 맑은고딕 |

스킬: `skills/video-edit/SKILL.md` (편집장 두뇌).  
intent: `edit_timeline`, `render_title`, `render_edit`, `edit_qa`.

---

## 3. 스키마 `edit_timeline.v1`

경로 예: `$AGENT_WORKSPACE/edits/<name>/timeline.json`

```json
{
  "schema": "edit_timeline.v1",
  "fps": 24,
  "width": 1920,
  "height": 1080,
  "sample_rate": 48000,
  "background": "#000000",
  "clips": [
    {
      "id": "c1",
      "path": "clips/S01.mp4",
      "track": "V1",
      "start": 0.0,
      "in": 0.0,
      "out": 3.2,
      "speed": 1.0,
      "opacity": 1.0,
      "transform": { "fit": "cover" }
    }
  ],
  "overlays": [
    {
      "id": "t1",
      "kind": "lower_third",
      "text": "포기하지 마",
      "subtext": "",
      "start": 0.4,
      "end": 2.8,
      "preset": "lower_third",
      "font": "default"
    }
  ],
  "audio": [
    {
      "id": "a1",
      "path": "audio/master.wav",
      "start": 0.0,
      "in": 0.0,
      "out": null,
      "volume": 1.0,
      "role": "master"
    }
  ],
  "transitions": [
    { "id": "x1", "from": "c1", "to": "c2", "type": "crossfade", "dur": 0.25 }
  ]
}
```

### 규칙

- 시간 단위 = **초** (에이전트 친화). 컴파일러가 fps로 프레임 양자화.
- `out` 생략 = 소스 끝까지. `audio.out` null = 남은 타임라인.
- `track`: v1은 `V1` (픽처) + overlays는 항상 위. `V2`는 v1에서 무시하거나 에러.
- `fit`: `cover` | `contain` | `stretch`. 기본 cover (쇼츠/뮤비).
- `kind`: `title` | `lower_third` | `caption` | `card` (이미지 path).
- `transitions.type` v1: `cut` | `crossfade`. 그 외는 `cut`으로 강등 + warning.
- 경로는 timeline 파일 기준 상대 또는 절대. 렌더 시 존재 검사.

### 파생

```text
duration = max(clip.start + (out-in)/speed, overlay.end, audio.end)
```

---

## 4. v1 컴파일 (FFmpeg)

`lib/edit_compile_ffmpeg.py`

1. 각 클립: `trim` + `setpts` + `scale/pad` → 동일 캔버스.
2. `transitions`가 `crossfade`면 `xfade=transition=fade:duration=d:offset=...`.
3. 하드컷은 `concat` 필터.
4. overlays:  
   - 텍스트: `drawtext` (폰트 파일 필수) 또는 미리 `render_title`로 만든 png/mov를 `overlay=enable='between(t,s,e)'`.  
   - **한글 기본은 title PNG** (drawtext 폰트 깨짐 회피). `render_title`이 카드 이미지를 만들고 overlay path를 넣는다.
5. audio: `atrim` + `adelay` + `volume` + `amix`.
6. 맵: `-map [vout] -map [aout] -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k`.

에이전트에게 노출하는 것은 `render_edit.py --timeline t.json -o master.mp4` 뿐.  
디버그: `--print-graph` 로 filter_complex만 stdout.

### 왜 v1이 FFmpeg인가

- 이미 팩토리 의존성. Windows에서 동작 중.
- 쇼츠/뮤비 편집의 80%는 trim + xfade + overlay + amix.
- 같은 JSON을 나중에 MLT로 컴파일하면 그래프가 커져도 에이전트 계약은 불변.

MLT를 v1 필수로 두지 않는다. melt 미설치가 편집 선반을 죽이지 않게.

---

## 5. 타이틀

`lib/edit_title.py` + `scripts/render_title.py`

**부품 조립이 본선.** 이름 붙은 프리셋은 출발 레시피일 뿐, 잠금이 아니다.

| 층 | 부품 | 인자 |
|----|------|------|
| 자리 | `caption` `title` `lower_third` `yeonung` `card` | `--layout` |
| 페인트 | 색·외곽선·크기·굵기·기울기·폰트 | `--color --outline --size --weight --tilt --font` |
| 장식 | 사각 플레이트 / 말풍선 / 하단 바 / 리액션 줄 | `--box --bubble --bar --subtext --react-color` |
| 좌표 | 글자 중심 0–1 | `--x --y` |

에이전트는 프리셋 없이 층을 골라 새 룩을 만든다.  
`compose_style()`이 병합 SSOT. `--list-parts`로 메뉴를 읽는다.  
`--preset yt_hook` 등은 같은 부품을 미리 채워 둔 바로가기.

구현 v1: **Pillow + 지정 폰트 → PNG (투명)**.  
폰트: `--font` 또는 `EDIT_FONT` 또는 Windows `C:\Windows\Fonts\malgun.ttf`. 없으면 `FONT_MISSING`로 실패.

v2: Revideo/Motion Canvas로 같은 부품을 움직이게. JSON `overlays[].engine = "revideo"`.

Boogu는 스틸 잡지 타이포. EDIT 타이틀의 기본 엔진이 아님 (느리고 Comfy).

---

## 6. 모듈 / 파일

| 파일 | 책임 |
|------|------|
| `lib/edit_timeline.py` | 로드/저장/검증, duration, import_from_shots |
| `lib/edit_compile_ffmpeg.py` | JSON → ffmpeg argv |
| `lib/edit_title.py` | 부품 조립 → PNG (프리셋은 바로가기) |
| `scripts/edit_timeline.py` | CLI: `init` `validate` `from-clips` |
| `scripts/render_title.py` | CLI: 텍스트 → png |
| `scripts/render_edit.py` | CLI: timeline → mp4 |
| `tests/test_edit_timeline.py` | 스키마, duration |
| `tests/test_edit_compile.py` | 그래프에 xfade/overlay 포함 (ffmpeg 없어도 문자열) |
| `tests/test_edit_cli.py` | 짧은 color 픽스처로 실제 렌더 (ffmpeg 있을 때) |
| `workflows/human/edit/AGENT_GUIDE.md` | when / CLI / JSON 예 |
| `docs/tool_catalog.md` · `TOOLS.md` · `lib/tool_intent.py` · `catalog.json` | 등록 |
| `video_backends.json` | `edit_ffmpeg` status ready |

에피소드 헬퍼 (should, 작음):

- `lib/edit_timeline.import_episode(story)` — 샷 순서 클립을 V1에 일렬로. 그 다음 에이전트가 trim/title.

`assemble_video`는 수정하지 않는다.

---

## 7. CLI 계약

```bash
# 빈 타임라인
python scripts/edit_timeline.py init --fps 24 --width 1080 --height 1920 \
  -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"

# 클립을 순서대로 올리기 (하드컷)
python scripts/edit_timeline.py from-clips \
  -i a.mp4 -i b.mp4 -i c.mp4 \
  --xfade 0.25 \
  -o "%AGENT_WORKSPACE%/edits/s01/timeline.json"

# 타이틀 PNG
python scripts/render_title.py --preset caption --text "포기하지 마" \
  --width 1080 --height 1920 -o "%AGENT_WORKSPACE%/edits/s01/cap.png"

# 최종
python scripts/render_edit.py \
  --timeline "%AGENT_WORKSPACE%/edits/s01/timeline.json" \
  -o "%AGENT_WORKSPACE%/edits/s01/master.mp4"
```

공통: `_bootstrap`, `--json`, `die_if_toolbox`, `ok_result`/`fail_result`.

---

## 8. 에이전트 루프 (말 → 마스터)

`video-direction`은 **생성 전** 연출이다. 클립이 생긴 뒤는 **`video-edit` 스킬**이 본선이다. Gate 7 concat으로 납품하지 않는다.

```text
GATE E0  INTAKE     사용자 말 → 길이, 비율, 플랫폼, 음악 유무, 한 줄 무드
GATE E1  EDIT_PLAN  페이싱 / 컷 리듬 / 타이틀 일 / 믹스 / 룩   ⛔ 렌더 금지
GATE E2  TIMELINE   plan을 edit_timeline.v1 으로 옮김
GATE E3  TITLES     render_title (한글 PNG). 화면에 글자 일마다 1장
GATE E4  RENDER     render_edit → master.mp4
GATE E5  QA         edit_qa_pack 열고 기록. fail → E1/E2만 고치고 E4
GATE E6  DELIVER    프로젝트 경로만. 툴박스에 마스터 금지
```

### EDIT_PLAN.md (렌더 전 필수)

프로젝트 `edits/<name>/EDIT_PLAN.md`:

```text
TARGET: 15s / 9:16 / 쇼츠
SPINE: 한 줄 (무엇을 보여주는 영상인가)
PACING: hook 1.2s → build → peak 훅 → residual
SIZE RHYTHM: (클립이 허용하는 한) 와이드/미디엄/인서트 교차
CUTS: 클립별 in/out + 왜 거기서 자르는지 (한 줄)
TITLES: 몇 개, 무슨 일 (훅 / 크레딧 / 없음). 가사 전부 올리지 않음
MIX: master locked | vo+bgm duck | 클립 오디오 mute
LOOK: 대비/채도 한 줄 (v1 ffmpeg colorbalance 또는 패스)
ANTI: 3연속 동일 프레이밍, 가사 슬라이드, 검은 공백, 팝
```

하드밴 (video-direction과 동일 정신):

- 같은 샷 크기 느낌 3연속
- 가사/대사 1:1 자막 슬라이드
- 짧은 클립 freeze-pad로 길이 채우기
- 타이틀 없이 “글자가 필요 없는 훅”인데 훅이 안 보임
- QA 없이 납품

### QA (`edit_qa_pack.py`)

마스터에서 뽑는다: 0.3s / 1.5s(훅) / 중간 / 피크 / 끝 직전 프레임 + duration + max peak dB.  
에이전트가 **파일을 연다.** 기록: `edit_qa_record.py --verdict pass|fail`. fail이면 timeline만 수정.

생성 클립 붕괴(얼굴, freeze)는 EDIT가 고치지 않는다. 해당 샷을 다시 GENERATE.

---

## 8.1 말만 있을 때 에이전트가 채우는 것

사용자가 초/페이드를 안 말해도 스킬이 채운다.

| 사용자 | 에이전트가 정함 |
|--------|----------------|
| “15초 쇼츠” | 훅 1–1.5s, 컷 4–7개, 피크 위치 |
| “케이팝 뮤비처럼” | 비트에 in/out, 후렴=이벤트, 글자 최소 |
| “이 곡 깔아” | music_locked, 클립 오디오 mute, 페이드 인/아웃 0.1–0.4s |
| “세게 열어” | 첫 컷 짧고 크게, 타이틀은 늦게 또는 없음 |
| “이름 넣어” | lower_third 1회, 2초 안팎 |

이 결정이 EDIT_PLAN에 남아야 재렌더가 가능하다.

---

## 9. 단계

| 단계 | 범위 | 엔진 |
|------|------|------|
| **v1** | trim, 배치, cut/xfade, 타이틀 PNG overlay, 오디오 트랙, master mp4 | FFmpeg + Pillow |
| **v2** | 키네틱 타이포, 복잡한 멀티트랙 | Revideo 또는 MLT. JSON 필드만 추가 |
| **v3** | 키, OCIO 그레이드 | Natron **또는** Blender 컴프. 별 CLI `comp_shot.py` |

한 단계가 동작·등록·테스트되기 전에 다음 엔진을 넣지 않는다.

---

## 10. 리서치 도구 매핑 (넣지 않는 이유)

| 도구 | v1 | 이유 |
|------|----|------|
| FFmpeg | **본선** | 이미 있음 |
| MLT | v2 후보 | 멀티트랙이 filter_complex를 넘을 때. Windows melt는 setup 스크립트 |
| Revideo / Motion Canvas | v2 후보 | 움직이는 글자. Node 스택. 정적 타이틀은 Pillow로 충분 |
| Natron | v3 | 키/OFX. Windows 헤드리스 리스크. 일상 편집 필수 아님 |
| Blender | 이미 MESH/VFX | NLE가 아님. 컴프가 필요하면 기존 MCP |

문서의 Docker 멀티엔진 이미지는 **안 만든다.** 로컬 CLI + setup.

---

## 11. 에러

| 코드 | 때 |
|------|----|
| `TIMELINE_INVALID` | 스키마/음수 시간/없는 id |
| `CLIP_MISSING` | path 없음 |
| `FONT_MISSING` | 한글 타이틀인데 폰트 없음 |
| `FFMPEG_FAILED` | 렌더 실패 (stderr 꼬리) |
| `EXIT_TOOLBOX_WRITE` 14 | `-o`가 이 레포 |

---

## 12. 테스트

- `test_edit_timeline`: 3클립 from-clips duration, 잘못된 transition id → error.
- `test_edit_compile`: xfade 있는 JSON → filter 문자열에 `xfade`와 `overlay`.
- `test_edit_cli`: ffmpeg로 1초 color 소스 2개를 xfade + caption → mp4 exists, duration ~1.75s.

픽스처는 `tests/fixtures/edit/`에 생성 (커밋하지 않는 대용량 금지. 테스트가 ffmpeg lavfi color로 만듦).

---

## 13. 등록 체크리스트 (구현 PR과 동일 커밋)

`docs/toolbox_card_standard.md` 그대로.

- `edit_timeline` / `render_title` / `render_edit` intent 카드
- `TOOLS.md` 선반 행 **EDIT**
- `docs/tool_catalog.md` §1 + §2 EDIT
- `workflows/agent/catalog.json` status `ready` (v1 세 CLI)
- `workflows/human/edit/AGENT_GUIDE.md`
- `process.md` 한 줄
- `video_backends.json` `edit_ffmpeg`

`assemble_video` when_not에 “컷을 다시 짜거나 타이틀을 올리려면 render_edit”.

---

## 14. 구현 순서 (말→마스터가 한 줄로 통할 때까지)

품질 계약이 “도구 존재”가 아니라 **에이전트가 혼자 마스터를 냄**이므로, 스킬과 QA를 렌더러와 같이 싣는다.

1. **`skills/video-edit`** + `templates/EDIT_PLAN.md` + video-direction Gate 7을 EDIT로 넘기는 한 줄
2. `edit_timeline` 스키마 + `from-clips` + 테스트
3. `render_title` 한글 PNG
4. `render_edit` (cut/xfade/overlay/amix + 약한 colorbalance)
5. `edit_qa_pack` / `edit_qa_record`
6. 카탈로그 · intent · `workflows/human/edit/AGENT_GUIDE.md`
7. 스모크: 말 한 줄 가정 → PLAN → 3클립 마스터 → QA 팩이 열리는지
8. **v2 PR:** Revideo 키네틱 훅 자막 (글자가 “만진” 느낌의 큰 점프)
9. **v3 PR:** 룩 패스 (ffmpeg LUT 또는 Blender/Natron 한 경로). 키는 필요할 때만

v1만으로도 “자른 쇼츠”는 된다.  
**전문 피니시(움직이는 타이포, 그레이드, 키)** 는 8–9가 있어야 손이 더 느껴진다. 판단(스킬) 없이 8–9만 올리면 또 얇다.

이 문서는 구현 허가가 아니다. 착수 세션은 14절 1–7을 한 묶음으로 본다.
