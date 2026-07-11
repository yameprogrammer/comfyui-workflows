# 📈 Moody 워크플로우 개발 및 변경 이력 (process.md)

이 문서는 에이전트들이 `agent_custom` 디렉토리 내에서 진행한 작업 내역을 누적하여 기록하는 개발 로그입니다. 새로운 작업을 시작하거나 마칠 때 반드시 이 문서를 업데이트해 주십시오.

---

## 📅 작업 이력 로그

### [2026-07-11] episode_status / pipeline / contact_sheet
* **작업 에이전트**: Grok
* **작업 목표**: 수주 에피소드의 다음 액션 파악 + 단계 오케스트레이션 + 컨택시트.
* **주요 변경**:
  1. `lib/episode_status.py` + `scripts/episode_status.py`
  2. `scripts/episode_pipeline.py` (status→contact→i2v→upscale→assemble→package)
  3. `lib/contact_sheet.py` + `scripts/episode_contact_sheet.py` (Pillow)
* **검증**: status 표, pipeline --run --dry-run, contact sheet 3 panels OK
* **다음**: 실 미니 에피소드 또는 LTX

### [2026-07-11] deliveries/ 사용자 납품 패키징
* **작업 에이전트**: Grok
* **작업 목표**: 에피소드 결과물을 사용자 전달용 폴더+zip으로 스냅샷.
* **구성**: `deliveries/<ep>__UTC/` = FINAL + STILLS + CLIPS + MANIFEST + META + README
* **CLI**: `scripts/package_delivery.py` · `lib/delivery_package.py` · [docs/delivery_handoff.md](docs/delivery_handoff.md)
* **실측**: hand_ep01 stills2+clips2+final → zip OK 후 정리
* **원칙**: stories=작업실, deliveries=납품 상자, characters/locations=공유 자산(풀 복사 안 함)

### [2026-07-11] assemble_video — FFmpeg 에피소드 조립
* **작업 에이전트**: Grok
* **작업 목표**: work/deliver 클립 concat + optional BGM → exports/final.
* **주요 변경**:
  1. `lib/ffmpeg_util.py` — find_ffmpeg, concat_videos, mux_bgm
  2. `scripts/assemble_video.py` — --episode, --stage auto|work|deliver, --bgm / --no-bgm
* **실측**: 0.5s color 클립 2개 concat → final mp4 OK (~3.6KB)
* **다음**: LTX / 실 미니 에피소드 파일럿 / VO 다중 오디오 트랙

### [2026-07-11] episode_i2v / episode_upscale 배치 CLI
* **작업 에이전트**: Grok
* **작업 목표**: approved 키프레임 → work 클립 → deliver 업스케일 배치.
* **주요 변경**:
  1. `scripts/episode_i2v.py` — default `all_approved`, format/backend from episode, frames≈duration×fps
  2. `scripts/episode_upscale.py` — deliver tier + format, seedvr2 기본
* **검증**: dry-run only (approved 2샷 선택, draft 제외, upscale job 1920×1080 resolve)
* **다음**: assemble_video / 실 Comfy 미니 에피소드

### [2026-07-11] 스토리 팩 S1–S4 — story_init / shot_compose / shot_approve
* **작업 에이전트**: Grok
* **작업 목표**: 에피소드 패키지 + look/char/loc 키프레임 조립 CLI (실 Comfy E2E는 파일럿 시).
* **주요 변경**:
  1. `stories/_template`, `shot_type_presets.json`, `schemas/shots.schema.json`
  2. `lib/story_package.py` (format work size resolve, look cores)
  3. `scripts/story_init.py`, `shot_compose.py`, `shot_approve.py`
* **검증**: story_init dry-run+create, shot_compose dry-run (mina approved ref → 960×540), location 없으면 code=11
* **다음**: episode_i2v 배치 / L3 로케 파일럿 / P-E1 미니 에피소드

