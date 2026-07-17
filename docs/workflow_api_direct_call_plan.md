# 워크플로우 JSON 직접 API 호출 — 전환 플랜

**상태:** Phase 0 완료 (runner + Lonecat T2I 프리셋 + 스모크 OK)  
**작성:** 2026-07-16  
**원칙:** ComfyUI 생성은 **검증된 워크플로우 JSON(API 포맷)을 로드 → 포트만 패치 → `POST /prompt`**.  
Python은 그래프를 조립·해킹하지 않는다.

### Phase 0 결정 — T2I 워크플로우

| 항목 | 선택 |
|------|------|
| **T2I SSOT** | **Lonecat's AIO Z-Image ver 17** (Turbo 코어 프리셋) |
| **프리셋 alias** | `lonecat_t2i_turbo` |
| **파일** | `workflows/agent/presets/lonecat_t2i_turbo.api.json` |
| **runner** | `lib/workflow_api_runner.py` · `scripts/run_workflow_api.py` |
| **쓰지 않음** | `T2I-moody.json` (미니, 품질 경로 폐기 방향) |

이유: 수동/스모크로 품질 검증됨, ZIT + Clownshark 2-pass + detailer/upscale 확장 가능.  
재export 시 USAGE.md 바이패서: Qwen OFF, LoadImage/I2I OFF, Latent=Empty, denoise=1.0.

관련:

- Lonecat 사용법: [`workflows/human/Lonecat_AIO_Z-Image_ver17_USAGE.md`](../workflows/human/Lonecat_AIO_Z-Image_ver17_USAGE.md)
- **에이전트 기능 선택:** [`workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md`](../workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md)
- **CAPABILITIES JSON:** [`workflows/human/Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json`](../workflows/human/Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json)
- **feature→preset:** [`workflows/agent/presets/lonecat_feature_presets.json`](../workflows/agent/presets/lonecat_feature_presets.json)
- 현재 catalog: [`workflows/agent/catalog.json`](../workflows/agent/catalog.json)
- 갭 검토 결론: still 본선은 미니 `I2I-moody` / inject 위주였음

### Bypasser / 셀렉터 → 프리셋 (에이전트 규칙)

에이전트는 UI 바이패서를 직접 조작하지 않는다.  
`matchTitle` 로 묶인 기능을 **feature_id** 로 보고, **ready 프리셋** 만 호출한다.

| feature_id | UI 스위치 요약 | ready preset |
|------------|----------------|--------------|
| `model_diffusion` | Model selector → Diffusion | `lonecat_t2i_turbo` |
| `model_gguf` | Model selector → GGUF | `lonecat_t2i_gguf` |
| `load_image_i2i` | `!` 바이패서 + Latent=encode | `lonecat_i2i_identity` (planned) |
| `detailers` / `controlnet` / `inpaint` / … | 해당 matchTitle 바이패서 | planned — UI export 후 등록 |

재생성: `python scripts/_build_lonecat_capabilities.py`

---

## 1. 목표 아키텍처

```text
[UI에서 기능 조합 고정]
  Fast Groups Bypasser / Switch 설정
       ↓
[1회 export]
  Save (API Format)  또는  frontend graphToPrompt
       ↓
workflows/agent/presets/<name>.api.json   ← SSOT 그래프
workflows/agent/presets/<name>.ports.json ← 패치 포트 맵 (node_id + input key)
       ↓
lib/workflow_api_runner.py
  load_api_json → apply_ports(prompt, seed, image, …) → queue_prompt → download
       ↓
scripts/generate_*.py · shot_compose · character_* · episode_*
  = runner 호출 + 메타/경로만
```

### 1.1 허용되는 코드 역할

| 허용 | 금지 |
|------|------|
| API JSON 로드 | 노드 클래스 런타임 삽입 (IPAdapter inject 등) |
| 문서화된 포트 패치 (text/seed/image/denoise/size) | `convert_ui_to_api`로 AIO 재해석 |
| input 폴더에 이미지 복사 | PIL로 “품질 엔진” 대체 (레이아웃 합성은 **선택 프리셋**으로만) |
| `/prompt` + history + 저장 | 빈 그래프를 Python dict로 조립 (Qwen inject 폐기 방향) |
| 프리셋 선택 (`--preset t2i_turbo`) | 미니 14노드를 프로덕션 기본으로 유지 |

