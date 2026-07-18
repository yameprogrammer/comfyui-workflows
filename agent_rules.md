# 📜 에이전트 작업 협업 규칙 및 핸드북 (agent_rules.md)

이 문서는 `agent_custom` 를 개선·운영하는 **AI 코딩 에이전트**를 위한 지침이다.

## 정체성 (SSOT)

```text
agent_custom = ComfyUI 미디어 생성 도구 모음 (toolbox)
            ≠ 정형화된 영상 양산 공정 / 단일 파이프라인 강제
```

* **도구 명세·선택 (의도 선반 SSOT):** [docs/tool_catalog.md](docs/tool_catalog.md) · 입구 [TOOLS.md](TOOLS.md)  

* **소비자 진입:** [AGENTS.md](AGENTS.md)  
* 각 미디어 **프로젝트**가 공정·스토리를 정하고, 여기서는 **도구를 골라** 쓴다.  
* `stories/` + approve + assemble 은 **옵션 레시피** (프로젝트 선택 시만 Rule 7.x 게이트 적용).

---

## 📌 레이아웃 (먼저 열 곳)

```text
agent_custom/
  README.md  AGENTS.md  agent_rules.md  process.md
  docs/tool_catalog.md     ← 도구 특징 명세 (1순위)
  workflows/agent|human/   ← 프리셋·UI 원본
  scripts/  lib/           ← CLI · 러너
  characters/ looks/ locations/ stories/  ← 헬퍼 데이터·옵션 에피소드
  failures/ docs/          ← 실패 노트 · 상세 스펙
```

* CLI: `python scripts/<name>.py ...` (루트 cwd)  
* 카탈로그: `workflows/agent/catalog.json`  
* docs 인덱스: [docs/README.md](docs/README.md)  
* 스킬(연출 등): [skills/](skills/) — **에피소드 레일·품질 향상용, 전 작업 필수 아님**

---

## 📌 소비자 에이전트 (도구만 호출할 때)

1. [TOOLS.md](TOOLS.md) → [docs/tool_catalog.md](docs/tool_catalog.md) 에서 **의도 선반**을 고른다  
   (GENERATE / TRANSFORM / CAMERA / MOTION / VOICE / FINISH · ASSETS·BUNDLE은 옵션).  
2. when / when not · 대안 CLI 확인 후, cwd = 레포 루트에서 `python scripts/...` 실행.  
3. 출력은 `-o` / 로컬 경로 / 또는 프로젝트로 **복사**.  
4. 에피소드 패키지(`stories/`)·캐릭 패키지를 **쓸 때만** 해당 계약·게이트 적용.  
5. 단일 still / I2V / inpaint / TTS 호출만으로도 **완료 가능** (전체 영상 공정 불필요).  
6. 스크립트 목록(선반별): [scripts/README.md](scripts/README.md).

---

## 📌 핵심 작업 규칙

### Rule 1. 이력 관리의 의무 (`process.md` 상시 업데이트)
* 코드·워크플로우 JSON·성능 최적화 시 **즉시 `process.md` 최상단**에 이력을 추가한다.
* **[작업 일자], [에이전트 이름], [작업 목표], [주요 변경·파라미터]** 를 남긴다.