### [2026-07-11] 로케이션 팩 L1–L2 구현 (template + CLI)
* **작업 에이전트**: Grok
* **작업 목표**: Location Pack 설계(L0)를 코드로 — 캐릭터 팩과 대칭 create/expand/approve.
* **주요 변경**:
  1. `locations/_template`, `location_presets.json`, `profiles.json`, schemas
  2. `lib/location_package.py`
  3. `scripts/location_create.py` / `location_expand_sheets.py` / `location_approve.py`
* **사용**:
  ```bash
  python scripts/location_create.py --id cafe_seoul_v1 --name "Seoul Cafe" --architecture "..."
  python scripts/location_approve.py --id cafe_seoul_v1 --from refs/master/<file>.png --as master_wide --set-primary
  python scripts/location_expand_sheets.py --id cafe_seoul_v1 --sheets all_mvp
  ```
* **상태**: L1–L2 ✅. L3 실 Comfy 파일럿·stories/shot_compose 다음.

### [2026-07-11] 설계 정합 패치 — deliver 티어·룩·멀티 트랙
* **작업 에이전트**: Grok
* **작업 목표**: 요구사항 리뷰에서 지적한 소수정리 반영.
* **주요 변경**:
  1. **deliver 명칭 통일**: 납품 = `deliver_1080|1440|2160` (upscale SSOT) + format aspect; `deliver_16x9_1080` 등은 deprecated alias
  2. **`looks/`** + [look_style_system.md](docs/look_style_system.md) + `cinematic_moody_v1` 기본 룩
  3. **키프레임 = format 캔버스**, char/loc ref 비율 분리 규칙 (production + storyboard)
  4. **agent_rules** 멀티 트랙 (C/L/S/M/U/K), L3만 분리; CHARACTER_L2 단일 활성 트랙 문구 완화
  5. video_backends v3, resolve/upscale alias 코드
* **상태**: 설계 정합 완료. 다음 구현: locations 템플릿 또는 stories+shot_compose.

### [2026-07-11] 로케이션·스토리보드·프로덕션 자산 설계 문서화
* **작업 에이전트**: Grok
* **작업 목표**: 실제 영상 제작에 필요한 로케이션 시트·스토리보드 결과물 형식을 웹/SNS/커뮤니티 리서치 후 문서 SSOT로 반영.
* **신규 문서**:
  1. `docs/production_asset_pipeline.md` — 캐릭터·로케·스토리 통합 지도·체크리스트·티켓
  2. `docs/location_sheet_system_design.md` — Location Pack (establishing, multi-angle, lighting, empty_stage, bible…)
  3. `docs/storyboard_pipeline_design.md` — shots.json, 보드, 키프레임, I2V 연결, CLI 계약
* **갱신**: video_pipeline_roadmap, docs/README, agent_rules Rule 6.1
* **상태**: 설계만. 코드 `locations/`·`stories/` 미구현. 다음 구현 후보 L1 템플릿 또는 S1 stories 템플릿.

### [2026-07-11] 이미지·영상 업스케일 리서치 + 멀티 백엔드 CLI
* **작업 에이전트**: Grok
* **작업 목표**: 웹/커뮤니티/SNS + 로컬 4090 인벤토리 기반 업스케일 스택 구축 (≤4K 선택).
* **리서치 요약**: 품질=SeedVR2, 속도=RTX VSR/ESRGAN, 4K는 1080→4K 2-pass 권장 (Comfy handbook·Reddit·X 합의).
* **구현**:
  1. `docs/upscale_research_and_design.md`
  2. `upscale_backends.json` + `lib/upscale_backends.py` + `lib/upscale_runners.py`
  3. `scripts/upscale_image.py` / `upscale_video.py` (`esrgan`/`rtx_vsr`/`seedvr2`/`seedvr2_max`, presets 720–2160)
* **의존성 픽스**: SeedVR2 CLI가 `ModuleNotFoundError: rotary_embedding_torch` 로 기동 실패 → portable python에 `rotary-embedding-torch` 설치 후 `--help` 정상.
* **실측**: ESRGAN `deliver_1080` 이미지 스모크 OK. SeedVR2 장시간 벤치는 후속.
* **다음**: SeedVR2/RTX 실측 벤치(1080/4K), agent UI WF 스냅샷 선택.