### 1.2 프리셋 = 바이패서 상태의 스냅샷

Lonecat 같은 AIO는 코드로 스위치를 돌리지 않는다.  
**UI에서 조합 → API export → 파일 하나 = 기능 하나.**

예:

| 프리셋 파일 | 의미 (바이패서 상태) |
|-------------|----------------------|
| `lonecat_t2i_turbo.api.json` | Turbo ON, Qwen OFF, LoadImage OFF, denoise=1 |
| `lonecat_i2i_identity.api.json` | LoadImage+I2I ON, Latent=encode, denoise~0.5, Qwen OFF |
| `lonecat_i2i_detailer.api.json` | 위 + Face detailer ON |
| `lonecat_i2i_upscale.api.json` | 위 + Hi Rez / 또는 SeedVR2 |

---

## 2. 기능 전체 목록 (현재 방식 → 목표)

### 범례

| 현재 | 의미 |
|------|------|
| **MINI** | 미니 agent UI JSON + 부분 `convert_ui_to_api` |
| **INJECT** | 워크플로우 파일 없음, Python이 API dict 조립 |
| **HACK** | 미니 그래프 + 런타임 노드 삽입/전처리 |
| **FILE** | JSON 있으나 “그대로 패치 호출” runner 없음 |
| **API-READY** | 이미 API 포맷에 가깝거나 export 됨, **본선 미연결** |
| **N/A** | Comfy 이미지 생성이 아님 (TTS/BGM/assemble 등) |

---

### 2.1 Still — 텍스트/이미지 생성 (최우선)

| ID | 기능 | 진입 스크립트 | 현재 | 목표 워크플로우/프리셋 | 우선도 |
|----|------|---------------|------|------------------------|--------|
| S1 | 에피소드 키프레임 합성 | `shot_compose.py` | **HACK** (layout+ipa+I2I-moody) | Lonecat `i2i_identity` / `t2i_turbo` 프리셋 | **P0** |
| S2 | Moody T2I | `generate_moody.py` | **MINI** T2I-moody | Lonecat `t2i_turbo` 또는 전용 T2I API | **P0** |
| S3 | Moody I2I | `generate_moody_i2i.py` | **MINI** I2I-moody | Lonecat `i2i_*` API | **P0** |
| S4 | I2I identity lock | `generate_moody_i2i_lock.py` | **HACK** (문구+denoise cap) | 프리셋 denoise 고정본으로 대체·폐기 | **P0** |
| S5 | I2I + IPAdapter | `generate_moody_i2i_ipadapter.py` | **HACK** (노드 inject) | Lonecat/전용 face-lock **API 프리셋** (inject 금지) | **P0** |
| S6 | I2I + ControlNet | `generate_moody_controlnet.py` | **MINI** | Lonecat CN ON 프리셋 또는 전용 CN API | **P1** |
| S7 | Krea T2I | `generate_krea.py` | **FILE**/MINI T2I-krea | `T2I-krea`를 **API 포맷으로 재export** 후 runner | **P1** |
| S8 | Z-Image Turbo T2I base | catalog only | **FILE** 미연결 | API export + runner 또는 Lonecat으로 흡수 | **P2** |
| S9 | Ideogram4 | `generate_ideogram4.py` | 외부 API | Comfy JSON 대상 아님 (범위 외 표기) | — |

### 2.2 Still — 캐릭터/로케이션 파이프

