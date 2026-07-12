# 오디오 · 모션 드라이버 · 프로덕션 모드 설계

- **작성일**: 2026-07-11  
- **상태**: 설계 확정 / 구현 단계적  
- **관련**: [storyboard_pipeline_design.md](storyboard_pipeline_design.md), [commission_workflow.md](commission_workflow.md), [video_delivery_and_backends.md](video_delivery_and_backends.md), [video_pipeline_roadmap.md](video_pipeline_roadmap.md)

---

## 0. 한 줄 결론

소리는 “나중에 BGM 한 줄”이 아니다.  
**프로덕션 모드(작품 종류)** × **샷 모션 드라이버(그 컷을 무엇으로 움직이느냐)** × **믹스 정책(줄기를 언제 합치느냐)** 세 축으로 다룬다.

| 축 | 단위 | 예 |
|----|------|-----|
| `production_mode` | 에피소드/수주 | `music_video`, `story`, `hybrid` |
| `motion_driver` | 샷 | `i2v`, `si2v`, `still`, (나중 `flf2v`) |
| `mix_policy` | 에피소드 | `music_locked`, `dialogue_sfx_first_bgm_late`, `video_only` |

업스케일 기본은 **RTX VSR** 유지. SeedVR2는 히어로 opt-in (본 문서 범위 밖).

---

## 1. 프로덕션 모드

### 1.1 `music_video`

| 항목 | 정책 |
|------|------|
| 마스터 오디오 | 클라이언트/제공 **music master** 가 타임라인 SSOT |
| 길이 | 원곡(또는 편집본) 길이에 영상 구간을 맞춤 |
| 일반 컷 | `motion_driver=i2v` — 키프레임 + 모션 프롬프트 |
| 립·퍼포 컷 | `motion_driver=si2v` — 키프레임 + **해당 구간 오디오 슬라이스** |
| 믹스 | `mix_policy=music_locked` — 최종에 master 정렬. “BGM 후깔”이 아님 |
| BGM 필드 | `audio/masters/` 또는 `audio/music/` 의 지정 파일 |

```text
music master
  → beat/section markers (수동 또는 툴)
  → shots with t_in/t_out on master
  → per shot: i2v | si2v(audio slice)
  → upscale (rtx_vsr)
  → timeline align + music master mux
```

### 1.2 `story` (드라마·스토리 숏폼)

| 항목 | 정책 |
|------|------|
| 대사 | 온스크린 캐릭터 말 → `dialogue` stem (+ 필요 시 SI2V 입력) |
| VO | 오프 내레이션 → `vo` stem (보통 립싱크 불필요) |
| SFX | 장면 효과·앰비언스 → `sfx` stem, 샷 큐 또는 글로벌 |
| BGM | **후반 침대** 가능 — 생성 입력이 아닐 수 있음 |
| 일반 컷 | `i2v` |
| 말하는 컷 | `si2v` (권장) 또는 `i2v` + 후입 립(품질 낮음) |
| 믹스 | `mix_policy=dialogue_sfx_first_bgm_late` |

```text
synopsis / shots.json
  → keyframes
  → dialogue/vo assets (녹음 or TTS — 나중)
  → per shot: i2v | si2v
  → sfx bed
  → (optional) bgm late
  → stem mix → final
```

### 1.3 `hybrid`

광고·예능·뮤비+내레이션 혼재.  
샷마다 `motion_driver`와 `audio_refs`를 명시. 에피소드 `mix_policy`는 기본 `layered` 또는 커스텀.

### 1.4 `video_only` (레거시/테스트)

오디오 없음. 현재 mina_cafe 파일럿과 동일. `mix_policy=video_only`.

---

## 2. 샷 모션 드라이버

### 2.1 정의

| `motion_driver` | 필수 입력 | 출력 | 비고 |
|-----------------|-----------|------|------|
| **`i2v`** | keyframe, motion_prompt | 무음(또는 무시) work clip | **현재 구현됨** (`episode_i2v` / wan22) |
| **`si2v`** (S2V) | keyframe, **audio segment**, (opt) text | 립/제스처↔소리 클립 | **✅ `generate_s2v` / `episode_s2v`** |
| **`still`** | keyframe | duration hold | Ken Burns 선택 |
| **`flf2v`** | first + last keyframe | 브리지 | 나중 |

