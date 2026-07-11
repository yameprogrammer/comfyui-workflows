# 📜 에이전트 작업 협업 규칙 및 핸드북 (agent_rules.md)

이 문서는 `agent_custom` 디렉토리 내에 위치한 워크플로우와 스크립트를 개선, 수정, 운영하려는 모든 AI 코딩 에이전트(개발자)들을 위한 공식 지침서입니다. 협업의 연속성과 품질을 유지하기 위해 반드시 아래 규칙들을 항상 숙지하고 준수해 주십시오.

---

## 📌 핵심 작업 규칙

### Rule 1. 이력 관리의 의무 (`process.md` 상시 업데이트)
* 코드를 수정하거나, 워크플로우 JSON 설정을 변경하거나, 성능을 최적화한 경우 **작업 즉시 `process.md` 최상단에 변경 이력을 추가**해야 합니다.
* 기록 시 **[작업 일자], [에이전트 이름], [작업 목표], [주요 변경 내역 및 파라미터 수치]**를 명확하게 포함해야 합니다.

### Rule 2. 자동화 스크립트 정합성 유지
* ComfyUI 웹 UI에서 워크플로우 JSON을 수정하여 저장했다면, 반드시 그에 매핑되는 파이썬 자동화 스크립트(`generate_moody.py` 혹은 `generate_moody_i2i.py`)의 `convert_ui_to_api` 노드 파싱 및 변수 주입 로직을 연동하여 갱신해 주어야 합니다.
* JSON만 바꾸고 스크립트 매핑을 생략하여 배치가 실패하게 만드는 행위는 금지됩니다.

### Rule 3. Flow Matching 모델 연산의 이해 및 보존
* 본 프로젝트의 코어 모델인 `Z-Image-Turbo`는 Flow Matching 아키텍처를 따릅니다.
* 일반적인 SDXL 등과 다른 스케줄 및 샘플러 특성을 가집니다. 특히 I2I(이미지 편집) 시에는 `res_multistep` 대신 **`euler`/`normal` 조합**을 사용해야 노이즈가 주입되며, **디노이즈 최적 임계치(`0.70 ~ 0.85`)**를 지켜야 캐릭터 아이덴티티와 프롬프트 반영력이 조화를 이룹니다.
* 타임스텝 왜곡이 발생하는 커스텀 시프터 노드는 I2I 시 우회해야 하며, 이 하드 와이어링 구조를 무단으로 변경하여 전체 배치를 망가뜨리지 않도록 유의하십시오.

### Rule 4. 경로 무결성 보존
* ComfyUI 환경 경로(`F:\ComfyUI_windows_portable\ComfyUI\`) 및 입력 캐시 경로 등은 이 시스템의 드라이브 명에 하드코딩된 부분이 있습니다. 
* 환경을 이전하거나 실행할 때 경로가 깨지지 않도록 절대 경로 수정 시 주의하십시오.

### Rule 5. 철저한 인수인계 핸드훅 남기기
* 작업을 마칠 때에는 항상 대화의 마지막 턴이나 생성한 문서에 **[현재 워크플로우의 안정성 상태], [새롭게 밝혀낸 물리적 법칙/임계치], [다음 에이전트가 이어서 착수해야 할 작업 추천]**을 일목요연하게 전달하여 연속성을 100% 보장하십시오.

### Rule 7. 영상 해상도·백엔드 규약
* 영상 **납품**은 기본 **16:9, 최소 1080p (1920×1080)** 를 목표로 한다. 상세: [video_delivery_and_backends.md](video_delivery_and_backends.md).
* I2V **생성**은 동일 종횡비의 **work 해상도**로 돌리고, 1080p는 **업스케일 마감 층**에서 올린다. 매 튜닝 루프마다 네이티브 1080p I2V를 기본으로 쓰지 말 것.
* I2V 백엔드는 상황에 따라 **`wan22`(기본)** / **`ltx23`(대안)** 등을 선택할 수 있는 구조로 확장한다. 구현 시 `video_backends.json` 및 `generate_i2v.py --backend` 를 SSOT로 맞출 것.

### Rule 6. 캐릭터 패키지 및 구현 스펙 준수
* 캐릭터 시트/일관성 관련 **코드 구현** 시 상위 설계([character_sheet_system_design.md](character_sheet_system_design.md))보다 **구현 스펙([character_impl_spec.md](character_impl_spec.md))** 을 우선한다.
* 시트별 denoise·프롬프트·approve 별칭은 **`characters/sheet_presets.json`을 SSOT**로 사용한다. 하드코딩 시 파일과 반드시 동기화할 것.
* 용도(영상 레퍼 vs 아트북) 설정은 **`characters/profiles.json`을 SSOT**로 한다. 기본 프로필은 **`video_ref`**. 해상도·MVP를 임의 하드코딩하지 말 것.
* 스토리 키프레임·영상용 인물 샷은 **`approved/`에 승격된 레퍼런스**만 기본 입력으로 사용한다 (`status=draft` 패키지를 본 촬영에 쓰지 말 것).
* 활성 트랙이 `CHARACTER_L2_SOFT_FACTORY`인 동안 **L3 LoRA 학습 / I2V 본구현을 같은 PR에 섞지 않는다** (스파이크는 별도 세션). ControlNet turnaround·프로필(P2.5)은 캐릭터 트랙 내 허용.
* 새 캐릭터 폴더는 `characters/_template/` 구조를 벗어나 임의로 만들지 않는다.
* 동일 인물을 위해 artbook/video 용도로 **character_id를 쪼개지 않는다** — 프로필·exports로 분기한다.
 
### Rule 7. Z-Image-Turbo 공식 ControlNet (Union 2.1) 운용 규정
* Z-Image-Turbo 전용 Union 2.1 컨트롤넷 모델 파일(`Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors`)은 일반 `controlnet` 폴더가 아닌 **`models/model_patches/`** 폴더에 배치해야 로더가 정상적으로 스캔합니다.
* 워크플로우 결합 시 프롬프트 Conditioning을 수정하는 표준 `ControlNetApply` 노드는 400 에러를 유발하므로, 모델 자체를 직접 패치하여 KSampler로 전송하는 **`ZImageFunControlnet`** 및 로더용 **`FL_ZImageControlNetPatch`** 노드를 필수적으로 연동해야 합니다.
* 컨트롤넷 강도는 `0.65 ~ 0.80` 사이를 권장하며, I2I 결합 시 디노이즈 `0.70` 선에서도 완벽한 자세 변환이 수행됨을 명심하십시오.

### Rule 8. Krea 2 Turbo 모델 운용 규정
* Krea 2 Turbo 모델 파일(`krea2_turbo_int8_convrot.safetensors`)은 `models/diffusion_models/Krea2Turbo/` 폴더에 배치해야 합니다.
* 텍스트 인코더는 `models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`를 사용하며, `CLIPLoader` 타입은 반드시 `"krea2"`로 매핑해야 합니다.
* VAE는 `models/vae/qwen_image_vae.safetensors`를 활용합니다.
* 샘플링 실행 시 **디노이즈 단계 8 steps**, **CFG 1.0**, **샘플러 `"euler_ancestral"`**, **스케줄러 `"simple"`** 설정을 준수하여 초고속 생성 효율을 보장해 주십시오.
