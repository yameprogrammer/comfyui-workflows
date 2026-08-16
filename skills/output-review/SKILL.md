---
name: output-review
version: 1.0.0
description: >
  Actively judge generated stills, clips, and audio against the brief before
  showing the user or advancing. Use after every generate_*, when evaluating
  quality, 검수, 평가, review, QA, "잘 나왔나", "어때". Ban treating CLI exit 0
  as done. Open the file, record pass/fail, pick the next repair CLI.
  Slash: /output-review
---

# output-review — 생성물 능동 평가

당신은 생성 봇이 아니다. **심판 + 다음 도구를 고르는 손**이다.

`generate_*` 가 끝난 것은 파일이 생겼다는 뜻이다. 목표에 맞는지, 보여줄 품질인지는 아직 모른다.

**손:** `python scripts/review_media.py`  
**에피소드 키프레임/클립:** 기존 `shot_qa_pack` / `shot_qa_record` (이 스킬이 그 레일을 대체하지 않음)  
**편집 마스터:** `edit_qa_pack` (`video-edit` E5)

---

## 0. Equip (generate_* 직후 · 유저에게 보여 주기 전)

```bash
python scripts/skill_equip.py show output-review
python scripts/review_media.py pack -i "%AGENT_WORKSPACE%/stills/hero.png" \
  --intent "비 오는 골목 medium, 노란 우산, 발 클로즈업 아님" \
  -o "%AGENT_WORKSPACE%/reviews/hero"
```

세션에 이 스킬이 없으면 `SKILL.md` 를 읽고 아래 루프를 따른다.

---

## 1. SYSTEM identity

```text
Brief first. Open the file. Judge against the brief, not against "it rendered".
Fail one blocking item → do not claim done. Call the mapped repair CLI.
Same generate + same prompt is not a repair.
Draft scout may skip record. Anything shown, reused, or sent to motion/mix/delivery may not.
```

---

## 2. 루프 (순서 고정)

```text
B0 BRIEF     이 파일이 만족해야 할 것 1–5줄 (샷/동작/금지 또는 BPM·키·역할)
B1 GENERATE  generation-prompt 방언으로 generate_*   ⛔ 여기서 끝내지 말 것
B2 PACK      review_media pack (또는 에피 shot_qa_pack / 편집 edit_qa_pack)
B3 OPEN      팩이 가리키는 파일을 연다. 이미지는 read_file. 클립은 프레임. 오디오는 스펙트로그램+메트릭
B4 JUDGE     항목별 pass/fail. 막힘 항목 1개면 전체 fail
B5 RECORD    review_media record --verdict … --opened
B6 NEXT      pass → 유저에게 보여 주거나 다음 단계
             fail → 레버 CLI (references/next_lever.md). 같은 호출 금지
```

`exit 0` 만 보고 “완료”라고 쓰면 **작업 미완료**다.

---

## 3. 언제 필수인가

| 상황 | 평가 |
|------|------|
| 초안/스카우트, 유저에게 안 보여 줌 | PACK+OPEN 권장. record 생략 가능 |
| 유저에게 보여 줌 | **필수** |
| 이 스틸로 I2V / 이 스템으로 믹스 | **필수** (입력이 이미 틀리면 뒤가 전부 틀림) |
| 납품·마스터·approve | **필수** |
| 에피소드 `stories/<ep>` | `shot_qa_*` (Rule 7.3). 이 CLI 아님 |
| `edit_pack` 마스터 | `edit_qa_*` |

---

## 4. Brief (기준이 없으면 평가가 아니다)

생성 **전에** 한 블록을 남긴다. 없으면 지금 쓴다.

```text
intent: 비 오는 편의점 골목, medium, 노란 파라솔
must: 우산이 주인공, 얼굴은 hero 아님
anti: 발 기형, 얼굴 CU, 8k 태그수프 룩
kind: still
```

오디오면 `bpm / key / role=drums|bed|sfx / seconds` 를 적는다.  
모션이면 `camera + body action` 만 (얼굴·의상 재서술 금지).

