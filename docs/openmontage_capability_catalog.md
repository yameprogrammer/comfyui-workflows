# OpenMontage 기능 카탈로그 · agent_custom 연동 지도

- **작성일**: 2026-07-12  
- **상태**: **카탈로그 READY** · **본선 파이프 공식 연동 ❌** (참고·선택 이식)  
- **위치**:
  - `OpenMontage/` — 얇은 클론 (마케팅/부분 lib)
  - **`OpenMontage_full/`** — 풀 소스 카탈로그 대상 ([calesthio/OpenMontage](https://github.com/calesthio/OpenMontage))
- **관련**: [openmontage_eval_notes.md](openmontage_eval_notes.md) · [agent_rules.md](../agent_rules.md) Rule 7.1 · [assemble_video / episode_pipeline](../scripts/README.md)

---

## 0. 한 줄 정책 (에이전트)

```text
본선 생성·납품 = agent_custom (Comfy + scripts/)
OpenMontage_full  = 참고 monorepo / 아이디어 소스 / (선택) 로컬 도구 직접 호출
전체 파이프 대체·이중 지휘 금지
```

| 해도 됨 | 하지 말 것 |
|---------|------------|
| 기능 목록 보고 “이런 게 있다” 안내 | OpenMontage로 episode_pipeline 대체 |
| 유용 조각을 agent_custom에 **얇게 이식** 제안 | 클라우드 Kling/Veo를 기본 생성 경로로 전환 |
| FFmpeg 계열·자막·믹스·QA 패턴 참고 | avatar lip-sync로 LTX/IT SI2V 폐기 |
| Remotion/HyperFrames는 **별 프로젝트** 검토 | monorepo 전체를 git 제품 트리에 커밋 |

**연동 정의 상태:**  
공정 SOP(어느 단계에서 어떤 OM 도구를 호출)는 **아직 없음**. 이 문서는 **목록 + 유용도 라벨**만 고정한다.

### 유용도 라벨

| 라벨 | 의미 |
|------|------|
| **A 이식 후보** | agent_custom 본선에 곧 붙이면 이득 (로컬·우리 스택과 충돌 적음) |
| **B 참고** | 아이디어·스키마·프롬프트만 참고 |
| **C 중복** | 우리가 이미 더 깊게 가짐 → 호출 비권장 |
| **D 비본선** | 클라우드/타사 API 중심, 또는 무거운 Node 스택 — 별도 프로젝트 |
| **E 비권장** | 정책 충돌 (이중 립스택, 전체 오케스트레이션 대체 등) |

---

## 1. 레포 큰 덩어리

| 영역 | 경로 | 역할 | 유용도 |
|------|------|------|--------|
| **Tools** | `tools/` | Python BaseTool — 실제 실행 단위 | 혼합 (아래 상세) |
| **Skills** | `skills/` | 에이전트 지시 MD (파이프 스테이지·크리에이티브) | B |
| **Agent skills (번들)** | `.agents/skills/` | HyperFrames, Remotion, LTX2, ACE-Step, 클라우드 비디오 등 | B/D |
| **Pipelines** | `pipeline_defs/*.yaml` | 장르별 제작 파이프 매니페스트 | B |
| **Schemas** | `schemas/` | brief, script, edit_decisions, video_stitch 등 JSON schema | B |
| **Lib** | `lib/` | slideshow_risk, delivery_promise, media_profiles, scoring… | **A**/B |
| **Remotion composer** | `remotion-composer/` | React 자막·토킹헤드·콜라주 렌더 | D |
| **Backlot** | `backlot/` | 브라우저 스토리보드/런 보드 UI | D |
| **Ink theater** | `ink-theater/` | 잉크 드로잉·모캡 캐릭 애니 | D |
| **Styles playbook** | `styles/*.yaml` | 비주얼 스타일 프리셋 | B |
| **Comfy 브리지** | `tools/_comfyui/` | 얇은 Comfy 클라이언트 + wan/flux 샘플 WF | C (우리 comfy_client가 본선) |

---

## 2. 파이프라인 정의 (`pipeline_defs/`)

장르 템플릿 — **우리 commission/episode 와 병렬 개념**, 직접 호출 안 함.

**레시피별 긴 설명·스테이지·우리와의 관계:**  
→ **[openmontage_pipeline_recipes.md](openmontage_pipeline_recipes.md)**

| YAML | 용도 | 유용도 |
|------|------|--------|
| `talking-head.yaml` | 토킹헤드 | B |
| `cinematic.yaml` | 시네마틱 | B |
| `clip-factory.yaml` | 롱→숏 클립 공장 | **A** 아이디어 (숏폼 리퍼포즈) |
| `documentary-montage.yaml` | 다큐 몽타주 | B |
| `podcast-repurpose.yaml` | 팟캐스트 재가공 | B |
| `localization-dub.yaml` | 더빙·로컬라이즈 | B |
| `avatar-spokesperson.yaml` | 아바타 대변인 | E (립 스택 중복) |
| `character-animation.yaml` | 캐릭 애니 | B |
| `animation.yaml` / `animated-explainer.yaml` | 애니·설명 | D (Manim/HyperFrames) |
| `screen-demo.yaml` | 스크린 데모 | B |
| `hybrid.yaml` | 혼합 | B |
| `framework-smoke.yaml` | 스모크 | — |

스테이지 스킬 패턴 (공통): idea / research / script / scene / asset / compose / edit / publish / executive-producer 등 디렉터 MD.

---

## 3. Tools 카탈로그 (`OpenMontage_full/tools/`)

### 3.1 Video 편집·조립 — 쇼츠 후반에 가장 관련

| 도구/모듈 | 기능 | 유용도 | agent_custom 대응 |
|-----------|------|--------|-------------------|
| `video/video_stitch.py` | 클립 스티치 | **A** 참고 | `assemble_video.py` (본선) |
| `video/video_compose.py` | 세로/가로 컴포즈 | **A** 참고 | format SSOT + assemble |
| `video/video_trimmer.py` | 트림 | **A** | ffmpeg_util / 수동 |
| `video/silence_cutter.py` | 무음 컷 | **A** | 없음 → 후보 |
| `video/auto_reframe.py` | 자동 리프레임 | **A** | 없음 → 9:16 리프레임 후보 |
| `video/remotion_caption_burn.py` | 자막 번인 | **A**/D | 자막 약함 → 후보 |
| `video/hyperframes_compose.py` | HTML→영상 컴포즈 | D | 없음 |
| `video/green_screen_*` | 크로마키 | B | 없음 |
| `video/showcase_card.py` | 쇼케이스 카드 | B | package_delivery 일부 |
| `video/clip_cache.py` / `clip_search.py` | 클립 캐시·검색 | B | 없음 |
| 클라우드 video (`kling_`, `sora_`, `veo_`, `runway_`, `minimax_`, `seedance_`, `heygen_`, `grok_video`, `gemini_omni_`, `cogvideo_`, `hunyuan_`, `wan_video`, `ltx_video_*`) | 외부 생성 | **C/D** | **본선 = 로컬 Comfy I2V/SI2V** |
| `video/comfyui_video.py` | OM 쪽 Comfy 비디오 | C | `generate_i2v` / `episode_*` |
| `video/stock_sources/*` | B-roll 스톡 (Pexels, NASA, Mixkit…) | **A** (B-roll 필요 시) | 없음 |

### 3.2 Analysis · QA

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `analysis/scene_detect.py` | 장면 검출 | **A** | 롱폼 컷 분해 |
| `analysis/frame_sampler.py` | 프레임 샘플 | **A** | 립/연속 육안 보조 |
| `analysis/visual_qa.py` | 비주얼 QA | **A** | episode_qa 보강 아이디어 |
| `analysis/composition_validator.py` | 구도 검증 | B | |
| `analysis/audio_probe.py` / `audio_energy.py` | 오디오 프로브 | **A** | spill/무음 검수 |
| `analysis/face_tracker.py` | 얼굴 추적 | B | |
| `analysis/transcriber.py` / `dashscope_asr.py` | 전사 | **A** | 자막 전단계 |
| `analysis/video_analyzer.py` / `video_understand.py` | 영상 이해 | B | 레퍼런스 분석 |
| `analysis/video_downloader.py` | 다운로드 | B | |
| `lib/slideshow_risk.py` | “슬라이드쇼 티” 위험 | **A** | 납품 게이트 이식 1순위 |
| `lib/delivery_promise.py` | 납품 약속/검수 | **A** | |
| `lib/source_media_review.py` | 소스 푸티지 리뷰 | B | |
| `lib/variation_checker.py` | 변형 일관성 | B | |
| `lib/verify_scene_pacing.py` | 페이싱 | B | |

### 3.3 Audio · TTS · Music

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `audio/audio_mixer.py` | 덕킹·loudnorm·세그먼트 BGM | **A** | assemble mix_policy 보강 참고 |
| `audio/audio_enhance.py` | 오디오 향상 | B | |
| `audio/music_gen.py` / `music_library.py` | 음악 생성·라이브러리 | C/B | 우리 `episode_bgm` / ACE |
| `audio/*_tts.py`, `tts_selector.py` | 다공급자 TTS | C | 우리 Qwen3-TTS 본선 |
| `audio/pixabay_music.py` 등 | 스톡 음악 | B | BGM 폴백 아이디어 |
| `.agents/skills/acestep` | ACE-Step 스킬 | C | 우리 generate_bgm과 겹침 |

### 3.4 Subtitle

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `subtitle/subtitle_gen.py` | 자막 생성 | **A** | 숏폼 자막 약점 보완 1순위 |
| skills: `subtitle-sync`, `whisperx` | 싱크·전사 | **A** | |

### 3.5 Enhancement

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `enhancement/upscale.py` | 업스케일 | C | `upscale_video` / rtx_vsr 본선 |
| `enhancement/face_restore.py` / `face_enhance` / `eye_enhance` | 얼굴 복원 | B | 선택 후처리 |
| `enhancement/color_grade.py` | 컬러 그레이드 | B | look 코어와 역할 분리 주의 |
| `enhancement/bg_remove.py` | 배경 제거 | B | |

### 3.6 Avatar · Character (주의)

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `avatar/lip_sync.py` | Wav2Lip 계열 립 | **E** | SI2V(LTX/IT) 와 이중 스택 |
| `avatar/talking_head.py` | 토킹헤드 | E/D | |
| `character/character_animation.py` | 캐릭 애니 | B | 우리 character sheet 공정과 별개 |

### 3.7 Graphics · Image gen

| 도구 | 기능 | 유용도 | 메모 |
|------|------|--------|------|
| `graphics/image_gen.py` + selectors | 다공급자 이미지 | C/D | Moody T2I/I2I 본선 |
| `graphics/comfyui_image.py` | Comfy 이미지 | C | |
| `graphics/diagram_gen.py` / `math_animate.py` / `code_snippet.py` | 다이어그램·수식 | D | 설명 영상용 |
| stock image adapters | Pexels/Pixabay… | B | |

### 3.8 Capture · Publish

| 도구 | 기능 | 유용도 |
|------|------|--------|
| `capture/screen_recorder.py` 등 | 스크린 캡처 | B |
| `publishers/export_bundle.py` | 납품 번들 | **A** 참고 → `package_delivery` |

### 3.9 Comfy 브리지

| 경로 | 기능 | 유용도 |
|------|------|--------|
| `tools/_comfyui/client.py` | Comfy API | C |
| `workflows/wan22-i2v-4step.json` 등 | 샘플 WF | B (레시피 참고만) |

---

## 4. Skills 요약 (`skills/` + `.agents/skills/`)

### 4.1 Core / Creative (편집 감각)

| 스킬 | 내용 | 유용도 |
|------|------|--------|
| `core/ffmpeg.md` | FFmpeg 패턴 | **A** 참고 |
| `core/subtitle-sync.md` / `whisperx.md` | 자막 | **A** |
| `core/remotion.md` / `hyperframes.md` | 모션 그래픽 런타임 | D |
| `core/color-grading.md` | 그레이드 | B |
| `creative/video-editing.md` / `video-stitching.md` | 편집·스티치 SOP | **A** 참고 |
| `creative/short-form.md` | 숏폼 | **A** 참고 |
| `creative/sound-design.md` | 사운드 | B |
| `creative/lip-sync-usage.md` | 립 | E (경로 다름) |
| `creative/upscale-usage.md` | 업스케일 | C |
| `creative/*-prompting.md` | 벤더 프롬프트 | B |
| `meta/reviewer.md` / `checkpoint-protocol.md` | 검수·체크포인트 | **A** 아이디어 |
| `meta/video-reference-analyst.md` | 레퍼런스 영상 분석 | **A** |

### 4.2 HyperFrames / Remotion / 모션 그래픽 (번들)

`.agents/skills/`: `hyperframes*`, `remotion*`, `motion-graphics`, `music-to-video`, GSAP/Three.js 등 — 전부 **D** (Node·별 런타임).  
숏폼 자막·타이포가 필요할 때만 **별 프로젝트**로 검토.

### 4.3 클라우드 비디오 스킬

`ai-video-gen`, `seedance-2-0`, `gemini-omni`, `create-video`, `avatar-video` 등 — **D/C**. 본선 생성 경로로 쓰지 않음.

---

## 5. agent_custom 쇼츠에 “이런 게 있다” 치트시트

지금 에피소드(`cafe_gomin` 류) 기준으로 **열어볼 가치**:

| 니즈 | OpenMontage에 있는 것 | 당장 권장 |
|------|----------------------|-----------|
| 클립 이어붙이기 | `video_stitch`, skills/video-stitching | **본선 `assemble_video`** 유지; OM은 패턴 참고 |
| 대사 덕킹·믹스 | `audio_mixer` (duck/loudnorm) | BGM 살릴 때 **A 이식 후보** |
| 숏폼 자막 | `subtitle_gen`, remotion_caption_burn | **A** — 유튜브 쇼츠 자막 |
| 무음 구간 정리 | `silence_cutter` | **A** |
| 납품 전 “슬라이드쇼 티” | `slideshow_risk` | **A** → episode_qa 규칙 |
| 레퍼런스 쇼츠 분석 | video-reference-analyst + scene_detect | **A** 기획 단계 |
| 9:16 리프레임 | `auto_reframe` | 가로 소스 있을 때 **A** |
| 싱글테이크 이음 | (없음 — FLF는 우리 로드맵) | **우리** `docs/flf2v_f2f_roadmap.md` |
| 립싱크 | avatar lip_sync / 클라우드 | **우리 SI2V** (IT/LTX) |
| BGM | music_gen / acestep skill | **우리 episode_bgm** |

---

## 6. 호출 방법 (공식 연동 전 · 수동)

OpenMontage는 자체 `BaseTool` + registry 중심이라 **agent_custom `python scripts/...` 와 동일 진입점이 아니다.**

가능한 수준:

1. **문서·스킬만 읽기** — 경로 `OpenMontage_full/skills/...`  
2. **모듈 단위 실험** — `OpenMontage_full` 를 cwd/PYTHONPATH로 두고 개별 tool 스크립트 실행 (의존성: `requirements.txt`, 키, Node 등 **별도 설치**)  
3. **아이디어 이식** — 로직을 `agent_custom/scripts` 또는 `lib` 로  thrift 이식 후 본선 CLI화  

```text
# 예: 문서만
OpenMontage_full/skills/creative/short-form.md
OpenMontage_full/lib/slideshow_risk.py

# 예: 이식 우선순위 (제안)
1 slideshow_risk / delivery_promise 아이디어 → episode_qa
2 subtitle_gen 패턴 → scripts/episode_subtitles.py (신규)
3 audio_mixer ducking → assemble mix_policy 보강
```

**체크리스트 (OM 도구를 만지기 전)**

- [ ] 본선 키프레임·I2V/SI2V가 agent_custom에 있는가?  
- [ ] OM 호출이 클라우드 기본 경로로 새지 않는가?  
- [ ] 결과물을 작업대(`export_episode_to_workspace`)로 가져왔는가?  

---

## 7. 비범위 · 금지

- OpenMontage **전체 파이프**로 `story_init → shot_compose → episode_*` 대체  
- monorepo를 agent_custom 배포 산출물에 포함 (gitignore 유지)  
- FLF/F2F를 OM에 있다고 오해 — **그 로드맵은 우리 문서** (`flf2v_f2f_roadmap.md`)  
- Wav2Lip/SadTalker 계열을 SI2V 본선으로 승격  

---

## 8. 다음 액션 (선택 · 미착수)

| # | 액션 | 상태 |
|---|------|------|
| 1 | 본 카탈로그 유지 | ✅ |
| 2 | slideshow_risk 아이디어 → `episode_qa` 규칙 초안 | ⬜ |
| 3 | 자막 thin wrapper (`episode_subtitles`) | ⬜ |
| 4 | assemble 덕킹 보강 (audio_mixer 참고) | ⬜ |
| 5 | Remotion 자막 — 별 레포 검토 | ⬜ |
| 6 | **공식 연동 SOP** (`openmontage_integration` 단계 정의) | ⬜ 아직 정의 안 함 |

---

## 9. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초안. 풀 클론 tools/skills/pipelines 목록화 + agent_custom 유용도 라벨. 공식 연동 미정의 명시. |
