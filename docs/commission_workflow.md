# 수주(Commission) → 납품 에이전트 워크플로

에이전트가 **한 편의 에피소드 영상**을 맡았을 때 권장 순서.

---

## 1. 브리프 받기

JSON 브리프 (스키마: [commission_brief.schema.json](commission_brief.schema.json))  
예: [stories/examples/commission_brief_example.json](../stories/examples/commission_brief_example.json)

필수: `episode_id`, `format`, `shots[]` (`shot_id`, `action`)

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

# 파이프: status → assets → compose → contact → i2v → upscale → assemble → package
python scripts/episode_pipeline.py --episode <id>
python scripts/episode_pipeline.py --episode <id> --run --from assets --to package --dry-run
python scripts/episode_pipeline.py --episode <id> --run --from i2v --to package

# 또는 단계별
python scripts/episode_i2v.py --episode <id>
python scripts/episode_upscale.py --episode <id> --preset deliver_1080
python scripts/assemble_video.py --episode <id>
python scripts/package_delivery.py --episode <id>
```

사용자에게: `deliveries/<episode>__<stamp>.zip`

---

## 5. 샷 수정

```bash
python scripts/shot_edit.py --episode <id> --shot S02 --action "..." --motion "..."
python scripts/shot_edit.py --episode <id> --shot S04 --create --action "..." --character mina_park_v1
```
