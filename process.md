## 2026-07-15 — V2V intent pipeline (camera/motion/style) P0
- docs/v2v_intent_pipeline_design.md SSOT (separate from FLF + SI2V)
- lib/v2v_contract.py · generate_v2v.py · episode_v2v.py
- LTX AIO true video inject (node 787 VHS_LoadVideo) + generate_s2v --video
- backends: ltx23_aio_v2v_true(_audio); motion_driver enum v2v_*
- tooling_todo P3-4; schema video_refs
## 2026-07-15 — ComfyUI auto-ensure (autostart)
- `lib/comfy_client.ensure_comfy_running`: probe → lock → bat spawn → ready wait
- Default bat: `F:\ComfyUI_windows_portable\run_nvidia_gpu_fast_fp16_accumulation.bat`
- Duplicate guards: API probe + `.agent_cache/comfy_launch.lock` + launch_state cooldown
- Wired into `queue_prompt` / `get_queue` / `get_system_stats` / `free_comfy_memory` / `fetch_object_info`
- CLI: `python scripts/comfy_ensure.py` (`--status`, `--json`, env opt-out `AGENT_COMFY_AUTOSTART=0`)
- Docs: agent_consumer_workspace_contract · scripts/README · smoke checklist
## 2026-07-14 — creative brief autonomy (doc rail)
- docs/creative_brief_autonomy_design.md: keyword/music-only planning SOP, no mandatory new CLI
- tooling_todo P3-2 checked for doc; README + agent_rules + AGENTS links
## 2026-07-14 — dance_challenge pipeline backlog
- docs/dance_challenge_pipeline_design.md (design stub)
- agent_video_tooling_todo P3-1 + Sprint E; docs/README link
- Separate track from cafe talking shorts
## 2026-07-14 — docs cleanup
- docs/README.md 재작성: 활성 / 참고 / archive
- archive/: sessions, ltx23_debug, research (세션노트·LTX 일회성 분석·원문 리서치)
- 깨진 링크 수정 (storyboard, LTX, openmontage)
- video_pipeline_roadmap / reliability → 신규 작업은 agent_video_tooling_todo 로 안내
## 2026-07-14 — agent_video_tooling_todo.md
- P0: SI2V length contract, emotion-linked performance motion (not always calm), auto-export
- P1/P2 backlog + sprint order; linked from agent_rules + AGENTS
## 2026-07-14 — Rule 8: agent-autonomous tool pick
- Until user names a tool, Grok Build agent chooses factory vs native image/video
- User tool override wins; no per-step tool menus
## 2026-07-14 — Grok Build hybrid tooling rule
- docs/grok_build_hybrid_tooling.md + agent_rules Rule 8 + AGENTS.md pointer
- Native image_gen/edit/video for preview & surgical stills; factory SSOT for lips/assemble/export
- Does not change non-Grok agents
# 📈 Moody 워크플로우 개발 및 변경 이력 (process.md)

이 문서는 에이전트들이 `agent_custom` 디렉토리 내에서 진행한 작업 내역을 누적하여 기록하는 개발 로그입니다. 새로운 작업을 시작하거나 마칠 때 반드시 이 문서를 업데이트해 주십시오.

[2026-07-13] - Grok — **cafe_gomin_ep01 스토리보드 재작성 (신 시놉)**
- S01–S09 · sho_heroine_v3 · one_take continuity · BGM under · 24fps
- 대사 6 + sip I2V + open/close I2V; SI2V default infinitetalk
- `STORYBOARD_DESIGN.md` · `beats.md` · `shots.json` (구 대본 교체)
- 채널: `episodes/cafe_gomin_ep01/`
- Next: shot_compose 키프레임

[2026-07-13] - Grok — **v3 의상 수정: 짧은 치마 + alt1 수정 + 원테이크 요구**
- wardrobe: SHORT mini skirt + strappy sandals (여름)
- costume_alt1 I2I 미니어처 버그 → crop 전신 인셋으로 교체 승인
- 시놉/캐논: **원 테이크 감** 명시
- 주의: `--sheets costume` 은 그룹 전체; alt1만은 `--only costume.alt1`

[2026-07-13] - Grok — **sho_heroine_v3 full_sheet 완료**
- `character_full_sheet --run --model real --turn-engine qwen` ~19분, exit 0
- missing_mvp=[] · approved 33 · review_FULL_PACKAGE + grids
- 채널: `characters/sho_heroine_v3/exports/full_sheet/`
- Next: 신 시놉 스토리보드 / shots.json

[2026-07-13] - Grok — **여주 v3 promote + 여름 의상 lock + BGM 요구**
- pick → **`sho_heroine_v3`** · summer wardrobe + iced americano props

[2026-07-13] - Grok — **여주 재캐스팅 cast v2 (시놉 개정)**
- cast_id: `short_cafe_gomin_cast_v2` · 9 OK
- 채널: `casts/short_cafe_gomin_cast_v2/`

[2026-07-13] - Grok — **IT 립 승자 → hero 기본 반영**
- 승자: `S02_it_lip_24fps_s12_as1.5_notea` (차분·입 맞춤)
- 기본: **24fps / 12step / audio_scale 1.5 / lightx2v ON / TeaCache OFF**
- 갱신: `episode_s2v`, `episode_pipeline` hero, `generate_s2v` defaults
- 벤치: `_bench_it_lip/` · `exports/bench_it_lip/`

[2026-07-13] - Grok — **Wan2.2 BlockSwap = 상황별 조절 (기록)**
- 개념: 블록 GPU↔offload (**VRAM ↔ 속도**). 품질 스킵 아님.
- 스모크: swap20 32.2s · swap10 24.2s · swap0 20.3s (작 스펙 OOM 없음)
- **정책**: 만능 고정 아님 — 일상 출발 deliver=10, 큰 작업/OOM→20+, 여유 시 0 시도
- SSOT: `docs/wan22_i2v_speed_research.md` §4.1 · CLI `--block-swap`
- 클립: `_bench_wan22_speed/S01_p1b_swap{0,10,20}_f17.mp4`