에피소드 배치 CLI는 향후:

```text
episode_motion.py  (가칭)
  for shot in approved:
    if driver == i2v:  episode_i2v path
    if driver == si2v: episode_s2v path
    if driver == still: ffmpeg still
```

과도기: `episode_i2v` 는 `motion_driver in (i2v, null, missing)` 만 처리.  
`si2v` 샷은 스킵 + status `needs_s2v`.

### 2.2 SI2V 백엔드 (예정)

| 항목 | 방향 |
|------|------|
| 설정 위치 | `video_backends.json` → `backends.s2v_*` 또는 `motion_backends` 섹션 |
| 상태 | `planned` until workflow in `workflows/agent/` |
| CLI | `scripts/generate_s2v.py` (I2V 대칭) |
| 입력 오디오 | `audio_refs.driving` → 파일 + `start_sec`/`end_sec` 또는 full file |
| Work res | I2V와 동일 — format work preset, **W/H %16==0** |

엔진 후보(로컬 확정 시 문서 갱신): Wan S2V 계열 / Comfy talking-head 노드 등.  
**미보유 시 스키마·폴더·믹스만 선행**, 러너는 stub.

### 2.3 샷 필드 (확장)

```json
{
  "shot_id": "S04",
  "motion_driver": "si2v",
  "duration_sec": 3.2,
  "dialogue": "오늘도 같은 자리네.",
  "audio_refs": {
    "driving": {
      "path": "audio/dialogue/S04.wav",
      "start_sec": 0,
      "end_sec": null,
      "role": "dialogue"
    },
    "sfx": [
      { "path": "audio/sfx/cup_clink.wav", "at_sec": 1.2, "gain": 0.8 }
    ]
  },
  "motion_prompt": "natural speech, subtle head motion, eye contact",
  "negative_motion": "warp, identity morph, desync mouth"
}
```

- `dialogue` / `vo` / `sfx` / `music_cue`: **서술·큐 텍스트** (사람·에이전트 가독)  
- `audio_refs`: **실제 파일 바인딩** (도구 SSOT)

---

## 3. 오디오 줄기(stem) 레이아웃

```text
stories/<episode>/audio/
  masters/     # 뮤비 원곡·클라이언트 풀 믹스 (music_locked)
  music/       # BGM 침대 (story late bed 또는 masters 별칭)
  dialogue/    # 캐릭터 대사 웨이브
  vo/          # 내레이션
  sfx/         # 효과·앰비언스 라이브러리/샷 파일
  beds/        # (선택) 사전 믹스 앰비언스 루프
  exports/     # 중간 stem bounce (dialogue+sfx 등)
```

| stem | 폴더 | 믹스 역할 |
|------|------|-----------|
| master_music | masters/ or music/ | music_locked 시 최종 기준 |
| dialogue | dialogue/ | 스토리 대사 |
| vo | vo/ | 내레이션 |
| sfx | sfx/ | 효과 |
| bgm | music/ | late bed, 볼륨 낮게 |

**납품**: `deliveries/` 에 final 뿐 아니라 옵션으로 stems zip (재믹스용) — P3.

---

## 4. 믹스 정책 (`mix_policy`)

| policy | 동작 |
|--------|------|
| **`video_only`** | 영상 concat만. 오디오 없음 |
| **`music_locked`** | concat 영상 + master 정렬 (`-shortest` 또는 music 길이 기준 패드/트림 정책 명시). 샷 내장 오디오는 보통 mute (SI2V 결과 오디오를 쓸지 정책 플래그 `use_clip_audio`) |
| **`bgm_under`** | 레거시: 단일 BGM under (현재 `assemble_video --bgm`) |
| **`dialogue_sfx_first_bgm_late`** | dialogue+vo+sfx 합 → (opt) bgm 낮은 볼륨 under |
| **`layered`** | 샷 타임라인에 맞춘 큐 배치 (amix + adelay) — P1~P2 |

