<!-- LTX25-CURRENT-START -->
> **LTX-2.5 현재 상태 (2026-10-16T15:46:24.123116+00:00): ready_experimental.** T2V/I2V/FLF/T2A/A2V 짧은 실행 확인; Ingredients는 소품/장소 참조 시각 PASS, 정확 얼굴·청취는 pending. 이전 실패/접근 차단 문장은 당시 이력이다. [현재 사용 가이드](F:/Agent_media_tools/workflows/human/ltx25_official/AGENT_GUIDE.md)에서 시트 규칙·실패 양상·검증 입력/출력·정확 재현 명령·미검증 목록을 확인한다. [복구 진단](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md).
<!-- LTX25-CURRENT-END -->

# TOOLS — 프로젝트 에이전트 입구

## Higgs TTS 3 — original 8188 / ready_experimental

Short Korean/English speech with official emotion tags and local-reference conditioning. Original Transformers 4.57.3 is preserved; a private Transformers 5 subprocess performs inference. Listening emotion/timbre QC and browser UI execution remain unverified. Creator content requires prominent Boson AI's Higgs Audio credit.

`python scripts/generate_higgs3_tts.py -t "안녕하세요. 반갑습니다." --emotion elation -o F:/my_project/voice.wav`

Guide: [Higgs TTS 3](workflows/human/higgs3_tts/AGENT_GUIDE.md); measured matrix: `F:/Agent_media_sandboxes/higgs3/validation`. Existing locked VoiceDesign: use `generate_qwen3_tts.py`; singing: `generate_yue2_music.py`.

이 레포는 **ComfyUI 미디어 공구함**입니다.  
정형 영상 양산 공정이 **아닙니다.** **결과물 창고도 아닙니다.**

에이전트는 **만들고 싶은 영상/컷**에 맞춰 도구를 **자유롭게 고르고 조합**합니다.  
생성물은 **반드시 자기 프로젝트 경로**에 둡니다 (`-o` / `--output` / `--dest` / `AGENT_WORKSPACE`).  
`stories/`, `dumps/`, `characters/<id>/`, `deliveries/` 에 mp4·png·wav를 쌓지 마세요.

```text
목표  →  tool_intent 검색 또는 tool_catalog 선반  →  CLI 1회 (-o 프로젝트)
      →  review_media pack → 파일 열기 → record → 다음 의도
```

생성 `exit 0` 은 파일이 생겼다는 뜻이다. 목표에 맞는지는 **연 뒤에만** 말한다.  
스킬: [skills/output-review/SKILL.md](skills/output-review/SKILL.md)

### 빠른 검색 (의도 → CLI)

```bash
python scripts/tool_intent.py "얼굴 유지하면서 장면 바꿔"
python scripts/tool_intent.py search "camera push in" --json
python scripts/tool_intent.py list --shelf MOTION
python scripts/tool_intent.py shelves

# 인덱스 드리프트 검사 (intent / catalog / backends)
python scripts/tool_index_check.py

# 모델별 공식 프롬프트 방언 (생성 직전)
python scripts/prompt_dialect.py pick "시네 인물"
python scripts/prompt_dialect.py show krea
python scripts/prompt_dialect.py list

# 생성 직후 능동 평가 (exit 0 ≠ 품질)
python scripts/review_media.py pack -i "%AGENT_WORKSPACE%/stills/hero.png" --intent "medium, yellow parasol" -o "%AGENT_WORKSPACE%/reviews/hero"
python scripts/tool_intent.py "결과 검수"

# Krea2 / Lonecat v7 기능 맵 (바이패스 스위치 인벤토리)
python scripts/krea2_features.py list --ready
python scripts/krea2_features.py search "style"

# 업스케일러 선택 (매체·목표·도메인 → backend/style)
python scripts/upscale_recommend.py --media image --goal delivery --domain photo
python scripts/upscale_recommend.py --media video --goal hero --source blurry
python scripts/upscale_recommend.py matrix
```

Comfy 불필요 · 생성 안 함 · 추천 CLI + (관련 시) 실패 노트 프리플라이트.

### 생성 전 실수 방지 (failure notes)

```bash
# PREVENT 먼저 출력 — 같은 실패 반복 금지
python scripts/failure_note.py before "freeze OR feet OR framing"
python scripts/failure_note.py before "i2v"
python scripts/failure_note.py search "anatomy_feet"
# FAIL 후 기록
python scripts/failure_note.py add --stage keyframe --tags ... --symptom "..." ...
```

Docs: [docs/failure_notes_system.md](docs/failure_notes_system.md) · Rule 7.4


## MiniMax H3 — 모델 계열별 기본 도구

실행 전 [H3 반복 안정화 가이드](docs/comfyui_h3_stability.md)를 따른다. 서버 설정·러너 정리 노드·로컬 KJNodes 캐시 방지를 함께 확인한다.