### [2026-07-11] 영상 format 프로필 — 비율은 프로젝트마다
* **작업 에이전트**: Grok
* **작업 목표**: 납품 비율이 16:9 고정이 아님을 코드·문서 SSOT에 반영.
* **주요 변경 사항**:
  1. `video_backends.json` v2: `formats` (`cinematic_16x9`, `shorts_9x16`, `classic_4x3`, `portrait_3x4`, `square_1x1`) + 4:3/3:4 work·deliver 프리셋
  2. `lib/video_backends.py` / `generate_i2v.py`: `--format`, `--list-formats`
  3. 문서·Rule 7: aspect는 format 선택; 16:9는 기본값일 뿐
* **사용**: `python scripts/generate_i2v.py --format shorts_9x16 ...`

### [2026-07-11] D1/D2 I2V 백엔드·프리셋 SSOT
* **작업 에이전트**: Grok
* **작업 목표**: 납품 문서의 work 16:9 기본 + 멀티 백엔드 CLI 계약 코드화.
* **주요 변경 사항**:
  1. **`video_backends.json`**: backends (`wan22` ready / `ltx23` planned) + presets (`work_16x9_*`, `work_1x1_smoke`, deliver_*)
  2. **`lib/video_backends.py`**: `resolve_i2v_job`, `BackendNotReady`
  3. **`scripts/generate_i2v.py`**: `--backend`, `--preset`, `--list-backends`, `--list-presets`; 기본 `wan22` + `work_16x9_540` (960×540)
  4. 문서 티켓 D1/D2 ✅
* **상태**: Wan 경로 프리셋 적용 가능. LTX는 명시적 에러. 다음: D4 업스케일 또는 D3 LTX WF.

### [2026-07-11] 프로젝트 레이아웃 전면 정리 (에이전트 도구 구조)
* **작업 에이전트**: Grok
* **작업 목표**: 루트 혼재 구조를 에이전트용 레이아웃으로 재배치. 휴먼 편의보다 에이전트 탐색·SSOT 우선.
* **주요 변경 사항**:
  1. **`scripts/`**: `generate_*`, `character_*`, `shot_*` 이동 + `_bootstrap.py` (repo root/scripts on path)
  2. **`docs/`**: 설계·스펙·로드맵·moody guide 이동
  3. **루트 워크플로우 JSON 삭제** — SSOT는 `workflows/agent/` 만
  4. 루트는 `README.md` / `agent_rules.md` / `process.md` 입구만 유지
  5. README·agent_rules Rule 2.2·workflows 규약·catalog 경로 갱신
* **실행 예**: `python scripts/generate_moody.py ...` (모든 CLI `--help` 스모크 OK)
* **다음**: 기능 작업 재개 (D1 프리셋/`--backend`, 업스케일, LTX 등). 문서 본문 중 구 경로 예시는 점진 정리.

### [2026-07-11] 에이전트 전용 워크플로우 디렉터리 분리
* **작업 에이전트**: Grok
* **작업 목표**: 휴먼 UI 워크플로우와 에이전트(스크립트)용 워크플로우를 구조적으로 분리.
* **주요 변경 사항**:
  1. **`workflows/agent/`**: 프로덕션 JSON 복사 + `catalog.json` (별칭 SSOT)
  2. **`workflows/human/`**: UI 실험 전용 (스크립트 미사용)
  3. **`lib/workflow_paths.py`**: agent 우선 → 루트 레거시 폴백 경로 해석
  4. **`generate_moody*.py` / `generate_i2v.py` / `generate_krea.py`**: agent 경로 사용, `--workflow` 옵션
  5. **규약 문서**: `workflows/README.md`, agent_rules Rule 2.1, README 구조 갱신