### Rule 2. 도구 CLI · 워크플로 정합성
* **도구 목록·특징 SSOT:** [docs/tool_catalog.md](docs/tool_catalog.md) (프로젝트는 여기서 선택).
* **주요 CLI 매핑 (요약 — 상세는 카탈로그):**
  - still: `generate_moody` / `generate_krea` / `generate_krea_nsfw`(18+)
  - I2I·CN: `generate_moody_i2i*` / `generate_moody_controlnet`
  - Qwen: `generate_qwen_edit` · `generate_qwen_inpaint` · `generate_qwen_angle`
  - video: `generate_i2v` / `generate_s2v` (LTX AIO 기본, Wan fallback) · `generate_flf2v`
  - LTX 품질 티어: `--ltx-profile draft|work|hero` (기본 work; 히어로 컷만 hero). 리서치: `docs/ltx23_quality_research_and_improvement.md`
  - NSFW video: `generate_ltx_nsfw_i2v` / `generate_ltx_nsfw_director` (18+)
  - TTS: `generate_qwen3_tts` (custom/design/**clone**) · `voice_register` — 클론 ref **≤~30s** · 감정 `--instruct` · 가이드 `workflows/human/qwen3_tts/AGENT_GUIDE.md`
  - 타이포 파이프: `generate_boogu_typo` — Boogu→Ideogram4→Krea2 (`NEWKrea2BooguIdeogram4_booguKrea2`) · 가이드 `workflows/human/NEWKrea2BooguIdeogram4_AGENT_GUIDE.md`
* **실 UI 도구:** 미니 그래프·무단 inject 본선 금지. 포트/스위치/GGUF 스왑만.  
  비상: `--legacy-mini` / `AGENT_*_BACKEND=legacy_mini`.
* UI 변경 후: API re-export 또는 expand 러너 + catalog / ports 갱신 + **tool_catalog.md 블록 추가**.
* JSON만 바꾸고 CLI·카탈로그를 안 맞추면 금지.

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

### Rule 3.0 AIO 워크플로우 — 기능은 프리셋으로 선택 (Bypasser 분석 결과)
* Lonecat / Krea2 등 AIO의 **Fast Groups Bypasser / selector / Any Switch** 는 UI 기능 스위치다.
* 에이전트는 UI를 클릭하지 않고 **`feature_id` → ready `agent_preset` → `*.api.json` + port patch** 만 사용한다.
* **Lonecat (Z-Image):** `workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md`, `…_CAPABILITIES.json`
* **Krea2:** `workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md`, `…_CAPABILITIES.json` · 소스 `krea2SFWNSFWUncensoredImageTo_v10` · 기본 프리셋 `krea2_t2i_v10` (CLIP **type=krea2** abliterated, Lonecat과 혼용 금지) · **NSFW 도구:** `generate_krea_nsfw` / alias `krea2_nsfw_t2i`
* **LTX23 NSFW (Kenpechi v20):** `workflows/human/ltx23_nsfw/AGENT_GUIDE.md` · I2V `ltx23I2VWorkflow_v20` · Director `ltx23DirectorWorkflow_directorV20` · 스위치 `lib/ltx23_nsfw_switches.py` · CLI `generate_ltx_nsfw_i2v` / `generate_ltx_nsfw_director` · 기본 프로필 `gguf_10eros`
* 공통 인덱스: `workflows/agent/presets/lonecat_feature_presets.json` (families 포함)
* 목록: `python scripts/run_workflow_api.py --list-features` · 재스캔: `_build_lonecat_capabilities.py` / `_build_krea2_capabilities.py`
* 새 기능 = UI에서 바이패서 조합 고정 → API export → presets 등록. full AIO `convert_ui_to_api` / 런타임 노드 inject 금지.

### Rule 3. Flow Matching 모델 연산의 이해 및 보존
* 코어 모델 `Z-Image-Turbo` 는 Flow Matching 이다.
* I2I 시 `res_multistep` 대신 **`euler`/`normal`**, CFG 권장 **≥ 3.5**.
* **Denoise는 목적별로 나눈다** (일괄 0.70–0.85 금지 — 얼굴/아이덴티티 붕괴의 주원인):
  - **프로덕션 키프레임 + 인물 ID 유지** (`shot_compose`, face-bearing source): **0.42–0.58** (기본 ~0.52). `i2i_lock` / IPAdapter 우선.
  - **장소/빈 세트/insert** (인물 없음): **0.50–0.65**.
  - **강한 구조 변경·시트 리믹스** (아이덴티티 희생 가능): **0.65–0.80**. 얼굴 있으면 lock/IPA 필수.
  - **헤드리스 costume / face crop cover** 를 medium 키프레임 source로 쓰지 말 것. pose·full body·layout 합성 사용.
* I2I 타임스텝 시프터 하드 와이어를 무단 변경하지 말 것.

### Rule 4. 경로 무결성 보존
* ComfyUI 경로(`F:\ComfyUI_windows_portable\ComfyUI\`) 등 드라이브 하드코딩이 있다. 이전 시 주의.
* **Comfy 미기동 시**: `lib/comfy_client.ensure_comfy_running` 이 기본 런처 bat으로 자동 기동한다.
  - 기본 bat: `F:\ComfyUI_windows_portable\run_nvidia_gpu.bat` (수동 기동 SSOT)
  - **기동 SSOT**: `_launch_comfy_process` → bat **내용을 파싱**해 동일 argv 실행 (cwd = portable 루트).  
    `run_nvidia_gpu.bat` 예:  
    `python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --output-directory F:\ComfyUI_data\output --input-directory F:\ComfyUI_data\input --temp-directory F:\ComfyUI_data\temp`  
    (`--fast` / `--disable-smart-memory` **없음**). `start`/`startfile`/중첩 cmd **금지**. 다른 bat은 `AGENT_COMFY_LAUNCH_BAT`로 지정.
  - 생성 스크립트는 **`queue_prompt` / `comfy_ensure.py`** 경로만 (예: `generate_krea.py`도 동일). raw `/prompt` POST 금지.
  - 중복 기동 방지: API probe + launch lock + launch_state cooldown
  - 끄기: `AGENT_COMFY_AUTOSTART=0` · 사전 점검: `python scripts/comfy_ensure.py`

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
  - 프로필: **`full_sheet`**. `video_ref`는 영상 thin pack 전용 — 시트 완성이 아님.
  - **B2 필수 (face 다음)**: 의상·소품 선잠금  
    `python scripts/character_set_wardrobe.py --id <id> --default "..." --alt1 "..." --props "..." --lock`  
    bible: `wardrobe_default` / `wardrobe_alt1` / `props_default` / `wardrobe_locked`.
  - **원샷 C**: `python scripts/character_full_sheet.py --id <id> --run`  
    순서: wardrobe 게이트 → master_full → **B2.5 design plates** (off-body flat/callout/prop) → on-model costume → **Qwen turns** → expr/pose/props.hand → grids.  
    미잠금 시 중단 (`--allow-unlocked-wardrobe` 비상만).
  - **B2.5 디자인 플레이트** (사람 없음): `costume.flat_front/back`, `costume.callout`, `props.hero`, `props.turn_3view` (T2I product).  
    페이즈만: `--phases design`
  - 엔진: design=`t2i` product · head/body turn=`qwen` · expression=`i2i` · pose=`controlnet` · on-model costume/props=`i2i`+bible.
  - body 소스 우선순위: `approved/costume_default` → `master_full`.
  - 턴만: `character_qwen_turns.py --mode both --approve`
  - OpenPose 턴 / **ipadapter 노드 inject**: 폐기. `engine=ipadapter` 는 Lonecat I2I identity 프리셋으로 라우트.
  - **스틸 편집 엔진 공존** (역할 합치지 말 것):
    - Moody/Lonecat I2I (`generate_moody_i2i` / `shot_keyframe_edit --engine moody`) — `lonecat_i2i_identity` API 프리셋 (denoise 리믹스·아이덴티티)
    - Qwen Edit (`generate_qwen_edit` / `shot_keyframe_edit --engine qwen`) — 기본 **2509 Q5 GGUF** + 지시 편집 (Angles LoRA 없음)
    - Qwen Angle (`generate_qwen_angle` / `character_qwen_turns`) — **2511 GGUF** + Lightning + **Angles LoRA**, 멀티뷰 턴
    - **Qwen Edit Lightning 정책**: 기본 **ON** (4step). 결과 부족(국소 실패·소품 과삭제) 시에만 `--no-lightning --steps 20 --cfg 4` 승격.
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
* **Clip-first (합본 전 컷 검수)**: 워크 클립 생성 후 **컷별 육안 승인 전 `assemble_video` 금지**. 상세 Rule 7.2.
* **비율**: char/loc 시트 ref는 고유 비율 OK. **board/keyframe/I2V 출력만 episode format 캔버스**.
* 로케이션: [docs/location_sheet_system_design.md](docs/location_sheet_system_design.md).  
  - 패키지: `locations/<id>/` · 원샷: `python scripts/location_full_sheet.py --id <id> --run`  
  - MVP(video_ref): master_wide + angles(eye/reverse/high/low) + empty_stage + light_day  
  - 파일럿: `cafe_seoul_v1` (L2). 키프레임은 `location_id` + approved 로케 ref 없이 배경 즉흥 금지.  
* 스토리보드 · 키프레임 (커뮤니티 실무 정렬):  
  - 보드·키프레임: [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md) · 리서치 원문(아카이브): [docs/archive/research/storyboard_keyframe_community_research.md](docs/archive/research/storyboard_keyframe_community_research.md)  
  - 순서: asset packs → `story_init` → `shot_compose` → **`storyboard_export`** (contact gate) → `shot_approve` → I2V/SI2V → **컷별 `shot_approve --clip`** → assemble.  
  - **T2V 장편 직행 금지**. 샷당 production keyframe still @ episode format.  
  - I2V `motion_prompt` = 모션/카메라만 (얼굴·의상 재서술 금지).  
  - `shot_type`이 approved ref 우선순위 결정 (`stories/shot_type_presets.json`).  
* 스토리 설계: [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md).

### Rule 7.0 영상 연출 레일 (**옵션** — `stories/` 에피소드 본선을 쓸 때만)
* **적용 조건:** 프로젝트가 이 레포의 **에피소드 패키지 + shot_compose + assemble** 레일을 쓰기로 한 경우.  
  단일 I2V/still/inpaint 도구 호출만 할 때는 **이 절을 강제하지 않는다.**
* **권장 스킬:** [skills/video-direction/SKILL.md](skills/video-direction/SKILL.md) · [generation-prompt](skills/generation-prompt/SKILL.md)  
* **권장 산출 (에피소드 레일):** `CREATIVE.md` · `SHOT_DESIGN.md` → 키프레임 QA → 모션 → clip approve → assemble  
* **컷 문법 (레일 사용 시):** 동일 framing 3연속 금지 · coverage · freeze-pad 금지 — 상세 master persona  
* **범위 밖:** 도구 버그픽스·스모크·카탈로그 단일 CLI.  
* 연결: [docs/tool_catalog.md](docs/tool_catalog.md) §4 옵션 레일 · [AGENTS.md](AGENTS.md) §0.

### Rule 7. 영상 해상도·백엔드 규약
* **format** = 종횡비 (`cinematic_16x9` …). 16:9 고정 아님. SSOT: `video_backends.json`.
* **work 프리셋** = format별 픽셀 (**기본 `work_*_720`** 2026-07-18; draft/fast = `work_*_540`). I2V 생성용.
* **deliver 티어** = 짧은 변만 (`deliver_1080` / `deliver_1440` / `deliver_2160`). SSOT: **`upscale_backends.json`**. aspect는 format이 담당.
* 구 ID `deliver_16x9_1080` 등은 **deprecated** (`deliver_aliases` → `deliver_1080`).
* I2V: work 해상도 **기본 720p** (`--ltx-profile work`; draft≈540 · hero≈1080 gen). 납품: `scripts/upscale_* --preset deliver_1080 --format …`.
* 업스케일 **기본 = esrgan** (`--style photo|anime|…`). seedvr2는 히어로 opt-in (실무 배치 비권장). rtx_vsr은 노드 있을 때 optional. **엔진 모름 →** `python scripts/upscale_recommend.py --media … --goal …` (matrix/scenarios). 팩: [image_upscale_dual](workflows/human/image_upscale_dual/AGENT_GUIDE.md) · [docs/upscale_research_and_design.md](docs/upscale_research_and_design.md).
* **Wan2.2 `block_swap` (BlockSwap)**: VRAM↔속도 조절. **만능 고정값 아님 — 작업 크기·VRAM에 따라 `--block-swap` 조절.**  
  일상 출발 deliver≈10 · 큰 해상/긴 클립/OOM → 20+ · 여유 시 0. 품질 스킵(Tea/Mag)과 무관.  
  SSOT: [docs/wan22_i2v_speed_research.md](docs/wan22_i2v_speed_research.md) §4.1.

### Rule 7.1 오디오 · 모션 드라이버
* 작품 종류 = `production_mode` (`music_video` / `story` / `hybrid` / `video_only`). 뮤비 원곡 ≠ 스토리 late BGM.
* 샷 모션 = `motion_driver` (`i2v` 기본, **`si2v` = 온스크린 입·보컬**, still…, **`flf2v` = first–last 브리지 📋 PLANNED** — 상세 `docs/flf2v_f2f_roadmap.md`).  
  - 싱글테이크 연속감: FLF 구현 전에는 `shot_compose --source prev_keyframe` 체인으로 키프레임만 이을 것. FLF≠립.  

  - **story**: 대사 컷 → `si2v` + dialogue wav.  
  - **music_video**: 카메라 앞 **노래/보컬 퍼포** 컷 → `si2v` + master 구간 슬라이스(보컬 prep 권장). B-roll·춤-only는 `i2v`.  
  - SI2V는 스토리 전용이 아님. I2V만으로 립싱크 때우지 말 것.
* 뮤비 최종 오디오 = **music master** (`music_locked`). SI2V driving 슬라이스는 모션용; 클립 오디오로 원곡을 대체하지 말 것.
* 조립 = `mix_policy` + stems (`audio/masters|music|dialogue|vo|sfx`). SSOT: [docs/audio_motion_production_modes.md](docs/audio_motion_production_modes.md).
* **본선 = Comfy 생성 품질** (키프레임·I2V·SI2V). 외부 편집 monorepo(OpenMontage 등)는 참고만.  
  - 기능 목록·유용도: `docs/openmontage_capability_catalog.md` (공식 연동 SOP 없음 — “이런 게 있다” 수준).  
  - 전체 파이프 대체 금지. 이식 시 얇은 wrapper + 작업대 export 유지.
* SI2V 기본 백엔드 = **`ltx23_ia2v`**. **`infinitetalk`** = 1급 대안 (v4 center_voicey 실용 립). 폐기 금지.
* SI2V 기본 캔버스 = **square** (얼굴/입); 에피소드 aspect는 deliver/upscale 단계에서.
* Driving prep 기본 = **`auto`** (demucs → center_voicey).
* 뮤비 보컬 컷: `audio_bind_driving.py -e <ep> --shot S0x --start … --duration …`
* CLI: `audio_status.py`, `audio_prepare_driving.py`, `audio_bind_driving.py`, `episode_s2v.py`, `assemble_video.py --mix-policy …`.
* **대사/내레이션 TTS (Qwen3-TTS)**:  
  - 로컬 Comfy `FB_Qwen3TTS*` — custom 프리셋 / design 새 목소리 / **clone 복제**.  
  - CLI: `generate_qwen3_tts.py` (temperature·instruct 튜닝), `voice_register.py` (`voices/<id>/`), `episode_tts.py --bind-si2v`.  
  - **본선 감정 대사** = TTS(감정 instruct 또는 감정 있는 clone ref) → prepare_driving → `episode_s2v`.  
  - 클론: 5–15s 클린 샘플 + **ref_text 필수에 가깝게**. 첫 clone 시 Base 모델 다운로드 가능.  
  - 어색하면 temperature↓(0.65–0.8), 문장 짧게, instruct 과장 줄이기.  
  - SSOT: [docs/qwen3_tts_ltx_audio_pipeline.md](docs/qwen3_tts_ltx_audio_pipeline.md).
* **BGM (ACE-Step 1.5)**:  
  - 로컬 Comfy ACE-Step XL turbo (사용자 WF `audio_ace_step1_5_xl_turbo.json`).  
  - CLI: `generate_bgm.py`, `episode_bgm.py` → `stories/<ep>/audio/music/`.  
  - 기본 **instrumental only**; 뮤비 원곡 `masters/` 는 AI로 대체하지 않음.  
  - 립싱크 driving에 BGM 섞지 말 것 (보이스 stem만).

### Rule 7.2 컷별 검수 게이트 (에피소드 **assemble 레일** 사용 시 · hard)
* **문제**: 합본(final)만 보고 중간 컷을 고치면 재생성·체인 재작업 비용이 폭증한다.  
  last-frame SI2V 체인은 붕괴 컷의 끝 프레임이 **다음 seed**가 되어 피해가 전파된다.
* **의무 순서**  
  1. **키프레임 육안** (Rule **7.3**) 통과 → `keyframe_status=approved` → 모션 생성 허용  
  2. 샷별 work clip 생성 (`episode_i2v` / `episode_s2v` / `chain_si2v_last_frame` / 하이브리드 본선 클립)  
  3. **클립 육안** (Rule **7.3**) 통과 → `clip_status=approved` (`shot_approve -e EP -s S0x --clip approved`)  
  4. (체인) **이전 컷 `clip_status=approved` 전** 다음 샷 last-frame 생성 금지  
  5. **전 조립 대상 샷 `clip_status=approved`** 후에만 `assemble_video`  
  6. 합본 검수 = 컷 간 이음·길이·BGM/믹스만 (컷 품질 재검수가 아님)
* **`clip_status` 계약**  
  - 값: `pending` | `in_review` | `approved` | `rejected`  
  - 워크 클립이 있는데 필드 없음 → `pending`  
  - 육안 내용 SSOT: [docs/image_cut_verification_gate.md](docs/image_cut_verification_gate.md)  
  - **자동 점수 없음** — 사람 또는 비전 에이전트가 **파일을 열고** 올린다  
  - SI2V의 `lip_status`는 하위 신호로 유지. `--clip approved` 시 립도 함께 본 것으로 보고 `lip_status=approved` 동기화 가능  
  - 클립 **재생성** 시 `clip_status`·`lip_status` → `pending` 으로 리셋
* **하드 게이트 (코드)**  
  - `assemble_video`: 조립에 쓰는 각 샷의 `clip_status` ∉ {`approved`,`ok`} 이면 **거부** (exit `22`)  
  - 우회: `--force-clip-gate` 만 (탐색/디버그). 본선·납품 경로에서 사용 금지  
  - `chain_si2v_last_frame`: 다음 샷으로 last-frame 넘기기 전 이전 샷 `clip_status` 확인 (동일 우회 플래그)  
  - `episode_status`: `need_clip_approve` · `overall_next=shot_approve_clip`  
  - `episode_qa --require-clip`: 미승인 클립 hard fail
* **합본의 역할 축소**  
  - final mp4는 **이음·오디오 믹스 확인용**. “중간 컷 얼굴이 괜찮은가”는 **컷 단계에서 끝낸다**.  
  - 불합격 컷만 재생성 → 재승인 → 그 샷부터 체인 재개 → 그 다음에 assemble.
* CLI:
  ```bash
  # 컷 생성 후 (SI2V/I2V 공통) — 육안 후에만
  python scripts/shot_approve.py -e EP -s S02 --clip approved
  python scripts/episode_status.py -e EP   # CLIP 열 / need_clip_approve
  python scripts/assemble_video.py -e EP --stage work   # 미승인이면 code=22
  ```

### Rule 7.3 이미지 컷 · 키프레임 · 클립 **육안 검증** (내용 SSOT · **기계 게이트**)
* **문제**: `approved` 플래그만 일괄 세팅하고 이미지를 열지 않으면, 구도 복붙·사지 붕괴·차량 파손·**후반 프리즈 패드**·**컷 간 인물 붕괴**가 본편에 그대로 들어간다.
* **SSOT**: [docs/image_cut_verification_gate.md](docs/image_cut_verification_gate.md) §8 기계 계약
* **의무**
  1. `shot_qa_pack` → **파일을 연 뒤** 체크리스트(K*/C*) Pass/Fail  
  2. `shot_qa_record` 로 `meta/visual_qa/<shot>_<stage>.json` 기록 (verdict=pass + notes + 필수 체크)  
  3. 그 다음에만 `shot_approve` — **QA 없으면 exit 23** (파일 존재만으로 approve 불가)  
  4. Fail → 재생성/수정 → **재검증** 후에만 approve  
  5. `QA_LOG.md` 자동 append — 로그 없는 mass approve **금지**  
  6. 3+ 키프레임: `episode_identity_sheet` + identity QA pass (컷 간 동일 인물)  
  7. 보드: 동일 `shot_type` **3컷 연속 금지** · **프리즈 패드 금지**  
  8. **Freeze**: 생성 후 기본 감지 fail (`FREEZE_PAD_SUSPECT`); tpad로 길이 채우기 금지. 의도 still만 `--allow-freeze` / `motion_driver=still`
