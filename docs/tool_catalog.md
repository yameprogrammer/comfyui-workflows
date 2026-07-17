# 도구 카탈로그 — 프로젝트 에이전트용 선택 가이드

**이 레포 역할:** ComfyUI 미디어 **도구를 제공**한다.  
**프로젝트 에이전트 역할:** 자기 프로젝트 목표에 맞게 **도구를 읽고 선택·호출**한다.

```text
1) 이 문서에서 역할 맞추기
2) “언제 씀 / 안 씀” 확인
3) CLI 한 줄 실행 (레포 루트 cwd)
4) 결과가 필요하면 프로젝트 폴더로 복사
```

| 이 문서 | 아님 |
|---------|------|
| 워크플로별 **기능·쓰는 법·한계** | 고정 양산 파이프라인 강제 |
| 현명한 **선택 기준** | “무조건 CREATIVE→assemble” |

- **기계 인덱스:** [workflows/agent/catalog.json](../workflows/agent/catalog.json)  
- **백엔드 메타:** [video_backends.json](../video_backends.json)  
- **소비자 계약:** [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md) · [AGENTS.md](../AGENTS.md)

---

## A. 30초 매트릭스 (먼저 여기)

| 하고 싶은 일 | 도구 CLI | 한 줄 |
|--------------|----------|--------|
| 일반 인물/무드 스틸 | `generate_moody` | Lonecat Z-Image turbo T2I |
| **애니/일루스 XL 스틸** | `generate_illustrious_standard` | Standard_V37 · Face/Hand/I2I/Hires 스위치 |
| 빨간맛 스틸 | `generate_krea_nsfw` | Krea2 + abliterated CLIP · **18+** |
| 사진 유지하며 살짝 바꾸기 | `generate_moody_i2i` | denoise 낮게 (ID 유지) |
| 포즈/구조 맞추기 | `generate_moody_controlnet` | Fun Union CN |
| 문장으로 전체 편집 | `generate_qwen_edit` | “배경만 바꿔” |
| **부위만** 고치기 | `generate_qwen_inpaint` | **마스크** + InstantX |
| 캐릭 각도 여러 장 | `generate_qwen_angle` | multi-view |
| 타이틀/간판 글자 (가벼움) | `generate_ideogram4` | Ideogram4 단독 |
| **잡지·포스터** 글자+인물 | `generate_boogu_typo` | Boogu→Ideogram→Krea |
| 영상 모션 (품질 기본) | `generate_i2v` | LTX AIO I2V |
| **Wan 2.2 T2V/I2V (YAW MoE)** | `generate_yaw_wan22` | 실 UI · GGUF · green T2V/I2V 스위치 |
| 첫·끝 프레임 연결 | `generate_flf2v` | LTX flf |
| 이미지+오디오→립/연동 | `generate_s2v` | LTX aio / InfiniteTalk |
| 빨간맛 영상 클립 | `generate_ltx_nsfw_i2v` | Kenpechi · **18+** |
| 감정·복제 TTS | `generate_qwen3_tts` | custom / clone / design |
| 보이스 샘플 등록 | `voice_register` | `voices/<id>/` |

상세 플래그·모델은 아래 카드 또는 `*_AGENT_GUIDE.md`.

---

## B. 이미지 도구

### B1. Lonecat Z-Image — 일반 스틸 / I2I

| 항목 | 내용 |
|------|------|
| **기능** | T2I, I2I(identity), lock, IPAdapter, ControlNet |
| **CLI** | `generate_moody` · `generate_moody_i2i` · `generate_moody_i2i_lock` · `generate_moody_i2i_ipadapter` · `generate_moody_controlnet` |
| **언제** | 키프레임·캐릭 스틸·무드컷 기본 |
| **언제 말고** | 강한 NSFW still → Krea NSFW · 밀집 타이포 → Boogu/Ideogram |
| **핵심 플래그** | `-p` prompt · `-i` image · `-d` denoise · `--seed` · size |
| **가이드** | [Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md](../workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md) |

