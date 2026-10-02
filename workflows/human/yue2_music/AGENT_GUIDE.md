# YuE2 — Agent Guide & Official Features

> **Official Backend:** `Comfy-Org/YuE2` (M·A·P YuE2-3B Transformer + SheetSage2 Audio Encoder)  
> **Shelf:** VOICE / MUSIC  
> **Specialty:** Full-length vocal songs & music cover rearrangement (up to 6 minutes / 360s) via ABC symbolic notation.  
> **License:** Apache 2.0 / CC-BY-NC 4.0  

---

## 1. 개요 및 핵심 특징 (Core Innovations)

YuE2는 기존의 블랙박스형 음악 생성 모델(Suno, Udio 계열)과 달리 **음악적 기호 추론(Symbolic Music Chain-of-Thought)**을 결합한 차세대 오픈소스 음악 파운데이션 모델입니다.

1. **ABC 표기법 기반 작곡 계획 (ABC Notation Planning)**:
   - 오디오를 바로 생성하기 전에, 먼저 음악의 멜로디와 화성 진행을 표준 **ABC 기호 악보**로 계획 및 생성합니다.
   - 멜로디의 프레이징, 마디 구조, 코드 진행(`[C]`, `[Am]`, `[G7]` 등)의 음악적 개연성을 극대화합니다.
2. **SheetSage2 기반 음악 커버 (Music Cover / Transcribe)**:
   - 기존 음원(보컬/멜로디 트랙)을 `SheetSage2` 인코더가 자동으로 ABC 악보로 채보(Transcribe)합니다.
   - 원곡의 멜로디 골격을 유지하면서 완전히 새로운 장르, 악기 편성, 보컬 스타일로 재편곡(Cover)할 수 있습니다.
3. **최대 360초 (6분) 풀 트랙 생성**:
   - 인트로-벌스-코러스-브릿지-아웃트로를 아우르는 완곡 생성을 단일 패스로 처리합니다.
4. **로컬 최적화 (INT8 ConvRot)**:
   - 24GB VRAM(RTX 4090) 환경에서 VRAM 부담 없이 실시간에 가까운 고속 추론을 지원합니다.

---

## 2. 프롬프트 작성 가이드 (Prompt Dialect Guide)

YuE2는 **Style (스타일)**과 **Lyrics (구조화 가사)** 두 개의 프롬프트 축으로 동작합니다.

### A. Style 프롬프트 구성 (콤마 구분 자연어)
스타일 프롬프트는 5가지 핵심 요소를 포함할 때 가장 완성도가 높습니다:

1. **보컬 특성 (Vocal Qualities)**:
   - `female vocals`, `male vocals`, `clear bright tone`, `raspy soulful delivery`, `airy harmonies`
   - 보컬 없는 연주곡일 경우: `instrumental only, no vocals`
2. **장르 및 서브장르 (Genre & Subgenre)**:
   - `emotional pop ballad`, `synthwave 80s pop`, `k-pop dance`, `city pop`, `acoustic indie folk`, `melodic lofi hip-hop`, `hard rock`
3. **악기 편성 (Instrumentation)**:
   - `grand piano`, `acoustic guitar strumming`, `warm analog synthesizers`, `deep 808 bass`, `punchy drum kit`, `lush string section`
4. **템포 및 분위기 (Tempo & Mood)**:
   - `slow tempo 72 bpm, melancholic, intimate`, `upbeat 128 bpm, energetic, joyful, groovy`
5. **사운드 프로덕션 (Production/Space)**:
   - `intimate room reverb`, `polished modern studio mix`, `warm vintage cassette tape saturation`

> **추천 예시 (Pop Ballad)**:
> `"female vocals, emotional Korean pop ballad, grand piano, acoustic guitar, gentle strings, intimate room acoustics, slow tempo 76 bpm, melancholy, polished modern studio production"`

---

### B. Lyrics 가사 태그 구성 (Executable Section Tags)
가사는 구조 태그를 반드시 **독립된 줄**에 대괄호 `[ ]`로 작성해야 모델이 송폼(Song Form)을 인식합니다:

- `[Intro]` : 전주 (악기 도입부)
- `[Verse]` / `[Verse 1]` / `[Verse 2]` : 절 (이야기 전개)
- `[Pre-Chorus]` : 후렴 전 고조 구간
- `[Chorus]` : 메인 후렴구
- `[Bridge]` : 분위기 반전 구간
- `[Solo]` : 악기 솔로 구간
- `[Outro]` : 마무리 후주