* **CLI**
  ```bash
  python scripts/shot_qa_pack.py -e EP -s S03
  python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict pass \
    --pass-required --notes "opened pack; anatomy OK; matches master"
  python scripts/shot_approve.py -e EP -s S03 --status approved
  python scripts/episode_identity_sheet.py -e EP
  python scripts/episode_qa.py -e EP --require-visual-qa
  # clip: freeze check is default on
  python scripts/shot_qa_record.py -e EP -s S03 --stage clip --verdict pass \
    --pass-required --notes "full motion end-to-end"
  ```
* **우회**: `--force-approve` / `AGENT_REQUIRE_VISUAL_QA=0` / `AGENT_FREEZE_GATE=0` 는 디버그 전용 (감사 시 위반).
* **키프레임 최소 탈락 사유 (즉시 rejected)**  
  사지·손발 기형 · 지정 insert가 전신/얼굴로 대체 · 차량·유리·거울 구조 붕괴 · 필수 모티프 누락 · 직전 컷과 동일 구도 남발
* **클립 최소 탈락 사유**  
  후반 정지 구간 · 워프/모핑 · 아이덴티티 붕괴 · music_locked 인데 클립 오디오 정책 위반
* Grok 네이티브 산출물도 공장 경로에 넣기 **전** 동일 게이트. 프리뷰 경로(`_preview_grok/`)는 approve·assemble 입력 금지 (Rule 8).

