# 도구 카탈로그 — **의도 중심 공구함**

`agent_custom` = ComfyUI 미디어 **도구 모음**.  
에이전트는 **만들고 싶은 영상/컷에 맞게** 도구를 골라 조합한다.

```text
목표(영상·컷)  →  의도 고르기(§1)  →  when/when-not 확인  →  CLI 1회
              →  결과를 프로젝트로 복사  →  다음 의도
```

| 이 문서가 하는 일 | 하지 않는 일 |
|------------------|--------------|
| **능력(intent) → CLI** 매핑 | 고정 양산 공정 강제 |
| when / when not · 한계 | “무조건 CREATIVE→assemble” |
| 조합 **예시**(영감) | 모든 작업에 에피소드 레일 요구 |

**기계 인덱스:** [workflows/agent/catalog.json](../workflows/agent/catalog.json)  
**소비자 계약:** [AGENTS.md](../AGENTS.md) · [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md)  
**입구:** [TOOLS.md](../TOOLS.md)  
**의도 검색 CLI:** `python scripts/tool_intent.py "하고 싶은 일"` (Comfy 없음 · 생성 없음)

```bash
python scripts/tool_intent.py "같은 사람 유지"
python scripts/tool_intent.py search "dance reference" --limit 3
python scripts/tool_intent.py list --shelf MOTION
python scripts/tool_intent.py shelves
```

### 생성 전 실수 방지 (`failure_note`)

```text
tool_intent 검색  →  failure_note before "관련 키워드"  →  generate_*  →  FAIL 시 add
```

```bash
python scripts/failure_note.py before "freeze OR feet OR car OR framing"
python scripts/failure_note.py before   # 최근 high/critical
# FAIL / 유저 리젝 후:
# python scripts/failure_note.py add --stage keyframe --tags ... --symptom "..." --cause "..." --fix "..." --prevention "..."
```

Docs: [failure_notes_system.md](failure_notes_system.md) · Rule 7.4

---

## 0. 이용 계약 (에이전트)

| Do | Don’t |
|----|--------|
| 막히면 **`tool_intent` 검색** 또는 이 문서 선반 | 매 작업마다 `story_init` / approve 강제 |
| 목표에 맞는 **최소 도구**만 호출 | 도구를 짐작만 하고 문서/검색 스킵 |
| **생성 전** `failure_note.py before "…"` | 이전 에이전트 실패 무시하고 같은 실수 반복 |
| **FAIL 후** `failure_note.py add` | 침묵 (조직 학습 리셋) |
| `-o`로 출력 경로 명시 · 필요 시 프로젝트로 복사 | 공장 `stories/`만 최종본으로 착각 |
| 막히면 when-not · 대안 도구 · `failure_note` 검색 | 같은 도구 denoise만 무작정 상향 |
| 에피/캐릭 **패키지 헬퍼는 원할 때만** | 패키지를 모든 스틸의 전제 조건으로 |
| 스킬·자체 툴을 품질에 맞게 병행 (Rule 8) | 카탈로그에 없는 도구를 있는 척 호출 |

**cwd:** 항상 이 레포 루트 · **Comfy:** `127.0.0.1:8188`

---

## 1. 의도 선반 (30초) — 먼저 여기

### 1.A 만들고 싶은 것 → 출발 도구

