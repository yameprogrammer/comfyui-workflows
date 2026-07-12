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

### 0.1 SI2V(립싱크)는 스토리 전용이 아니다

`motion_driver=si2v` 는 **온스크린에서 입이 소리를 내는 모든 컷**에 쓴다. 장르를 가리지 않는다.

| 작품 | SI2V를 쓰는 컷 | 드라이빙 오디오 예 |
|------|----------------|-------------------|
| **`music_video`** | 보컬이 카메라 앞에서 **노래·후렴·랩** 하는 퍼포 컷 | master 구간 슬라이스 → (권장) 보컬 stem / `center_voicey` |
| **`story`** | 캐릭터가 **대사**를 말하는 컷 | `audio/dialogue/` 녹음·TTS |
| **`hybrid`** | 뮤비 보컬 구간 + 내레이션·대사 혼재 시 해당 샷만 | 샷별 `audio_refs.driving` |

| 작품 | SI2V **안** 쓰는 컷 (보통 `i2v` / `still`) |
|------|---------------------------------------------|
| 뮤비 B-roll, 풍경, 손·소품, 춤만(입 닫힘), 비트 연출 | |
| 스토리 와이드, 리액션(무대사), VO-only(입 안 움직임) | |

**금지 오해:** “SI2V = story 대사 전용 기능” ❌  
**정답:** SI2V = **립·보컬·스피치 구동 모션 드라이버**. 뮤비 중간 보컬 클로즈업/미디엄도 1급 유스케이스.

---

## 1. 프로덕션 모드

### 1.1 `music_video`

| 항목 | 정책 |
|------|------|
| 마스터 오디오 | 클라이언트/제공 **music master** 가 타임라인 SSOT |
| 길이 | 원곡(또는 편집본) 길이에 영상 구간을 맞춤 |
| 일반 컷 | `motion_driver=i2v` — 키프레임 + 모션 프롬프트 (풍경·춤·B-roll·비트 연출) |
| **보컬·립 퍼포 컷** | `motion_driver=si2v` — 키프레임 + **그 구간의 노래 슬라이스(보컬 우선)** |
| 믹스 | `mix_policy=music_locked` — 최종에 master 정렬. “BGM 후깔”이 아님 |
| BGM 필드 | `audio/masters/` 또는 `audio/music/` 의 지정 파일 |

뮤비에서 SI2V가 필요한 전형 연출:

- 후렴 직캠/클로즈업 보컬
- 버스킹·카페 창가에서 **노래를 부르는** 미디엄
- 듀엣 한 명만 입이 움직이는 구간 (다른 명은 `i2v` 또는 still)

