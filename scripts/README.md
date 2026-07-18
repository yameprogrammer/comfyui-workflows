# scripts/ — 에이전트 CLI 도구

이 저장소의 **실행 진입점** (ComfyUI API 배치).  
**무엇을 고를지:** [docs/tool_catalog.md](../docs/tool_catalog.md) — 의도 선반. 고정 공정 강제 아님.

```bash
# 레포 루트 cwd
python scripts/<name>.py --help
```

`_bootstrap.py` 가 레포 루트·`scripts/` 를 path에 넣음 → `lib.*` / 동료 스크립트 import OK.

---

## 의도 선반 → CLI

에이전트: **목표 → 선반 → 스크립트**. ASSETS / BUNDLE 은 **옵션**.

### GENERATE — 새 스틸

| 스크립트 | 역할 |
|----------|------|
| `generate_moody.py` | 실사 T2I (Lonecat) |
| `generate_illustrious_standard.py` | 애니 XL / Illustrious |
| `generate_krea.py` / `generate_krea_nsfw.py` | Krea2 스틸 (**nsfw=18+**) |
| `generate_ideogram4.py` | 가벼운 타이틀·간판 |
| `generate_boogu_typo.py` | 잡지·포스터 글자+인물 |

### TRANSFORM — 레퍼 변형 · 편집

| 스크립트 | 역할 |
|----------|------|
| **`generate_character_consistent.py`** | ID 유지 lock/soft/remix/pack/anchor… |
| **`generate_ref_pack.py`** | 가벼운 ID 레퍼 팩 (master+각도, 패키지 없이) |
| **`generate_style_transfer.py`** | 스타일 전이 (preset / ref / look · Qwen 기본) |
| `generate_moody_i2i.py` | Lonecat I2I |
| `generate_moody_i2i_lock.py` | I2I + identity cap |
| `generate_moody_i2i_ipadapter.py` | IPA 경로 (실험·비권장 SOP) |
| `generate_qwen_edit.py` | 문장 전역 편집 |
| `generate_qwen_inpaint.py` | 마스크 국소 인페 |
| `shot_keyframe_edit.py` | 에피 키프레임 국소 수정 *(BUNDLE와 겹침)* |
| `shot_edit.py` | 샷 메타/파일 편집 헬퍼 |

### CAMERA — 각도 · 포즈

| 스크립트 | 역할 |
|----------|------|
| `generate_qwen_angle.py` | 멀티앵글 (앞/옆/뒤) |
| **`generate_viewpoint.py`** | 깊이·시점 과장 (하이/로우/버즈아이, Comfy Qwen) |
| `generate_moody_controlnet.py` | Fun Union ControlNet |
| `character_qwen_turns.py` | 캐릭 패키지 턴 배치 |
| **`generate_reframe.py`** | 샷 사이즈 리프레임 (크롭/줌, Comfy 불필요) |

### MOTION — 영상

| 스크립트 | 역할 |
|----------|------|
| **`generate_camera_move.py`** | 카메라 무빙 의도 I2V (`--preset push_in` 등) |
| **`generate_idle_loop.py`** | 아이들 모션 + 루프 (pingpong / roundtrip / idle) |
| **`generate_dance_ref.py`** | 댄스/레퍼 모션 (V2V motion · i2v 스타일) |
| `generate_i2v.py` | I2V 일반 · **`--motion-preset`** (동일 프리셋) |
| `generate_v2v.py` | V2V 의도 camera/motion/style (저수준) |
| `generate_yaw_wan22.py` | Wan 2.2 MoE T2V/I2V |
| `generate_flf2v.py` | 첫·끝 프레임 |
| `generate_s2v.py` | 이미지+오디오 (립 등) |
| `generate_v2v.py` | V2V 의도 (experimental) |
| `generate_ltx23_latentheart.py` | LTX Director 모듈 |
| `generate_ltx23_redmix_i2v.py` | REDMix I2V |
| `generate_ltx_nsfw_i2v.py` / `generate_ltx_nsfw_director.py` | 성인 모션 **18+** |
| `run_ltx_aio_features.py` | LTX AIO 기능 목록/실험 |