| 하고 싶은 일 | 먼저 볼 CLI | 한 줄 |
|--------------|-------------|--------|
| 텍스트만으로 실사 한 장 | `generate_moody` | Lonecat T2I |
| 애니/일루스 한 장 | `generate_illustrious_standard` | XL 태그 스틸 |
| 성인 실사 한 장 | `generate_krea_nsfw` | **18+** |
| **같은 사람** 유지하며 장면 바꾸기 | `generate_character_consistent` | lock / soft / remix |
| 사진 살짝 고치기 (ID) | `generate_moody_i2i` · `…_i2i_lock` | denoise 낮게 |
| “배경만 밤으로” 문장 편집 | `generate_qwen_edit` | 전역 instruction |
| 옷·손 등 **부위만** | `generate_qwen_inpaint` | **마스크** 필수 |
| 옆/뒤 등 **각도** | `generate_qwen_angle` | multi-view |
| 포즈 맵에 맞추기 | `generate_moody_controlnet` | Fun Union CN |
| 타이틀·간판 글자 | `generate_ideogram4` | 가벼운 타이포 |
| 잡지·포스터 글자+인물 | `generate_boogu_typo` | Boogu→Ideogram→Krea |
| 스틸 → 짧은 모션 | `generate_i2v` | LTX I2V 기본 |
| **카메라 무빙 (의도 I2V)** | `generate_camera_move` | push_in / pan / idle … (Comfy I2V) |
| **아이들·루프** | `generate_idle_loop` | 대기 모션 + pingpong/roundtrip 루프 |
| **댄스/레퍼 모션** | `generate_dance_ref` | 레퍼 영상→캐릭 모션 (V2V) |
| 모션 프리셋 (I2V 옵션) | `generate_i2v --motion-preset …` | 동일 프리셋, 저수준 |
| Wan 폴백·MoE 실험 | `generate_i2v --backend wan22` · `generate_yaw_wan22` · [맵](wan22_workflow_map.md) | 에피 기본은 LTX |
| 첫·끝 프레임 이음 | `generate_flf2v` | FLF |
| 말하기·립 | `generate_s2v` · InfiniteTalk | 오디오 연동 |
| **샷 사이즈 리프레임** | `generate_reframe` | wide/MCU/CU 크롭 (Comfy 불필요) |
| **깊이·시점 과장** | `generate_viewpoint` | 하이/로우/버즈아이 (Comfy Qwen) |
| **가벼운 ID 레퍼 팩** | `generate_ref_pack` | face+각도 (패키지 없이) |
| **스타일 전이 / 레스타일** | `generate_style_transfer` | 애니·유화·무드보드 ref |
| 대사 TTS | `generate_qwen3_tts` | custom / clone |
| 스틸/영상 키우기 | **`upscale_recommend`** → `upscale_image` · `upscale_video` | 납품 해상도 · 엔진 선택 |
| **유튜브 레퍼 이해** | **`youtube_ingest`** · `youtube_highlights` | 자막·요약·하이라이트 클립 |

### 1.B 의도 선반 지도 (조합용)

```text
INGEST     밖 레퍼 가져오기        youtube_ingest · youtube_highlights
GENERATE   빈 화면 → 그림          moody · illustrious · krea* · ideogram · boogu
TRANSFORM  있는 그림 고치기         i2i · character_consistent · qwen_edit · inpaint · ref_pack · style_transfer
CAMERA     각도·포즈·시점·프레이밍   qwen_angle · viewpoint · controlnet · reframe
MOTION     그림 → 영상             camera_move · idle_loop · dance_ref · i2v · flf · s2v
VOICE      말·노래 재료            qwen3_tts · voice_register · bgm
FINISH     키우기·다듬기           upscale_recommend → upscale_* · face_enhance(실험)
ASSETS     재사용 패키지(옵션)     character_* · location_* · look_* · ref_pack(lite)
BUNDLE     여러 파일 묶기(옵션)    assemble · episode_* · story_init · qa
```

상세 카드는 **§2**. 에피소드 레일은 **§4 (옵션)**.

---

## 2. 능력 카드 (선반별)

각 카드: **언제 / 언제 말고 / CLI / 가이드**.

---

### 2.0 INGEST — 레퍼 유튜브 · 외부 자료

| CLI | 언제 | 말고 |
|-----|------|------|
| **`youtube_ingest`** | URL → 메타·자막·요약·하이라이트 패키지 | 원본 재업로드 · 이미 로컬 대본만 있을 때 |
| **`youtube_highlights`** | 패키지에서 구간 재계산·ffmpeg 클립 | 인제스트 없이 단독 검색 |

```bash
python scripts/youtube_ingest.py "https://www.youtube.com/watch?v=VIDEO" -o dumps/yt_demo
python scripts/youtube_ingest.py "URL" --whisper          # 자막 없을 때 ASR
python scripts/youtube_ingest.py "URL" --cut --max-clips 5  # 하이라이트 클립
python scripts/youtube_highlights.py -i dumps/yt_demo --cut
python scripts/tool_intent.py "유튜브 자막"
```

출력: `meta.json` · `transcript.json` · `transcript.srt` · `summary.md` · `highlights.json` · (옵션) `source.mp4` · `clips/`  
정책: **내부 레퍼·분석 전용** (재배포·원본 납품 금지).  
리서치: [youtube_ref_ingest_research.md](youtube_ref_ingest_research.md)

---

### 2.1 GENERATE — 새 스틸

#### Lonecat Z-Image (실사 기본)