```bash
python scripts/generate_moody.py -p "cinematic portrait..." -o out.png
python scripts/generate_moody_i2i.py -i face.png -p "holding cup" -d 0.52 -o out.png
```

---

### B2. Krea2 — SFW/NSFW 스틸

| 항목 | 내용 |
|------|------|
| **기능** | Krea2 turbo T2I · abliterated CLIP (SFW+NSFW 동일 그래프) |
| **CLI** | `generate_krea` · **`generate_krea_nsfw`** (18+ 정책) |
| **언제** | 언센서/성인 still · 패션·바디 표현 |
| **언제 말고** | 일반 스토리 키프레임 기본은 Lonecat 권장 · Lonecat CLIP과 혼용 금지 |
| **가이드** | [Krea2_SFW_NSFW_v10_AGENT_GUIDE.md](../workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md) |

```bash
python scripts/generate_krea_nsfw.py -p "adult woman, ..." -o out.png --seed 42
```

---

### B3. Qwen Edit — 전역 지시 편집

| 항목 | 내용 |
|------|------|
| **기능** | 자연어로 이미지 **전체** 편집 (GGUF UNet 기본) |
| **CLI** | `generate_qwen_edit` |
| **언제** | “배경을 밤으로”, “옷을 코트로”처럼 **영역 지정 없이** 고칠 때 |
| **언제 말고** | 손·얼굴 **국소만** → `generate_qwen_inpaint` |
| **핵심** | `-i` · `-p` instruction · `--no-lightning` (품질) |

---

### B4. Qwen InstantX Inpaint — 마스크 인페인트

| 항목 | 내용 |
|------|------|
| **기능** | 마스크 안만 재생성 + 마스크 밖 원본 composite |
| **CLI** | **`generate_qwen_inpaint`** |
| **언제** | 옷/소품/손 등 **지정 부위** 교체 |
| **언제 말고** | 마스크 없이 전체 분위기 변경 → qwen_edit |
| **핵심** | `-i` image · `--mask` (흰=편집) · `-p` · 기본 GGUF (`--gguf-light` 저VRAM) |
| **주의** | 마스크가 얼굴을 덮으면 얼굴이 깨짐 · 마스크·프롬프트 부위 일치 필수 |
| **가이드** | [Qwen_InstantX_Inpaint_AGENT_GUIDE.md](../workflows/human/Qwen_InstantX_Inpaint_AGENT_GUIDE.md) |

```bash
python scripts/generate_qwen_inpaint.py -i photo.png --mask torso_mask.png \
  -p "blue denim jacket..." -o out.png --gguf-light
```

---

### B5. Qwen Multi-Angle

| 항목 | 내용 |
|------|------|
| **기능** | 캐릭 멀티뷰 / 각도 턴 |
| **CLI** | `generate_qwen_angle` · `character_qwen_turns` |
| **언제** | 동일 인물 여러 방향 시트 |

---

### B6. Ideogram4 — 단독 타이포

| 항목 | 내용 |
|------|------|
| **기능** | Ideogram 4 T2I · 구조화 캡션 · 타이틀/간판 슬롯 |
| **CLI** | `generate_ideogram4` |
| **언제** | 가벼운 타이틀 카드·메뉴·간판 |
| **언제 말고** | 밀집 글자+인물 잡지 표지 풀 파이프 → `generate_boogu_typo` |
| **가이드** | [ideogram4_typography_tool.md](ideogram4_typography_tool.md) |

```bash
python scripts/generate_ideogram4.py --slot title_card --text "에피소드 제목" --aspect 9:16 -o title.png
```

---

### B7. Boogu + Ideogram4 + Krea2 — 타이포·잡지 파이프