### Rule 7.4 실패 노트 공유 (learn from failure · hard 습관)
* **문제**: 에이전트가 같은 실패(프리즈 패드, face CU 남발, 발/차량 붕괴, mass approve)를 **에피소드마다 리셋**한다.
* **저장소**: `failures/notes/*.json` · `failures/INDEX.md` · SSOT 문서 [docs/failure_notes_system.md](docs/failure_notes_system.md)
* **CLI**
  ```bash
  # 생성·보드 전 (관련 키워드/태그)
  python scripts/failure_note.py search "freeze OR feet OR car"
  python scripts/failure_note.py search --tag freeze_pad
  python scripts/failure_note.py list --limit 15

  # QA FAIL / 유저 리젝 직후 (같은 세션)
  python scripts/failure_note.py add --stage keyframe --tags anatomy_feet,insert_failed \
    --symptom "..." --cause "..." --fix "..." --prevention "..." \
    --severity high --agent grok -e EP -s S03
  ```
* **의무**
  1. **본선 생성 전** `search` 또는 INDEX 확인 (영상·캐릭 시트·로케 본선)  
  2. **FAIL/리젝** 시 `add` — symptom · root_cause · fix · **prevention** 필수  
  3. 침묵하고 넘어가기 금지 (severity medium 이상)  