| | |
|--|--|
| **언제** | 시네·인물·무드 키프레임 기본 |
| **언제 말고** | 강한 NSFW → Krea · 밀집 타이포 → Ideogram/Boogu · 애니 태그 → Illustrious |
| **CLI** | `generate_moody` · I2I는 §2.2 |
| **가이드** | [Lonecat AGENT_GUIDE](../workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md) |

```bash
python scripts/generate_moody.py -m pro -p "cinematic portrait..." -o out.png --seed 42
```

#### Illustrious Standard (애니 XL)

| | |
|--|--|
| **언제** | Illustrious/NoobAI 태그 스틸 · Face/Hand/Hires 스위치 |
| **언제 말고** | 실사 → Lonecat · 마스크 인페 → qwen_inpaint |
| **CLI** | `generate_illustrious_standard` (`--list-features`) |
| **가이드** | [illustrious_standard_v37/AGENT_GUIDE.md](../workflows/human/illustrious_standard_v37/AGENT_GUIDE.md) |

#### Krea2 (SFW/NSFW 스틸)

| | |
|--|--|
| **언제** | 언센서·성인 still · 패션/바디 |
| **언제 말고** | 일반 스토리 기본은 Lonecat · Lonecat CLIP과 혼용 금지 |
| **CLI** | `generate_krea` · **`generate_krea_nsfw`** (**18+**) |
| **가이드** | [Krea2 AGENT_GUIDE](../workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md) |

#### 타이포 · 포스터

| 도구 | 언제 | 말고 |
|------|------|------|
| `generate_ideogram4` | 가벼운 타이틀·간판 | 밀집 잡지 표지 |
| `generate_boogu_typo` | 글자+인물 잡지/포스터 | 단순 한 줄 타이틀만 |

가이드: [ideogram4](ideogram4_typography_tool.md) · [Boogu pack](../workflows/human/NEWKrea2BooguIdeogram4_AGENT_GUIDE.md)

---

### 2.2 TRANSFORM — 레퍼 기반 변형 · 편집

#### 캐릭터 일관성 (의도 오케스트레이션)

| | |
|--|--|
| **언제** | “이 사람 그대로” 장면·표정·미니 보드 |
| **언제 말고** | 장기 캐릭 패키지 양산 → `character_full_sheet` · 부위만 → inpaint |
| **CLI** | **`generate_character_consistent`** |
| **모드** | `lock`(기본) · `soft` · `remix` · `anchor` · `pack` · `angle` · `pose` |
| **가이드** | [character_consistency/AGENT_GUIDE](../workflows/human/character_consistency/AGENT_GUIDE.md) · [research](character_consistency_research.md) |

```bash
python scripts/generate_character_consistent.py --print-policy
python scripts/generate_character_consistent.py --mode lock \
  -i face.png -p "cafe table, holding cup" -o scene.png --seed 42
```

#### 스타일 전이 / 레스타일

| | |
|--|--|
| **언제** | 사진→애니/유화/코믹/누아르 · 무드보드 스타일 이미지 적용 · look 방언 |
| **언제 말고** | 매체 동일 장면 변경 → `character_consistent` · 시리즈 톤 SSOT → `looks/` |
| **CLI** | **`generate_style_transfer`** |
| **모드** | `preset` · `ref` (style image) · `look` |
| **엔진** | `qwen` 기본 · `i2i` 옵션 |
| **가이드** | [style_transfer/AGENT_GUIDE](../workflows/human/style_transfer/AGENT_GUIDE.md) · [research](style_transfer_research.md) |

```bash
python scripts/generate_style_transfer.py --list-styles
python scripts/generate_style_transfer.py --mode preset --style anime \
  -i photo.png -o out_anime.png --seed 42
python scripts/generate_style_transfer.py --mode ref \
  -i content.png --style-image mood.png -o out.png --strength hard
```

#### Lonecat I2I / lock (저수준)

| CLI | 언제 |
|-----|------|
| `generate_moody_i2i` | 직접 denoise 제어 ID 리믹스 |
| `generate_moody_i2i_lock` | identity phrase + denoise cap |
| `generate_moody_i2i_ipadapter` | 실험용 (공정 SOP 비권장) |

#### 문장 편집 · 마스크 인페

| CLI | 언제 | 말고 |
|-----|------|------|
| `generate_qwen_edit` | 영역 없이 전체 지시 편집 | 손/얼굴 **국소만** |
| `generate_qwen_inpaint` | 마스크 안만 교체 | 마스크 없이 전체 분위기 |