| 항목 | 내용 |
|------|------|
| **기능** | Boogu(밀집 글자) → Ideogram 다듬기 → Krea2 실사 폴리시 · 옵션 SeedVR2 |
| **CLI** | **`generate_boogu_typo`** |
| **모드** | `boogu` 초안 · `pipeline` 기본 체인 · `upscale` +SeedVR2 |
| **언제** | **잡지 표지·포스터·광고**처럼 글자+인물+레이아웃 |
| **프롬프트** | **산문** 권장 (`exactly reading LUXE`). JSON 키 이름을 그대로 넣으면 글자로 찍힘 |
| **가이드** | [NEWKrea2BooguIdeogram4_AGENT_GUIDE.md](../workflows/human/NEWKrea2BooguIdeogram4_AGENT_GUIDE.md) |
| **출처** | [Civitai collection](https://civitai.red/models/579280?modelVersionId=3066747) |

```bash
python scripts/generate_boogu_typo.py --mode pipeline --prefer krea2 \
  -p "High fashion magazine cover, masthead text exactly reading LUXE, ..." \
  -o cover.png --seed 88
```

---

### B8. Illustrious Standard_V37 — XL/Illustrious/NoobAI 애니 스틸

| 항목 | 내용 |
|------|------|
| **출처 목적** | Legendaer **“Workflow for XL/Illustrious/NoobAI Models”** — 애니·일러 체크포인트용 모듈형 생성 툴 |
| **팩 위치** | 🟦 **Standard** = Advanced의 축소판(일상 메인). 🟥Advanced 풀기능 · 🟩Detailer(기존 이미지 후처리/인·아웃페)는 **별 JSON** |
| **기능 (Standard)** | 실 UI 스위치: T2I·I2I·LoRA·Wildcards·Detail Enhancers(Face/Hand/Eyes…)·HiresFix·Ultimate SD Upscale(Canny)·Color Match·VPred·Signature·Post FX |
| **CLI** | **`generate_illustrious_standard`** |
| **언제** | Illustrious/NoobAI 태그 스틸 · Clip Skip 2 · Fabricated XL 등 · 디테일/하이레스 옵션 |
| **언제 말고** | 실사 Z-Image → Lonecat · 마스크 인페 → qwen_inpaint · TIPO/IPA/OpenPose/Regional → **Advanced** · 기존 컷 인/아웃페 전문 → **Detailer** |
| **쓰는 법** | Danbooru+quality 태그 → `t2i_face` 1차 → 손/눈/hires 스위치 추가 (`--list-features`) |
| **기본** | Face ADetailer ON · 1024×1536 · `fabricatedXL_v70` · Clip Skip 2 |
| **원칙** | **출처 목적 유지** · **미니그래프 금지** · 실 UI 그룹 mode + 포트 |
| **가이드** | [illustrious_standard_v37/AGENT_GUIDE.md](../workflows/human/illustrious_standard_v37/AGENT_GUIDE.md) |
| **출처** | [Civitai 1386234](https://civitai.red/models/1386234/comfyui-image-workflows) · [Guide article](https://civitai.red/articles/17339) |

```bash
python scripts/generate_illustrious_standard.py --list-features
python scripts/generate_illustrious_standard.py -p "masterpiece, best quality, 1girl, solo, portrait" \
  -o out.png --seed 42
python scripts/generate_illustrious_standard.py --preset t2i_clean -p "1girl, ..." -o out.png
python scripts/generate_illustrious_standard.py -i ref.png -d 0.55 -p "winter coat" -o i2i.png
python scripts/generate_illustrious_standard.py -p "..." --hand --eyes --hires-post -o out.png
```

---

## C. 영상 도구

### C1. LTX 2.3 AIO — SFW 모션 기본

| 항목 | 내용 |
|------|------|
| **기능** | I2V / FLF / FML / V2V / T2V ± 오디오 (`[[P:]]` 스위치) |
| **CLI** | `generate_i2v` · `generate_s2v` · `generate_flf2v` · `--ltx-mode` |
| **언제** | 일반 숏 모션 품질 기본 (Wan 대비 A/B 채택) |
| **옵션** | face_stability · format 프리셋 |
| **가이드** | [LTX23_AIO_v44_AGENT_GUIDE.md](../workflows/human/LTX23_AIO_v44_AGENT_GUIDE.md) |
| **목록** | `python scripts/run_ltx_aio_features.py --list` |

```bash
python scripts/generate_i2v.py -i key.png -p "slow push-in, natural motion" -o clip.mp4
python scripts/generate_flf2v.py -i start.png --last end.png -p "..." -o bridge.mp4
```

---

### C2. Wan 2.2 — 빠른 fallback (기존 API)

| 항목 | 내용 |
|------|------|
| **CLI** | `generate_i2v --backend wan22` |
| **언제** | 빠른 실험 · LTX 불가 시 |
| **약점** | 모션 평탄 → 품질 기본은 LTX |
| **가이드** | [wan22/AGENT_GUIDE.md](../workflows/human/wan22/AGENT_GUIDE.md) |

---

### C2b. YAW Wan 2.2 MoE — 실 UI T2V/I2V

| 항목 | 내용 |
|------|------|
| **출처 목적** | boobkake22 **easy T2V+I2V** 템플릿 (Wan 2.2 MoE high/low) |
| **기능** | green **T2V↔I2V** · lightx2v · End Image · VFI(GIMM/RIFE) · 32/60fps · post grain |
| **CLI** | **`generate_yaw_wan22`** |
| **모델** | 기본 **GGUF Q4** (`UnetLoaderGGUF`) — 팩 fp16 풀은 거대 (`--fp16` 옵션) |
| **언제** | Wan 2.2 MoE **T2V / I2V** · green 그룹 스위치 · lightx2v / VFI 옵션 |
| **언제 말고** | 다른 백엔드가 더 맞을 때(에이전트가 카탈로그에서 자유 선택) · 예: 립싱크 중심 → s2v 계열 |
| **원칙** | **실 UI + 스위치** · 미니그래프 금지 · 본선/폴백 강제 없음 |
| **가이드** | [yaw_wan22/AGENT_GUIDE.md](../workflows/human/yaw_wan22/AGENT_GUIDE.md) |
| **출처** | [Civitai 2008892](https://civitai.red/models/2008892/yet-another-workflow-easy-t2v-i2v-yaw-wan-22) |

```bash
python scripts/generate_yaw_wan22.py --list-features
python scripts/generate_yaw_wan22.py --task t2v -p "cinematic motion..." -o out.mp4 --seed 42
python scripts/generate_yaw_wan22.py -i start.png -p "slow push-in" -o i2v.mp4
```

---

### C3. Kenpechi LTX NSFW — 빨간맛 영상

| 항목 | 내용 |
|------|------|
| **기능** | 10Eros GGUF I2V · Director 멀티샷 |
| **CLI** | `generate_ltx_nsfw_i2v` · `generate_ltx_nsfw_director` |
| **언제** | 성인 모션 클립 (**18+ only**) |
| **가이드** | [ltx23_nsfw/AGENT_GUIDE.md](../workflows/human/ltx23_nsfw/AGENT_GUIDE.md) |

---

### C4. InfiniteTalk — 립 히어로

| 항목 | 내용 |
|------|------|
| **CLI** | `generate_s2v --backend infinitetalk` |
| **언제** | 토킹헤드 립싱크 품질이 중요할 때 (기본 SI2V 아님) |

---

### C5. 후처리 (experimental)

| CLI | 기능 |
|-----|------|
| `generate_wan22_face_enhance` | 얼굴 향상 (실험) |
| `generate_wan22_upscale` | 영상 업스케일 옵트인 |
| `upscale_image` / `upscale_video` | 납품 해상도 티어 |

---

## D. 오디오 도구

### D1. Qwen3-TTS — 복제 · 감정 · 프리셋

| 항목 | 내용 |
|------|------|
| **기능** | custom / design / **clone** TTS |
| **CLI** | **`generate_qwen3_tts`** · `voice_register` · `episode_tts` |
| **감정** | custom/design: `--instruct` · clone: 감정 ref + stage direction |
| **클론 ref** | **5–15s 권장 · 최대 ~30s** |
| **가이드** | [qwen3_tts/AGENT_GUIDE.md](../workflows/human/qwen3_tts/AGENT_GUIDE.md) |

```bash
# 프리셋 + 감정
python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee \
  --instruct "soft sad, quiet" --text "비가 오네." -o sad.mp3

# 음성 복제 + 감정
python scripts/generate_qwen3_tts.py --mode clone \
  --ref-audio sample.wav --ref-text "샘플 문장" \
  --instruct "warm happy" --text "오늘 정말 기뻐." -o clone.mp3
```

| 모드 | 음색 | 감정 |
|------|------|------|
| `custom` | 프리셋 화자 | `--instruct` 필드 |
| `design` | 자연어 설계 | `--instruct` 필수 |
| `clone` | 샘플 복제 | 연기된 ref + `--instruct` 우회 |

---

### D2. BGM

| CLI | 기능 |
|-----|------|
| `generate_bgm` | 배경음 생성 (프로젝트 정책에 맞게) |

---

## E. 옵션 헬퍼 (프로젝트가 쓸 때만)

에피소드 패키지·합본이 **필요할 때만**. 도구 선택의 전제가 아님.

| 스크립트 | 기능 |
|----------|------|
| `story_init` / `shot_compose` | 샷 패키지·키프레임 |
| `shot_qa_pack` / `shot_qa_record` / `shot_approve` | QA·승인 게이트 |
| `episode_i2v` / `episode_s2v` / `episode_tts` | 배치 모션·TTS 바인딩 |
| `assemble_video` | 합본 (승인 정책 적용 가능) |
| `export_episode_to_workspace` | 프로젝트로 반출 |
| `failure_note.py` | 실패 교훈 공유 |

연출 스킬: [skills/video-direction](../skills/video-direction/SKILL.md) — **에피소드 레일·장편 기획 시** 권장.

---

## F. 선택 트리 (복붙용)

```text
이미지?
  전역 문장 편집          → generate_qwen_edit
  마스크 부위만           → generate_qwen_inpaint
  일반 스틸               → generate_moody
  성인 스틸               → generate_krea_nsfw
  가벼운 타이틀 글자      → generate_ideogram4
  잡지/포스터 풀 연출     → generate_boogu_typo
  멀티앵글                → generate_qwen_angle
  포즈 CN                 → generate_moody_controlnet

영상?
  일반 I2V 품질           → generate_i2v (LTX)
  빠른 실험               → generate_i2v --backend wan22
  첫·끝 프레임            → generate_flf2v
  오디오 연동             → generate_s2v
  립 히어로               → generate_s2v --backend infinitetalk
  성인 모션               → generate_ltx_nsfw_i2v

오디오?
  프리셋+감정             → generate_qwen3_tts --mode custom --instruct
  복제+감정               → generate_qwen3_tts --mode clone --ref-audio ...
  보이스 등록             → voice_register
```

---

## G. 공통 주의

| 항목 | 내용 |
|------|------|
| **cwd** | 항상 `agent_custom` 루트에서 `python scripts/...` |
| **Comfy** | `127.0.0.1:8188` |
| **18+** | krea_nsfw · ltx_nsfw_* |
| **VRAM** | 큰 모델 OOM 시 재시작 · GGUF · 짧은 클립 |
| **결과 위치** | `-o` 명시 권장 · 프로젝트로 복사 |
| **실 UI 도구** | 미니그래프 재작성 금지 · 포트/스위치/문서화된 스왑만 |

---

## H. 제공 측 유지 규칙 (우리)

새 워크플로를 도구로 넣을 때:

1. UI → `workflows/human/`  
2. CLI `scripts/generate_*.py` (+ runner)  
3. **이 카탈로그에 카드 1개** (기능 · 언제 · CLI · 가이드)  
4. `workflows/agent/catalog.json` 한 줄  
5. (가능하면) 스모크 1회 + `process.md` 한 줄  

프로젝트 에이전트는 **H를 수행하지 않아도 됨** — **A~F만 읽고 고르면 됨**.
