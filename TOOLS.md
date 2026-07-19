# TOOLS — 프로젝트 에이전트 입구

이 레포는 **ComfyUI 미디어 공구함**입니다.  
정형 영상 양산 공정이 **아닙니다.**

에이전트는 **만들고 싶은 영상/컷**에 맞춰 도구를 **자유롭게 고르고 조합**합니다.

```text
목표  →  tool_intent 검색 또는 tool_catalog 선반  →  CLI 1회  →  결과 복사  →  다음 의도
```

### 빠른 검색 (의도 → CLI)

```bash
python scripts/tool_intent.py "얼굴 유지하면서 장면 바꿔"
python scripts/tool_intent.py search "camera push in" --json
python scripts/tool_intent.py list --shelf MOTION
python scripts/tool_intent.py shelves

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
| **GENERATE** | 빈 화면 → 그림 (**기본: Krea2**) | `generate_krea` · `generate_krea_nsfw` · `generate_moody` · `generate_illustrious_standard` |
| **TRANSFORM** | 같은 인물·편집·스타일 | `generate_character_consistent` · `generate_style_transfer` · `generate_qwen_edit` · `generate_qwen_inpaint` |
| **CAMERA** | 각도·포즈·시점·프레이밍 | `generate_qwen_angle` · `generate_viewpoint` · `generate_moody_controlnet` · `generate_reframe` |
| **MOTION** | 영상 모션 · 카메라 · 아이들/루프 · 댄스 레퍼 | `generate_camera_move` · `generate_idle_loop` · `generate_dance_ref` · `generate_i2v` · `generate_s2v` |
| **TRANSFORM+** | 가벼운 ID 팩 | `generate_ref_pack` · `generate_character_consistent` |
| **VOICE** | 대사·BGM | `generate_qwen3_tts` · `generate_bgm` |
| **INGEST** | 유튜브 레퍼 이해 | `youtube_ingest` · `youtube_highlights` |
| **FINISH** | 업스케일 (먼저 추천) | `upscale_recommend` · `upscale_image` · `upscale_video` |
| **ASSETS** | 캐릭/로케 패키지 *(옵션)* | `character_*` · `location_*` |
| **BUNDLE** | 멀티샷 묶기·QA *(옵션)* | `story_init` · `assemble_video` · `shot_qa_*` |

전체 표·카드·조합 예: **tool_catalog §1–§3**.

---

## 어떻게 쓰나

```bash
# 레포 루트에서
python scripts/<도구>.py ... -o <원하는_경로>
```

1. 목표에 맞는 **선반** 고르기  
2. **when / when not** 확인  
3. CLI 실행 · 결과 검수  
4. 프로젝트 작업이면 **워크스페이스로 복사**

에피소드 패키지·approve·assemble은 **필요할 때만** (카탈로그 §2.8).

---

## 역할 분담

| 이 레포 (제공) | 프로젝트 에이전트 (소비) |
|----------------|--------------------------|
| 워크플로 · CLI · 카탈로그 | 목표에 맞는 도구 **선택·조합** |
| 스모크 · 가이드 유지 | 호출 · 검수 · **자기 프로젝트에 반영** |
| catalog 갱신 | 스토리·파이프라인·납품은 **프로젝트 쪽** |
