# 📜 에이전트 작업 협업 규칙 및 핸드북 (agent_rules.md)

이 문서는 `agent_custom` 워크스페이스를 개선·운영하는 **AI 코딩 에이전트**를 위한 공식 지침이다.  
이 저장소는 휴먼 GUI 앱이 아니라 **에이전트용 ComfyUI 도구** 구성이 목표다. 협업 연속성과 품질을 위해 아래 규칙을 준수한다.

---

## 📌 레이아웃 (먼저 열 곳)

```text
agent_custom/
  agent_rules.md   process.md   README.md     ← 규칙·이력·입구
  workflows/agent/                             ← 워크플로우 JSON SSOT
  scripts/                                     ← CLI 진입점
  lib/                                         ← 공유 코드
  characters/                                  ← 캐릭터 패키지
  looks/                                       ← 룩/스타일 코어
  locations/                                   ← 로케이션 패키지
  stories/                                     ← 에피소드 작업실
  deliveries/                                  ← 사용자 납품 상자 (zip)
  docs/                                        ← 설계·스펙·로드맵
```

* CLI: `python scripts/<name>.py ...` (루트 cwd 권장, 경로는 `_bootstrap` 이 처리)
* 워크플로우: `workflows/agent/` + `catalog.json` / `lib/workflow_paths.py`
* 구현 스펙: [docs/character_impl_spec.md](docs/character_impl_spec.md)
* 영상 납품: [docs/video_delivery_and_backends.md](docs/video_delivery_and_backends.md)
* **프로덕션 자산 통합**: [docs/production_asset_pipeline.md](docs/production_asset_pipeline.md)
* 로케이션 설계: [docs/location_sheet_system_design.md](docs/location_sheet_system_design.md)
* 룩/스타일: [docs/look_style_system.md](docs/look_style_system.md) · `looks/cinematic_moody_v1`
* 스토리보드 설계: [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md)

---

## 📌 핵심 작업 규칙

### Rule 1. 이력 관리의 의무 (`process.md` 상시 업데이트)
* 코드·워크플로우 JSON·성능 최적화 시 **즉시 `process.md` 최상단**에 이력을 추가한다.
* **[작업 일자], [에이전트 이름], [작업 목표], [주요 변경·파라미터]** 를 남긴다.

### Rule 2. 자동화 스크립트 정합성 유지
* ComfyUI UI에서 워크플로우를 바꾸면, 대응 스크립트(`scripts/generate_moody.py`, `scripts/generate_moody_i2i.py` 등)의 `convert_ui_to_api`·노드 주입 로직을 **함께** 갱신한다.
* JSON만 바꾸고 스크립트 매핑을 생략해 배치를 깨뜨리는 행위는 금지.

### Rule 2.1 에이전트 전용 워크플로우 경로
* 스크립트가 읽는 워크플로우 **SSOT는 `workflows/agent/`** 이다.
* 휴먼 UI 실험은 `workflows/human/` → 검증 후 agent 로 **프로모트**.
* 루트에 워크플로우 JSON을 두지 않는다 (레거시 제거됨). 폴백이 필요하면 `lib/workflow_paths` 가 루트를 볼 수 있으나 **SSOT는 agent 만**.
* agent 반영 시 관련 `scripts/generate_*.py` 와 함께 커밋 + `process.md` 기록.

### Rule 2.2 디렉터리 역할 고정
* **신규 CLI** → `scripts/`
* **공유 모듈** → `lib/`
* **설계·스펙 문서** → `docs/`
* **캐릭터 데이터** → `characters/`
* **룩** → `looks/`
* **로케이션 / 스토리** → `locations/`, `stories/`
* **사용자 납품** → `deliveries/` (`package_delivery.py`). 작업실은 `stories/`. 상세 [docs/delivery_handoff.md](docs/delivery_handoff.md).
* 루트에 실행 스크립트·워크플로우 JSON·장문 스펙을 새로 쌓지 말 것.

