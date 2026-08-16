# TOOLS — 프로젝트 에이전트 입구

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

---

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
| **MOTION** | 영상 모션 · 품질 계획 · 카메라 · 댄스 · **MiniMax H3** | **`clip_quality`** · `generate_i2v` · `generate_s2v` · `generate_camera_move` · `generate_idle_loop` · **`generate_wan_animate2`** · **`generate_wan22_animate`** · **`generate_minimax_h3`** · `generate_flf2v` |
| **TRANSFORM+** | 가벼운 ID 팩 | `generate_ref_pack` · `generate_character_consistent` |
| **VOICE** | 대사·노래·BGM·SFX·MIDI 반주 | `generate_qwen3_tts` · **`generate_minimax_music` (완곡/보컬)** · **`generate_stable_audio` (악기/SFX)** · **`generate_midi_cover_bed` (화성→새 MIDI 반주)** · `generate_bgm` |
| **INGEST** | 유튜브 레퍼 이해 · 화성 뼈대 | `youtube_ingest` · `youtube_highlights` · **`extract_music_skeleton`** |
| **FINISH** | 업스케일 · 디테일러 · 포스트 | `upscale_*` · **`generate_anima --mode hires`** · **`generate_illustrious_detailer`** · **`generate_krea2_face/eyes/hand_detail`** · **`generate_krea2_region_detail`** · **`generate_krea2_post`** · `generate_rmbg` · `ltx_relight` |
| **ASSETS** | 캐릭/로케 패키지 *(옵션)* | `character_*` · `location_*` |
| **MESH** | 2D→3D 메쉬·GLB·VRM 프로토타입 | **`generate_hy3d_mesh`** · `process_mesh_glb` · `export_mesh_vrm` |
| **BUNDLE** | 멀티샷 묶기·QA *(옵션)* | `story_init` · `assemble_video` · `shot_qa_*` |
| **EDIT** | 컷·타이틀·믹스·룩·마스터 | **`edit_pack`** · `render_edit` · `comp_shot` · `edit_timeline` · `render_title` · `edit_qa_pack` |
| **REVIEW** | 생성물 능동 평가 | **`review_media`** · `shot_qa_*` · `edit_qa_*` |

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