### VOICE · AUDIO

| 스크립트 | 역할 |
|----------|------|
| `generate_qwen3_tts.py` | TTS custom/design/clone |
| `voice_register.py` | 보이스 샘플 등록 |
| `generate_bgm.py` | BGM |
| `audio_slice.py` / `audio_prepare_driving.py` / `audio_bind_driving.py` / `audio_status.py` | 드라이빙·슬라이스 유틸 |

### FINISH — 업스케일 · 다듬기

| 스크립트 | 역할 |
|----------|------|
| `upscale_image.py` | 스틸 업스케일 |
| `upscale_video.py` | 영상 업스케일 |
| `generate_wan22_face_enhance.py` | 얼굴 향상 (실험) |
| `generate_wan22_upscale.py` | Wan 업스케일 옵트인 |

### ASSETS — 재사용 패키지 *(옵션)*

장기 시리즈·동일 캐릭/장소 자산이 필요할 때만.

| 스크립트 | 역할 |
|----------|------|
| `character_create.py` · `character_cast_pool.py` · `character_shortlist.py` · `character_promote.py` | 캐스팅 |
| `character_approve.py` · `character_status.py` · `character_set_wardrobe.py` | 승인·의상 |
| `character_expand_sheets.py` · `character_full_sheet.py` · `character_turnaround_sheet.py` · `character_pipeline.py` | 시트 |
| `location_create.py` · `location_expand_sheets.py` · `location_full_sheet.py` · `location_approve.py` | 로케 |
| `look_create.py` · `look_status.py` | 룩 |
| `assets_list.py` | 자산 목록 |
| `shot_with_character.py` | 캐릭 템플릿 샷 (헬퍼) |

### BUNDLE — 멀티샷 · 에피 · 검수 *(옵션)*

`stories/` 레일·합본·배치를 **원할 때만**.

| 스크립트 | 역할 |
|----------|------|
| `story_init.py` · `storyboard_export.py` | 에피 골격·보드 |
| `shot_compose.py` · `shot_approve.py` · `shot_qa_pack.py` · `shot_qa_record.py` | 키프레임·QA·승인 |
| `episode_i2v.py` · `episode_s2v.py` · `episode_tts.py` · `episode_v2v.py` · `episode_bgm.py` · `episode_upscale.py` | 배치 (`episode_i2v --motion-preset`) |
| `episode_status.py` · `episode_qa.py` · `episode_identity_sheet.py` · `episode_contact_sheet.py` · `episode_subtitles.py` · `episode_pipeline.py` | 상태·검수·자막 |
| `chain_one_take.py` · `chain_si2v_last_frame.py` · `assemble_video.py` · `assemble_single_take.py` | 이음·합본 |
| `export_episode_to_workspace.py` · `package_delivery.py` · `clip_review_sheet.py` | 반출·리뷰 |
| `commission_start.py` · `smoke_agent_av.py` | 커미션·스모크 |

### META — 공장 운영 (모든 선반 공통)

| 스크립트 | 역할 |
|----------|------|
| **`tool_intent.py`** | **의도 → CLI 검색** (+ 관련 failure 프리플라이트) |
| **`failure_note.py`** | **실수 방지** · `before` / search / add / list (Rule 7.4) |
| `comfy_ensure.py` | Comfy 기동 확인/자동 기동 |
| `run_workflow_api.py` | API 프리셋 직접 실행 |
| `skill_equip.py` | 스킬 장착 (연출 등) |
| `factory_cleanup.py` | 스테이징 정리 |

---

## 실행 메모

- Comfy: `127.0.0.1:8188` · 런처 SSOT `run_nvidia_gpu.bat` (`F:\ComfyUI_data` input/output)
- 상세 when/when-not: **tool_catalog** · 도구별 `workflows/human/**/AGENT_GUIDE.md`
- `_archive/` · `__pycache__` 는 프로덕션 입구 아님