### Rule 3. Flow Matching 모델 연산의 이해 및 보존
* 코어 모델 `Z-Image-Turbo` 는 Flow Matching 이다.
* I2I 시 `res_multistep` 대신 **`euler`/`normal`**, denoise **`0.70 ~ 0.85`**, CFG 권장 **≥ 3.5**.
* I2I 타임스텝 시프터 하드 와이어를 무단 변경하지 말 것.

### Rule 4. 경로 무결성 보존
* ComfyUI 경로(`F:\ComfyUI_windows_portable\ComfyUI\`) 등 드라이브 하드코딩이 있다. 이전 시 주의.

### Rule 5. 인수인계 핸드훅
* 작업 종료 시 **[안정성 상태], [물리 법칙/임계치], [다음 추천 작업]** 을 남긴다.

### Rule 6. 캐릭터 패키지 및 구현 스펙
* 코딩 시 [docs/character_impl_spec.md](docs/character_impl_spec.md) 가 [docs/character_sheet_system_design.md](docs/character_sheet_system_design.md) 보다 우선.
* 시트 denoise·alias → `characters/sheet_presets.json` SSOT.
* 용도 프로필 → `characters/profiles.json` SSOT, 기본 `video_ref`.
* 본 촬영 입력은 **`approved/` 승격 레퍼**만.
* 새 캐릭터는 `characters/_template/` 구조. artbook/video 로 character_id 를 쪼개지 말 것.
* **L3 LoRA 학습** 은 캐릭터 품질 전용 PR로 분리 (로케/스토리/I2V/업스케일과 한 PR에 섞지 말 것).
* 캐릭터 턴어라운드 품질 고도화는 **병렬 트랙**. establishing/medium 에피소드의 블로커로 두지 말 것.

### Rule 6.2 캐릭터 캐스팅 공정 (A→B→C)
* **A 탐색**: `character_cast_pool.py` — 다엔진(Moody/Krea) 후보. identity 미고정. `characters/casts/`.
* **B 승격**: `character_promote.py` — 고른 이미지 → 패키지 + `approved/master_front` + core 고정.
* **C 일관 / 캐릭터 시트**: 업계 **풀 시트**가 공정 본체.
  - 프로필: **`full_sheet`** (`profiles.json` `character_sheet_process_profile`). `video_ref`는 영상 thin pack 전용 — 시트 완성이 아님.
  - 원샷: `python scripts/character_full_sheet.py --id <id> --run` (expand full_pack → approve → review grids).
  - 구성: head turn · body turn · expression · costume(+detail) · pose/action · props.
  - 엔진 auto: 표정/헤드 `i2i`/`i2i_lock`, 턴·포즈 `controlnet`, 의상/소품 `i2i`.
  - **`ipadapter`**: CLI 유지, **공정 SOP 미사용**.
* 확정 전 LoRA 학습은 기본 경로 아님. SSOT: [docs/character_casting_pipeline.md](docs/character_casting_pipeline.md).

### Rule 6.3 Look / Style Core
* 전역 톤 = `looks/<look_id>/` cores. 에피소드 `look_id` 필수에 가깝게 취급.
* 생성: `look_create` · 검증: `look_status` · 샷: `shot_compose` 가 자동 주입.
* SSOT: [docs/look_style_system.md](docs/look_style_system.md).

### Rule 6.0 멀티 트랙 (활성 작업 모델)
* 단일 `CHARACTER_L2_SOFT_FACTORY` 전용이 아니다. 동시 허용:
  - **C** 캐릭터 L2 · **L** 로케이션 · **S** 스토리/샷 · **M** I2V/모션 · **U** 업스케일/조립 · **K** 룩
* 통합 지도: [docs/production_asset_pipeline.md](docs/production_asset_pipeline.md).

### Rule 6.1 로케이션·스토리보드·룩
* 에피소드 = **char + loc + look + shots**. 룩: [docs/look_style_system.md](docs/look_style_system.md), 기본 `looks/cinematic_moody_v1`.
* 키프레임·I2V: **draft 로케/캐릭터 금지**. `location_id` 없이 배경 즉흥 금지.
* **Storyboard-first**: 키프레임 검수 전 전 샷 I2V 금지.
* **비율**: char/loc 시트 ref는 고유 비율 OK. **board/keyframe/I2V 출력만 episode format 캔버스**.
* 로케이션: [docs/location_sheet_system_design.md](docs/location_sheet_system_design.md). 스토리: [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md).

### Rule 7. 영상 해상도·백엔드 규약
* **format** = 종횡비 (`cinematic_16x9` …). 16:9 고정 아님. SSOT: `video_backends.json`.
* **work 프리셋** = format별 픽셀 (`work_16x9_540` …). I2V 생성용.
* **deliver 티어** = 짧은 변만 (`deliver_1080` / `deliver_1440` / `deliver_2160`). SSOT: **`upscale_backends.json`**. aspect는 format이 담당.
* 구 ID `deliver_16x9_1080` 등은 **deprecated** (`deliver_aliases` → `deliver_1080`).
* I2V: work 해상도. 납품: `scripts/upscale_* --preset deliver_1080 --format …`.
* 업스케일 **기본 = rtx_vsr**. seedvr2는 히어로 opt-in (실무 배치 비권장). [docs/upscale_research_and_design.md](docs/upscale_research_and_design.md).

### Rule 7.1 오디오 · 모션 드라이버
* 작품 종류 = `production_mode` (`music_video` / `story` / `hybrid` / `video_only`). 뮤비 원곡 ≠ 스토리 late BGM.
* 샷 모션 = `motion_driver` (`i2v` 기본, **`si2v` = 온스크린 입·보컬**, still…).  
  - **story**: 대사 컷 → `si2v` + dialogue wav.  
  - **music_video**: 카메라 앞 **노래/보컬 퍼포** 컷 → `si2v` + master 구간 슬라이스(보컬 prep 권장). B-roll·춤-only는 `i2v`.  
  - SI2V는 스토리 전용이 아님. I2V만으로 립싱크 때우지 말 것.
* 뮤비 최종 오디오 = **music master** (`music_locked`). SI2V driving 슬라이스는 모션용; 클립 오디오로 원곡을 대체하지 말 것.
* 조립 = `mix_policy` + stems (`audio/masters|music|dialogue|vo|sfx`). SSOT: [docs/audio_motion_production_modes.md](docs/audio_motion_production_modes.md).
* **본선 = Comfy 생성 품질** (키프레임·I2V·SI2V). 외부 편집 monorepo(OpenMontage 등)는 참고만.
* SI2V 기본 백엔드 = **`ltx23_ia2v`**. **`infinitetalk`** = 1급 대안 (v4 center_voicey 실용 립). 폐기 금지.
* SI2V 기본 캔버스 = **square** (얼굴/입); 에피소드 aspect는 deliver/upscale 단계에서.
* Driving prep 기본 = **`auto`** (demucs → center_voicey).
* 뮤비 보컬 컷: `audio_bind_driving.py -e <ep> --shot S0x --start … --duration …`
* CLI: `audio_status.py`, `audio_prepare_driving.py`, `audio_bind_driving.py`, `episode_s2v.py`, `assemble_video.py --mix-policy …`.

### Rule 8. Z-Image-Turbo ControlNet (Union 2.1)
* 모델 파일은 `models/model_patches/` (`controlnet` 폴더 아님).
* 표준 `ControlNetApply` 금지 → **`ZImageFunControlnet`** + **`FL_ZImageControlNetPatch`**.
* 강도 권장 `0.65 ~ 0.80`.

### Rule 9. Krea 2 Turbo
* UNet: `models/diffusion_models/Krea2Turbo/krea2_turbo_int8_convrot.safetensors`
* TE: `qwen3vl_4b_fp8_scaled.safetensors`, CLIPLoader type `"krea2"`
* VAE: `qwen_image_vae.safetensors`
* 기본: **8 steps**, **CFG 1.0**, sampler **`euler_ancestral`**, scheduler **`simple`**
