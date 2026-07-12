# 수주(Commission) → 납품 에이전트 워크플로

에이전트가 **한 편의 에피소드 영상**을 맡았을 때 권장 순서.

---

## 1. 브리프 받기

JSON 브리프 (스키마: [commission_brief.schema.json](commission_brief.schema.json))  
예: [stories/examples/commission_brief_example.json](../stories/examples/commission_brief_example.json)

필수: `episode_id`, `format`, `shots[]` (`shot_id`, `action`)

선택 (오디오·모션 — [audio_motion_production_modes.md](audio_motion_production_modes.md)):

- `production_mode`: `music_video` | `story` | `hybrid` | `video_only`
- `mix_policy`, `default_motion_driver`, `audio.{master,bgm,bgm_volume}`
- 샷: `motion_driver` (`i2v`|`si2v`|…), `dialogue`/`sfx`/`audio_refs`  
  - **`si2v`**: story **대사** 컷 **및** music_video **보컬 퍼포** 컷 (둘 다 1급). driving = 대사 wav 또는 master 보컬 슬라이스

---

## 2. 에피소드 스캐폴드

```bash
python scripts/commission_start.py --brief path/to/brief.json --dry-run
python scripts/commission_start.py --brief path/to/brief.json
```

생성: `stories/<episode_id>/` + `shots.json` + bible/beats

---

## 3. 자산 확인

```bash
python scripts/assets_list.py
python scripts/assets_list.py --episode <id>
python scripts/episode_status.py --episode <id>
# character / location 팩 없으면 생성·승인 후 진행
```

---

## 4. 키프레임 → 모션 → 납품

```bash
# 키프레임 단건 또는 배치
python scripts/shot_compose.py --episode <id> --shot S01 --dry-run
python scripts/shot_compose.py --episode <id> --all --dry-run
python scripts/shot_approve.py --episode <id> --shot S01

# 파이프: status → assets → compose → contact → i2v → s2v → upscale → assemble → package
python scripts/episode_pipeline.py --episode <id>
python scripts/episode_pipeline.py --episode <id> --run --from assets --to package --dry-run
python scripts/episode_pipeline.py --episode <id> --run --from i2v --to package

# 또는 단계별
python scripts/episode_i2v.py --episode <id>          # motion_driver=i2v (B-roll 등)
python scripts/episode_s2v.py --episode <id>          # motion_driver=si2v (대사 · 뮤비 보컬)
python scripts/episode_upscale.py --episode <id> --preset deliver_1080
python scripts/audio_status.py --episode <id>
# mix_policy 에 따라 music/dialogue/sfx stems 배치 후
python scripts/assemble_video.py --episode <id>
# 강제 무음: --no-audio | 뮤비 마스터: --mix-policy music_locked --bgm path/to/master.wav
python scripts/package_delivery.py --episode <id>
```

사용자에게: `deliveries/<episode>__<stamp>.zip`

**참고:**  
- `episode_i2v` → `i2v` 만 / `episode_s2v` → `si2v` + `audio_refs.driving` 만. 파이프에 `s2v` 단계 포함.  
- 뮤비에서 보컬이 입을 움직이는 컷은 **story 대사가 없어도** `si2v` 로 돌린다.

---

## 5. 샷 수정

```bash
python scripts/shot_edit.py --episode <id> --shot S02 --action "..." --motion "..."
python scripts/shot_edit.py --episode <id> --shot S04 --create --action "..." --character mina_park_v1
```
