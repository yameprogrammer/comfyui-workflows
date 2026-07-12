# LTX 2.3 All-in-One v44 — 라우팅·스위치 분석 (기능별 이식 전제)

- **작성일**: 2026-07-12  
- **소스**: `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json`  
- **기계 판독 맵**: `docs/_ltx23_aio_v44_routing_map.json` (재생성: `python scripts/_analyze_ltx23_aio_routing.py`)  
- **관련**: [ltx23_aio_pipeline_integration.md](ltx23_aio_pipeline_integration.md)

---

## 0. 한 줄 결론

이 워크플로는 **단일 직선 그래프가 아니라**,

1. **루트 오케스트레이션 쉘** (포트 · Set/Get 버스 · Switch · Orchestrator muter)  
2. **서브그래프 내부 LTX 본체** (206노드, 모드별 mute 분기)  

로 나뉜 **다중 모드 스위치 시스템**이다.

에이전트가 만든 축소 API 그래프(`LoadAudio→Encode→Concat`)는  
**「Audio input 옵션을 켠 AIO」와 동치가 아니다.**  
기능별 정합 이식은 **스위치 테이블 + `[[P:]]` 태그 mute 규칙**을 먼저 재현해야 한다.

---

## 1. 아키텍처 레이어

```
┌─────────────────────────────────────────────────────────┐
│ ROOT (~93 nodes) — orchestration shell                    │
│  · Group P (ports) + OrchestratorNodeMuter (black switch) │
│  · ComfySwitchNode ×2 (model path / prompt path)          │
│  · SetNode/GetNode bus (m audio in, m frame first, …)     │
│  · Loaders, Prompt, Output previews                         │
└───────────────────────────┬─────────────────────────────┘
                            │ bus / subgraph IO
┌───────────────────────────▼─────────────────────────────┐
│ SUBGRAPH (~206 nodes) — LTX compute core                  │
│  · Empty latent / ImgToVideo / AddGuide / AV encode       │
│  · Mode-tagged nodes [[P:Audio input]] etc. muted/unmuted │
│  · Sampler · SeparateAV · Decode · combine                │
└─────────────────────────────────────────────────────────┘
```

| 레이어 | 역할 | 에이전트 함의 |
|--------|------|----------------|
| Root | 사용자 선택·입력 포트·모델/프롬프트 스위치 | CLI 플래그 = muter 옵션 조합 |
| Bus (`m *`) | 해상도·fps·프레임·오디오·VAE 공유 | 모드 전환 시 같은 슬롯에 다른 소스 |
| Subgraph | 실제 LTX 연산 분기 | **여기 mute 세트가 “진짜 모드”** |

---

## 2. Comfy `mode` (mute) 규약

| mode | 이름 | 의미 |
|------|------|------|
| **0** | ALWAYS | 실행됨 |
| **2** | NEVER | **뮤트** — 해당 옵션이 꺼져 있으면 이 상태 |
| **4** | BYPASS | 바이패스 (로더 등) |

Orchestrator / 스위치가 옵션을 고르면 **`[[P:…]]` 태그 노드들의 mode를 일괄 토글**한다.  
Note 937:

> Group name and node title tags are essential…  
> Don’t edit group name **`P`**.  
> Don’t edit tags like `[[P:02 Image to Video]]`.

**태그 문자열 = 스위치 라우팅 키.** 이름 바꾸면 자동 전환이 깨진다.

---

## 3. 공식 워크플로 테이블 (Note 923)

| 사용 목적 | Orchestrator에서 켤 옵션 (Select options) |
|-----------|-------------------------------------------|
| Text to Video | `01 Text to Video` |
| Text + Audio to Video | `01 Text to Video` + **`Audio input`** |
| Image to Video | `02 Image to Video` |
| **Image + Audio to Video** | `02 Image to Video` + **`Audio input`** |
| First/Last Frame | `02 Image to Video` + **`Last Frame input`** |
| First/Last + Audio | `02` + `Last Frame input` + **`Audio input`** |
| First/Mid/Last | `02` + `Last` + **`Mid Frame input`** |
| First/Mid/Last + Audio | `02` + `Last` + `Mid` + **`Audio input`** |
| Video to Video (extend) | `03 Video to Video` |