### 4.1 SI2V 클립 오디오

SI2V 출력에 드라이빙 오디오가 포함된 경우:

- `use_clip_audio=true` (샷 또는 에피소드): concat 시 클립 오디오 유지, 별도 dialogue stem과 **이중 깔림 주의**  
- 기본 권장: SI2V는 **모션만** 쓰고 오디오는 stem에서 한 번만 (또는 클립 오디오를 dialogue stem으로 승격)

정책 필드: `episode.audio.use_clip_audio` default `false` for music_video, `true` optional for story si2v.

---

## 5. 에피소드 JSON 계약

`shots.json` 루트 확장:

```json
{
  "episode_id": "…",
  "format": "cinematic_16x9",
  "production_mode": "story",
  "mix_policy": "dialogue_sfx_first_bgm_late",
  "audio": {
    "master": null,
    "bgm": "audio/music/bed.mp3",
    "bgm_volume": 0.28,
    "use_clip_audio": false,
    "dialogue_volume": 1.0,
    "sfx_volume": 0.85
  },
  "default_motion_driver": "i2v",
  "default_backend_i2v": "wan22",
  "default_backend_s2v": null,
  "shots": [ … ]
}
```

commission brief 동일 필드 optional. 없으면:

| production_mode | default mix_policy | default_motion_driver |
|-----------------|--------------------|------------------------|
| music_video | music_locked | i2v |
| story | dialogue_sfx_first_bgm_late | i2v |
| hybrid | layered | i2v |
| video_only / null | video_only | i2v |

---

## 6. 파이프라인 위치

```text
commission (mode + mix_policy)
  → assets (char/loc/look)
  → shot_compose / approve
  → [audio prep: place masters/dialogue/sfx files]
  → episode_motion (i2v | si2v | still)   ← 현재 episode_i2v 만
  → episode_upscale (rtx_vsr default)
  → assemble (mix_policy)
  → package_delivery
```

`episode_status.overall_next` 확장 (구현 시):

- clips ready + mix_policy needs audio missing → `audio_assets`  
- si2v shots without driving audio → `audio_driving`  
- else assemble / package

---

## 7. 구현 계획 (단계)

### P0 — 계약 + 조립 기초 ✅

| ID | 작업 | 산출 |
|----|------|------|
| A0.1 | 본 설계 문서 | `docs/audio_motion_production_modes.md` |
| A0.2 | schema + template 폴더 | shots/commission schema, `audio/dialogue|masters` |
| A0.3 | `lib/audio_package.py` | mode defaults, stem path resolve, list assets |
| A0.4 | `ffmpeg_util` stem mix + assemble 정책 분기 | video_only / bgm_under / music_locked / simple layered |

### P1 — 샷 오디오 바인딩 ✅ (부분)

| ID | 작업 | 상태 |
|----|------|------|
| A1.1 | `audio_refs` resolve (rel path under episode) | ✅ `collect_timeline_events` |
| A1.2 | assemble `layered`: 샷 offset + sfx at_sec + atrim | ✅ `mix_timeline_under_video` |
| A1.3 | `scripts/audio_status.py` | ✅ |
| A1.3b | `scripts/audio_slice.py` 마스터 구간 추출 | ✅ |
| A1.4 | package_delivery optional STEMS/ | ⬜ 다음 |
| A1.5 | music_locked 실측 (소나기 master → ~12s final) | ✅ AAC 포함 |

### P2 — SI2V

| ID | 작업 | 상태 |
|----|------|------|
| A2.0 | 로컬 인벤토리: InfiniteTalk patches, wav2vec2-korean, WanVideoAddS2VEmbeds | ✅ 확인 |
| A2.1 | 로컬 S2V 워크플로 → `workflows/agent/` | ⬜ API inject 러너로 대체 (JSON 스냅샷 선택) |
| A2.2 | `video_backends` s2v 항목 (`infinitetalk`, `wan_s2v` planned) | ✅ |
| A2.3 | `generate_s2v.py` scaffold + dry-run plan meta | ✅ |
| A2.4 | episode_i2v: skip si2v shots | ✅ |
| A2.5 | Comfy API inject InfiniteTalk + 실측 스모크 | ✅ ~5s audio / 640² / 20step |
| A2.6 | `audio_prepare_driving` (center/voicey/vocal_band) | ✅ FFmpeg 폴백 (MelBand 아님) |
| A2.7 | `episode_s2v` 배치 + pipeline `s2v` stage | ✅ |
| A2.8 | 클린 VO / center_voicey 품질 QA | ✅ 실측 (process.md) |