[2026-07-13] - Grok — **Wan2.2 Tea/MagCache 품질 탈락 → 기본 off**
- 사용자 육안: `S01_p1_teacache_*` / `S01_p1_magcache_*` **자글자글** 사용 불가
- 조치: 전 프로필 `cache=none` 기본; `--cache` 는 실험 opt-in 만
- 본선 가속 유지분: **sageattn + lightx2v steps + preview 저해상/저step** (캐시 제외)

[2026-07-13] - Grok — **Wan2.2 I2V P1: TeaCache/MagCache + 프로필**
- TeaCache/MagCache → dual sampler `cache_args`; BlockSwap 프로필화
- 벤치 속도: none 32.3s · tea 26.2s · mag 24.4s — **이후 품질 탈락으로 기본 off**
- VHS unique prefix (Comfy full-cache 시 구 파일 복사 버그 수정)
- **Next**: 본선 속도는 sage+steps/해상도; cache 재시도 시 thresh 대폭 하향 A/B

[2026-07-13] - Grok — **Wan2.2 I2V P0 구현·스모크**
- **W0**: steps + dual boundary (`steps//2`) INTConstant 배선 수정
- **W1**: attention 기본 `sageattn` (`--attention` / `AGENT_WAN_ATTENTION=sdpa`)
- **W2**: `elapsed_sec` meta + `--dry-run`
- **스모크** (368×640, 17f, 6step, seed42): sage warm **38.3s** / sdpa **40.3s** / sage cold 54.9s
- 벤치: `stories/cafe_gomin_ep01/clips/work/_bench_wan22_speed/`

[2026-07-13] - Grok — **Wan2.2 I2V 속도 리서치**
- **문서**: `docs/wan22_i2v_speed_research.md`
- **현황 (리서치 시점)**: lightx2v 있음; sage/TeaCache 미적용 → P0에서 sage 적용
- IT 가속과 별 경로 (2.1 IT ≠ 2.2 I2V 그래프)

[2026-07-13] - Grok — **퀄리티: S02 벤치 결과 → +1.5 유지**
- 비교: baseline 6s (audio+1.5) vs LTX tight 4s vs IT mild
- **사용자 판정**: baseline이 **입모양·사물 안정** 우세 → 채택
- 가설 “꼬리 짧을수록 좋음”은 S02에서 기각; 장클립 드리프트는 별 이슈
- 도구 기본 Clip Length: **`audio+1.5` 유지** (tight 실험: `AGENT_LTX_CLIP_TIGHT=1`)
- 본선 `S02_s2v.mp4` = baseline 동일; 다음 `shot_approve --clip`

[2026-07-13] - Grok — **퀄리티: LTX Clip Length A/B (중간 실험)**
- tight `ceil(audio)` 구현 후 S02 벤치 → **사용자 기각**, +1.5 복귀 (위 항목)

[2026-07-13] - Grok — **컷별 검수 규칙 + assemble 하드 게이트**
- **배경**: 합본 후 중간 컷 교체 비용↑ · last-frame 체인 붕괴 전파
- **규칙**: `agent_rules.md` Rule 7.2 — Clip-first (합본 전 `clip_status=approved` 필수)
- **코드**:
  - `shot_approve.py --clip` · `lib/episode_status` clip 게이트
  - `assemble_video` 미승인 시 exit 22 (`--force-clip-gate` 우회만)
  - `chain_si2v_last_frame` 이전 컷 승인 전 다음 샷 금지
  - `episode_qa --require-clip`
- **Next 연결**: LTX 얼굴 살리기 실험도 **컷 단위 승인 후** 합본

[2026-07-13] - Grok — **EOD / 어디까지 됐나**
- **상태 SSOT**: `docs/session_status_2026-07-13_ltx_aio_switch.md`
- **Done**
  1. LTX 전 모드 → 실 AIO UI + `[[P:]]` 스위치 (`ltx_aio_workflow_runner`); 미니 그래프 비기본
  2. cafe_gomin_ep01 LTX 쇼츠 1편 (S01 i2v + S02–05 SI2V 체인 + BGM hardcut) → `exports/final/cafe_gomin_ep01_ltx23_switch_playable.mp4` + 채널 exports 복사
  3. SageAttention: Comfy 설치 확인; IT `attention_mode=sageattn` 기본 (`AGENT_IT_ATTENTION` 폴백)
- **QA 미해결**: LTX 장클립 얼굴 붕괴; last-frame 체인=재생성 seed일 뿐 원테이크 아님; Wan/IT는 속도·톤 튜닝 필요(2.2 전면 채택 보류)
- **Next**: 짧은 LTX+고정 키프레임 재생성 → IT turbo/mild 벤치 → 하이브리드 공정