* **상태**: 루트 `*.json` 은 폴백으로 유지(신규 편집은 agent 만). 이후 human 실험 → agent 프로모트 플로우 사용.
* **다음**: 필요 시 루트 JSON deprecation 안내 후 제거; API-native 최소 그래프 정리(선택).

### [2026-07-11] 영상 납품 스펙·멀티 I2V 백엔드 문서화
* **작업 에이전트**: Grok
* **작업 목표**: 저해상 생성→1080p 업스케일 전략과 Wan2.2/LTX2.3 상황별 백엔드 구조를 문서에 고정.
* **주요 변경 사항**:
  1. **`video_delivery_and_backends.md` 신규**: 2단 해상도(work/deliver), 16:9·최소 1080p, work 프리셋 표, 업스케일 필수 마감 층, `wan22`/`ltx23` 멀티 백엔드 API·휴리스틱·티켓 D0~D6
  2. **`video_pipeline_roadmap.md`**: 해상도 전략 확정, I2V 백엔드 표, 구축 순서·상태 갱신
  3. **`agent_rules.md` Rule 7**: 납품 1080p / work 생성 / 멀티 백엔드 규약
  4. README 링크
* **상태**: 문서 확정. 코드: Wan I2V MVP만 존재. 다음 구현 후보 D1 프리셋·`--backend` 또는 D4 업스케일 / D3 LTX.

### [2026-07-11] P8 I2V (Wan2.2 A14B GGUF) 에이전트 CLI 추가
* **작업 에이전트**: Grok
* **작업 목표**: 키프레임 이미지 → 짧은 영상 클립 자동화 (영상 로드맵 P0).
* **주요 변경 사항**:
  1. **`I2V-wan22-a14b.json`**: WanVideoWrapper 2.2 I2V A14B 예제를 로컬 GGUF High/Low + lightx2v 4step LoRA + `wan_2.1_vae` + umt5 경로로 패치; torch.compile 비활성
  2. **`lib/comfy_ui_convert.py`**: UI→API 변환 (object_info 위젯 순서, 링크 우선)
  3. **`generate_i2v.py`**: image/prompt/frames/size/seed CLI, 출력 mp4 복사
  4. **실측**: mina 카페 키프레임 → `F:\generated_videos\mina_i2v_test.mp4` 성공 (~1분, 640², 33f, 6step)
* **상태**: I2V MVP 사용 가능. 다음: 조립(FFmpeg)·포즈맵·긴 클립 튜닝.

### [2026-07-11] P7 shot_with_character 키프레임 CLI 추가
* **작업 에이전트**: Grok
* **작업 목표**: video_ref 캐릭터 패키지로 스토리 키프레임(I2I) 생성.
* **주요 변경 사항**:
  1. **`shot_with_character.py`**: `--shot`, `--ref`/`--expression`, `--template`, denoise/cfg/seed, draft 경고
  2. positive_core 주입 + approved ref 기본 선택
  3. 출력 `refs/shots/` + meta; 템플릿 `shot_templates.json`
  4. 실측: mina 카페 medium_dialogue 샷 생성 성공 (seed 80001)
* **상태**: P7 기본 경로 사용 가능. 다음 후보 I2V 연결 또는 포즈맵 개선.
* **참고**: 작업 트리 커밋 전 상태는 이미 clean이었음 → 본 커밋에 P7 포함.

### [2026-07-11] 턴어라운드 품질 경로: full-body master + ControlNet
* **작업 에이전트**: Grok
* **선행 커밋**: `0ae21a4` (CN 인프라)
* **작업 목표**: 클로즈업 VAEEncode 고정을 깨고 전신 multi-view 후보 품질 개선.
* **주요 변경 사항**:
  1. **`lib/fullbody_source.py`**: 전신 master T2I 자동 생성(의상 강제·nude 네거티브), `ensure_fullbody_source`
  2. **expand**: 턴어라운드 시 full-body 소스 우선 + `--ensure-fullbody` / `--engine controlnet_empty`
  3. **controlnet**: `--empty-latent` (EmptySD3 rewire, denoise 1.0)
  4. **실측**: clothed full-body master `s60011` 성공 → `approved/master_full.png`
  5. full-body 소스 CN 턴 4장: **전신 구도 유지 성공**; front 양호, side 약한 회전, back 아직 정면 고정 + 스틱 라인 아티팩트
