# 📜 에이전트 작업 협업 규칙 및 핸드북 (agent_rules.md)

이 문서는 `agent_custom` 워크스페이스를 개선·운영하는 **AI 코딩 에이전트**를 위한 공식 지침이다.  
이 저장소는 휴먼 GUI 앱이 아니라 **에이전트용 ComfyUI 도구** 구성이 목표다. 협업 연속성과 품질을 위해 아래 규칙을 준수한다.

---

## 📌 레이아웃 (먼저 열 곳)

```text
agent_custom/
  agent_rules.md   process.md   README.md     ← 규칙·이력·입구
  workflows/agent/                             ← 워크플로우 JSON SSOT
  scripts/                                     ← CLI 진입점
  lib/                                         ← 공유 코드
  characters/                                  ← 캐릭터 패키지
  docs/                                        ← 설계·스펙·로드맵
```

* CLI: `python scripts/<name>.py ...` (루트 cwd 권장, 경로는 `_bootstrap` 이 처리)
* 워크플로우: `workflows/agent/` + `catalog.json` / `lib/workflow_paths.py`
* 구현 스펙: [docs/character_impl_spec.md](docs/character_impl_spec.md)
* 영상 납품: [docs/video_delivery_and_backends.md](docs/video_delivery_and_backends.md)

---

## 📌 핵심 작업 규칙

### Rule 1. 이력 관리의 의무 (`process.md` 상시 업데이트)
* 코드·워크플로우 JSON·성능 최적화 시 **즉시 `process.md` 최상단**에 이력을 추가한다.
* **[작업 일자], [에이전트 이름], [작업 목표], [주요 변경·파라미터]** 를 남긴다.

### Rule 2. 자동화 스크립트 정합성 유지
* ComfyUI UI에서 워크플로우를 바꾸면, 대응 스크립트(`scripts/generate_moody.py`, `scripts/generate_moody_i2i.py` 등)의 `convert_ui_to_api`·노드 주입 로직을 **함께** 갱신한다.
* JSON만 바꾸고 스크립트 매핑을 생략해 배치를 깨뜨리는 행위는 금지.

### Rule 2.1 에이전트 전용 워크플로우 경로
* 스크립트가 읽는 워크플로우 **SSOT는 `workflows/agent/`** 이다.
* 휴먼 UI 실험은 `workflows/human/` → 검증 후 agent 로 **프로모트**.
* 루트에 워크플로우 JSON을 두지 않는다 (레거시 제거됨). 폴백이 필요하면 `lib/workflow_paths` 가 루트를 볼 수 있으나 **SSOT는 agent 만**.
* agent 반영 시 관련 `scripts/generate_*.py` 와 함께 커밋 + `process.md` 기록.

### Rule 2.2 디렉터리 역할 고정
* **신규 CLI** → `scripts/`
* **공유 모듈** → `lib/`
* **설계·스펙 문서** → `docs/`
* **캐릭터 데이터** → `characters/` (템플릿 구조 준수)
* 루트에 실행 스크립트·워크플로우 JSON·장문 스펙을 새로 쌓지 말 것.

### Rule 3. Flow Matching 모델 연산의 이해 및 보존
* 코어 모델 `Z-Image-Turbo` 는 Flow Matching 이다.
* I2I 시 `res_multistep` 대신 **`euler`/`normal`**, denoise **`0.70 ~ 0.85`**, CFG 권장 **≥ 3.5**.
* I2I 타임스텝 시프터 하드 와이어를 무단 변경하지 말 것.

### Rule 4. 경로 무결성 보존
* ComfyUI 경로(`F:\ComfyUI_windows_portable\ComfyUI\`) 등 드라이브 하드코딩이 있다. 이전 시 주의.

### Rule 5. 인수인계 핸드훅
* 작업 종료 시 **[안정성 상태], [물리 법칙/임계치], [다음 추천 작업]** 을 남긴다.

### Rule 6. 캐릭터 패키지 및 구현 스펙
* 코딩 시 [docs/character_impl_spec.md](docs/character_impl_spec.md) 가 [docs/character_sheet_system_design.md](docs/character_sheet_system_design.md) 보다 우선.
* 시트 denoise·alias → `characters/sheet_presets.json` SSOT.
* 용도 프로필 → `characters/profiles.json` SSOT, 기본 `video_ref`.
* 본 촬영 입력은 **`approved/` 승격 레퍼**만.
* 활성 트랙 `CHARACTER_L2_SOFT_FACTORY` 동안 L3 LoRA 학습과 I2V 본구현을 같은 PR에 섞지 말 것 (스파이크 별도). ControlNet·프로필은 캐릭터 트랙 내 허용.
* 새 캐릭터는 `characters/_template/` 구조. artbook/video 로 character_id 를 쪼개지 말 것.

### Rule 7. 영상 해상도·백엔드 규약
* 납품: **16:9, 최소 1080p**. 상세 [docs/video_delivery_and_backends.md](docs/video_delivery_and_backends.md).
* I2V 생성은 **work 해상도**; 1080p는 업스케일 마감 층.
* 백엔드·프리셋 SSOT: 루트 **`video_backends.json`** + `lib/video_backends.py`. CLI: `scripts/generate_i2v.py --backend wan22|ltx23 --preset work_16x9_540`. 기본 work 프리셋은 16:9 (정사각 스모크는 `work_1x1_smoke`).

### Rule 8. Z-Image-Turbo ControlNet (Union 2.1)
* 모델 파일은 `models/model_patches/` (`controlnet` 폴더 아님).
* 표준 `ControlNetApply` 금지 → **`ZImageFunControlnet`** + **`FL_ZImageControlNetPatch`**.
* 강도 권장 `0.65 ~ 0.80`.

### Rule 9. Krea 2 Turbo
* UNet: `models/diffusion_models/Krea2Turbo/krea2_turbo_int8_convrot.safetensors`
* TE: `qwen3vl_4b_fp8_scaled.safetensors`, CLIPLoader type `"krea2"`
* VAE: `qwen_image_vae.safetensors`
* 기본: **8 steps**, **CFG 1.0**, sampler **`euler_ancestral`**, scheduler **`simple`**
