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
| `upscale_image.py` | 이미지 업스케일 ≤4K | 기본 **rtx_vsr**; seedvr2는 히어로 opt-in |
| `upscale_video.py` | 영상 업스케일 ≤4K (4K 시 2-pass) | 동일 |
| `location_create.py` | 로케이션 패키지 + master_wide T2I | `locations/` |
| `location_expand_sheets.py` | 각도/조명/랜드마크 I2I | location_presets.json |
| `location_approve.py` | refs → approved 승격 | aliases: master_wide, empty_stage, … |
| `story_init.py` | 에피소드 패키지 생성 | `stories/` + format + look |
| `shot_compose.py` | look+char+loc → 키프레임 | format work size |
| `shot_approve.py` | keyframe_status 승격 | I2V 전 게이트 |
| `episode_i2v.py` | approved 키프레임 배치 I2V (`motion_driver=i2v`) | → `clips/work/` |
| `episode_s2v.py` | approved 키프레임 배치 SI2V (`motion_driver=si2v`) | → `clips/work/*_s2v.mp4` |
| `episode_upscale.py` | work 클립 배치 업스케일 | → `clips/deliver/` (default rtx_vsr) |
| `assemble_video.py` | FFmpeg concat + **mix_policy** stems | → `exports/final/` |
| `audio_status.py` | production_mode / stems / si2v 준비도 | 설계: docs/audio_motion_production_modes.md |
| `audio_slice.py` | 마스터 음원 구간 추출 → stems | 뮤비/SI2V 준비 |
| `audio_prepare_driving.py` | SI2V 드라이빙 stem (center/voicey/vocal_band) | MelBand 없을 때 FFmpeg 폴백 |
| `generate_s2v.py` | SI2V InfiniteTalk live runner | `video_backends.infinitetalk` |
| `package_delivery.py` | 사용자 납품 폴더+zip | → `deliveries/<ep>__<stamp>/` |
| `episode_status.py` | 에피소드 진행 상태/다음 액션 | 텍스트 또는 JSON |
| `episode_contact_sheet.py` | 키프레임 컨택시트 | `boards/contact_sheet.png` |
| `episode_pipeline.py` | status→…→package 오케스트레이션 | `--run` / `--dry-run` |
| `commission_start.py` | 브리프 JSON → 에피소드 스캐폴드 | 수주 입구 |
| `shot_edit.py` | shots.json 샷 생성/수정 | 액션·모션·캐릭터 등 |
| `shot_compose.py --all` | 미생성 키프레임 배치 컴포즈 | format work size |
| `assets_list.py` | char/loc/look 목록·에피소드 자산 점검 | `--episode` |
| `generate_krea.py` | Krea T2I | `t2i_krea` |
| `character_create.py` | 패키지 + 마스터 후보 | t2i |
| `character_approve.py` | refs → approved 승격 | — |
| `character_expand_sheets.py` | 시트 배치 | i2i / controlnet |
| `shot_with_character.py` | 스토리 키프레임 | i2i |

워크플로우 JSON은 **`workflows/agent/`** 만 수정·프로모트한다.