* **결론**: “클로즈업 소스”가 주범이었음. full-body master가 필수. 측면/후면 정밀 각도는 포즈 맵 품질 추가 개선 필요.
* **다음**: OpenPose/실사 포즈 레퍼 또는 empty-latent+LoRA 정밀 각도.

### [2026-07-11] P4 ControlNet turnaround 연동 (인프라)
* **작업 에이전트**: Grok
* **선행 커밋**: `1045511` (P2.5 프로필 롤백 포인트)
* **작업 목표**: 캐릭터 expand가 턴어라운드 시 I2I-ControlNet-moody + 포즈 템플릿을 사용하도록 연결.
* **주요 변경 사항**:
  1. **`generate_moody_controlnet.py`**: lib 공통화, seed/meta/core-prefix, dict 반환, `ZImageFunControlnet` strength 수정
  2. **`lib/pose_templates.py`**: front/qf/side/back 스틱 실루엣 자동 생성
  3. **`lib/edge_preprocess.py`**: Canny(OpenCV) 또는 PIL FIND_EDGES 폴백
  4. **`character_expand_sheets.py`**: `--engine auto|i2i|controlnet`, turnaround preset → controlnet
  5. **`sheet_presets.json`**: turnaround에 engine/pose_template/control_strength
* **실측 (mina, seed 30001–30004)**: 4장 생성 성공. 그러나 **전신/측면 전환은 실패** — 얼굴 클로즈업 유지 + 스틱 라인 아티팩트. 원인: 워크플로가 얼굴 이미지를 VAEEncode한 I2I 베이스라 구도 attractor가 강함. denoise 0.95 재시도에도 동일.
* **다음 품질 작업**: Empty latent + ControlNet 포즈 전용 WF, 또는 진짜 full-body master를 소스로 쓰는 경로; OpenPose 계열 템플릿 강화.
* **상태**: 파이프라인 연동 완료 / multi-view 품질 미해결.

### [2026-07-11] P2.5 용도 프로필 코드 연동 (video_ref / artbook)
* **작업 에이전트**: Grok
* **작업 목표**: 스펙 P2.5에 따라 `--profile` 로 영상 레퍼/아트북 설정을 선택 가능하게 구현.
* **판단**: 파일럿 후 우선순위 2위였던 **P2.5를 먼저** 진행 (video_ref MVP 정식화 → 이후 ControlNet 품질).
* **주요 변경 사항**:
  1. **`lib/profiles.py`**: profiles.json 로드, size_for_sheet, profile_all_mvp_preset_ids, export dirs, bible.exports
  2. **CLI**: `character_create/expand/approve` 에 `--profile` (기본 `video_ref`)
  3. **create**: 프로필 size → T2I `width/height`; artbook은 full-body master 기본 포함
  4. **expand**: `all_mvp` 가 프로필별 (video_ref=expression 6종만; artbook=turn+expr+costume…)
  5. **missing_mvp**: 프로필 `mvp_aliases` 기준 (`video_ref`는 turn/costume 불필요)
  6. **mina_park_v1** 를 `active_profile=video_ref` 로 재계산 → missing_mvp=[] 유지
  7. approve SameFileError 방어
* **한계**: I2I는 입력 이미지 해상도를 따르므로 expand의 size_hint는 메타/로그 수준 (전신 리사이즈는 ControlNet/후속).
* **다음**: P4 ControlNet turnaround 연동 (선택 시트 품질).

