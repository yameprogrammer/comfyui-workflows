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
* **근시일 영상 툴 TODO**: [docs/agent_video_tooling_todo.md](docs/agent_video_tooling_todo.md) (길이 계약 · 감정 연동 모션 · auto-export 등)
* **docs 인덱스**: [docs/README.md](docs/README.md) · 만료·세션·디버그: [docs/archive/](docs/archive/)
* **기획 자율 (키워드/음악만)**: [docs/creative_brief_autonomy_design.md](docs/creative_brief_autonomy_design.md) — 기능 필수 아님, 에이전트 SOP·가드레일
* **프로덕션 자산 통합**: [docs/production_asset_pipeline.md](docs/production_asset_pipeline.md)
* 로케이션 설계: [docs/location_sheet_system_design.md](docs/location_sheet_system_design.md)
* 룩/스타일: [docs/look_style_system.md](docs/look_style_system.md) · `looks/cinematic_moody_v1`
* 스토리보드 설계: [docs/storyboard_pipeline_design.md](docs/storyboard_pipeline_design.md)
* **소비자 에이전트 경로 계약**: [docs/agent_consumer_workspace_contract.md](docs/agent_consumer_workspace_contract.md) · 루트 [AGENTS.md](AGENTS.md)

---

## 📌 소비자 에이전트 (도구만 호출할 때)

이 레포를 **공장**으로 쓰고, **작업대는 호출 측 프로젝트 디렉터리**다.

1. cwd = `agent_custom` 루트에서 `python scripts/...` 실행  
2. 산출물 기본 위치 = `stories/<episode_id>/` (키프레임·clips·audio·exports)  
3. **의무**: `export_episode_to_workspace.py --dest <내_작업대>` 또는 `-o`로 작업대 직접 지정  
4. `AGENT_RESULT` / 메타의 **절대 경로를 읽고 복사**하지 않으면 미완료  
5. 공장(`stories/`)에만 두고 “끝” 보고 금지  

```bash
python scripts/export_episode_to_workspace.py -e EP --dest "D:/my_project/episodes/EP"
# 또는 set AGENT_WORKSPACE=D:/my_project
```

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
  - OpenPose 턴 / **ipadapter**: 레거시·실험, 공정 SOP 기본 아님.
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

### Rule 7. 영상 해상도·백엔드 규약
* **format** = 종횡비 (`cinematic_16x9` …). 16:9 고정 아님. SSOT: `video_backends.json`.
* **work 프리셋** = format별 픽셀 (`work_16x9_540` …). I2V 생성용.
* **deliver 티어** = 짧은 변만 (`deliver_1080` / `deliver_1440` / `deliver_2160`). SSOT: **`upscale_backends.json`**. aspect는 format이 담당.
* 구 ID `deliver_16x9_1080` 등은 **deprecated** (`deliver_aliases` → `deliver_1080`).
* I2V: work 해상도. 납품: `scripts/upscale_* --preset deliver_1080 --format …`.
* 업스케일 **기본 = rtx_vsr**. seedvr2는 히어로 opt-in (실무 배치 비권장). [docs/upscale_research_and_design.md](docs/upscale_research_and_design.md).
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

### Rule 7.2 컷별 검수 게이트 (합본 전 · hard)
* **문제**: 합본(final)만 보고 중간 컷을 고치면 재생성·체인 재작업 비용이 폭증한다.  
  last-frame SI2V 체인은 붕괴 컷의 끝 프레임이 **다음 seed**가 되어 피해가 전파된다.
* **의무 순서**  
  1. `keyframe_status=approved` → 모션 생성 허용  
  2. 샷별 work clip 생성 (`episode_i2v` / `episode_s2v` / `chain_si2v_last_frame`)  
  3. **컷 검수** → `clip_status=approved` (`shot_approve -e EP -s S0x --clip approved`)  
  4. (체인) **이전 컷 `clip_status=approved` 전** 다음 샷 last-frame 생성 금지  
  5. **전 조립 대상 샷 `clip_status=approved`** 후에만 `assemble_video`  
  6. 합본 검수 = 컷 간 이음·길이·BGM/믹스만 (컷 품질 재검수가 아님)
* **`clip_status` 계약**  
  - 값: `pending` | `in_review` | `approved` | `rejected`  
  - 워크 클립이 있는데 필드 없음 → `pending`  
  - 육안 체크: 얼굴 유지, 모션/소품 이상, (SI2V) 립·대사 타이밍, (체인) 끝 프레임이 다음 seed로 쓸 만한지  
  - **자동 점수 없음** — 사람 또는 비전 에이전트가 클립을 보고 올린다  
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
  # 컷 생성 후 (SI2V/I2V 공통)
  python scripts/shot_approve.py -e EP -s S02 --clip approved
  python scripts/episode_status.py -e EP   # CLIP 열 / need_clip_approve
  python scripts/assemble_video.py -e EP --stage work   # 미승인이면 code=22
  ```

### Rule 8. Grok Build 하이브리드 툴링 (그록 에이전트 전용)
* **적용:** Grok Build / Grok CLI 처럼 **네이티브 이미지·영상 생성 툴**이 있는 에이전트.  
  Claude·Codex 등 공장 CLI만 쓰는 에이전트는 이 Rule을 무시해도 된다.
* **도구 선택 주체 (기본 = 에이전트 자율)**  
  * 사용자가 **특정 도구를 쓰라고 명시하기 전**에는, 에이전트가 목표·품질·속도·게이트를 보고  
    **공장 CLI / 그록 네이티브 중 적절한 것을 스스로 고른다.**  
  * “어떤 툴로 할까요?”를 매번 묻지 않는다. 결과와 트레이드오프만 필요할 때 짧게 보고.  
  * 사용자가 “Comfy로만 / 그록 image_edit로 / IT로 다시” 등 **도구를 지정하면 그 지시를 우선**한다.
* **원칙:** 공장(`agent_custom` CLI·approve 게이트·assemble)이 **SSOT·본선**.  
  그록 툴은 **가속·프리뷰·국소 수술**이다. 게이트를 우회하지 않는다.
* **그록 쪽을 에이전트가 고르기 좋은 경우**
  * 컨셉/무드보드 → `image_gen`
  * 키프레임 **국소 수정**(물방울·소품 등, 구도·정체성 OK) → `image_edit` 후 `keyframes/S0x.png` 교체 → **draft 재승인**
  * 무대사 모션 **의도 프리뷰** → `image_to_video` / `reference_to_video` → 확정 후 `episode_i2v` 본선
* **공장 쪽을 에이전트가 고르기 좋은 경우 (그록으로 대체 금지에 가까움)**
  * 캐릭/룩/로케 pack, `shot_compose` 본선 키프레임 배치  
  * TTS + **SI2V 립** (`episode_s2v` / InfiniteTalk)  
  * BGM, assemble, 1080 upscale, `export_episode_to_workspace`
* **금지**
  * 그록 영상으로 립 컷 대체  
  * 그록 프리뷰를 `clip_status=approved` 또는 assemble 입력  
  * 전 샷 픽셀 블러 “물방울 제거” 후 본선 확정 (실사 붕괴)
* **핸드오프:** 그록 산출물은 디스크 경로로 공장에 넣고, 메타/process에 툴 출처 한 줄.  
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