**간주 및 연주 지시어**:
- 가사 사이에 괄호 `(piano solo)`, `(electric guitar riff)`, `(drum break)` 등을 넣으면 해당 구간의 연주 표현이 자연스러워집니다.
- 한국어, 영어, 일본어 등 다국어 가사를 자연스럽게 가창합니다.

---

## 3. 실행 모드 및 ABC Planning 선택 기준

| 모드 | 인자 | 역할 | 권장 상황 |
| :--- | :--- | :--- | :--- |
| **Text to Music (Full ABC)** | `--mode text2music --abc-mode full` | 멜로디 + 코드 기호 동시 생성 후 합성 | **기본 추천**. 풀 밴드, 팝, 발라드 완곡 작곡 |
| **Text to Music (Melody ABC)** | `--mode text2music --abc-mode melody` | 단선율 멜로디 악보만 계획 | 단순 보컬 솔로, 민요, 동요, 어쿠스틱 독주 |
| **Text to Music (Direct / Off)** | `--mode text2music --no-abc-planning` | ABC 기호 계획 생략, 오디오 토큰 직행 | 빠른 스케치, 추상적 앰비언트 사운드스케이프 |
| **Music Cover** | `--mode cover -i ref.mp3 --abc-mode melody` | SheetSage2로 음원 멜로디 채보 ➔ 신규 스타일 편곡 | **기존 곡 리메이크 / 커버 / 장르 변경** |

---

## 4. 모델 배치 경로 (ComfyUI Models)

```text
ComfyUI/models/
├── checkpoints/
│   └── yue2_3b_int8_convrot.safetensors   # (3.77 GB) 기본 체크포인트
└── audio_encoders/
    └── sheetsage2_bf16.safetensors        # (1.32 GB) 커버 모드 오디오 인코더
```

---

## 5. CLI 도구 사용법 (`generate_yue2_music.py`)

에이전트는 작업 공간(`F:\Agent_media_tools`)에서 아래 CLI를 실행합니다.

### 1) 텍스트로부터 신규 완곡 작곡 (Text to Music)
```bash
python scripts/generate_yue2_music.py \
  --style "female vocals, emotional pop ballad, grand piano, acoustic guitar, 75 bpm" \
  --lyrics "[Intro]\n(piano melody)\n\n[Verse]\n창밖에 스며든 불빛 사이로...\n\n[Chorus]\n다시 부르는 이 노래 속에\n\n[Outro]\n(fading piano)" \
  --duration 120 \
  -o workspace/ballad_song.flac
```

### 2) 기존 음원을 새로운 장르로 편곡 커버 (Music Cover)
```bash
python scripts/generate_yue2_music.py \
  --mode cover \
  -i "D:/Music/original_voice.mp3" \
  --style "acoustic jazz lounge, smooth saxophone, upright bass, brushed drums, relaxed 85 bpm" \
  --lyrics "[Verse]\n원곡 가사 또는 개사 가사..." \
  --duration 150 \
  -o workspace/jazz_cover.flac
```

### 3) 무보컬 — 악보를 고친 뒤 렌더 (2026-10-02)

가사 빈 문자열은 보컬을 끄지 않는다. 악보와 곡을 한 호출로 만들지 않는다. 상세는 볼트 `decisions/yue2_instrumental_pipeline.md`.

```bash
python scripts/generate_yue2_music.py --plan-only \
  --style-file style.txt --lyrics-file sections.txt \
  --seed 20261074 -o score.abc

python scripts/generate_yue2_music.py \
  --abc-file score_muted.abc \
  --style-file style.txt --lyrics-file sections.txt \
  --duration 200 --seed 20261074 -o track.flac
```

스타일에 언어·가수·`no vocals`를 넣지 않는다. 가사 파일은 `[intro]` `[verse]` `[chorus]` `[bridge]` `[chorus]` `[outro]`만, 태그 사이는 빈 줄. 노래 성부를 쉼표로 바꾸는 일은 에이전트가 `score.abc`를 본 뒤에 한다. 천장은 3분보다 위(약 200초). 출력 길이가 천장과 같으면 잘린 엔딩이다.

개인 창작자의 생성물 수익화는 `MODEL_LICENSE` 2026-09-16 추가 허가에 포함된다. 제3자 인스트루멘탈 LoRA는 수익용 곡에 쓰지 않는다. 스템 분리로 보컬을 지우지 않는다.

### 4) 권장 샘플링 파라미터 (Knobs)
- `--steps`: **32** (공식 템플릿 표준)
- `--cfg`: **1.0** (YuE2의 CFG는 토큰 오토리그레시브 단계에서 처리되므로 확산 KSampler CFG는 1.0 유지)
- `--sampler`: **`dpm_2`**
- `--scheduler`: **`sgm_uniform`**