### [2026-07-11] 캐릭터 시트 용도 프로필 스펙 문서화 (video_ref / artbook)
* **작업 에이전트**: Grok
* **작업 목표**: 시트 도구를 사용 목적(영상 레퍼 vs 아트북)에 따라 설정할 수 있도록 스펙·작업 계획에 반영.
* **주요 변경 사항**:
  1. **`characters/profiles.json` 신규** — `video_ref`(기본, ~1024, MVP=master+expression) / `artbook`(~1536+, 풀시트, upscale/grid 옵션).
  2. **`character_impl_spec.md` §1.5** — 프로필 원칙, CLI `--profile`, bible.exports, 단계적 구현 P2.5a~e.
  3. **`character_sheet_system_design.md`** — §0.3 용도 프로필, Phase **P2.5**, 우선순위·다음 액션 갱신.
  4. README / characters/README / agent_rules 교차 언급.
* **상태**: 스펙·SSOT 완료. **코드 `--profile` 연동은 미착수 (Ticket P2.5)**.
* **다음**: P2.5a CLI 로드 또는 P4 ControlNet (품질) 중 선택 착수.

### [2026-07-11] 파일럿 mina_park_v1 E2E 실행 (Comfy 실생성)
* **작업 에이전트**: Grok
* **작업 목표**: L2 Soft Factory 파이프라인을 ComfyUI 실서버에서 end-to-end 검증.
* **실행**:
  1. `character_create.py --id mina_park_v1 --from-brief-samples --model pro --candidates 4 --seed-base 10001` → 마스터 4장 성공
  2. master 승격: `s10002__c02` → `approved/master_front.png`
  3. `character_expand_sheets.py --sheets all_mvp --candidates 1 --seed-base 20001` → 12/12 성공 (~5분)
  4. MVP alias 전부 approve → `status=approved`, `level=L2`, `missing_mvp=[]`
* **품질 발견**:
  * Expression 변화는 soft I2I로 양호 (identity 유지 + 표정 반영).
  * Turnaround side/back/full-body 는 master 상반신 구도에 묶여 각도·전신 전환 실패에 가까움 (denoise 0.82–0.85 불충분).
  * Costume도 구도 유지로 전신 의상 시트 미달. mole 좌우 드리프트 관측.
* **결론**: 도구 파이프라인 검증 완료. 프로급 multi-view는 **ControlNet turnaround + full-body master** 후속 필수.
* **상세**: `characters/mina_park_v1/PILOT_NOTES.md`
* **다음 추천**: ControlNet expand 연동, 또는 full-body master 재생성 후 costume/turn 재확장.