### P3 — 생성형 오디오 (선택)

| ID | 작업 |
|----|------|
| A3.1 | TTS 어댑터 (대사 → dialogue wav) |
| A3.2 | SFX 라이브러리 인덱스 |
| A3.3 | 뮤비 beat marker 보조 툴 |

---

## 8. 에이전트 규칙 (요약)

1. **모드를 먼저 정한다.** 뮤비와 스토리를 같은 `assemble --bgm`으로 퉁치지 말 것.  
2. **립싱크 컷 = SI2V 드라이버.** I2V 후 입만 맞추기는 최후 수단.  
3. **대·SFX·음악 stem 분리.** 최종 납품 전 한 번만 믹스 (이중 트랙 방지).  
4. **music_locked** 에서 제공곡이 타임라인 SSOT.  
5. **story** 에서 BGM은 기본 late bed; 없어도 대사+SFX면 조립 가능해야 함.  
6. 업스케일은 **rtx_vsr** 기본; 오디오와 무관.

---

## 9. 로컬 SI2V 인벤토리 (2026-07-11)

| 항목 | 경로/노드 |
|------|-----------|
| InfiniteTalk patches | `models/model_patches/Wan2_1-InfiniteTalk-Multi_fp16.safetensors`, `…Single…` |
| wav2vec (KO) | `models/audio_encoders/wav2vec2-korean-base_fp16.safetensors` |
| 노드 | `WanVideoAddS2VEmbeds`, `WanInfiniteTalkToVideo`, MultiTalk*, FantasyTalking* |
| 예제 | `ComfyUI-WanVideoWrapper/example_workflows/*InfiniteTalk*` |
| 테스트 음원 | `D:\뮤직비디오 작업\소나기\소나기mastered.wav` (~202.16s) |
| 슬라이스 예 | `audio_slice.py --start 38 --duration 3.2` → dialogue stem |

**실측:** `music_locked` + 소나기 master → mina 12.2s final **video+aac OK**.  

**SI2V live (프레임 육안 QA 포함):**

| 버전 | 파일 | 판정 |
|------|------|------|
| v1 | `S02_s2v_smoke.mp4` | 파이프 OK. **립싱크 불량** (손 등장·표정 붕괴) |
| v2 | `S02_s2v_smoke_v2.mp4` | identity 안정↑, 입 개폐 약함. **정밀 립싱크는 여전히 미달** |
| v3 | `S02_s2v_smoke_v3_clean_vo.mp4` | **클린 TTS VO 5s** + master_front + voicey. 입 개폐 대비 기준 |
| v4 | `S02_s2v_smoke_v4_center_voicey.mp4` | 소나기 slice **center_voicey** stem (FFmpeg mid+speech EQ) |

**드라이빙 준비 CLI:** `python scripts/audio_prepare_driving.py -i mix.wav -m center_voicey -o drive.wav`  
모드: `copy` / `voicey` / `center` / `vocal_band` / `center_voicey`.

주의: **exit 0 ≠ 립싱크 합격**. 풀 믹스 음원·보컬 미분리 시 약함.  
권장 순서: (1) 클린 dialogue/VO → (2) FFmpeg center_voicey → (3) MelBand/demucs 보컬 stem (미설치 시 후순위).

---

## 10. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안: production_mode / motion_driver / mix_policy / stems / P0–P3 계획 |
| 2026-07-11 | P1 layered + audio_slice; 소나기 music_locked 스모크; generate_s2v scaffold |
| 2026-07-12 | prepare_driving + episode_s2v + pipeline s2v; clean VO / center_voicey QA |