| ID | 기능 | 진입 스크립트 | 현재 | 목표 | 우선도 |
|----|------|---------------|------|------|--------|
| C1 | 캐릭터 생성/캐스팅 풀 | `character_create.py`, `character_cast_pool.py` | **MINI** T2I-moody/krea | S2/S7 runner | **P1** |
| C2 | full_sheet | `character_full_sheet.py` | **MINI/HACK** I2I 계열 | Lonecat sheet용 프리셋 또는 I2I API | **P0** (품질 직결) |
| C3 | expand_sheets | `character_expand_sheets.py` | **HACK** lock/ipa/cn | 동일 | **P0** |
| C4 | turnaround / wardrobe | `character_turnaround_sheet.py`, `character_set_wardrobe.py` | **MINI/HACK** | I2I API 프리셋 | **P1** |
| C5 | Qwen multi-angle turns | `character_qwen_turns.py` | **INJECT** | Qwen angle **API JSON export** 후 runner | **P1** |
| L1 | location create/full/expand | `location_*.py` | **MINI** moody | Lonecat T2I/I2I 프리셋 | **P1** |
| K1 | shot + character 헬퍼 | `shot_with_character.py` | **MINI** | S1과 동일 runner | **P1** |
| K2 | keyframe edit | `shot_keyframe_edit.py` | moody I2I / qwen inject | 프리셋 선택 runner | **P1** |

### 2.3 Still — 편집 (Qwen)

| ID | 기능 | 진입 | 현재 | 목표 | 우선도 |
|----|------|------|------|------|--------|
| Q1 | 지시 기반 이미지 편집 | `generate_qwen_edit.py` | **INJECT** | UI 성공 그래프 → API JSON + ports | **P1** |
| Q2 | 멀티앵글 | `generate_qwen_angle.py` | **INJECT** | 동일 | **P1** |

### 2.4 Video

| ID | 기능 | 진입 | 현재 | 목표 | 우선도 |
|----|------|------|------|------|--------|
| V1 | I2V (wan22) | `generate_i2v.py`, `episode_i2v.py` | **FILE** I2V-wan22 + 패치 | API 포맷 고정 + port patch only | **P1** |
| V2 | S2V / IA2V LTX | `generate_s2v.py`, `episode_s2v.py` | **INJECT**/부분 FILE | LTX 성공 human JSON → API export | **P2** |
| V3 | V2V | `generate_v2v.py`, `episode_v2v.py` | 확인 필요 | 동일 원칙 | **P2** |
| V4 | video upscale | `episode_upscale.py`, `upscale_video.py` | 백엔드별 | 워크플로우 있으면 API export | **P2** |

### 2.5 비-Comfy 또는 후단 (이번 전환 범위 밖 / 후순위)

| ID | 기능 | 비고 |
|----|------|------|
| X1 | TTS / BGM / subtitles / assemble | Comfy still JSON 대상 아님 |
| X2 | QA / approve / export workspace | I/O만 |
| X3 | Ideogram 등 외부 API | 별도 |

---

## 3. 공통 인프라 (모든 기능의 선행 작업)

| 단계 | 산출물 | 완료 조건 |
|------|--------|-----------|
| **I0** | `lib/workflow_api_runner.py` | `run(preset_or_path, ports={...}) → {ok, path, seed, prompt_id}` |
| **I1** | port 스키마 | `ports.json`: `{ "positive": {"node":"1315","key":"text"}, "seed": {...}, ... }` |
| **I2** | catalog v2 | `format: "api"`, `file: "*.api.json"`, `ports: "*.ports.json"` |
| **I3** | export 절차 문서 | UI 바이패서 고정 → Save API Format → agent/presets 복사 체크리스트 |
| **I4** | 레거시 플래그 | `--legacy-mini` 임시 유지 후 제거 일정 |
| **I5** | 스모크 하네스 | 프리셋당 1장 생성 + 메타에 `workflow_api` 경로 기록 |

**규칙:** 신규 생성 코드는 runner만 호출. `convert_ui_to_api`는 레거시 미니 전용으로 격리 후 삭제 후보.

---

## 4. 작업 순서 (페이즈)

### Phase 0 — 기반 (1차 보고 후 착수)

1. `workflow_api_runner` 구현 (로드/패치/큐/다운로드/메타).  
2. Lonecat 기존 export로 **T2I 스모크** runner 단위 테스트 (이미 수동 검증된 경로 재현).  
3. catalog에 `lonecat_t2i_turbo` 등록.  
4. agent_rules / workflows README 원칙 문구 개정:
   - “미니 그래프 + inject” 금지  
   - “API 프리셋 + port patch” 필수  

**완료 게이트:** CLI 한 줄로 Lonecat T2I 1장 재현.

---

### Phase 1 — Still 본선 교체 (소나기 키프레임 직결) **P0**