가이드: [Qwen InstantX Inpaint](../workflows/human/Qwen_InstantX_Inpaint_AGENT_GUIDE.md)

---

### 2.3 CAMERA — 각도 · 포즈 · 구조

| CLI | 언제 | 말고 |
|-----|------|------|
| `generate_qwen_angle` | 동일 인물 멀티뷰 턴 (앞/옆/뒤) | 하이/로우 **과장**만 → viewpoint |
| **`generate_viewpoint`** | 하이·로우·버즈/웜즈아이·와이드/타이트 히어로 (Comfy) | 크롭만 → reframe · 스타일 매체 → style_transfer |
| `generate_moody_controlnet` | 포즈/캐니 등 구조 | 얼굴 ID 단독 해결책으로 과신 |
| `character_qwen_turns` | 캐릭 패키지 안 턴 배치 | 패키지 없이 한 장만 필요 → angle |
| **`generate_reframe`** | 같은 스틸 → wide/MCU/CU 등 **샷 사이즈** (비-Comfy) | 카메라 높이를 다시 그림 → viewpoint |

```bash
python scripts/generate_viewpoint.py --list-presets
python scripts/generate_viewpoint.py -i still.png --preset low_angle -o out_low.png --seed 42
python scripts/generate_viewpoint.py -i still.png --preset birds_eye --strength hard -o top.png
```

가이드: [viewpoint/AGENT_GUIDE](../workflows/human/viewpoint/AGENT_GUIDE.md) · [research](viewpoint_research.md)

```bash
python scripts/generate_reframe.py --list-sizes
python scripts/generate_reframe.py -i key.png -s close_up -o key_cu.png --width 1080 --height 1920
python scripts/generate_reframe.py -i key.png --pack-dir out/frames
```

`character_consistent --mode angle|pose` 는 angle/CN 백엔드 래퍼.

#### 원샷 레퍼 팩 (패키지 없이)

| | |
|--|--|
| **언제** | 얼굴 1장 → master + 표정(+각도) 보드 · 이후 lock/i2v 공통 `-i` |
| **언제 말고** | 장기 SSOT → `character_full_sheet` · 한 컷만 → 바로 `character_consistent` |
| **CLI** | **`generate_ref_pack`** |
| **산출** | `manifest.json` (`primary_ref`) · contact_sheet · README |
| **가이드** | [ref_pack/AGENT_GUIDE.md](../workflows/human/ref_pack/AGENT_GUIDE.md) |

```bash
python scripts/generate_ref_pack.py --list-profiles
python scripts/generate_ref_pack.py -i face.png -o dumps/my_ref_pack --profile quick
python scripts/generate_ref_pack.py -i face.png -o dumps/my_ref_pack --profile default --seed 42
# profiles: copy | quick (I2I) | default (+1 angle) | full (3 angles)
# then: character_consistent / i2v -i <pack/primary_ref from manifest.json>
```

샷 필드 `motion_preset` 등: [toolbox_shot_fields.md](toolbox_shot_fields.md).

---

### 2.4 MOTION — 스틸 → 영상