저장본 스냅샷의 Orchestrator widgets 예:

```text
[false, null, false, null, false, true, false, false, false, false]
```

→ 특정 옵션 한 줄만 true (저장 시점 UI 상태). **실행 시마다 모드에 맞게 다시 세팅**해야 함.

---

## 4. 루트 `[[P:]]` 포트 (공개 입력)

| id | 기본 mode (저장본) | type | port label |
|----|--------------------|------|------------|
| 149 | ALWAYS | LoadImage | **02 Image to Video** (First Frame) |
| 852 | ALWAYS | PreviewImage | 02 Image to Video (preview) |
| 412 | **NEVER** | LoadAudio | **Audio input** |
| 786 | **NEVER** | LoadImage | **Last Frame input** |
| 1705 | **NEVER** | LoadImage | **Mid Frame input** |
| 787 | **NEVER** | VHS_LoadVideo | **03 Video to Video** |

저장본 기본값 ≈ **순수 I2V (오디오/FLF/V2V 꺼짐)**.  
Image+Audio를 쓰려면 Orchestrator가 **Audio input 관련 노드를 ALWAYS로 살리고** LoadAudio(412)를 활성화해야 한다.

---

## 5. 서브그래프 — Audio input 관련 핵심 노드

저장본에서 **NEVER(뮤트)** 인 Audio 태그 예:

| id | type | title |
|----|------|--------|
| **1495** | `LTXVAudioVAEEncode` | `LTXV Audio VAE Encode [[P:Audio input]]` |
| **1496** | `SolidMask` | `SolidMask [[P:Audio input]]` |
| **1499** | `SetLatentNoiseMask` | `Set Latent Noise Mask [[P:Audio input]]` |

항상 켜져 있는(ALWAYS) AV 계열 (공용 백본 추정):

| id | type | 비고 |
|----|------|------|
| 1061 | `LTXVEmptyLatentAudio` | 빈 오디오 latent |
| 1201 | `LTXVAudioVAEEncode` | (다른 encode 경로 — 태그 없음) |
| 1202 | `LTXVAudioVideoMask` | AV 마스크 |
| 1055 / 1782 | `LTXVConcatAVLatent` | 비디오+오디오 latent 결합 |
| 1064 | `LTXVAudioVAEDecode` | 출력 음성 디코드 |
| 1068 / 1783 | `LTXVSeparateAVLatent` | 분리 |

**해석 (가설 → 검증 필요):**

- 오디오 모드 OFF: Empty audio latent + mask 경로로 “무음/빈 AV” 유지.  
- 오디오 모드 ON: **`[[P:Audio input]]` encode + SolidMask/SetLatentNoiseMask** 가 살아나 입력 웨이브를 AV 경로에 주입.  
- 에이전트 미니 그래프는 EmptyLatentAudio / AudioVideoMask / SolidMask / SetLatentNoiseMask **전무** → AIO Audio 분기와 구조적으로 불일치.

FLF/Mid 쪽 NEVER 예:

- `LTXVAddGuideMulti [[P:Last Frame input]]`  
- `LTXVAddGuideMulti [[P:Mid Frame input]]`  
- Resize / Preprocess 동 태그  

V2V: `[[P:03 Video to Video]]` 다수 (VideoInfo, GetRange, Resize, Math frame align 등).

---

## 6. 기타 루트 스위치

### ComfySwitchNode

| id | 역할 (연결 기준) |
|----|------------------|
| 1801 | MODEL: GGUFLoaderKJ 두 경로 중 선택 (`on_false` / `on_true`, switch 입력) |
| 1798 | STRING 프롬프트: 수동 multiline vs `TextGenerateLTX2Prompt` |

→ **모드 테이블 본선이 아니라** 모델/프롬프트 보조 스위치.