```text
music master
  → beat/section markers (수동 또는 툴)
  → shots with t_in/t_out on master
  → vocal-on-camera shots: si2v(slice ± vocal prep)
  → other shots: i2v | still
  → upscale (rtx_vsr)
  → timeline align + music master mux  (SI2V 클립 오디오는 보통 mute)
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
| **`si2v`** (S2V) | keyframe, **audio segment**, (opt) text | 립/제스처↔소리 클립 | **✅ `generate_s2v` / `episode_s2v`** — **story 대사 + music_video 보컬 공통** |
| **`still`** | keyframe | duration hold | Ken Burns 선택 |
| **`flf2v`** | first + last keyframe | 브리지 | 나중 |

배치 CLI:

```text
episode_i2v.py   → motion_driver=i2v
episode_s2v.py   → motion_driver=si2v   (스토리 대사 컷 · 뮤비 보컬 컷 동일 경로)
episode_pipeline … i2v → s2v → upscale …
```

`episode_i2v` 는 non-i2v 스킵, `episode_s2v` 는 non-si2v 스킵.

### 2.2 SI2V 백엔드

| 백엔드 ID | 상태 | 엔진 | 비고 |
|-----------|------|------|------|
| **`ltx23_ia2v`** | ✅ **default** | LTX 2.3 distilled GGUF + **custom audio** AV latent | 속도 우위. Custom-Audio IA2V |
| **`infinitetalk`** | ✅ **ready (1급 대안)** | **Wan 2.1 I2V** + InfiniteTalk | `center_voicey` 시 립 동기 **실용 수준** 진입 (v4 사용자 육안). **폐기 금지** |
| `ltx23_lipdub` | ⬜ blocked | LTX IC-LoRA LipDub (V2V) | 공식 립더빙. **gated HF** |
| `wan_s2v` | ⬜ planned | WanVideoAddS2VEmbeds | — |

#### 백엔드 선택 휴리스틱 (에이전트)

| 상황 | 권장 |
|------|------|
| 기본 / 빠른 배치 / 뮤비 보컬 컷 | **`ltx23_ia2v`** |
| LTX 손·의상 드리프트, 얼굴 클로즈업 고정 우선 | **`infinitetalk`** |
| 클린 VO 톡킹 헤드 | 둘 다 OK → 먼저 LTX, 불만 시 IT |
| 품질 비교 | 같은 이미지·driving으로 **양쪽 생성 후 육안** |

> **메모 (2026-07-12):**  
> `S02_s2v_smoke_v4_center_voicey(_playable).mp4` — InfiniteTalk + 소나기 **center_voicey**  
> 사용자 육안: **입이 제법 맞기 시작**. Wan/InfiniteTalk 스택은 임시 실험이 아니라 **후속 프로덕션 후보**.  
> (I2V 베이스 = 로컬 **Wan2.1** 14B Q4 + InfiniteTalk 패치. 일반 모션용 Wan2.2 A14B 와는 별 트랙.)

| 항목 | 상태 |
|------|------|
| SSOT | `video_backends.json` (`default_backend_s2v` = ltx23_ia2v) |
| CLI | `generate_s2v.py --backend …`, `episode_s2v.py --backend …` |
| 입력 오디오 | `audio_refs.driving` (+ `audio_bind_driving`) |
| 드라이빙 prep | `center_voicey` 등; 클립 출력은 48 kHz stereo 정규화 |
| Work res | IT: %16; LTX: %32 |
| 검수 | VS Code 미리보기는 무음처럼 보일 수 있음 → **OS 미디어 플레이어** |

```bash
python scripts/generate_s2v.py --backend ltx23_ia2v   -i face.png -a drive.wav -o ltx.mp4
python scripts/generate_s2v.py --backend infinitetalk -i face.png -a drive.wav -o it.mp4
```

### 2.3 샷 필드 — **story 대사** 예

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

### 2.4 샷 필드 — **music_video 보컬 퍼포** 예

```json
{
  "shot_id": "S07",
  "motion_driver": "si2v",
  "duration_sec": 4.0,
  "music_cue": "chorus A — on-camera vocal",
  "dialogue": "",
  "audio_refs": {
    "driving": {
      "path": "audio/exports/s2v_drive/chorus_A_vocal.wav",
      "start_sec": 0,
      "end_sec": null,
      "role": "vocal"
    }
  },
  "motion_prompt": "singing to camera, natural lip motion, subtle head sway, cinematic music video",
  "negative_motion": "warp, identity morph, closed mouth while singing, desync mouth"
}
```

준비 파이프 (뮤비) — **권장 원샷**:

```bash
# master 구간 → prepare → 샷에 si2v + driving 바인딩
python scripts/audio_bind_driving.py -e <ep> --shot S07 \
  --start 38 --duration 4 --prepare-mode center_voicey \
  --motion "singing to camera, natural lip motion, cinematic music video"