| CLI | 언제 | 말고 / 메모 |
|-----|------|-------------|
| **`generate_camera_move`** | 카메라 무빙 의도 한 방 (push_in, pan, idle…) | 스틸 시점만 → `generate_viewpoint` · 립 → s2v |
| **`generate_idle_loop`** | 대기 모션 + **루프** (pingpong 기본 · roundtrip · idle) | 대사 립 → s2v · 스토리 카메라 → camera_move |
| **`generate_dance_ref`** | 레퍼 댄스/제스처 → 캐릭 스틸 모션 (V2V motion) | 풀 챌린지 에피 → design doc · 립 → s2v |
| **`generate_i2v`** | 일반 I2V · 자유 모션 문장 (기본 LTX) | 의도 id만 고르면 camera_move가 편함 |
| **`--ltx-profile`** | `draft`(~540) / **`work`(720p 기본)** / **`hero`(~1080)** | 배치는 work · 러프만 draft |
| **`--motion-preset`** | i2v/episode_i2v에 같은 프리셋 연결 | camera_move와 id 공유 |
| `generate_i2v --backend wan22` | LTX 폴백·카메라/텍스처 재시도 (GGUF+lightx2v) | 에피 기본 I2V 금지 · 모션 평탄할 수 있음 |
| `generate_i2v --backend wan22_flf` | Wan first+last 폴백 | 품질 FLF 본선 = LTX flf |
| **`generate_yaw_wan22`** | Wan 2.2 MoE T2V/I2V 쉬운 실 UI | 립 → s2v · 에피 본선 대체 아님 |
| **`generate_flf2v`** | 첫·끝 프레임 연결 | 단일 키프레임 모션 → i2v |
| **`generate_s2v`** | 이미지+오디오 연동 | 무음 순수 모션 → i2v |
| `generate_s2v --backend infinitetalk` | 토킹 립 품질 | VRAM·길이 계약 주의 |
| `generate_ltx23_latentheart` | Director 모듈 조합 | 단순 I2V면 generate_i2v |
| `generate_ltx23_redmix_i2v` | Krea/Ideogram 스틸 애니 | |
| `generate_ltx_nsfw_i2v` | 성인 모션 **18+** (LTX 10Eros) | SFW → 일반 i2v |
| **`generate_wan22_nsfw_i2v`** | 성인 모션 **18+** (Wan dual+lightx2v ± NSFW LoRA) | SFW → i2v · LTX 10Eros 대안 |
| `generate_v2v` | 영상→영상 의도 (experimental) | |

가이드 예: [LTX AIO](../workflows/human/LTX23_AIO_v44_AGENT_GUIDE.md) · [wan22 맵](wan22_workflow_map.md) · [wan22 pack](../workflows/human/wan22/AGENT_GUIDE.md) · [yaw_wan22](../workflows/human/yaw_wan22/AGENT_GUIDE.md) · [redmix](../workflows/human/ltx23_redmix_krea2/AGENT_GUIDE.md)  
LTX 품질: [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md) · Wan 정리: [wan22_workflow_map.md](wan22_workflow_map.md)

```bash
python scripts/generate_camera_move.py --list-presets
python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4 --seed 42
python scripts/generate_camera_move.py -i key.png --preset talk_gesture \
  -p "holding a cup" -o talk.mp4
# idle + seamless loop (pingpong)
python scripts/generate_idle_loop.py -i key.png -o idle_loop.mp4 --mode pingpong
# dance / ref motion
python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o dance_out.mp4 --hook-sec 8
python scripts/generate_dance_ref.py -i hero.png --mode i2v --style kpop -o dance_i2v.mp4
# LTX quality tiers (work default · hero for showcase)
python scripts/generate_s2v.py --list-ltx-profiles
python scripts/generate_i2v.py -i key.png --motion-preset push_in -o clip.mp4 --ltx-profile work
python scripts/generate_i2v.py -i key.png -p "gentle head turn" -o hero.mp4 --ltx-profile hero --frames 73
python scripts/generate_flf2v.py -i start.png --last end.png -p "..." -o bridge.mp4
```

가이드: [camera_move](../workflows/human/camera_move/AGENT_GUIDE.md) · [idle_loop](../workflows/human/idle_loop/AGENT_GUIDE.md) · [dance_ref](../workflows/human/dance_ref/AGENT_GUIDE.md)

---

### 2.5 VOICE · AUDIO

| CLI | 언제 |
|-----|------|
| `generate_qwen3_tts` | 대사 · 감정 instruct · clone |
| `voice_register` | 클론용 보이스 샘플 등록 |
| `generate_bgm` | 배경음 |

| TTS 모드 | 음색 | 감정 |
|----------|------|------|
| `custom` | 프리셋 화자 | `--instruct` |
| `design` | 자연어 설계 | `--instruct` |
| `clone` | ref 오디오 | 연기된 ref + instruct |

가이드: [qwen3_tts AGENT_GUIDE](../workflows/human/qwen3_tts/AGENT_GUIDE.md)

---

### 2.6 FINISH — 업스케일 · 다듬기

**먼저 고르기 (Comfy 없음):**

```bash
python scripts/upscale_recommend.py --media image --goal delivery --domain photo
python scripts/upscale_recommend.py --media video --goal hero --source blurry
python scripts/upscale_recommend.py matrix      # 성능·특징 표
python scripts/upscale_recommend.py scenarios  # 시나리오 매트릭스
```