| 순 | 작업 | 건드리는 기능 ID |
|----|------|------------------|
| 1.1 | UI에서 Lonecat **I2I identity** 바이패서 고정 → API export + ports | S3, S4, S5 |
| 1.2 | `generate_moody_i2i.py` → runner 위임 (기본 프리셋 Lonecat i2i) | S3 | **done 2026-07-16** |
| 1.3 | `i2i_lock` / `ipadapter` → 프리셋으로 대체 또는 deprecated | S4, S5 | **done** (inject 제거, Lonecat I2I) |
| 1.4 | `shot_compose` 기본 엔진 = runner + Lonecat i2i/t2i 프리셋 | S1 |
| 1.5 | PIL layout: **기본 OFF**. 필요 시 별도 전처리 옵션 또는 전용 프리셋만 | S1 |
| 1.6 | `character_full_sheet` / `expand_sheets` → 동일 I2I runner | C2, C3 |
| 1.7 | 소나기_v2 스모크 S01/S04 재생성 비교 (구 REJECTED vs 신규) | 검증 |

**완료 게이트:** `shot_compose -e sonagi_mv_v3 -s S01` 가 Lonecat API JSON 경로로 돌고, 메타에 `workflow: lonecat_…api.json` 기록.

---

### Phase 2 — T2I·로케·Krea·CN **P1**

| 순 | 작업 | ID |
|----|------|-----|
| 2.1 | Lonecat T2I 프리셋을 `generate_moody` 기본으로 | S2 |
| 2.2 | location_* → T2I/I2I runner | L1 |
| 2.3 | Krea: UI/현재 JSON API export → runner | S7, C1 |
| 2.4 | ControlNet 프리셋 export → `generate_moody_controlnet` | S6 |
| 2.5 | `shot_with_character`, cast pool 경로 정리 | K1, C1 |

**완료 게이트:** character create 1장 + location master 1장이 미니 moody 없이 생성.

---

### Phase 3 — Qwen 편집 그래프 파일화 **P1**

| 순 | 작업 | ID |
|----|------|-----|
| 3.1 | 현재 inject로 성공하는 설정을 UI에 재현하거나 기존 성공 그래프 확보 | Q1, Q2 |
| 3.2 | API export + ports (image, instruction, seed, …) | |
| 3.3 | `generate_qwen_edit` / `angle` / `character_qwen_turns` / `shot_keyframe_edit` → runner | Q1, Q2, C5, K2 |
| 3.4 | inject 빌더 코드 삭제 또는 `--legacy-inject` 격리 | |

**완료 게이트:** catalog에 `qwen_edit_*.api.json` 존재, inject 경로 기본 OFF.

---

### Phase 4 — Video 정렬 **P1–P2**

| 순 | 작업 | ID |
|----|------|-----|
| 4.1 | wan22 I2V: 현재 JSON을 API 포맷으로 고정, runner 패치만 | V1 |
| 4.2 | LTX IA2V: human 성공본 API export | V2 |
| 4.3 | episode_i2v/s2v가 runner만 쓰는지 확인 | V1, V2 |
| 4.4 | upscale/v2v 동일 원칙 | V3, V4 |

**완료 게이트:** I2V 1클립이 미니 키프레임이 아닌 Lonecat 키프레임 입력으로 통과 (키프레임 품질 전제).

---

### Phase 5 — 정리·폐기

| 순 | 작업 |
|----|------|
| 5.1 | `convert_ui_to_api` 사용처 제거 또는 test-only |
| 5.2 | `I2I-moody.json` 등 미니 그래프 → `workflows/agent/_legacy/` |
| 5.3 | IPAdapter inject 함수 삭제 |
| 5.4 | process.md / agent_rules / catalog README 최종 동기화 |
| 5.5 | 임시 `_tmp_lonecat_*.py` / 실험 스크립트 정리 |

---

## 5. 권장 구현 순서 (한 줄 백로그)

