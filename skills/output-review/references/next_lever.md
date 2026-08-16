# Fail → next CLI

Do not retry the same generate with the same prompt. Pick one row.

## Still

| Fail | Next | CLI |
|------|------|-----|
| S1_intent | 방언 맞춰 프롬프트 재작성 | `prompt_dialect.py show <family>` 후 같은 계열 `generate_*` |
| S2_shot_size | 리프레임 또는 사이즈를 앞에 두고 재생성 | `python scripts/generate_reframe.py -i img.png --size medium -o out.png` |
| S3_identity | 얼굴 잠금 | `python scripts/generate_character_consistent.py -i ref.png -p "..." -o out.png` |
| S4_anatomy (손) | 손 디테일러 | `python scripts/generate_krea2_hand_detail.py -i img.png -o out.png` |
| S4_anatomy (얼굴) | 얼굴 디테일러 | `python scripts/generate_krea2_face_detail.py -i img.png -o out.png` |
| S4_anatomy (눈) | 눈 디테일러 | `python scripts/generate_krea2_eyes_detail.py -i img.png -o out.png` |
| S4_anatomy (몸) | 해부 디테일러 / 인페인트 | `python scripts/generate_krea2_anatomy_detail.py -i img.png -o out.png` |
| S5_anti | anti를 프롬프트 앞에 명시하고 재생성 | 같은 CLI, **문장을 바꿈** |
| S6_junk_text | 글자 제거 편집 | `python scripts/generate_qwen_edit.py -i img.png -p "Remove all on-image text, keep the scene" -o out.png` |
| S7_light | 빛/카메라 문장 보강 | 모델 교체 금지. `generation-prompt` 후 재생성 |

2D 애니 해부는 Anima inpaint/hires. 실사 디테일러를 애니에 쓰지 말 것.

## Clip

| Fail | Next | CLI |
|------|------|-----|
| C1_no_freeze | 짧게 다시. 패드 금지 | `generate_i2v` / `generate_camera_move` 길이↓, motion 문장만 |
| C2_motion_matches | I2V 프롬프트 재작성 | 얼굴·의상 빼기. 동사 하나 |
| C3_identity_hold | 스틸부터 다시 QA | 키프레임 fail이면 모션 금지 |
| C4_no_warp | 움직임 줄이고 짧게 | hero 프로필 남용하지 말 것 |
| C5_duration | 분할 또는 FLF | `generate_flf2v` / chain. freeze-pad 금지 |

## Audio

| Fail | Next | CLI |
|------|------|-----|
| A1_duration | `--duration` / `--seconds` 재생성 또는 트림 | 침묵 패드로 길이 맞추지 말 것 |
| A2_not_dead | ACE면 audio-codes ON, 15s 청크 | `generate_bgm --engine ace --audio-codes` |
| A3_bpm | MIDI로 시계 잠금 | `generate_midi_arrangement` → render |
| A4_role_pure | 그 스템 폐기 | MIDI 역할 트랙 또는 프롬프트에 `solo X, no other instruments` |
| A5_key | 스켈레톤에 맞춰 재생성 | `extract_music_skeleton` / MIDI |
| A6_not_fullmix | 완곡으로 취급하거나 솔로 재생성 | MiniMax/ACE 믹스는 레이어가 아님 |

## When to change the model

Only after two repairs on the **same fail ID** still miss, or the dialect is wrong for the medium (실사에 Anima, 애니에 Krea).