* **QA_LOG 와의 구분**: QA_LOG=작품 컷 판정 / failures=전 에이전트 교훈. FAIL은 가능하면 둘 다.
* 태그 권장 목록: `failures/tags.json`.

### Rule 7.5 생성 프롬프트 품질 (T2I / I2I / I2V / SI2V · hard 습관)
* **문제**: 기획·샷 설계가 좋아도 **프롬프트가 빈약·태그 나열·의도 충돌**이면 키프레임/모션이 무너진다.
* **SSOT**: [docs/generation_prompt_craft.md](docs/generation_prompt_craft.md)
* **의무**
  1. 본선 생성 전 프롬프트를 §1 순서(**Subject → Action → Setting → Light → Camera → Style**)로 쓴다.  
  2. **한 샷 한 주 의도**. “beautiful 8k masterpiece” 도배 금지.  
  3. **I2V `motion_prompt` = 모션/카메라/환경만** — 얼굴·의상 재서술 금지 (기존 Rule 6.1과 동일 정신).  
  4. insert/feet/car/glass 등 risk 샷은 **제약 절** 필수 (craft §6).  
  5. insert에 character face core가 action을 이기면 face 블록 제거 또는 전용 T2I.  
  6. I2I는 denoise 표(craft §2.2 / moody guide)에 맞추고 **변경점 위주** 프롬프트.  
  7. 영어 본선 프롬프트 (연출 메모는 한국어 OK).  