FL2VA 계열 **T2V/I2V/FLF는 `scripts/generate_minimax_h3.py` 기본 단일 샘플링을 우선 사용**한다. `--profile work` 또는 `native`, 숏츠는 `--aspect 9:16`. `native_fast`, `--latent-upscale 2` 및 개선형 FL2VA 15+5는 현재 제작 기본값에서 제외하고 원인 분리 실험에만 사용한다. **R2V/V2V/AI2V는 `scripts/generate_minimax_h3_optimized.py` 우선**을 유지한다. FLF는 기본형의 VAE 전 모델 해제 보완 후 8초·576×1024 저장 성공을 확인했고, 네이티브 해상도 성공은 사용자가 보고했다. 2026-10-05 기본 I2V는 8초·576×1024 두 번과 직후 짧은 실행을 서버 재시작 없이 검증했다. T2V 및 native 고해상도 전체의 장시간 안정성 검증을 뜻하지 않는다.

가이드: [H3_OPTIMIZED_GUIDE](workflows/human/minimax_h3/H3_OPTIMIZED_GUIDE.md). V2V는 영상 참조 생성, AI2V는 오디오+이미지 참조 생성이며 H3 생성 오디오를 저장한다. 원본 WAV를 그대로 입히거나 정확한 립싱크를 보장하지 않는다. `generate_minimax_h3`는 FL2VA 기본 생성과 polish/carry/특수 혼합 참조에 사용한다. 잠긴 카메라는 먼저 `camera-previz`를 따르고, 필요한 이미지+참조 영상 입력을 지원하는 기존 경로를 유지한다. `generate_minimax_h3_7plus1`은 기존 R2V 호환 도구로 유지한다. 생성물과 리뷰는 호출하는 프로젝트에 저장하며 failure_note / generation-prompt / output-review 절차를 유지한다.

## 무엇을 읽나

| 우선 | 문서 |
|------|------|
| **0** | **`python scripts/tool_intent.py "…"`** — 의도 키워드 검색 |
| **1** | **[docs/tool_catalog.md](docs/tool_catalog.md)** — 의도 선반 · when/when-not · CLI · 조합 예시 |
| 2 | `workflows/human/**/AGENT_GUIDE.md` — 도구별 상세 |
| 3 | [AGENTS.md](AGENTS.md) — 소비자 계약 (공구함 vs 작업대) |

---

## 의도 선반 (한눈에)

| 선반 | 하는 일 | 대표 CLI |
|------|---------|----------|
| **GENERATE** | 빈 화면 → 그림 (**기본: Krea2**) | `generate_krea` · **`generate_krea_draft`** · `generate_krea_nsfw` · **`generate_anima` (2D 애니)** · `generate_moody` · `generate_illustrious_standard` · **`generate_illustrious_advanced`** · **`generate_flux`** · **`generate_flux2_klein`** · **`generate_sdxl`** |
| **TRANSFORM** | 같은 인물·편집·스타일·인페인팅 | `generate_character_consistent` · `generate_style_transfer` · **`generate_krea2_style`** · `generate_qwen_edit` · `generate_qwen_inpaint` · **`generate_flux_fill`** · **`generate_anima --mode lineart/inpaint`** |
| **CAMERA** | 각도·포즈·시점·프레이밍 | `generate_qwen_angle` · `generate_viewpoint` · **`generate_openpose_pose`** · **`generate_anima --mode pose/depth`** · **`generate_krea2_control`** · `generate_moody_controlnet` · `generate_reframe` |
| **MOTION** | 영상 모션 · 품질 계획 · 카메라 · 댄스 · **MiniMax H3 / LTX 2.5** | **`clip_quality`** · `generate_ltx25_aio` · `generate_minimax_h3_optimized` · `generate_i2v` · `generate_s2v` · `generate_camera_move` · **`generate_previz`** · `generate_idle_loop` · **`generate_wan_animate2`** · **`generate_wan22_animate`** · `generate_flf2v` |
| **TRANSFORM+** | 가벼운 ID 팩 | `generate_ref_pack` · `generate_character_consistent` |
| **VOICE** | 대사·노래·BGM·SFX·MIDI 반주 | `generate_qwen3_tts` · **`generate_minimax_music` (완곡/보컬, 캡션은 `music-caption-rewriter`)** · **`generate_yue2_music` (ABC 악보/음악 커버)** · **`generate_stable_audio` (악기/SFX)** · **`generate_midi_cover_bed` (화성→새 MIDI 반주)** · `generate_bgm` |
| **INGEST** | 유튜브 레퍼 이해 · 화성 뼈대 | `youtube_ingest` · `youtube_highlights` · **`extract_music_skeleton`** |
| **FINISH** | 업스케일 · 디테일러 · 포스트 | `upscale_*` · **`generate_anima --mode hires`** · **`generate_illustrious_detailer`** · **`generate_krea2_face/eyes/hand_detail`** · **`generate_krea2_region_detail`** · **`generate_krea2_post`** · `generate_rmbg` · `ltx_relight` |
| **ASSETS** | 캐릭/로케 패키지 *(옵션)* | `character_*` · `location_*` |
| **MESH** | 2D→3D 메쉬·GLB·VRM 프로토타입 | **`generate_trellis_mesh`** · `process_mesh_glb` · `export_mesh_vrm` (Hunyuan `generate_hy3d_mesh` = KR 라이선스 패스) |
| **BUNDLE** | 멀티샷 묶기·QA *(옵션)* | `story_init` · `assemble_video` · `shot_qa_*` |
| **EDIT** | 컷·타이틀·믹스·룩·마스터 | **`edit_pack`** · `render_edit` · `comp_shot` · `edit_timeline` · `render_title` · `edit_qa_pack` |
| **REVIEW** | 생성물 능동 평가 | **`review_media`** · `shot_qa_*` · `edit_qa_*` |