```text
P0-1  workflow_api_runner + Lonecat T2I 스모크
P0-2  Lonecat I2I identity API export + ports
P0-3  generate_moody_i2i → runner
P0-4  shot_compose → runner (layout 기본 off)
P0-5  character full_sheet / expand → runner
P0-6  소나기 S01/S04 스모크 A/B
P1-1  generate_moody T2I → Lonecat
P1-2  location + krea API export
P1-3  controlnet 프리셋
P1-4  qwen edit/angle API 파일화
P1-5  i2v wan API 정렬
P2    s2v/ltx, upscale, legacy 삭제
```

---

## 6. 프리셋 포트 맵 템플릿

`workflows/agent/presets/<name>.ports.json` 예시:

```json
{
  "preset": "lonecat_i2i_identity",
  "workflow_api": "presets/lonecat_i2i_identity.api.json",
  "description": "LoadImage+I2I, Qwen off, face-friendly denoise",
  "ports": {
    "positive": { "node": "1315", "key": "text" },
    "negative": { "node": "1314", "key": "text", "optional": true },
    "seed": { "node": "1307", "key": "seed" },
    "denoise": { "node": "2041", "key": "Xf" },
    "input_image": { "node": "2035", "key": "image", "copy_to_input_dir": true },
    "width": { "node": "1808", "key": "width", "optional": true },
    "height": { "node": "1808", "key": "height", "optional": true }
  },
  "defaults": {
    "denoise": 0.52
  },
  "notes": "Export with Latent Switch = VAEEncode; Qwen group bypassed"
}
```

실제 node id는 **export 시점 스냅샷**마다 다를 수 있으므로, export 직후 ports를 채운다 (하드코딩 금지 원칙: ports 파일이 SSOT).

---

## 7. 리스크와 대응

| 리스크 | 대응 |
|--------|------|
| AIO export 시 UE/SetGet 링크 누락 | export 후 스모크; 실패 시 UI에서 UE 끄고 명시 링크로 재export |
| Qwen/Florence 의존성 | 프리셋에서 해당 그룹 bypass 고정 |
| 프리셋 난립 | 소나기 기준 최소 3개만 P0 (t2i / i2i / i2i+detailer) |
| 기존 에피소드 깨짐 | `--legacy-mini` 한 버전 유지 후 제거 |
| 해상도 960×544 vs 1024×576 | 프리셋 기본을 Lonecat 해상도로; I2V work size는 후단 리사이즈 명시 |

---

## 8. 완료 정의 (Definition of Done)

전체 전환 “완료”는 다음을 모두 만족할 때:

1. **키프레임·캐릭터·로케 still 생성**이 전부 `*.api.json` runner 경로.  
2. catalog에 미니 전용 alias 없음 (legacy 폴더만).  
3. IPAdapter/Qwen **런타임 inject 코드 경로 기본 비활성**.  
4. 생성 메타 JSON에 `workflow_api` 절대/상대 경로 기록.  
5. 소나기 스모크 4장(S01/S04/S15/S22 또는 합의 세트) 재생성·육안 게이트 통과.  
6. `process.md` + `agent_rules` Rule 2/3 이 새 원칙과 일치.

---

## 9. 이번 보고: 준비 상태

| 항목 | 상태 |
|------|------|
| 기능 목록 (S/C/L/K/Q/V) | ✅ 본 문서 §2 |
| 페이즈·백로그 | ✅ §4–5 |
| 아키텍처·금지 사항 | ✅ §1 |
| Lonecat 사용/스위치 문서 | ✅ 기존 USAGE.md |
| Lonecat API 샘플 파일 | ✅ `workflows/agent/Lonecat_AIO_Z-Image_ver17.api.json` |
| runner 코드 | ❌ 미착수 (Phase 0) |
| shot_compose 연결 | ❌ 미착수 (Phase 1) |
| 프리셋 i2i/detailer export | ❌ UI 작업 필요 |

**작업 준비: 완료.**  
구현은 사용자 승인 후 **Phase 0 (runner + T2I 스모크)** 부터 시작하면 됩니다.

---

## 10. 제안 착수 명령 (승인 후)

```text
1) lib/workflow_api_runner.py + scripts/run_workflow_api.py
2) Lonecat T2I ports.json 정리 + catalog 등록
3) 스모크 1장
4) I2I 프리셋 UI export (사용자 또는 에이전트 가이드)
5) shot_compose 전환
```

승인 시 “Phase 0 진행”이라고만 주시면 됩니다.