[2026-07-13] - Grok
- **작업 목표**: LTX2.3 AIO 스위치 경로로 **cafe_gomin_ep01 쇼츠 1편** 재생성.
- **생성**: S01 `ltx23_aio_i2v`; S02–S05 `chain_si2v_last_frame` + `ltx23_aio` (runner=`ltx_aio_workflow_runner`)
- **조립**: hardcut + BGM 0.18 → `exports/final/cafe_gomin_ep01_ltx23_switch.mp4` (~44.5s, 576×960@24)
- **채널 복사**: `D:\쇼츠 작업\채널 주인장이 뭐해야 할지모르겠답니다\exports\cafe_gomin_ep01\`
- **QA**: 얼굴 붕괴·하드컷 연속성 불만 → 세션 상태 문서 §2–3

[2026-07-13] - Grok
- **작업 목표**: LTX2.3 관련 기능을 **실 AIO 워크플로 스위치/셀렉트**로 전부 통일 (미니 그래프 기본 경로 폐기).
- **구현**:
  - `generate_s2v` 기본 = `lib.ltx_aio_workflow_runner.build_aio_switched_api`
  - `ltx_aio_mode_select` [[P:]] mute + `ltx_aio_ui_expand` (widget 순서/AE CLIP/NEVER 스킵)
  - 미니 그래프 = `AGENT_LTX_FORCE_MINI_GRAPH=1` only
  - 매니페스트/video_backends/`ltx23_aio_ia2v_agent_usage.md` 갱신
- **스모크**: `stories/cafe_gomin_ep01/exports/S02_aio_switch_smoke.mp4` (~100s, runner=ltx_aio_workflow_runner)
- **dry-run**: i2v mode_changes=4, flf mode_changes=9

[2026-07-12] - Grok
- **작업 목표**: AIO 모드 일괄 이식 — I2V / FLF / FML / V2V (±Audio).
- **구현**: `build_ltx_aio_mode_api` + 백엔드 alias `ltx23_aio_*` + `--ltx-mode` / `--last` / `--mid` *(이후 07-13에 실 WF 스위치로 대체)*
- **스모크**: `ltx23_aio` I2V+Audio OK; `ltx23_aio_flf` OK (~81s/49f)
- **V2V**: agent 매핑 = 이전 클립 last-frame 이어 생성 (풀 ExtendSampler 후속)
- **문서/매니페스트** 갱신

[2026-07-12] - Grok
- **작업 목표**: 사용자 LTX2.3 All-in-One WF → agent **`ltx23_aio` MVP 편입**.
- **구현**:
  - `lib/ltx_s2v.py` profile=aio (dynamic distill lora @0.9, defaults)
  - `generate_s2v --backend ltx23_aio` + yuv420p playable re-encode
  - `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json` 보관
  - `workflows/agent/ltx23_aio.manifest.json`
  - `video_backends.json` / chain 기본 백엔드 aio
- **스모크**: S02 + fulltail → `_smoke_ltx23_aio.mp4` (~3.6min, 544x960, 89f@24)
- **문서**: `docs/ltx23_aio_pipeline_integration.md`

[2026-07-12] - Grok
- **작업 목표**: OpenMontage **제작 레시피(파이프라인) 13종** 목록·설명 문서화.
- **산출**: `docs/openmontage_pipeline_recipes.md` (YAML description 기반, 스테이지·우리 쇼츠 관계).
- **링크**: capability_catalog §2, docs/README.

[2026-07-12] - Grok
- **작업 목표**: OpenMontage 풀 클론 **기능 목록화** + agent_custom 유용도 라벨 문서화.
- **산출**: `docs/openmontage_capability_catalog.md` (tools/skills/pipelines, A~E 라벨, 쇼츠 치트시트, 공식 연동 미정의 명시).
- **갱신**: `openmontage_eval_notes.md` 요약화, `docs/README.md` 링크.
- **정책 유지**: 본선=Comfy/agent_custom · OM=참고·선택 이식 · 전체 대체 금지.

[2026-07-12] - Grok
- **작업 목표**: FLF2V/F2F(프레임↔프레임·first–last 이음)를 **추가 예정 기능**으로 툴 문서에 고정.
- **배경**: 쇼츠 소비자 피드백 — 컷 분할 시에도 싱글테이크 연속감 필요; 립(SI2V)과 화면 연결(FLF) 역할 분리.
- **산출**:
  - 신규 SSOT: `docs/flf2v_f2f_roadmap.md` (S6 하위 티켓 S6.0–S6.9, DoD, 임시 SOP)
  - 교차 링크: `docs/README.md`, `storyboard_pipeline_design.md` S6, `audio_motion_production_modes.md`, `storyboard_keyframe_community_research.md`, `production_asset_pipeline.md`
- **구현 상태**: CLI/WF **미구현**. 당분간 연속 키프레임 = `shot_compose --source prev.png` + 낮은 denoise.

[2026-07-12] - Antigravity
- **작업 목표**: AGENTS.md에 추가된 도구 사용 규칙을 공식 에이전트 작업 규칙(Rule 10)으로 통합 및 갱신.
- **주요 변경**: `agent_rules.md` 파일 하단에 외부 워크스페이스 내보내기 의무(`export_episode_to_workspace.py` 사용 등) 관련 Rule 10을 추가하고, `process.md`에 이력을 기록함.

---

## 🎯 수정 목표 (시트 품질 — 사용자 확정 2026-07-12)

캐릭터 시트 품질 개선 **DoD 3종**. 공정에 슬롯이 있는 것과 별개로, **육안으로 통과**해야 완료.

| # | 목표 | 합격 기준 (육안) | 실패 예 |
|---|------|------------------|---------|
| **1** | 풀바디 생성 시 **가이드/본 안 보이게** | 최종 PNG에 OpenPose 스틱·박스·관절 가이드 **잔상 0** | 몸에 색 선/스틱 오버레이 |
| **2** | **감정 헤드** + **방향 턴 헤드** 확실히 | 표정 6종 서로 구분 가능 · head front/qf/side/back **방향 전환 확실** | 전부 비슷한 정면 미소 · side/back이 정면 |
| **3** | **바디 프로필용 풀바디 다방향 턴** | body turn front/qf/side/back **각도 다양·전신 유지** | 전 컷 정면 전신 · 측면인데 정면 얼굴 |

### 기술 메모 (구현 시)
* **#1**: pose ControlNet = OpenPose RGB 맵만 (Canny 스틱 금지) · strength 과다 시 스틱 베이크
* **#2-expr**: Moody I2I 표정 유지 (expression chart 분리)
* **#2/#3 turn (공정 기본 = Qwen multi-angles)**:  
  - **Qwen-Image-Edit-2511** + Lightning 4step + Multiple-Angles LoRA (`<sks> azimuth elevation distance`)
  - head: master_front → 4 view · body: master_full → 4 view  
  - 정면 Moody I2I / OpenPose-only 턴은 **레거시** (정면 고착·누드/아티팩트 실패 다수)  
  - CLI: `python scripts/character_qwen_turns.py --id <id> --mode both --approve`  
  - expand 연동: `sheet_presets` head/turnaround `engine=qwen` · `character_full_sheet.py --run`  
  - 폴백: OpenPose multiview strip / `character_turnaround_sheet.py`

### 검증 캐릭터
`sonagi_heroine_v1` · profile `full_sheet` · look `cinematic_moody_v1`

---

## ⏸ HANDOFF — 이어서 할 작업 (2026-07-12)

### 지금 상태 한 줄
**B2 wardrobe/props 잠금 + 순서 고정 공정 READY.** 턴=Qwen. 소나기: cream cardigan 룩 잠금 → costume/body turn/props 재생성 완료. pose는 아직 구 의상(검정 티) — 필요 시 `--phases rest` 또는 pose만 재생성.

### 파일럿 캐릭터
| 항목 | 값 |
|------|-----|
| cast | `sonagi_heroine_cast_v2` (pick: i2i_light s91065 c05) |
| character_id | `sonagi_heroine_v1` |
| look | `cinematic_moody_v1` |
| profile (시트 공정) | **`full_sheet`** (video_ref는 thin only) |
| Qwen 턴 리뷰 | `exports/full_sheet/review_qwen_turns_both.png` |
| 풀 패키지 리뷰 | `exports/full_sheet/review_FULL_PACKAGE.png` |
| PNG | gitignore (`*.png`) — 로컬에만 존재 |

### 다음에 이어서 (우선순위)
1. **육안 검수** Qwen head/body 턴 (`review_02_head_turn.png`, `review_03_body_turn.png`, `review_qwen_turns_both.png`)  
2. 통과 시: expression/costume/pose 기존 유지, FULL_PACKAGE 재export만  
3. 턴 재생성 필요 시:
   ```bash
   python scripts/character_qwen_turns.py --id sonagi_heroine_v1 --mode both --seed-base 100801 --approve
   python scripts/character_full_sheet.py --id sonagi_heroine_v1 --approve-only
   ```
4. pose 세부 품질 / 피부 플라스틱 후속 (expr 코어 태그는 반영됨)
5. **ipadapter** 코드 유지, 공정 SOP 미사용 유지

### 핵심 코드/문서
| 경로 | 역할 |
|------|------|
| `scripts/generate_qwen_angle.py` | Qwen-Image-Edit-2511 multi-angle API graph |
| `scripts/character_qwen_turns.py` | head/body 4+4 배치 + approve |
| `scripts/character_expand_sheets.py` | `engine=qwen` + auto 프리셋 연동 |
| `scripts/character_full_sheet.py` | expand+approve+review (turn 기본 qwen) |
| `characters/sheet_presets.json` | head/turnaround `engine=qwen` (v1.2) |
| `docs/character_casting_pipeline.md` | C = full_sheet SOP |
| `agent_rules.md` Rule 6.2 | 풀시트 공정 규칙 |

### 스모크 성공 예시
- control: `pose_templates/openpose/openpose_walk_side_1024x1536.png`  
- out: `characters/sonagi_heroine_v1/refs/pose/_smoke_openpose_walk.png`  
- 결과: 스틱 오버레이 없음, 보행 포즈 자연스러움 (신발 누락 등 세부는 후속)

---

## 📅 작업 이력 로그

### [2026-07-12] ACE-Step BGM 도구화
* **작업 에이전트**: Grok
* **엔진**: 사용자 WF `audio_ace_step1_5_xl_turbo.json` → API 그래프
* **CLI**: `generate_bgm.py`, `episode_bgm.py` (기본 instrumental)
* **문서**: `docs/ace_step_bgm_pipeline.md`
* **폴백**: SoniloTextToMusic
* **주의**: ACE 가중치 `ACESTEP1.5/` 미설치 시 다운로드 필요 (노드·WF는 존재)

### [2026-07-12] Qwen3-TTS 도구화 + LTX/SI2V 연동 설계
* **작업 에이전트**: Grok
* **리서치**: Qwen3 CustomVoice/VoiceDesign/Clone; Comfy FB nodes; 커뮤니티 Qwen3-TTS+LTX talking avatar; LTX audio-cond I2V
* **구현**: `generate_qwen3_tts.py`, `episode_tts.py --bind-si2v`, `comfy_client` extract/download audio
* **문서**: `docs/qwen3_tts_ltx_audio_pipeline.md` · Rule 7.1 TTS 절
* **로컬**: CustomVoice 1.7B + Sohee 등 프리셋; design/clone 모델 온디맨드
* **본선 경로**: TTS wav → driving prep → episode_s2v (기존 립싱크)

### [2026-07-12] 스토리보드·키프레임 커뮤니티 리서치 → 공정 반영
* **작업 에이전트**: Grok
* **리서치**: YT/커뮤니티/벤더 (Topview asset cards, Kling keyframe-first, Runway/Luma multi-keyframe, Reddit bake-keyframes-first, FLF2V, location docs)
* **문서**: `docs/storyboard_keyframe_community_research.md`
* **구현 반영**:
  * `stories/shot_type_presets.json` v2 — shot_type별 char/loc approved alias 우선순위 + i2v_hint
  * `shot_compose.py` — 타입 기반 ref 바인딩, wardrobe_lock, motion_prompt 제안, I2V 규칙 meta
  * `storyboard_export.py` — contact sheet + inventory + checklist (`board/`)
  * Rule 6.1 / storyboard design SOP / scripts README
* **운영 포맷**: asset packs → shots.json → keyframes/*.png → board/storyboard_contact.png → approve → I2V

### [2026-07-12] 로케이션 시트 L3 파일럿 + full_sheet 원샷
* **작업 에이전트**: Grok
* **상태**: 인프라(L1–L2)는 이미 있었고 MVP 미완 → 보완
* **구현**:
  * `scripts/location_full_sheet.py` — expand + auto-approve + review grids
  * expand: bible `landmarks` 주입 (prop_a/b)
  * auto-approve 엄격 매칭 (wrong alias 방지)
* **파일럿 `cafe_seoul_v1`**: video_ref MVP 완료 L2, missing_mvp=[]
  * angles eye/reverse/high/low + empty_stage
  * lighting day/golden
  * landmarks a/b
  * 리뷰: `locations/cafe_seoul_v1/exports/video_ref/review_*.png`
* **후속**: ControlNet 각도 강화(L4), 소나기용 로케 추가, shot_compose 연동 검수

### [2026-07-12] B2.5 off-body design plates (의상 flat/callout + 소품 hero/3view)
* **작업 에이전트**: Grok
* **추가**: 사람 없는 의상·소품 디자인 플레이트
  * `costume.flat_front` / `flat_back` / `callout` (T2I product)
  * `props.hero` / `props.turn_3view` (T2I product)
  * on-model `props.hand_item` 유지
* **공정**: full_sheet Phase B2.5 `design_pack` → 이후 on-model costume
* **시트**: `sheet_presets` v1.4, expand engine `t2i`, full_sheet `--phases design`
* **MVP**: full_sheet aliases +5 (flat×2, callout, prop_hero, prop_turn_3view)

### [2026-07-12] B2 wardrobe/props 잠금 + full_sheet 생성 순서 재배열
* **작업 에이전트**: Grok
* **문제**: 의상 일관성 붕괴 — face 직후 full_pack 일괄, wardrobe/props 선결정 없음, detail/props 하드코딩
* **구현**:
  * `lib/wardrobe.py` + `scripts/character_set_wardrobe.py` (B2)
  * bible: `props_default`, `wardrobe_locked`, consistency must_keep default wardrobe
  * expand: bible 주입 (costume/detail/pose/props), costume_default 소스 우선
  * `character_full_sheet.py`: wardrobe 게이트 + Phase0 master_full →1 costume →2 Qwen turns →3 rest
  * sheet_presets v1.3 full_pack 순서 costume-first · wardrobe_pack/body_pack
  * promote optional `--wardrobe-default` / casting SOP Rule 6.2 갱신

### [2026-07-12] Qwen multi-angles → 캐릭터 시트 턴 기본 경로
* **작업 에이전트**: Grok
* **문제**: Moody OpenPose head/body 턴 시트 엉망 (정면 고착·아티팩트)
* **해결**: 로컬 Qwen-Image-Edit-2511 + Lightning + Multiple-Angles LoRA 를 공정 기본으로 편입
* **구현**:
  * `generate_qwen_angle.py` / `character_qwen_turns.py`
  * `sheet_presets` head.* / turnaround.* → `engine=qwen`, `qwen_view=…`
  * `character_expand_sheets.py` engine `qwen` 분기
  * `character_full_sheet.py` turn 기본 qwen + approve 시 `qwen_*` 우선
  * Rule 6.2 / casting SOP / process 목표 메모 갱신
* **파일럿**: `sonagi_heroine_v1` Qwen 8/8 ok, approve head_* + turn_*
* **리뷰**: `exports/full_sheet/review_qwen_turns_both.png`

### [2026-07-12] OpenPose 포즈 경로 전환 (품질 개선 착수) + 체크포인트
* **작업 에이전트**: Grok
* **문제**: 자체 스틱 실루엣 + Canny → Union CN → 박스/스틱 아티팩트 (쓸 수 없는 포즈 시트)
* **리서치**: Z-Image Fun ControlNet Union = Pose 조건은 **OpenPose/DWPose RGB 맵** 직접 입력 (Canny 금지)
* **구현**:
  * `lib/openpose_maps.py` — BODY_18 합성 맵 + Comfy python OpenPose extract
  * `pose_templates.ensure_pose_template` → openpose 맵 우선
  * `generate_moody_controlnet` `control_preprocess=auto|openpose|canny`
  * sheet_presets turn/pose → `control_preprocess: openpose`
* **스모크**: walk OpenPose OK (아티팩트 제거)
* **Task1 배치 (seed 96001)**: **강제 종료 완료** (2026-07-12)
  * ✅ turnaround 4: s96001–96004
  * ✅ pose: stand_idle s96005, walk s96006, sit s96007
  * ❌ pose 미완: hands_hips / wave / look_aside
  * 재개: `--sheets pose --seed-base 96008` (또는 전체 pose 재실행)
* **커밋**: `7202396` (+ process handoff 보강 가능)

### [2026-07-12] 업계 풀시트 공정 구현 + 소나기 풀팩 테스트
* **작업 에이전트**: Grok
* **사과/교정**: video_ref 표정 MVP를 시트 완성으로 보고한 것 잘못 — 공정 본체=`full_sheet`
* **구현**:
  * 프로필 `full_sheet` + `full_pack` 26 presets (head/turn/expr/costume+detail/pose/props)
  * pose templates walk/sit/wave/hands_hips/look_aside
  * `character_full_sheet.py` expand+auto-approve+review grids
  * casting SOP / agent Rule 6.2 갱신
* **테스트**: `sonagi_heroine_v1` success=26 fail=0 missing_mvp=[]
* **리뷰**: `characters/sonagi_heroine_v1/exports/full_sheet/review_*.png` + `review_FULL_PACKAGE.png`

### [2026-07-12] 소나기 풀시트 — 전신/턴/의상 보강
* **작업 에이전트**: Grok
* **배경**: video_ref `all_mvp`=표정만 → 사용자 피드백 후 전신 세트 추가 생성
* **추가**: master_full (T2I) + costume×2 (I2I) + turn×4 (ControlNet) → approve 14장
* **리뷰**: `exports/video_ref/full_package_review.png`
* **코어**: positive_core 클로즈업 문구 제거 · bible wardrobe 설정

### [2026-07-12] 소나기 B+C — sonagi_heroine_v1 시트 (video_ref MVP)
* **작업 에이전트**: Grok
* **Pick**: cast_v2 i2i_light s91065 c05 → promote `sonagi_heroine_v1`
* **C**: expand expression×6 `--engine i2i_lock` candidates=1 → approve 전부 → **missing_mvp=[] L2**
* **리뷰**: `characters/sonagi_heroine_v1/exports/video_ref/expression_sheet_review.png`
* **비고**: i2i_lock denoise cap 0.58 → 표정 변화가 약할 수 있음 (결과 육안 확인 필요)

### [2026-07-12] 소나기 캐스트 v2 — anchor I2I 변주
* **작업 에이전트**: Grok
* **Anchor**: v1 moody_pro s88035 c02 (분위기 유사 얼굴)
* **Cast**: `sonagi_heroine_cast_v2` — I2I/i2i_lock ×10 + anchor, contact_sheet
* **방법**: T2I 재오디션 아님. denoise 0.42–0.60, pro/real/wild, 의상·헤어·라이트 미세 변주
* **스크립트**: `scripts/_cast_v2_variations.py` (원샷)
* **대기**: 사용자 pick → promote

### [2026-07-12] 소나기 주인공 캐스트 테스트 A (Style Core + pool)
* **작업 에이전트**: Grok
* **Look**: `cinematic_moody_v1` 지정
* **Cast**: `sonagi_heroine_cast_v1` — moody_pro×3 + real×2 + wild×2 + krea×2 = **9후보** + contact_sheet
* **수정**: cast_pool Krea sampler `euler_sde`→`euler_ancestral` (Comfy 400 해결)
* **대기**: 사용자 pick → B promote → C expand `i2i_lock`

### [2026-07-12] C공정: ipadapter SOP 제외 (코드 유지)
* **작업 에이전트**: Grok
* **정책**: SD1.5 IP-Adapter는 ZIT/Krea와 공식 페어가 아니므로 **공정 치트시트·DoD에서 제외**. CLI/`generate_moody_i2i_ipadapter` 코드는 실험용으로 유지.
* **C 공정 엔진**: `i2i` (기본) · `i2i_lock` (권장 identity). docs/character_casting_pipeline.md 반영.

### [2026-07-12] C공정 IPAdapter + Style Core Production v1
* **작업 에이전트**: Grok
* **C identity**: `--engine i2i_lock|ipadapter` 구현 (plus-face SD15, ZIT I2I 주입, lock 폴백). e2e joy OK. → **이후 공정 정책으로 ipadapter는 SOP 제외**.
* **Look**: `look_create` / `look_status`, episode_status look 검증, look_style_system Production v1 (shot_compose 주입 기존)

### [2026-07-12] 캐릭터 공정 Production v1 마감
* **작업 에이전트**: Grok
* **DoD**: A cast → B promote → C expand/approve 를 **실무 치트시트 + CLI 세트**로 완결
* **추가**: `character_status`, `character_shortlist`, `character_pipeline`, SOP DoD in casting doc
* **검증**: promote+expand dry-run E2E; cast real smoke (moody_pro×1) when Comfy up
* **후속(비블로커)**: InstantID, shot_compose multi-engine, auto-approve

### [2026-07-12] 캐릭터 공정 A/B/C + 커뮤니티 리서치 반영
* **작업 에이전트**: Grok
* **리서치 요약**: sheet-first / multi-model cast / human gate / CN turnaround / IPAdapter는 확정 후 (후속)
* **공정**: A cast_pool → B promote → C expand (기존) → D video
* **구현**: `docs/character_casting_pipeline.md`, `lib/cast_pool.py`, `character_cast_pool.py`, `character_promote.py`
* **엔진**: moody_real|pro|wild + krea (탐색). 시트 일관은 Moody I2I 유지

### [2026-07-12] 생성 본선 재확인 + SI2V 품질 기본값
* **작업 에이전트**: Grok
* **방향**: OpenMontage = 편집/조립 참고만. **본선 = Comfy 이미지·클립 생성 품질**
* **변경**:
  1. driving prep 기본 **`auto`** (demucs 있으면 demucs, 없으면 center_voicey)
  2. `episode_s2v` 기본 **square 640** 얼굴 캔버스 (립 픽셀 우선; `--no-square` 로 에피소드 aspect)
* **OpenMontage**: 로컬 클론 평가만 (`docs/openmontage_eval_notes.md`). 생성 스택 대체 아님.

### [2026-07-12] demucs 보컬 분리 설치 + 스모크
* **작업 에이전트**: Grok
* **설치**: Comfy portable `python_embeded` → `demucs` 4.1.0 (torch 공유)
* **실측**: `sonagi_v1_slice5.wav` → `…/s2v_drive/sonagi_v1_slice5_demucs_vocals.wav` (5s mono 48k, mean≈−19dB)
* **SI2V**: LTX + demucs vocals → `S02_s2v_ltx_v3_demucs.mp4`
* **사용**: `audio_prepare_driving -m demucs` / `audio_bind_driving -m demucs`
* **참고**: demucs ≠ Comfy 노드. 최종 뮤비 사운드는 여전히 music master

### [2026-07-12] InfiniteTalk v4 QA — 1급 대안 유지
* **작업 에이전트**: Grok (+ 사용자 육안)
* **클립**: `S02_s2v_smoke_v4_center_voicey(_playable).mp4` — Wan2.1+InfiniteTalk + center_voicey
* **판정**: 입이 **제법 맞기 시작** → 실험용이 아니라 **후속 프로덕션 후보로 문서·backends 고정**
* **정책**: default=LTX, IT=1급 대안 (face stability / LTX drift 시)

### [2026-07-12] SI2V 기본=LTX + 뮤비 driving 바인딩 CLI
* **작업 에이전트**: Grok
* **default_backend_s2v** = `ltx23_ia2v` (`video_backends.json`, generate/episode_s2v 기본)
* **`audio_bind_driving.py`**: master 슬라이스 → prepare → `motion_driver=si2v` + `audio_refs.driving` 원샷
* **episode_status**: si2v/i2v 구분 next_action (`audio_bind_driving` / `episode_s2v` / `episode_i2v`)
* **검증**: bind dry-run + episode_status 표

### [2026-07-12] LTX 2.3 IA2V 백엔드 연동 + IT A/B
* **작업 에이전트**: Grok
* **인벤토리**: ComfyUI-LTXVideo, GGUF distilled/dev Q4, LTX23 audio/video VAE, gemma, distilled-lora-384 ✅  
  공식 **IC-LoRA LipDub** HF gated → 다운로드 거부 (승인 필요). V2V Just-Dub 경로 보류.
* **구현**: `lib/ltx_s2v.py` custom-audio 최소 그래프; `generate_s2v --backend ltx23_ia2v|infinitetalk`; episode_s2v `--backend`; SaveVideo `images[].mp4` 복사 픽스
* **실측** (master_front 640², clean VO 5s):
  - LTX v1: success ~100s, 입 개폐·블링크·미소 변화 명확, identity 안정, 손 살짝 등장
  - IT v3(이전): 입 개폐 명확, 소요 ~12min
* **권장**: 립 품질 우선 A/B 시 `ltx23_ia2v` 후보; 기본은 당분간 IT 유지 가능. LipDub LoRA HF 승인 후 V2V 경로 추가.
* **다음**: HF LipDub 승인·다운로드 시 `ltx23_lipdub`; demucs 보컬; 뮤비 타임라인 연동

### [2026-07-12] 문서: SI2V = story 대사 + music_video 보컬 공통
* **작업 에이전트**: Grok
* **요지**: 립싱크는 스토리 대사 전용이 아님. 뮤비 중간 온카메라 보컬/노래 컷도 `motion_driver=si2v` 1급.
* **갱신**: `audio_motion_production_modes.md` §0.1·§2.4, Rule 7.1, commission_workflow, episode_s2v docstring

### [2026-07-12] SI2V 재개 — prepare_driving + episode_s2v + 품질 v3/v4
* **작업 에이전트**: Grok
* **커밋 정리**: uncommitted 오디오/SI2V/업스케일/로케 묶음을 논리 커밋 6개로 분리 (rtx_vsr 기본, Wan dim snap, audio P0–P1, generate_s2v, cafe_seoul, process log)
* **구현**:
  1. `lib/ffmpeg_util.prepare_driving_audio` + `scripts/audio_prepare_driving.py` (`copy|voicey|center|vocal_band|center_voicey`)
  2. `lib/audio_package.materialize_driving_audio` (slice + prep cache under `audio/exports/s2v_drive/`)
  3. `scripts/episode_s2v.py` — `motion_driver=si2v` 배치 → `clips/work/*_s2v.mp4`
  4. `episode_pipeline` stage `s2v` (si2v 샷 없으면 exit 21 soft-ok)
* **실측 QA** (master_front 640² 25fps 20step, ~12min/clip):
  | ver | 오디오 | 판정 |
  |-----|--------|------|
  | v3 | 클린 TTS VO 5s + voicey | identity 안정, **입 개폐 명확** (f01 open → f05 closed → f07 teeth). talking-head 기준선 ✅ |
  | v4 | 소나기 5s **center_voicey** | identity 안정, 입 움직임 있음. v2 풀믹스 대비↑. 음절 단위 정밀 싱크는 여전 soft |
* **교훈**: 클린 dialogue/VO > FFmpeg center_voicey > 풀 믹스. demucs/MelBand는 미설치 — 뮤비 보컬 stem 다음 후보.
* **파일럿**: mina S02 `motion_driver=si2v` + driving=sonagi_v1_slice5 (에피소드 로컬, gitignore)
* **다음**: (선택) demucs/MelBand 보컬 분리; music_video 샷 타임라인 연동; agent WF JSON 스냅샷

### [2026-07-12] SI2V 품질 QA — 파이프 OK ≠ 립싱크 합격
* **작업 에이전트**: Grok
* **v1 육안**: 입 움직임은 있으나 립싱크 실패급 + 손/표정 붕괴
* **v2**: master_front + 25fps + 20step + voicey EQ → identity 안정, 입 개폐 약함, **정밀 립싱크 미달**
* **교훈**: 생성 exit 0만 보고 합격 판정 금지; 풀 믹스 뮤비 구간은 보컬 분리 필요
* **다음**: MelBand/보컬 stem 경로 또는 클린 VO 테스트 → **후속 항목에서 완료**

### [2026-07-11] InfiniteTalk SI2V 실생성 스모크 OK
* **작업 에이전트**: Grok
* **경로**: Wan2.1 I2V 14B Q4 GGUF + InfiniTetalk-Single fp16 + Tencent wav2vec (HF download node)
* **실측**: 소나기 5s slice + mina S02 → `clips/work/S02_s2v_smoke.mp4` (~3min, 640², 81f, 6step)
* **수정**: `audio_slice` 재인코딩(메타 깨짐 방지); InfiniteTalk hardlink to diffusion_models; `generate_s2v.py` live inject
* **다음**: episode_s2v 배치, 품질 튜닝(해상도/steps), music_video 샷 연동

### [2026-07-11] 오디오 P1 layered + 소나기 music_locked 스모크 + S2V scaffold
* **작업 에이전트**: Grok
* **P1**: `collect_timeline_events` / `mix_timeline_under_video` (atrim+adelay+amix); `audio_slice.py`
* **실측**: `소나기mastered.wav` → `assemble --mix-policy music_locked` → final **12.2s h264+aac**
* **SI2V**: 이후 실생성 스모크에서 확인
* **슬라이스**: t=38–43s → `audio/dialogue/sonagi_v1_slice5.wav`

### [2026-07-11] 오디오·모션 드라이버 설계 + P0 구현
* **작업 에이전트**: Grok
* **작업 목표**: 뮤비/스토리 등 프로덕션 모드와 대사·SFX·SI2V를 BGM 한 줄로 뭉개지 않도록 계약 고정 후 조립 기초.
* **설계**: [docs/audio_motion_production_modes.md](docs/audio_motion_production_modes.md)
  - 축: `production_mode` × `motion_driver` × `mix_policy`
  - stems: masters/music/dialogue/vo/sfx
  - 계획 P0 계약·조립 → P1 샷 타임라인 → P2 SI2V → P3 TTS
* **구현 (P0)**:
  1. `lib/audio_package.py` — mode defaults, readiness, stem resolve
  2. `lib/ffmpeg_util.mix_audio_under_video` — multi-stem amix
  3. `scripts/assemble_video.py` — mix_policy 분기 (`video_only`/`music_locked`/`bgm_under`/`dialogue_sfx_first_bgm_late`)
  4. `scripts/audio_status.py`
  5. schema/template/commission 필드; `episode_i2v` 가 non-i2v 드라이버 스킵
* **정책 참고**: 업스케일 기본 **rtx_vsr** (SeedVR2 실무 비권장)
* **다음**: P1 layered 타임라인 · P2 generate_s2v

### [2026-07-11] shot_compose --all / assets_list / pipeline stages
* **작업 에이전트**: Grok
* **작업 목표**: 배치 키프레임 컴포즈 + 자산 목록/에피소드 점검 + 파이프에 assets·compose 단계.
* **주요 변경**:
  1. `shot_compose.py --all` / `--force`
  2. `scripts/assets_list.py`
  3. `episode_pipeline` stages: status→assets→compose→contact→i2v→upscale→assemble→package
* **검증**: assets list, compose --all --dry-run, pipeline slice dry-run

### [2026-07-11] commission_start / shot_edit + deliveries gitignore
* **작업 에이전트**: Grok
* **작업 목표**: 수주 브리프 한 장으로 에피소드 스캐폴드; 샷 JSON 패치 CLI; 산출물 gitignore.
* **주요 변경**:
  1. `lib/commission.py` + `scripts/commission_start.py`
  2. `docs/commission_brief.schema.json`, example brief, `docs/commission_workflow.md`
  3. `scripts/shot_edit.py`
  4. `.gitignore`: stories/* working trees, deliveries, mp4/zip (templates/examples 유지)
* **검증**: brief dry-run + real scaffold, shot_edit create/patch

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







### [2026-07-14] Tooling: Ideogram4 typography + P0-1 SI2V length contract
- Ideogram4: `scripts/generate_ideogram4.py`, `lib/ideogram4_prompt.py` (official text/bbox schema), docs/ideogram4_typography_tool.md
- P0-1: `lib/s2v_length_contract.py`; IT default max frames 257; hard-fail over cap; prep auto=center_voicey; episode_s2v preflight + duration_sec sync
- Next: P0-2 performance profiles, P0-3 auto-export workspace

### [2026-07-14] P0-2 performance profiles (TTS + SI2V)
- `lib/performance_profiles.py` — warm_greeting / neutral_calm / mild_unsatisfied / thoughtful / cute_ask / sip_business
- `episode_tts --performance` sets instruct + shot.performance + bind motion/audio_scale
- `episode_s2v --performance`; speak markers never clobbered by bare still/static
- Next: P0-3 auto-export workspace

### [2026-07-14] P0-2 performance profiles (TTS + SI2V)
- `lib/performance_profiles.py` — warm_greeting / neutral_calm / mild_unsatisfied / thoughtful / cute_ask / sip_business
- `episode_tts --performance` sets instruct + shot.performance + bind motion/audio_scale
- `episode_s2v --performance`; speak markers never clobbered by bare still/static mouth false positives
- Next: P0-3 auto-export workspace

### [2026-07-14] P0-3 auto-export workspace
- `lib/workspace_export.py`; episode_i2v/s2v/tts end with export when AGENT_WORKSPACE set or --export-workspace
- CLI: --export-workspace / --export-dest / --no-export-workspace; AGENT_EXPORT_WORKSPACE=0|1
- Sprint A (P0-1..3 + Ideogram) complete; next P1 status health

### [2026-07-14] P1-1 episode_status length health
- shot rows: tts_sec / drive_sec / clip_sec + SHORT|DRIVE_MISMATCH|DURATION_SHORT
- overall_next: fix_driving_length / regen_s2v_longer

### [2026-07-14] P1-2 one-take chain polish
- `lib/one_take.py`; `shot_compose --from-prev-shot`; `chain_one_take` uses performance + length contract + fresh clip gate + export

### [2026-07-14] P1-3 surgical keyframe edit + P1-4 clip review sheet
- `shot_keyframe_edit.py` Moody I2I local edit → draft; history backup; refuse global blur
- `clip_review_sheet.py` first/last frames + contact grid under board/clip_review/

### [2026-07-14] P2-2 episode subtitles SRT + soft burn
- `lib/subtitles.py`, `scripts/episode_subtitles.py`
- Timeline from work clips; soft-burn via ffmpeg subtitles filter

### [2026-07-14] P2 wrap: assemble --subs, sfx notes
- assemble_video --subs writes SRT + soft-burn companion
- docs/sfx_queue_notes.md for layered SFX convention

### [2026-07-14] ACE-Step BGM fix (chunk stitch + ace15 max_tokens)
- Root cause (this box): single-shot ACE reliable only ~<=15s; longer => full-scale garbage PCM
- Fix: generate_bgm auto-chunks (15s) + acrossfade stitch; free models between chunks
- Comfy patch: text_encoders/ace15.py max_tokens=metadata max_tokens (was min_tokens twice)
- Sampling restored to temp=0.85 top_p=0.9 (official)
- Smoke: bgm_cafe_ace.mp3 45s mean~-18.5dB OK
