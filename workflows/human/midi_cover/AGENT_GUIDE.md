# MIDI cover bed — Agent Guide

> **Shelf:** INGEST + VOICE  
> **Comfy:** 없음  
> **Specialty:** 화성 뼈대만 읽고 새 장르 MIDI 반주를 쓴 뒤, MiniMax / Suno에 올릴 **새 반주** 팩을 만든다.

원음 마스터를 보컬 모델에 올리지 않는다. 기본 `--keep harmony_only`.

---

## 1. When / When not

| 목표 | 도구 | 쓰지 말 때 |
|------|------|------------|
| 코드·BPM·키만 뽑기 | `extract_music_skeleton` | 원음 재업로드 · 보컬 완곡 |
| 새 장르 MIDI 반주 | `generate_midi_arrangement` | 가사만으로 완곡 → `generate_minimax_music` |
| 팩 + 핸드오프 문서 | **`generate_midi_cover_bed`** (에이전트 기본) | 원곡 멜로디를 음 단위로 복제하고 싶을 때 (그 작업이 아님) |
| MIDI 프리뷰 WAV | `generate_midi_render` | FluidSynth / `.sf2` 없으면 스킵 |

---

## 2. Keep modes

| `--keep` | 가져오는 것 | 결과 |
|----------|-------------|------|
| **`harmony_only`** (기본) | 키, BPM, 코드, 섹션 | 원곡처럼 안 들림. 새 반주. |
| `contour` | 위 + 멜로디 윤곽 (v1 추출은 비어 있음) | 훅이 남으면 2차적저작물일 수 있음 |

---

## 3. Genres (v1)

`acoustic_ballad` · `lofi_hiphop` · `band_rock` · `edm_pulse` · `piano_pop`

---

## 4. CLI

```bash
# 권장: 코드 진행 → 팩
python scripts/generate_midi_cover_bed.py \
  --chords "Am,F,C,G" \
  --genre acoustic_ballad \
  --keep harmony_only \
  --lyrics-lang ko \
  -o "%AGENT_WORKSPACE%/beds/demo1"

# 로컬 음원 분석 (numpy 필요). 원음은 팩에 복사하지 않음.
python scripts/generate_midi_cover_bed.py -i demo.wav --genre lofi_hiphop --skip-render -o "%AGENT_WORKSPACE%/beds/s01"

# 단계별
python scripts/extract_music_skeleton.py --chords "Am,F,C,G" --bpm 96 -o "%AGENT_WORKSPACE%/beds/s.json"
python scripts/generate_midi_arrangement.py --skeleton "%AGENT_WORKSPACE%/beds/s.json" --genre piano_pop -o "%AGENT_WORKSPACE%/beds/bed.mid"
python scripts/generate_midi_render.py -i "%AGENT_WORKSPACE%/beds/bed.mid" -o "%AGENT_WORKSPACE%/beds/bed.wav" --soundfont "%SOUNDFONT%"
```

`-o` 는 **프로젝트 경로**. 이 레포 `dumps/` 에 쓰면 exit 14.

---

## 5. Pack layout

```text
<out>/
  SOURCE.md           # 분석 전용 정책
  skeleton.json       # music_skeleton.v1
  arrangement.json    # midi_arrangement.v1
  arrangement.mid
  arrangement.wav     # FluidSynth 있을 때만
  cover_prompt.md     # MiniMax caption + 가사 칸 + Suno Cover 메모
  result.json
```

---

## 6. Vocal handoff

1. `arrangement.wav` 가 없으면 DAW/VSTi로 `.mid` 를 렌더한다.
2. **MiniMax Music 3:** `cover_prompt.md` 의 caption + 새 가사를 `generate_minimax_music` 에 넣는다. 로컬 Music 3는 멜로디를 잠그지 못한다.
3. **Suno Cover:** `arrangement.wav` 를 업로드하고 새 가사를 넣는다. 소스 마스터를 올리지 않는다.

`--from-url` 은 분석용 임시 WAV만 받는다. 다운로드한 원음은 팩에 넣지 않는다.

---

## 7. WAV 렌더

```bash
python scripts/generate_midi_render.py -i bed.mid -o bed.wav
```

- 기본 `--engine auto`: **FluidSynth + GM 사운드폰트** (피아노 등). 없으면 내장 신스.
- 한 번만: `python scripts/setup_fluidsynth.py` → `third_party/fluidsynth` + `third_party/soundfonts/GeneralUser-GS.sf2`
- `--engine synth` 는 사운드폰트 없이 내장 전자음.

---

## 8. Legal one-liner

`harmony_only` = 새 반주. `contour` 로 원곡 멜로디가 알아들리면 2차적저작물이다. 기성곡 마스터를 보컬 모델에 넣지 않는다.

Failure-note tags: `midi`, `skeleton`, `arrange`.