* **생성 직전 체크**: craft §8 체크리스트.  
* **FAIL 시**: 프롬프트 보강 재생성 + `failure_note` (`prompt_ignored` 등).

### Rule 8.0 에이전트 자체 도구·스킬 자율 활용 (전 에이전트 · 영상 작업)
* **문제**: 유저는 Grok/Claude/Codex 등 **에이전트마다 다른 네이티브 툴·스킬·MCP**를 세세히 알 수 없어 “이때 뭘 쓰세요”라고 지시하기 어렵다.  
  에이전트가 공장 CLI 루틴만 수동적으로 돌리면 **품질·효율 기회**를 버린다.
* **SSOT**: [docs/agent_native_capability_autonomy.md](docs/agent_native_capability_autonomy.md)
* **의무 (영상·뮤비·쇼츠·비주얼 스토리)**  
  1. 세션에서 **사용 가능한** 자체 툴/스킬/MCP/서브에이전트를 내부 파악한다.  
  2. 기획·레퍼·키프레임 수술·모션 프리뷰·비전 검수 등 **도움이 되면 능동적으로 선택·실행**한다.  
  3. 유저가 툴을 **지정하기 전**에는 매 단계 툴 메뉴를 **묻지 않는다** (추천 1안 실행).  
  4. 유저가 툴/스킬을 **명시하면 그 지시 우선**.  
  5. 공장 게이트(페르소나·QA·clip approve·assemble·export·failure notes)는 **우회 금지**.  
  6. 자체 툴 본선 편입 시 디스크 경로 + 출처 한 줄 기록.  