### Set/Get 버스 (변수명)

`m audio in`, `m audio v2v`, `m frame first/last/mid`, `m width/hight`, `m fps`, `m clip length`, `m vae audio/video`, `m pos/neg`, `m model`, `m sampler`, `m noise`, `m video`, …

모드가 바뀌면 **같은 버스 키에 다른 소스가 Set** 되고, 서브그래프 Get이 소비.

---

## 7. 에이전트 현황 vs AIO 정합

| 항목 | AIO 실제 | agent `ltx23_aio` (현재) | 정합 |
|------|----------|--------------------------|------|
| Orchestrator 옵션 테이블 | 필수 | 미구현 | ❌ |
| `[[P:]]` mute 토글 | 필수 | 미구현 | ❌ |
| 서브그래프 전체 실행 | 본체 | 미실행 (축소 API만) | ❌ |
| EmptyLatentAudio + AudioVideoMask | Audio 경로 일부 | 없음 | ❌ |
| `[[P:Audio input]]` Encode+Mask | 오디오 ON 시 | 단순 LoadAudio→Encode→Concat | ❌ |
| GGUF UNet + fro09 LoRA + 24fps | 사용 | 유사 설정 | △ 스택만 유사 |
| DualClipLoaderGGUF Q4 | 사용자 선택 | 기본으로 맞춤 | △ TE만 |
| TTS 원음 보존 | AIO는 자체 AV 오디오 생성 강점 | 후처리 리먹스로 땜 | 별 이슈 |

**상태 정정:** 문서/매니페스트의 “Image + Audio ✅ READY” 는  
「축소 그래프가 돈다」의미이지 **「AIO Audio input 스위치 경로 이식 완료」가 아님.**

---

## 8. 기능별 이식 절차 (권장)

기능 하나(예: Image + Audio)를 “제대로” 붙이려면:

1. **Orchestrator** 에서 해당 옵션 조합만 켠 UI 스냅샷 저장 (또는 muter API로 mode 덤프).  
2. 루트+서브그래프에서 `mode==0` 노드 집합 = **활성 컷**.  
3. `[[P:Audio input]]` / `[[P:02 Image to Video]]` 등 활성 포트 입력 스키마 고정.  
4. 활성 컷만 API prompt 로 추출 (또는 전체 그래프 + mode 필드 포함 제출).  
5. 스모크: 짧은 TTS 1개 → 립·음색·프롬프트 반응을 **수동 AIO 동일 입력**과 비교.  
6. 통과 시에만 `backend=ltx23_aio` 를 “AIO-parity” 로 표시.

다른 모드(FLF, FML, V2V, T2V)도 **같은 절차를 모드마다 반복.**  
추측 축소 그래프 남발 금지.

### 자동화 도구 (이미 추가)

```bash
cd F:\ComfyUI_workflows\agent_custom
python scripts/_analyze_ltx23_aio_routing.py
# → docs/_ltx23_aio_v44_routing_map.json
```

후속: `export_aio_active_cut.py --options "02 Image to Video,Audio input"` 형태로  
**옵션 → 활성 노드 집합** 덤프 (Orchestrator 위젯 스키마 확보 후).

---

## 9. 작업 원칙 (팀/에이전트)

1. **스위치·mute·`[[P:]]` 태그** 를 무시하고 기능 이식하지 않는다.  
2. “AIO와 비슷하게 붙인 축소 그래프” 와 “AIO 옵션 경로” 를 **문서에서 이름을 분리**한다.  
   - 예: `ltx23_aio_approx_*` vs `ltx23_aio_parity_*`  
3. 오디오 쇼츠는 AIO-parity 확정 전, **수동 AIO 또는 InfiniteTalk** 를 정본으로 둘 수 있다.  
4. 분석 스크립트 출력을 SSOT 보조로 유지하고, WF 버전이 바뀌면 재실행한다.

---

## 10. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초판: 루트 쉘 / 서브그래프 / Orchestrator 테이블 / Audio mute 노드 / 에이전트 부정합 기록 |
