# 프로젝트 규칙 — 로컬 영상 (MiniMax H3)

이 파일이 있는 폴더가 **작업대**다. 생성물(png, mp4, wav, 자막, 리뷰)은 전부 여기 둔다.

공구함(코드·CLI만, 결과물 금지): `F:\Agent_media_tools`  
CLI는 공구함 루트를 cwd로 실행하고, `-o` / `--output` 은 이 폴더의 절대 경로로 준다.

```bat
set AGENT_WORKSPACE=<이 폴더의 절대 경로>
```

공장 카탈로그의 에피소드 대량 기본은 LTX다. **이 프로젝트는 그 기본을 쓰지 않는다.** 영상은 MiniMax H3만 만든다.

---

## 새 세션이 먼저 할 일

영상 한 편을 만들기 전에, 공구함에서 이 순서로 읽고 따른다.

1. `skills/video-direction/SKILL.md` — 콘셉트와 샷을 잠근 뒤 생성한다.  
   이 폴더에 `CREATIVE.md`, `SHOT_DESIGN.md`를 쓴다.
2. 생성 직전 `skills/generation-prompt/SKILL.md` — 모델 방언으로 프롬프트를 쓴다. H3는 `skills/generation-prompt/references/minimax_h3.md`.
3. 생성 직후 `skills/output-review/SKILL.md` — 파일을 연 뒤 판정한다. CLI exit 0은 품질 합격이 아니다.

카메라 경로를 3D로 잠글 때만 `skills/camera-previz/SKILL.md`를 읽고, 플레이트 mp4를 H3 `--ref-video`에 넘긴다.

스틸 한 장, 클립 한 개처럼 연출이 필요 없으면 1번은 건너뛰고 아래 도구만 호출한다.

---

## 로컬만

Seedance, Kling, Gemini 영상, HeyGen, 그 밖의 클라우드 영상 API는 호출하지 않는다.

| 할 일 | CLI |
|-------|-----|
| 스틸 | `python scripts/generate_krea.py` |
| 문장으로 스틸 수정 | `python scripts/generate_qwen_edit.py --preset qwen_image_21_edit` |
| **영상** | **`python scripts/generate_minimax_h3.py`** |
| 목소리 | `python scripts/generate_qwen3_tts.py` |
| 납품 마스터 | `python scripts/edit_pack.py` |
| 도구가 헷갈릴 때 | `python scripts/tool_intent.py "…"` |

`generate_i2v`(LTX), Wan, `generate_yaw_wan22`는 사용자가 그 이름을 말하기 전에는 호출하지 않는다.

무거운 생성 전: `python scripts/failure_note.py before "…"`.

---

## 영상 (H3)

프로필 기본은 `work`다. 출력은 이 폴더 아래 `clips\`.

```bat
python scripts/generate_minimax_h3.py --task i2v -i still.png -p "…" --profile work -o "%AGENT_WORKSPACE%\clips\S01.mp4"
python scripts/generate_minimax_h3.py --task r2v -i hero.png --ref-video plate.mp4 --profile work -o "%AGENT_WORKSPACE%\clips\S01.mp4"
python scripts/generate_minimax_h3.py --task polish -i work.mp4 -o "%AGENT_WORKSPACE%\clips\S01_polish.mp4"
```

스토리보드(키프레임)를 열어 통과하기 전에는 I2V를 돌리지 않는다.  
한 클립은 15초를 넘기지 않는다. 더 길면 샷을 나눈다.

녹음한 목소리를 입 모양에 그대로 붙일 때만 `generate_s2v`를 쓴다. H3 `--task a2v`는 쓰지 않는다.

가이드: `workflows/human/minimax_h3/AGENT_GUIDE.md`.

---

## 생성 후

```bat
python scripts/review_media.py pack -i "%AGENT_WORKSPACE%\clips\S01.mp4" --intent "…" -o "%AGENT_WORKSPACE%\reviews\S01"
```

파일을 열고 판정한 뒤에만 다음 샷으로 간다. 합격한 클립만 `edit_pack`으로 마스터를 만든다. `assemble_video` concat은 납품본이 아니다.

---

## 이 작품

- 제목:
- 한 줄:
- 길이 / 화면비:
- 말하지 말 것:

### 자막에 지켜야 할 이름

받아쓴 자막의 오타는 이 목록으로 고친 다음 굽는다.

| 틀린 받아쓰기 | 맞는 표기 |
|---------------|-----------|
|  |  |