* **금지**: 없는 툴 환각 · 프리뷰를 approve · 자체 툴로 립/assemble 대체(해당 공장 경로가 있을 때) · “뭘 쓸까요?” 반복.
* Grok 세부 매핑: Rule **8.1** · [docs/grok_build_hybrid_tooling.md](docs/grok_build_hybrid_tooling.md).

### Rule 8.1 Grok Build 하이브리드 툴링 (그록 에이전트)
* **적용:** Grok Build / Grok CLI (네이티브 이미지·영상 툴). Rule **8.0** 의 구체화.
* **도구 선택 주체** — Rule 8.0과 동일 (유저 미지정 시 에이전트 자율).
* **원칙:** 공장 CLI·approve·assemble = **SSOT**. 그록 = **가속·프리뷰·국소 수술**.
* **그록 우선 후보**: 컨셉 `image_gen` · 키프레임 국소 `image_edit` · 무대사 의도 `image_to_video` / `reference_to_video` 프리뷰.
* **공장 필수에 가까움**: 캐릭/룩/로케 pack · `shot_compose` 본선 배치 · TTS+SI2V · assemble · upscale · export.
* **금지**: 그록 영상으로 립 대체 · 프리뷰를 `clip_status=approved`/assemble · 전 샷 블러 “수정”.
* **핸드오프:** 경로로 `stories/<ep>/` 편입 · 메타에 `source=grok_*`.
  상세: [docs/grok_build_hybrid_tooling.md](docs/grok_build_hybrid_tooling.md).

