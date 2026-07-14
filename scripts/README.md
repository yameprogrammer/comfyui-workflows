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
| `shot_approve.py` | keyframe / **clip** / lip 승격 | I2V 전 + **assemble 전 컷 게이트** |
| `episode_i2v.py` | approved 키프레임 배치 I2V (`motion_driver=i2v`) | → `clips/work/` |
| `episode_s2v.py` | approved 키프레임 배치 SI2V (`motion_driver=si2v`) | → `clips/work/*_s2v.mp4` |
| `episode_upscale.py` | work 클립 배치 업스케일 | → `clips/deliver/` (default rtx_vsr) |
| `assemble_video.py` | FFmpeg concat + **mix_policy** stems; **clip_status hard gate** (exit 22) | → `exports/final/` |
| `audio_status.py` | production_mode / stems / si2v 준비도 | 설계: docs/audio_motion_production_modes.md |
| `audio_slice.py` | 마스터 음원 구간 추출 → stems | 뮤비/SI2V 준비 |
| `audio_prepare_driving.py` | SI2V 드라이빙 stem (center/voicey/vocal_band) | MelBand 없을 때 FFmpeg 폴백 |
| `audio_bind_driving.py` | 마스터 슬라이스+prep → 샷 `si2v` + `audio_refs.driving` | 뮤비 보컬 컷 1-shot |
| `generate_s2v.py` | SI2V multi-backend (`ltx23_ia2v` 기본, `infinitetalk`) | `video_backends.default_backend_s2v` |
| `episode_s2v.py` | approved `si2v` 샷 배치 | → `clips/work/*_s2v.mp4` |
| `package_delivery.py` | 사용자 납품 폴더+zip | → `deliveries/<ep>__<stamp>/` |
| `episode_status.py` | 에피소드 진행 상태/다음 액션 | 텍스트 또는 JSON |
| `episode_contact_sheet.py` | 키프레임 컨택시트 | `boards/contact_sheet.png` |
| `episode_pipeline.py` | status→…→package 오케스트레이션 | `--run` / `--dry-run` |
| `commission_start.py` | 브리프 JSON → 에피소드 스캐폴드 | 수주 입구 |
| `shot_edit.py` | shots.json 샷 생성/수정 | 액션·모션·캐릭터 등 |
| `shot_compose.py --all` | 미생성 키프레임 배치 컴포즈 | format work size |
| `assets_list.py` | char/loc/look 목록·에피소드 자산 점검 | `--episode` |
| `generate_krea.py` | Krea T2I | `t2i_krea` |
| `generate_ideogram4.py` | **타이포 전용** Ideogram 4 T2I (title/signage/menu) | API 그래프 · docs/ideogram4_typography_tool.md |
| `character_cast_pool.py` | **A** 다엔진 캐스팅 풀 (Moody/Krea) | 탐색 T2I |
| `character_shortlist.py` | A shortlist 찜 | cast |
| `character_status.py` | cast / 패키지 진행 상태 | ops |
| `character_promote.py` | **B** 후보 → 패키지 + master_front | cast→lock |
| `character_pipeline.py` | A→B→C 오케스트레이션 | production v1 |
| `character_create.py` | 패키지 + 마스터 후보 (Moody 단일 경로) | t2i |
| `character_approve.py` | refs → approved 승격 | — |
| `character_set_wardrobe.py` | **B2** 의상·소품 잠금 | bible wardrobe/props + lock 게이트 |
| `character_expand_sheets.py` | **C** 시트 expand | t2i design / qwen / i2i / controlnet |
| `character_qwen_turns.py` | **C** head/body 턴 | Qwen multi-angles (body=costume 우선) |
| `generate_qwen_angle.py` | Qwen 각도 1장 | Multiple-Angles LoRA `<sks> …` |
| `character_full_sheet.py` | **C** full_sheet 원샷 | design→costume→turns→rest + wardrobe 게이트 |
| `location_create.py` | 로케 패키지 + master T2I | architecture lock |
| `location_expand_sheets.py` | 로케 angles/lighting/landmarks | I2I from master_wide |
| `location_approve.py` | 로케 approved 승격 | alias |
| `location_full_sheet.py` | 로케 video_ref 원샷 | expand+approve+review |
| `story_init.py` | 에피소드 패키지 | shots.json + format/look |
| `shot_compose.py` | 프로덕션 키프레임 | look+char+loc @ format; shot_type ref 바인딩 |
| `storyboard_export.py` | 보드 contact + inventory | 사람 게이트용 패키지 |
| `shot_approve.py` | keyframe / clip_status / lip_status | draft→approved; assemble needs `--clip approved` |
| `episode_i2v.py` | approved 키프레임→영상 | motion-only 프롬프트 |
| `generate_qwen3_tts.py` | 대사/VO TTS | custom/design/clone + temp/top-p 튜닝 |
| `voice_register.py` | 클론 보이스 등록 | `voices/<id>/` (본인·타인 샘플) |
| `episode_tts.py` | 샷 dialogue TTS + SI2V bind | `--performance` + `--bind-si2v` → episode_s2v |
| `episode_s2v.py` | SI2V 배치 | `--performance` · 길이 계약 · **auto export** workspace |
| `export_episode_to_workspace.py` | 공장→작업대 복사 | `AGENT_WORKSPACE` · `--dest` |
| `chain_one_take.py` | 원테이크 체인 (i2v+si2v) | last-frame · clip gate · performance |
| `shot_compose.py --from-prev-shot` | 이전 클립 끝 프레임→키프레임 | Rule 7.2 clip approve |
| `shot_keyframe_edit.py` | 키프레임 국소 I2I 수술 | draft 재승인 · no global blur |
| `clip_review_sheet.py` | 컷 검수 first/last + contact | 자동 승인 아님 |
| `generate_bgm.py` | BGM 생성 | ACE-Step 1.5 turbo (or Sonilo) |
| `episode_bgm.py` | 에피소드 music stem | `audio/music/` + shots.json audio.bgm |
| `generate_moody_i2i_ipadapter.py` | I2I + IP-Adapter face | C identity |
| `generate_moody_i2i_lock.py` | I2I identity-strong (폴백) | C identity |
| `look_create.py` | Style Core 룩 패키지 생성 | looks/ |
| `look_status.py` | 룩 목록·검증·approve | looks/ |
| `shot_with_character.py` | 스토리 키프레임 | i2i |

워크플로우 JSON은 **`workflows/agent/`** 만 수정·프로모트한다.