> ⚠️ **영상 모델 단일 클립 최대 길이 가이드 (기준: 24fps @ 768p)**
> - **MiniMax H3:** **최대 8초** (약 192프레임, 17k+5 그리드). 8초 초과 시 CLI 경고 발생. 롱테이크는 `--carry-from` 룸 체인이나 컷 분할 권장.
> - **LTX 2.5:** 제작상 권장 약 10초이며 공식 하드 한도가 아님. 유효 프레임은 `8n+1`. 명시적 `generate_ltx25_aio`는 10모드 선언, GPU/QC 미검증(`ready_experimental`). 일반 I2V/S2V 기본은 기존 2.3 유지. [버전·검증 가이드](workflows/human/LTX25_AIO_AGENT_GUIDE.md).

전체 표·카드·조합 예: **tool_catalog §1–§3**.

---

## 어떻게 쓰나

```bash
# 레포 루트에서
python scripts/<도구>.py ... -o <원하는_경로>
```

1. 목표에 맞는 **선반** 고르기  
2. **when / when not** 확인  
3. CLI 실행 · **`review_media pack` → 파일 열기 → record**  
4. pass 만 유저에게 보여 주거나 다음 단계로

에피소드 패키지·approve·assemble은 **필요할 때만** (카탈로그 §2.8).

---

## 역할 분담

| 이 레포 (제공) | 프로젝트 에이전트 (소비) |
|----------------|--------------------------|
| 워크플로 · CLI · 카탈로그 | 목표에 맞는 도구 **선택·조합** |
| 스모크 · 가이드 유지 | 호출 · 검수 · **자기 프로젝트에 반영** |
| catalog 갱신 | 스토리·파이프라인·납품은 **프로젝트 쪽** |

## YuE2 커버곡 스모크

`python scripts/cover_music.py doctor` → [yue2-cover 스킬](skills/yue2-cover/SKILL.md) → [작업 가이드](workflows/human/cover_music/AGENT_GUIDE.md). 창작 보컬 기본, 레퍼런스 음색은 선택. 다운로드·채보·생성·결과 회수·내보내기.


## Latest LTX-2.5 validation (2026-10-16T15:25:12.160419+00:00)

Eight short GPU runs completed on original8188: T2V quality/none, I2V, FLF, T2A, A2V, Ingredients twice. Basic visual motion checks and technical audio checks passed; full playback/listening and production identity remain pending. **Historical initial trials: both failed; subsequent repaired prop case visually PASSED**, despite successful exact 2.5 adapter loading/execution. See [official-derived task guide](workflows/human/ltx25_official/AGENT_GUIDE.md) for commands, provenance and failures. Existing AIO quality LoRA policy and generic 2.3 defaults remain. No package/node updates or restart. Evidence: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/runtime-validation.json`. Earlier pending-stage entries below are historical and superseded by this entry.


## Ingredients recovery update — 2026-10-16T15:42:42.646004+00:00

Earlier two visual failures remain in history, but they are no longer the final result. A controlled untiled-only ablation failed; rebuilding the reference as one distinct prop panel plus a separate empty location and matching the positional inventory prompt removed the panel layout/dark occluder at the same seed4747, strength1, official768×448/121/24 bucket. This bounded prop/motion case visually PASSED. Black background is part of the official sheet contract and remains in the successful input; removing it is not the general fix. The individual contribution of image design versus wording is not isolated.

The same INT8+new2.5 Ingredients stack also combined a published character/guitar/stage sheet into one scene; exact face/hair fidelity and listening remain pending. No general production identity guarantee. Detailed hypotheses, official/community confidence, actual API and contacts: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md`; latest records: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-repair-status.json`.

CLI Ingredients defaults are now5sec/768×448 with untiled reference encoding, strength1 and Euler ancestral. Community comparison controls are explicit `--adapter-strength 1.4 --sampler euler_ancestral_cfg_pp`; they do not replace the official default or original AIO quality policy. All prior T2A/A2V graphs and other successful paths are preserved. No new models/nodes/packages, no restart. Model remains only at `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`; Downloads duplicate absent and full SHA reverified.
