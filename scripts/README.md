# scripts/ — 에이전트 CLI 도구

이 저장소의 **실행 진입점**이다. 휴먼 GUI 앱이 아니라 ComfyUI API 배치용.

## 실행

저장소 루트 또는 임의 cwd에서:

```bash
python scripts/generate_moody.py --help
python scripts/character_create.py --id ... --name ...
python scripts/generate_i2v.py -i keyframe.png -o out.mp4
```

`_bootstrap.py` 가 레포 루트와 `scripts/` 를 `sys.path` 에 넣으므로 `lib.*` 및 동료 스크립트 import가 동작한다.

## 목록

| 스크립트 | 역할 | 워크플로우 (catalog) |
|----------|------|----------------------|
| `generate_moody.py` | T2I | `t2i_moody` |
| `generate_moody_i2i.py` | I2I | `i2i_moody` |
| `generate_moody_controlnet.py` | I2I + ControlNet | `i2i_controlnet_moody` |
| `generate_i2v.py` | I2V multi-backend (`--backend` / `--preset`) | `video_backends.json` → `i2v_wan22_a14b` |
| `upscale_image.py` | 이미지 업스케일 ≤4K | `upscale_backends.json` (seedvr2/rtx/esrgan) |
| `upscale_video.py` | 영상 업스케일 ≤4K (4K 시 2-pass) | 동일 |
| `location_create.py` | 로케이션 패키지 + master_wide T2I | `locations/` |
| `location_expand_sheets.py` | 각도/조명/랜드마크 I2I | location_presets.json |
| `location_approve.py` | refs → approved 승격 | aliases: master_wide, empty_stage, … |
| `story_init.py` | 에피소드 패키지 생성 | `stories/` + format + look |
| `shot_compose.py` | look+char+loc → 키프레임 | format work size |
| `shot_approve.py` | keyframe_status 승격 | I2V 전 게이트 |
| `generate_krea.py` | Krea T2I | `t2i_krea` |
| `character_create.py` | 패키지 + 마스터 후보 | t2i |
| `character_approve.py` | refs → approved 승격 | — |
| `character_expand_sheets.py` | 시트 배치 | i2i / controlnet |
| `shot_with_character.py` | 스토리 키프레임 | i2i |

워크플로우 JSON은 **`workflows/agent/`** 만 수정·프로모트한다.