python scripts/episode_s2v.py -e <ep> --shots S07
# 기본 백엔드 ltx23_ia2v; 대안: --backend infinitetalk
```

수동 단계(슬라이스/prep 분리)도 가능: `audio_slice` + `audio_prepare_driving` + `shot_edit`.

- `dialogue` / `vo` / `sfx` / `music_cue`: **서술·큐 텍스트** (사람·에이전트 가독)  
- `audio_refs.driving`: **립을 움직일 실제 음원** (대사 wav **또는** 뮤비 보컬/슬라이스 — 역할 동일)

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
| master_music | masters/ or music/ | music_locked 시 최종 기준 (뮤비 원곡) |
| dialogue | dialogue/ | 스토리 **대사** wav (SI2V driving 후보) |
| vo | vo/ | 내레이션 (보통 립 불필요) |
| sfx | sfx/ | 효과 |
| bgm | music/ | story late bed, 볼륨 낮게 |
| s2v_drive | exports/s2v_drive/ | **SI2V 전용 드라이빙** (뮤비 보컬 slice·prep, 캐시) — 최종 믹스 SSOT는 아님 |

뮤비 보컬 슬라이스를 편의상 `dialogue/` 에 넣어도 동작은 하지만, **역할이 대사가 아니므로** `exports/s2v_drive/` 또는 별도 명명(`…_vocal.wav`)을 권장.

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

- **music_video + music_locked**: 최종 사운드는 **항상 music master**. SI2V 클립 오디오는 기본 **mute** (`use_clip_audio=false`). 드라이빙 슬라이스는 입 모션용일 뿐, 납품 트랙이 아님.  
- **story**: `use_clip_audio=true` 가능하나, dialogue stem과 **이중 깔림 주의**. 기본 권장도 “모션만 SI2V + 오디오는 stem 한 번”.  
- 정책 필드: `episode.audio.use_clip_audio` default **`false` for music_video**, optional for story.

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
2. **온스크린 입·보컬 컷 = SI2V.** story 대사 **와** music_video 보컬 퍼포 **모두**. I2V 후 입만 맞추기는 최후 수단.  
3. **뮤비 SI2V driving ≠ 납품 오디오.** driving은 슬라이스/보컬 stem; 최종은 music master (`music_locked`).  
4. **대·SFX·음악 stem 분리.** 최종 납품 전 한 번만 믹스 (이중 트랙 방지).  
5. **music_locked** 에서 제공곡이 타임라인 SSOT.  
6. **story** 에서 BGM은 기본 late bed; 없어도 대사+SFX면 조립 가능해야 함.  
7. 업스케일은 **rtx_vsr** 기본; 오디오와 무관.

---

## 9. 로컬 SI2V 인벤토리 (2026-07-11)

| 항목 | 경로/노드 |
|------|-----------|
| InfiniteTalk patches | `models/model_patches/Wan2_1-InfiniteTalk-Multi_fp16.safetensors`, `…Single…` |
| wav2vec (KO) | `models/audio_encoders/wav2vec2-korean-base_fp16.safetensors` |
| 노드 | `WanVideoAddS2VEmbeds`, `WanInfiniteTalkToVideo`, MultiTalk*, FantasyTalking* |
| 예제 | `ComfyUI-WanVideoWrapper/example_workflows/*InfiniteTalk*` |
| 테스트 음원 | `D:\뮤직비디오 작업\소나기\소나기mastered.wav` (~202.16s) |
| 슬라이스 예 | `audio_slice.py --start 38 --duration 3.2` → 뮤비 보컬 구간 (s2v_drive / dialogue) |

**실측:** `music_locked` + 소나기 master → mina 12.2s final **video+aac OK**.  

**SI2V live (프레임 육안 QA 포함):**

| 버전 | 파일 | 판정 |
|------|------|------|
| v1 | `S02_s2v_smoke.mp4` | 파이프 OK. **립싱크 불량** (손 등장·표정 붕괴) |
| v2 | `S02_s2v_smoke_v2.mp4` | identity 안정↑, 입 개폐 약함. **정밀 립싱크는 여전히 미달** |
| v3 IT | `S02_s2v_smoke_v3_clean_vo.mp4` | **클린 TTS VO 5s** + master_front + voicey. 입 개폐 대비 기준 |
| v4 IT | `S02_s2v_smoke_v4_center_voicey.mp4` (+ `_playable`) | 소나기 **center_voicey**. **사용자 육안: 립이 제법 맞기 시작 → IT 유지 후보** |
| LTX v1 | `S02_s2v_ltx_v1_clean_vo.mp4` | 클린 VO + LTX. 입·표정 다양, ~1–2min/5s |
| LTX v2 | `S02_s2v_ltx_v2_center_voicey.mp4` | center_voicey + LTX |

**드라이빙 준비 CLI:** `python scripts/audio_prepare_driving.py -i mix.wav -m center_voicey -o drive.wav`  
모드: `copy` / `voicey` / `center` / `vocal_band` / `center_voicey` / (옵션) `demucs` if installed.

주의: **exit 0 ≠ 립싱크 합격**. 풀 믹스 음원·보컬 미분리 시 약함.  
권장 순서: (1) 클린 dialogue/VO → (2) FFmpeg center_voicey → (3) demucs/MelBand 보컬 stem.

---

## 10. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안: production_mode / motion_driver / mix_policy / stems / P0–P3 계획 |
| 2026-07-11 | P1 layered + audio_slice; 소나기 music_locked 스모크; generate_s2v scaffold |
| 2026-07-12 | prepare_driving + episode_s2v + pipeline s2v; clean VO / center_voicey QA |
| 2026-07-12 | SI2V = story 대사 **및** music_video 보컬 퍼포 1급 유스케이스 명시 (§0.1, §2.4) |
| 2026-07-12 | IT v4 center_voicey 사용자 QA: 립 실용 수준 진입 → infinitetalk 1급 대안 유지 기록 |
| 2026-07-12 | prepare mode `demucs` 옵션 훅 (패키지 있으면 보컬 stem; 없으면 center_voicey 폴백 안내) |