### Rule 10. 외부 워크스페이스로의 작업물 내보내기(Export) 의무
* `agent_custom` 저장소는 ComfyUI 미디어 팩토리(도구 저장소)일 뿐, 사용자의 실제 영상 프로젝트 폴더가 아니다.
* 생성된 최종 에피소드 결과물(및 중간 산출물)은 반드시 사용자의 활성 워크스페이스 디렉터리(예: `D:\쇼츠 작업\...`)로 복사/내보내기 해야 한다. 결과물을 이 저장소(`agent_custom/`)에만 남겨두는 것은 **미완성(incomplete)** 작업으로 규정한다.
* 내보내기 실행 시 `scripts/export_episode_to_workspace.py` 도구를 사용하거나 환경 변수 `AGENT_WORKSPACE`를 활용한다.
  
  - 모델: `models/.../ACESTEP1.5/*` ([HF Comfy-Org pack](https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files)).  
  - SSOT: [docs/ace_step_bgm_pipeline.md](docs/ace_step_bgm_pipeline.md).

### Rule 8. Z-Image-Turbo ControlNet (Union 2.1)
* 모델 파일은 `models/model_patches/` (`controlnet` 폴더 아님).
* 표준 `ControlNetApply` 금지 → **`ZImageFunControlnet`** + **`FL_ZImageControlNetPatch`**.
* 강도 권장 `0.65 ~ 0.80`.

### Rule 9. Krea 2 Turbo
* UNet: `models/diffusion_models/Krea2Turbo/krea2_turbo_int8_convrot.safetensors`
* TE: `qwen3vl_4b_fp8_scaled.safetensors`, CLIPLoader type `"krea2"`
* VAE: `qwen_image_vae.safetensors`
* 기본: **8 steps**, **CFG 1.0**, sampler **`euler_ancestral`**, scheduler **`simple`**