| 축 | 값 | 의미 |
|----|-----|------|
| **media** | `image` \| `video` | 스틸 / 클립 |
| **goal** | `preview` \| `batch` \| `delivery` \| `hero` \| `master_4k` \| `face_fix` | 프리뷰·배치·납품·히어로·4K·얼굴만 |
| **domain** | `photo` \| `anime` \| `general` | ESRGAN `--style` 매핑 |
| **source** | `clean` \| `normal` \| `blurry` \| `ai_artifacts` | 복원 필요 여부 |

#### 백엔드 분류 (속도 ←→ 품질/복원)

| lane | backend | 속도 | 품질 | 복원 | 기본 용도 |
|------|---------|------|------|------|-----------|
| **FAST** | `esrgan` + `--style` | ★★★★ | ★★ | ★ | **기본** 키프레임·배치·에피 납품 |
| **SPEED** | `rtx_vsr` | ★★★★★ | ★★(클린) | ★ | optional, 클린 소스 초고속 |
| **HERO** | `seedvr2` / `seedvr2_comfy` | ★★ | ★★★★ | ★★★★ | 히어로·블러 복원 (opt-in) |
| **HERO_MAX** | `seedvr2_max` | ★ | ★★★★★ | ★★★★★ | 4K 마스터 소수 컷 |
| **FACE** | `wan22_face_enhance` | ★★★ | 얼굴 | — | I2V 후 스미어 (해상도 아님) |
| **EXPERIMENTAL** | `wan22_upscale` | ★★ | ★★★ | ★★★ | WAN 디퓨전 업스케일 opt-in |

#### 실행 CLI

| CLI | 언제 | 말고 |
|-----|------|------|
| **`upscale_recommend`** | 엔진 모름 → pick | 이미 backend 확정 |
| **`upscale_image`** | 스틸 1080–4K (`--style photo\|anime`) | 해부학 버그 수정 전 |
| **`upscale_video`** | 영상 납품 해상도 | 얼굴만 깨짐 → face_enhance 먼저 |
| `generate_wan22_face_enhance` | 얼굴 향상 **실험** | 전체 해상도 대용 |

```bash
# FAST still (default)
python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080
# Anime still
python scripts/upscale_image.py -i a.png -o a_1080.png --style anime --preset deliver_1080
# Hero still
python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080
# Video deliver / 4K two-pass
python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080
python scripts/upscale_video.py -i work.mp4 -o d4k.mp4 --backend seedvr2 --preset deliver_2160 --two-pass
```

**하드 룰:** work 해상도에서 생성 → 마감 층만 업스케일 · 구조 버그는 edit 먼저 · 배치는 esrgan · SeedVR2는 히어로.

가이드: [image_upscale_dual](../workflows/human/image_upscale_dual/AGENT_GUIDE.md) · 리서치 [upscale_research_and_design.md](upscale_research_and_design.md) · SSOT `upscale_backends.json`

---

### 2.7 ASSETS — 재사용 패키지 (**옵션**)

장기 시리즈·다컷에서 **같은 캐릭/장소**를 자산으로 쌓을 때만.

| 영역 | CLI (예) | 문서 |
|------|----------|------|
| 캐릭 | `character_create` · `cast_pool` · `promote` · `full_sheet` · `expand_sheets` | [casting](character_casting_pipeline.md) · [impl](character_impl_spec.md) |
| 장소 | `location_create` · `location_expand_sheets` | [location design](location_sheet_system_design.md) |
| 룩 | `look_create` · `look_status` | [look](look_style_system.md) |

**한 컷·실험만**이면 GENERATE/TRANSFORM만으로 충분. 패키지 필수 아님.

---

### 2.8 BUNDLE — 여러 샷 묶기 · 검수 (**옵션**)

프로젝트가 **에피소드 폴더·승인 게이트**를 쓸 때만. 도구 선택의 전제 아님.

| CLI | 기능 |
|-----|------|
| `story_init` | `stories/<ep>/` 골격 |
| `shot_compose` | 룩+캐릭+로케 → 키프레임 |
| `shot_keyframe_edit` | 키프레임 국소 수정 |
| `shot_qa_pack` / `shot_qa_record` / `shot_approve` | 열어보기 QA · 승인 |
| `episode_identity_sheet` | 크로스샷 얼굴 |
| `episode_i2v` / `episode_s2v` / `episode_tts` | 배치 모션·TTS (`episode_i2v --motion-preset` · shot.`motion_preset`) |
| `chain_one_take` / `chain_si2v_last_frame` | 컷 이음 |
| `assemble_video` | 합본 |
| `episode_subtitles` | 자막 |
| `export_episode_to_workspace` | 프로젝트 반출 |
| `episode_status` | 상태 |
| `failure_note.py` | 실패 교훈 · **`before`** 생성 전 프리플라이트 · `search`/`add` |