---

## 5. 여는 법

| 종류 | 연다 | 보조 |
|------|------|------|
| 스틸 | 이미지 파일 자체 | 레퍼가 있으면 나란히 |
| 클립 | first / mid / last 프레임 | 가능하면  scrub. 프리즈는 끝 프레임이 중간과 같으면 fail |
| 오디오 | `probe.json` + 스펙트로그램 | 길이·무음·BPM. 귀만 믿고 패스 금지 |

팩이 `OPEN:` 으로 적어 준 경로를 **실제로** 연다. 경로만 읽고 패스하지 않는다.

---

## 6. 막힘 항목 (하나라도 fail → 전체 fail)

전체 ID: `python scripts/review_media.py show still|clip|audio`

**스틸** — S1 의도 · S2 샷사이즈 · S3 신원 · S4 해부 · S5 금지항 · S6 쓰레기글자  
**클립** — C1 프리즈 · C2 모션일치 · C3 신원유지 · C4 워프 · C5 길이  
**오디오** — A1 길이 · A2 무음/클리핑 · A3 BPM · A4 역할순수 · A5 조성 · A6 솔로인데 풀믹스

에피소드 키프레임/클립의 긴 표는 [image_cut_verification_gate.md](../../docs/image_cut_verification_gate.md) (K*/C*). 여기서 다시 쓰지 않는다.

---

## 7. Fail → 다음 레버

같은 프롬프트로 같은 `generate_*` 를 다시 누르지 않는다.

| 실패 | 다음 |
|------|------|
| 손/발/얼굴만 깨짐 | 해당 디테일러 / 인페인트 |
| 사람만 같고 장면이 틀림 | `generate_character_consistent` / identity edit |
| 샷 사이즈만 틀림 | `generate_reframe` 또는 프롬프트에 사이즈 명시 후 재생성 |
| 의도와 다른 그림 | `generation-prompt` 방언으로 프롬프트 재작성 (모델 먼저 바꾸지 말 것) |
| I2V 프리즈/워프 | 더 짧게 · 모션 문장만 · freeze-pad 금지 |
| 오디오 BPM/역할 붕괴 | MIDI 잠금으로 후퇴하거나 그 스템 폐기 |

표 SSOT: `references/next_lever.md`

FAIL 이면 `python scripts/failure_note.py add` (Rule 7.4).

---

## 8. 하드밴

- 파일 안 열고 pass
- exit 0 = 품질 통과
- 막힘 항목을 무시하고 유저에게 “나왔습니다”
- 틀린 입력을 모션/믹스/업스케일로 넘김
- fail인데 모델만 교체 (레버 표에 모델 교체가 있을 때만)
- 에피소드 mass approve

---

## 9. CLI

```bash
# 원오프 (기본)
python scripts/review_media.py pack -i hero.png --intent "medium, yellow parasol" -o "%AGENT_WORKSPACE%/reviews/hero"
python scripts/review_media.py record --pack "%AGENT_WORKSPACE%/reviews/hero" \
  --verdict pass --opened --notes "medium OK; umbrella hero; hands OK"

python scripts/review_media.py record --pack "%AGENT_WORKSPACE%/reviews/hero" \
  --verdict fail --fail S4_anatomy --opened --notes "extra fingers" --next krea2_hand_detail

python scripts/review_media.py show still
python scripts/review_media.py lever S4_anatomy

# 에피소드
python scripts/shot_qa_pack.py -e EP -s S03
python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict pass --pass-required --notes "..."
```

`-o` 는 **프로젝트 경로**. 이 레포 안에 리뷰 팩을 쓰지 않는다.

---

## 10. Progressive disclosure

| Need | File |
|------|------|
| 스틸 항목 | `references/still.md` |
| 클립 항목 | `references/clip.md` |
| 오디오 항목 | `references/audio.md` |
| fail → CLI | `references/next_lever.md` |
| 에피소드 긴 체크 | `docs/image_cut_verification_gate.md` |
| 편집 마스터 QA | `skills/video-edit/SKILL.md` E5 |
