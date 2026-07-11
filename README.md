# agent_custom — 에이전트용 ComfyUI 미디어 도구

사람이 쓰는 앱 UI가 아니라, **로컬 ComfyUI(API)를 에이전트가 배치 제어**하기 위한 워크스페이스입니다.  
Z-Image-Turbo (Moody) T2I/I2I, ControlNet, 캐릭터 패키지, Wan2.2 I2V 등이 여기에 모입니다.

---

## 레이아웃 (에이전트 SSOT)

```text
agent_custom/
├── README.md                 # 이 파일 (입구)
├── agent_rules.md            # 협업 규칙 (항상 준수)
├── process.md                # 작업 이력 로그
├── workflows/
│   ├── agent/                # ★ 프로덕션 워크플로우 JSON + catalog.json
│   └── human/                # UI 실험 내보내기 (스크립트 기본 미사용)
├── scripts/                  # ★ CLI 진입점 (generate_*, character_*, shot_*)
├── lib/                      # 공유 파이썬 모듈
├── characters/               # 캐릭터 패키지·프리셋·스키마
└── docs/                     # 설계·로드맵·구현 스펙
```

| 찾을 것 | 위치 |
|---------|------|
| 워크플로우 JSON | `workflows/agent/` |
| CLI 실행 | `scripts/` |
| 공유 코드 | `lib/` |
| 캐릭터 데이터 | `characters/` |
| 스펙/로드맵 | `docs/` |
| 규칙/이력 | 루트 `agent_rules.md`, `process.md` |

상세 규약: [workflows/README.md](workflows/README.md) · [scripts/README.md](scripts/README.md) · [docs/README.md](docs/README.md)

---

## CLI (저장소 루트 기준)

ComfyUI: `127.0.0.1:8188`

### 이미지

```bash
python scripts/generate_moody.py --model pro --prompt "Cinematic photo of a Korean woman..."
python scripts/generate_moody_i2i.py -i "input.png" -p "holding a tumbler" -d 0.70 -c 3.5 -m pro -o "out.png"
python scripts/generate_moody_controlnet.py -i "char.png" --control "pose.png" -p "..." -d 0.70 -c 3.5 -s 0.80 -m pro
python scripts/generate_krea.py --prompt "Futuristic glass sphere over desert, 8k"
```

### 캐릭터 패키지

```bash
python scripts/character_create.py --id mina_park_v1 --name "Mina Park" --model pro --candidates 4 --from-brief-samples --seed-base 10001
python scripts/character_approve.py --id mina_park_v1 --from refs/master/<chosen>.png --as master_front --set-primary
python scripts/character_expand_sheets.py --id mina_park_v1 --sheets all_mvp --model pro --candidates 2
python scripts/shot_with_character.py --id mina_park_v1 --shot "medium shot in a coffee shop" --template medium_dialogue --expression neutral -d 0.75
```

### I2V

```bash
# 기본 format: cinematic_16x9 (960×540 work) — 비율은 고정이 아님
python scripts/generate_i2v.py -i path/to/keyframe.png -p "gentle camera push-in" -o F:\generated_videos\clip.mp4 --frames 33

# 세로 쇼츠 / 4:3 / 3:4
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format shorts_9x16
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format classic_4x3
python scripts/generate_i2v.py -i key.png -p "..." -o out.mp4 --format portrait_3x4

python scripts/generate_i2v.py --list-formats
python scripts/generate_i2v.py --list-presets
python scripts/generate_i2v.py --list-backends
```

### 업스케일 (work → 납품, 최대 4K)

```bash
python scripts/upscale_image.py -i key.png -o key_1080.png --preset deliver_1080 --backend seedvr2
python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080 --backend seedvr2
python scripts/upscale_video.py -i work.mp4 -o deliver_4k.mp4 --preset deliver_2160 --backend seedvr2   # 자동 2-pass
python scripts/upscale_video.py -i work.mp4 -o preview.mp4 --preset deliver_1080 --backend rtx_vsr
python scripts/upscale_image.py --list-backends
```

리서치·설계: [docs/upscale_research_and_design.md](docs/upscale_research_and_design.md)  
납품 비율은 **format 프로필** (16:9 / 9:16 / 4:3 / 3:4 …). SSOT: [video_backends.json](video_backends.json) · [upscale_backends.json](upscale_backends.json)

---

## 문서 지도

| 문서 | 용도 |
|------|------|
| [docs/production_asset_pipeline.md](docs/production_asset_pipeline.md) | **캐릭터·로케·룩·스토리 통합** (영상 제작 필독) |
| [docs/location_sheet_system_design.md](docs/location_sheet_system_design.md) | 로케이션 시트 설계 (구현 대기) |
| [docs/look_style_system.md](docs/look_style_system.md) | Look/style core (`looks/`) |
| [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md) | 스토리보드·샷 설계 (구현 대기) |
| [docs/video_pipeline_roadmap.md](docs/video_pipeline_roadmap.md) | 영상 파이프라인 로드맵 |
| [docs/video_delivery_and_backends.md](docs/video_delivery_and_backends.md) | format · 해상도 · I2V 백엔드 |
| [docs/upscale_research_and_design.md](docs/upscale_research_and_design.md) | 업스케일 ≤4K |
| [docs/character_impl_spec.md](docs/character_impl_spec.md) | 캐릭터 **구현 SSOT** |
| [docs/character_sheet_system_design.md](docs/character_sheet_system_design.md) | 캐릭터 장기 설계 |
| [docs/moody_workflow_guide.md](docs/moody_workflow_guide.md) | Moody 운용 가이드 |
| [agent_rules.md](agent_rules.md) | 에이전트 협업 규칙 |
| [process.md](process.md) | 변경 이력 |

---

## I2I denoise 가이드 (Flow Matching)

* **사물 교체**: `--denoise 0.70`, CFG ≥ 3.5  
* **분위기/조명**: `--denoise 0.78`  
* **의상/포즈/장면**: `--denoise 0.85`  
* 샘플러: I2I 시 **`euler` / `normal`** (res_multistep 금지 경향)

---

## 워크플로우 수정 규칙

1. UI 실험 → `workflows/human/`  
2. 검증 후 → `workflows/agent/` 프로모트  
3. 대응 `scripts/generate_*.py` 노드 주입 동기화 (Rule 2)  
4. `process.md` 기록 (Rule 1)