연출 사고(장편·뮤비 기획 시 권장 스킬): [skills/video-direction](../skills/video-direction/SKILL.md) · [generation-prompt](../skills/generation-prompt/SKILL.md)  
→ **스킬도 강제 공정이 아님.** 품질이 필요할 때 장착.

---

## 3. 조합 예시 (영감 · 비강제)

에이전트가 **따라 할 수도, 무시할 수도** 있는 패턴.

| 목표 | 가능한 조합 |
|------|-------------|
| 인물 쇼츠 1컷 | `moody` 또는 `character_consistent lock` → `generate_i2v` |
| 같은 캐릭 여러 장면 | `cc lock` × N → (선택) `assemble_video` |
| 토킹 헤드 | 스틸 → `qwen3_tts` → `generate_s2v` |
| 각도 먼저 고르기 | `qwen_angle` 또는 `cc pack` → 고른 장으로 lock/i2v |
| 전신 포즈 | `controlnet` + 전신 레퍼 → i2v |
| 텍스트 훅 | `ideogram4` / `boogu_typo` → (선택) i2v |
| 장기 시리즈 | ASSETS 패키지 → compose/cc → motion → (선택) BUNDLE |

```text
빠른 결정 트리
  레퍼 얼굴 있음 + 장면 변경?  → character_consistent / i2i_lock
  레퍼 없음 + 한 장?          → moody / illustrious / krea
  부위만?                    → qwen_inpaint (+ mask)
  문장으로 전체?              → qwen_edit
  각도?                      → qwen_angle
  포즈 구조?                 → controlnet
  움직이기?                  → i2v  (말하기면 s2v)
  여러 파일 한 영상?          → assemble (원할 때)
```

---

## 4. 공통 주의

| 항목 | 내용 |
|------|------|
| **cwd** | `agent_custom` 루트에서 `python scripts/...` |
| **Comfy** | `127.0.0.1:8188` · 런처 SSOT `run_nvidia_gpu.bat` (data: `F:\ComfyUI_data`) |
| **18+** | `krea_nsfw` · `ltx_nsfw_*` · `wan22_nsfw_i2v` |
| **VRAM** | OOM 시 짧은 클립 · GGUF · 엔진 free |
| **출력** | `-o` 권장 · 프로젝트 작업이면 **복사/export** |
| **실 UI 도구** | 미니그래프 재작성 금지 · 문서화된 포트/스위치만 |
| **프롬프트** | 품질 필요 시 [generation_prompt_craft.md](generation_prompt_craft.md) |

---

## 5. 제공 측 유지 규칙 (메인터)

새 능력을 넣을 때:

1. `workflows/human/<name>/` + AGENT_GUIDE (가능하면)  
2. `scripts/generate_*.py` (또는 명확한 CLI)  
3. **이 카탈로그 §1 표 + §2 카드** (의도 선반에 배치)  
4. `workflows/agent/catalog.json`  
5. **`lib/tool_intent.py` INTENT_TOOLS** — examples[] + alternatives[]  
6. 스모크 1회 + `process.md` 한 줄  

카드 필수 필드 (표준: [toolbox_card_standard.md](toolbox_card_standard.md)):

| 필드 | 내용 |
|------|------|
| when / when not | 언제 · 언제 말고 |
| **eg 한 줄** | 복붙 가능한 `python scripts/…` |
| **alternatives** | 실패·부적합 시 if → cli 한 줄 |
| 가이드 링크 | AGENT_GUIDE |

프로젝트 에이전트는 §5를 수행하지 않음 — **§0~§3 + tool_intent** 만 읽고 고르면 됨.

---

## 6. 관련 인덱스

| 문서 | 역할 |
|------|------|
| [TOOLS.md](../TOOLS.md) | 초단 입구 |
| [catalog.json](../workflows/agent/catalog.json) | 기계 인덱스 |
| [video_backends.json](../video_backends.json) | I2V 백엔드 메타 |
| [docs/README.md](README.md) | docs 전체 지도 |
| [failure_notes_system.md](failure_notes_system.md) | 실패 공유 |
| [agent_native_capability_autonomy.md](agent_native_capability_autonomy.md) | 자체 툴 병행 Rule 8 |