### [2026-07-11] Krea 2 Turbo 모델 T2I 워크플로우 신규 추가
* **작업 에이전트**: Antigravity
* **작업 목표**: 초고속 12B DiT 오픈소스 모델인 Krea 2 Turbo T2I 파이프라인 구성 및 이미지 검증.
* **주요 변경 사항**:
  1. **T2I 워크플로우 저장**: [T2I-krea.json](file:///F:/ComfyUI_workflows/agent_custom/T2I-krea.json) 구축 완료.
  2. **실행 스크립트 추가**: [generate_krea.py](file:///F:/ComfyUI_workflows/agent_custom/generate_krea.py) 추가 (8-steps, CFG 1.0, euler_ancestral, simple 스케줄러 기본값 탑재).
  3. **성능 검증 완료**: 사막 위의 미래형 유리 구 이미지([output_krea.png](file:///F:/generated_images/output_krea.png))를 8단계 만에 극상의 디테일로 생성 검증 성공.
* **상태**: T2I 연동 성공 및 안정화 완료.

### [2026-07-11] Character L2 Soft Factory 구현 (P1+P2)
* **작업 에이전트**: Grok
* **작업 목표**: 캐릭터 시트 구현 스펙에 따라 P1(기존 CLI 재현성) + P2(create/expand/approve) 코드 착수·완료.
* **주요 변경 사항**:
  1. **`lib/` 공용 모듈**: `comfy_client.py` (UI→API, queue/wait/download, meta), `prompt_assembly.py`, `character_package.py`
  2. **P1** `generate_moody.py` / `generate_moody_i2i.py`: `--seed`, `--prompt-file`, `--negative(-file)`, `--meta-out`, width/height/steps/cfg(T2I), `--core-prefix/suffix-file`(I2I), dict 반환, timeout
  3. **P2 CLI**: `character_create.py`, `character_expand_sheets.py`, `character_approve.py` (`sheet_presets.json` SSOT)
  4. 오프라인 패키지/approve·dry-run 검증 통과. **실 Comfy 생성 E2E는 서버 가동 후 파일럿 `mina_park_v1` 권장**
* **상태**: L2 도구 코드 사용 가능. 다음: Comfy 켜고 `character_create.py --from-brief-samples` 파일럿 실행 → approve → expand.
* **활성 트랙**: `CHARACTER_L2_SOFT_FACTORY`

### [2026-07-11] Z-Image-Turbo 공식 ControlNet (Union 2.1) 연동 워크플로우 추가
* **작업 에이전트**: Antigravity
* **작업 목표**: 포즈와 구조적 통제력을 극대화하여 캐릭터 일관성을 유지할 수 있도록 공식 Union 2.1 컨트롤넷 연동 파이프라인 구성.
* **주요 변경 사항**:
  1. **전용 노드 발굴 및 연동**: DiT 구조에 최적화된 모델 직접 패치 방식인 `ZImageFunControlnet` 및 로더 노드 `FL_ZImageControlNetPatch`를 적용하여 400 에러 해결.
  2. **새로운 워크플로우 저장**: [I2I-ControlNet-moody.json](file:///F:/ComfyUI_workflows/agent_custom/I2I-ControlNet-moody.json) 구축.
  3. **실행 스크립트 추가**: [generate_moody_controlnet.py](file:///F:/ComfyUI_workflows/agent_custom/generate_moody_controlnet.py) 추가하여 CLI 환경에서 캐릭터 이미지와 포즈 이미지를 손쉽게 제어 가능하도록 구성.
  4. **모델 전용 경로 규명**: Z-Image-Turbo 컨트롤넷 파일은 `models/model_patches/` 폴더에 위치해야 로더가 정상 스캔함을 밝혀내고 배치 완료.
* **상태**: 로더-패치 텐서 융합 및 이미지 생성 검증 완료.

### [2026-07-11] 캐릭터 시트 구현 착수 스펙·P0 산출물 보강
* **작업 에이전트**: Grok
* **작업 목표**: 기획 문서의 구멍을 메워 P1~P2 코딩에 바로 들어갈 수 있는 수준으로 문서·템플릿·프리셋을 완성.
* **주요 변경 사항**:
  1. **`character_impl_spec.md` 신규**: 활성 트랙, 명명 규칙, 기본값, P1 CLI 패치 스펙, P2 CLI 계약, 프롬프트 조립, 에러 코드, 티켓 순서, 테스트 계획.
  2. **`characters/` 트리**: `_template/`, `schemas/bible|manifest.schema.json`, `sheet_presets.json`, `pilots/mina_park_v1` + 샘플 프롬프트.
  3. **설계 문서 P0 완료 처리**, `agent_rules.md` Rule 6(캐릭터/스펙 준수) 추가, README 링크 갱신.
* **상태**: **P0 완료. 코드 구현은 미착수.** 다음 에이전트 추천: `character_impl_spec.md` Ticket **P1-A** (`generate_moody.py` seed/meta/prompt-file).
* **활성 트랙**: `CHARACTER_L2_SOFT_FACTORY` (L3/I2V 본구현 비혼합).

### [2026-07-11] 프로급 캐릭터 시트 시스템 기획·설계 문서화
* **작업 에이전트**: Grok
* **작업 목표**: AI 에이전트가 이용 가능한 프로급 캐릭터 시트 생성 도구에 대해, 업계 포맷 리서치 + 영상 연계 일관성 전략 + 작업 계획을 문서화.
* **주요 변경 사항**:
  1. **`character_sheet_system_design.md` 신규 작성**:
     * 프로 model sheet 유형 (turnaround, expression, pose, color, props, construction, bible 등) 리서치 정리
     * AI용 `characters/<id>/` 패키지 구조 및 `bible.json` 스키마 초안
     * 아이덴티티 계층 (I2I → IP-Adapter → LoRA → ControlNet hybrid) 및 Z-Image/Moody 매핑
     * 키프레임 고정 후 I2V로 이어지는 E2E 일관성 규칙·실패 모드
     * 작업 Phase P0~P9 및 우선순위 (L2 Soft Factory 우선, L3 LoRA)
  2. **`video_pipeline_roadmap.md` / `README.md`**에 캐릭터 설계 문서 교차 링크 추가.
* **상태**: 이후 구현 스펙 보강으로 이어짐 (위 이력 참고).

### [2026-07-11] 영상 제작 파이프라인 로드맵 문서화
* **작업 에이전트**: Grok
* **작업 목표**: AI 에이전트가 멋진 영상물을 만들기 위해 필요한 워크플로우 구성을 1차 목표 기준으로 문서화.
* **주요 변경 사항**:
  1. **`video_pipeline_roadmap.md` 신규 작성**: T2I/I2I 기반 위에서 영상 파이프라인에 필요한 워크플로우 레이어·우선순위·MVP 세트·구축 순서를 정리.
  2. **1차 MVP 정의**: T2I/I2I(기존) + I2V + Character ref + Upscale/Interpolate + FFmpeg assembler.
  3. **구축 단계 정의**: P0(I2V) → P1(체인) → P2(일관성) → P3(마감) → P4(조립) → P5(T2V/V2V 등 확장).
  4. **README.md** 파일 구조에 로드맵 문서 링크 추가.
* **상태**: 기획/로드맵 문서 저장 완료. 구현은 미착수. 다음 액션은 타깃 포맷(쇼츠 vs 시네마틱) 확정 후 I2V 설계.

### [2026-07-11] Moody 워크플로우 고도화 및 I2I 디버깅 완수
* **작업 에이전트**: Antigravity
* **작업 목표**: Moody T2I 모델 다양화 연동 및 I2I 이미지 편집 파이프라인의 오작동 해결 및 자동화 구축.
* **주요 변경 사항**:
  1. **T2I 워크플로우 및 자동화 구축**: Moody 모델 3종(`Real`, `Pro`, `Wild`)에 대응하는 `T2I-moody.json` 및 CLI 제어 스크립트(`generate_moody.py`) 완료.
  2. **I2I 노드 우회 및 다이렉트 와이어링**: `Lora Loader` 사용 안 할 시 데이터 흐름이 단절되던 현상을 우회하여 CLIP과 UNet을 KSampler에 직접 결합.
  3. **CLIPTextEncode 표준 노드 장착**: Conditioning 데이터를 누락시키던 `Prompt (LoraManager)` 커스텀 노드를 표준 노드로 교체하여 프롬프트 가이드 복원.
  4. **Flow Matching 디노이즈 바인딩**: `ModelSamplingAuraFlow` 시프터와 `res_multistep` 샘플러가 `denoise < 1.0` 시 노이즈 계산을 생략하던 버그를 규명하여 `euler`/`normal` 샘플러 강제 적용 및 시프터 우회 설정.
  5. **CLI 매개변수 노출**: `generate_moody_i2i.py`에 `--cfg` 및 `--denoise` 옵션을 설계하여 미디엄 제어력 확보.
  6. **디노이즈 스윕(Sweep) 분석**: 이 모델의 강한 Attractor 결합력을 분석하여 동작 임계치를 구간별로 정밀 규명함:
     * 사물 교체: `0.70 ~ 0.73`
     * 야간/조명 변환: `0.75 ~ 0.78`
     * 액션/포즈/배경 변환: `0.82 ~ 0.86`
* **상태**: 1번(부분 편집) 및 2번(인물 일관성 기반 액션 변환) 기능 성공적 완수. 안정성 확보 완료.

---
*(새로운 변경 사항은 상단에 누적하여 추가해 주십시오.)*
