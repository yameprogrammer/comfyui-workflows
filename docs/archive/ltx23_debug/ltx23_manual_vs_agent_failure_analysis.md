> **ARCHIVED (2026-07-14)** — 운영 SSOT 아님. 인덱스: [../../README.md](../../README.md). 활성 백로그: [../../agent_video_tooling_todo.md](../../agent_video_tooling_todo.md).

# 수동 IA2V 성공 vs 에이전트 실패 비교 분석

- **작성일**: 2026-07-12  
- **수동 성공 증거**: `ComfyUI/output/ltx2_00060-audio.mp4`  
- **history prompt_id**: `05473dc9-4699-4928-9851-d2d08f8a623d`  
- **수동 실행 시간**: **~94초** (success)  
- **관련**: [ltx23_aio_ia2v_agent_usage.md](ltx23_aio_ia2v_agent_usage.md)

---

## 0. 한 줄

수동이 빠른 이유는 **AIO 전체 IA2V 그래프(반해상도 1차 + 업스케일 2차 + 오디오 마스크 + 멀티 LoRA + GGUFLoaderKJ)** 를 쓰기 때문이다.  
에이전트 hang은 그 경로가 아니라 **축소 단일 스테이지 그래프 + 로더 차이 + (과거) 잘못된 마스크/길이** 조합 문제다.  
`sageattn is not defined` 는 **치명 아님** (pytorch attention fallback).

---

## 1. 수동 성공 런 스펙 (history 실측)

| 항목 | 값 |
|------|-----|
| 출력 | `ltx2_00060-audio.mp4` |
| 해상도 | **576×1024** (9:16), **24 fps**, **121 frames** ≈ **5.04s** |
| Clip Length 슬라이더 | **5 s** |
| Longer Edge | **1024** |
| 오디오 | `agent_qwen3_tts_custom_00011.mp3` |
| TrimAudioDuration | **start=0, duration=3** (소리 3초, 영상 5초 → 뒤는 입만 움직임) |
| 총 실행 | **~93.9 s** |
| TE | `DualClipLoaderGGUF` + `gemma-3-12b-it-UD-Q4_K_XL.gguf` |
| UNet | `GGUFLoaderKJ` + `LTX2.3\ltx-2.3-22b-dev-Q4_K_M.gguf`, attention_override=`sageattn` (실패 시 pytorch) |
| LoRA (Power) | fro09 **0.9** ON, upscale IC **0.6** ON, OmniNFT **0.5** ON |
| Sampler | **euler_ancestral** |
| 시그마 1차 | distill full: `1.0 … 0.0` (8단) |
| 시그마 2차 | refine: `0.8025, 0.6332, 0.3425, 0.0` |
| 출력 노드 | **VHS_VideoCombine** prefix `ltx2` |

### 수동 IA2V 핵심 파이프 (서브그래프)

```
EmptyLTXVLatentVideo @ (W/2 × H/2)     ← 반해상도
  → ImgToVideoInplace strength=0.8
  → ConcatAV( video , audio_latent_masked )
  → Sampler #1 (full distill sigmas)
  → SeparateAV
  → CropGuides / LatentUpsampler (+ upscale IC LoRA 경로)
  → ConcatAV again
  → Sampler #2 (short refine sigmas)
  → SeparateAV → VAEDecodeTiled + AudioVAEDecode
  → VHS_VideoCombine
```

오디오 쪽:

```
LoadAudio → TrimAudioDuration(0, 3)
  → LTXVAudioVAEEncode
  → SetLatentNoiseMask( SolidMask value=0 @ half spatial )
  → Concat 의 audio_latent
```

→ **저해상도에서 1차 샘플 → 업스케일 후 2차 리파인** 이라 VRAM·시간이 안정적.

---

## 2. 에이전트 축소 그래프가 하던 일

| 항목 | 에이전트 (문제 구간) |
|------|----------------------|
| 그래프 | `build_ltx_aio_mode_api` **~25 노드 단일 패스** |
| 해상도 | 처음부터 **544×960 풀 캔버스** Empty latent |
| 스테이지 | **1회** Sampler only (2차 refine / latent upsampler **없음**) |
| UNet 로더 | `UnetLoaderGGUF` (KJ 아님, sageattn 오버라이드 경로 다름) |
| TE | 한때 fp4 DualCLIPLoader / 한때 GGUF (설정 흔들림) |
| LoRA | fro09 하나만 |
| 오디오 | Trim 추가 전: 길이 불일치 가능; SolidMask를 **영상 크기**로 잘못 넣어 위험 |
| 샘플러 hang | 모델 로드 후 **수분+ 로그 없음**, 강제 interrupt ~500s |

성공했던 에이전트 스모크(`agent_ltx_aio_i2v_audio_*`)도 있었지만,  
이후 설정 변경(마스크/TE/연타 free 없음)과 **구조적 단축**이 겹치며 불안정해짐.

---

## 3. 차이 표 (왜 수동만 빠른가)

| 요인 | 수동 AIO IA2V | 에이전트 mini | 영향 |
|------|---------------|---------------|------|
| 반해상도 1차 + 업스케일 2차 | ✅ | ❌ 풀res 1패스 | **VRAM·속도 핵심** |
| SetLatentNoiseMask(audio,0) | ✅ 반해상 마스크 | ❌ 또는 잘못된 크기 | 오디오 고정 / OOM |
| Trim = 입력 길이에 맞춤 | ✅ 0 / 3 | 문서상 필요, 과거 누락 | latent 팽창 |
| GGUFLoaderKJ + multi LoRA | ✅ | UnetLoader + 단일 LoRA | 품질·경로 차이 |
| DualClipLoaderGGUF | ✅ (경고 있어도 동작) | 혼선 | clip missing 로그 |
| VHS combine / tiled decode | ✅ | SaveVideo + tiled | 부차 |
| sageattn 미정의 | 경고 후 pytorch | (경로 따라 다름) | **무시 가능** |

`sageattn` 에러: 수동 로그에도 동일 계열. **생성 자체는 성공**했으므로 원인 아님.

---

## 4. 결론

1. **수동이 된다 = IA2V 워크플로·모델·머신은 OK.**  
2. **에이전트가 안 된다 = 에이전트가 “다른(열등·위험한) 그래프”를 돌렸기 때문.**  
3. 특히 수동은 **half-res multi-stage** 이고, 에이전트는 **full-res single-stage** 라 같은 544~1024대에서도 부하 패턴이 다름.  
4. 수정 방향은 “또 다른 축소 추측”이 아니라:  
   - **history에 남은 성공 API 그래프(89노드)를 템플릿**으로 두고  
   - 입력(이미지/오디오/Trim/Clip/해상도)만 갈아끼우기  
   또는 그 그래프의 **반해상+2스테이지+오디오 마스크** 를 충실히 이식.

---

## 5. 권장 다음 구현

1. `history/05473dc9-...` 그래프를 `workflows/agent/ltx23_ia2v_live_template.json` 으로 저장.  
2. 에이전트 러너:  
   - LoadImage / LoadAudio / Trim(duration) / Clip Length / Longer Edge / seed / prompt 만 치환  
   - 나머지는 수동 성공 그래프 유지.  
3. 쇼츠 프리셋: aspect 9:16, longer edge 1024, clip_sec = max(audio+tail, …), trim = audio.  
4. 스모크 1회 → 수동 `ltx2_00060` 과 시간·VRAM 비교.

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 수동 ltx2_00060 history 기준 대조 분석 초판 |

