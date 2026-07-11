# 🎭 AI 에이전트용 프로급 캐릭터 시트 생성 시스템 — 기획 / 설계 / 작업 계획

- **작성일**: 2026-07-11
- **상태**: 기획·설계 완료 + **구현 스펙 착수 가능** (코드 P1~P2 대기)
- **범위**: 프로 제작 관행 리서치 → AI 에이전트용 캐릭터 패키지 설계 → 영상 연계 → 단계별 작업 계획
- **구현 착수 문서 (코딩 시 이것을 연다)**: [character_impl_spec.md](character_impl_spec.md)
- **관련 문서**: [video_pipeline_roadmap.md](video_pipeline_roadmap.md), [moody_workflow_guide.md](moody_workflow_guide.md), [../agent_rules.md](../agent_rules.md)
- **현재 기반**: Z-Image-Turbo (Flow Matching) + Moody T2I / I2I (`127.0.0.1:8188`)

---

## 0. 한 줄 요약

프로 현장의 캐릭터 시트는 **“예쁜 일러스트 한 장”이 아니라, 여러 부서가 같은 인물을 재현하기 위한 규격 레퍼런스 패키지**다.  
AI 에이전트 영상 파이프라인에서는 이를 **`characters/<id>/` 패키지 (바이블 + approved refs + 선택적 LoRA + 샷 주입 규칙)** 로 재해석해야 한다.  
현재 T2I/I2I만으로는 초안 수준만 가능하며, **프로덕션급을 목표로 하면 시트 자동화 + 아이덴티티 고정(LoRA 중심) + 영상 연계 규약**을 단계적으로 구축할 수 있다.

### 0.1 문서 역할 분리

| 문서 | 역할 | 코딩 시 |
|------|------|---------|
| **본 문서** | Why / What / 장기 What-next | 배경 참조 |
| **[character_impl_spec.md](character_impl_spec.md)** | How / CLI 계약 / 티켓 / 에러코드 | **필수 SSOT** |
| **[characters/sheet_presets.json](../characters/sheet_presets.json)** | 시트별 prompt·denoise·cfg | expand 구현 SSOT |
| **[characters/_template/](../characters/_template/)** | 패키지 스캐폴드 | create가 복사 |
| **[characters/pilots/](../characters/pilots/)** | 파일럿 브리프 | E2E 검증 |

### 0.2 활성 트랙

```text
CHARACTER_L2_SOFT_FACTORY
완료: P1 + P2 + 파일럿 mina_park_v1 E2E
다음: P2.5 용도 프로필(video_ref | artbook) → ControlNet turnaround / shot
L3 LoRA / I2V 본구현은 별 트랙
```

### 0.3 용도 프로필 (Purpose Profiles)

캐릭터 시트는 **인쇄 아트북 전용**이 아니라, 기본은 **영상 일관성 첨부(ref pack)** 이다.  
동시에 아트북·프레젠테이션 고퀄 시트가 필요할 수 있으므로 **프로필로 분기**한다.

| 프로필 | 용도 | 해상도 감 | MVP |
|--------|------|-----------|-----|
| **`video_ref`** (기본) | 키프레임/I2V 일관성 첨부 | ~1024² / 전신 세로 1024×1536 | master + expression |
| **`artbook`** | 결과물형 시트·인쇄 지향 | ~1536²+ / 업스케일 옵션 | master+turn+expr+costume+pose |

- **SSOT**: [characters/profiles.json](../characters/profiles.json)
- **상세 스펙·CLI·티켓**: [character_impl_spec.md §1.5](character_impl_spec.md) / Ticket **P2.5**
- 엔진 WF(T2I/I2I/ControlNet)는 프로필마다 복제하지 않음. identity 패키지는 공유.

---

## 1. 목표와 비목표

### 1.1 목표
1. AI 에이전트가 **재사용 가능한 프로급 캐릭터 에셋**을 생성·관리할 수 있게 한다.
2. 생성된 캐릭터가 **멀티샷 키프레임 → I2V → 최종 조립 영상**까지 일관성을 유지하도록 연결 규약을 정의한다.
3. 기존 Moody T2I/I2I를 폐기하지 않고 **시트 원본 생성기 / 샷 연출기**로 확장한다.

### 1.2 비목표 (1차)
- 디즈니/게임 스튜디오 수준의 construction 도해·마우스 차트·다국어 스타일 가이드 전체 자동화
- 실시간 3D 리깅 / 페이스 캡처 파이프라인
- 상업 배포용 캐릭터 IP 법무 체계

### 1.3 성공 기준 (Definition of Done)

| 레벨 | 기준 | 타깃 |
|------|------|------|
| **L1** | 마스터 1장 + I2I 파생 6장 이상, 폴더 규약 저장 | 프로토 |
| **L2** | turnaround / expression / costume 시트 + `bible.json` + approved refs | 프로덕션 최소 |
| **L3** | 캐릭터 LoRA + 멀티샷 얼굴 일관성 통과 + I2V 키프레임 주입 | 스토리 영상용 |
| **L4** | 에피소드 단위 버전 관리, 다중 캐릭터 scale, 검수 루프 | 스튜디오형 (후순위) |

**1차 제품 목표: L2 달성, L3 설계까지 문서·인터페이스 확정.**

---

## 2. 리서치: 프로가 쓰는 캐릭터 시트 형태

### 2.1 프로 정의 — “Model Sheet / Character Sheet”

애니·게임·VFX 프리비즈에서 캐릭터 시트(모델 시트)는:

> **다른 아티스트/부서가 이 자료만 보고 동일 캐릭터를 다시 그릴 수 있게 하는 공식 레퍼런스**

역할은 세 가지다.
1. **시각 일관성** — 얼굴·비율·의상·색이 컷마다 흔들리지 않게
2. **연기 가이드** — 표정·포즈·버릇으로 성격 전달
3. **부서 간 커뮤니케이션** — 스토리보드·애니·컬러·프롭 팀이 같은 기준 사용 (수정 비용 절감)

참고: 스튜디오 파이프라인 관점의 정리 (turnaround, expression, pose, props, color, annotations).  
(CGWire, Clip Studio Art Rocket, 업계 모델시트 튜토리얼 등)

### 2.2 표준 시트 유형 (업계 공통)

| 유형 | 영문 | 내용 | 최소 구성 |
|------|------|------|-----------|
| **구성/비율 시트** | Construction | head count 비율, 이목구비 위치 가이드 | 전신 비율 1장 + 주석 |
| **헤드 턴어라운드** | Head turnaround | 정면·3/4·측면·후면 머리 | 4방향 이상 |
| **전신 턴어라운드** | Body turnaround / Model turnaround | 정면·3/4·측면·후면 전신 | 4~8 view (산업 표준 8-point turnaround 언급 다수) |
| **표정 시트** | Expression sheet | 기쁨·슬픔·분노·놀람 등 | 기본 6표정+, 가능하면 각도 변형 |
| **포즈 시트** | Pose / Action sheet | 대표 동작, 실루엣 가독성 | 4~5 포즈 이상 |
| **컬러 키** | Color sheet / Palette | 피부·헤어·의상 HEX/주석, 명암 변형 | 스와치 + 라이팅 예시 |
| **의상/배리언트** | Costume variants | 기본복·외출복·야간 등 | 의상별 전신 1장+ |
| **프롭 연동** | Props | 소품 스케일, 착용 위치 | 캐릭터 대비 스케일 |
| **스케일 차트** | Scale chart | 다른 인물·문·차량 대비 키 | 멀티캐릭터 시 필수 |
| **주석/금칙** | Annotations / Do-Don't | “안경 두께”, “눈 맞춤” 등 규칙 | 텍스트 + 잘못된 예 |

### 2.3 전통 포맷 (파일/레이아웃)

| 포맷 | 용도 | 비고 |
|------|------|------|
| **단일 그리드 이미지** (A3/인쇄용) | 한눈에 보는 모델 시트 | 인쇄·공유에 강함, AI 재사용엔 약함 |
| **분리 에셋 세트** (뷰별 PNG) | 제작 파이프라인 실사용 | 3D 모델링·애니 레퍼에 유리 |
| **스타일 가이드 PDF/바인더** | 시리즈 전체 규칙 묶음 | turnaround+pose+expression+BG+폰트+Do/Don't |
| **Character Bible (문서)** | 성격·배경·외형 서술 | 작가/쇼러너 중심, 비주얼 시트와 병행 |
| **해상도 관행** | 인쇄 시 고해상 (예: ~3300×2550급 언급) | 디지털 AI 파이프에선 **뷰별 1024~1536+** 분리 저장이 더 중요 |

**핵심 시사점:**  
프로는 “한 장 시트 이미지”와 “분리 레퍼런스 + 규칙 문서”를 **함께** 쓴다.  
AI 에이전트에게는 **분리 에셋 + 기계 판독 가능한 bible**이 본체이고, 그리드 시트는 **사람 검수용 뷰**다.

### 2.4 8-point turnaround 관행

애니 업계에서 턴어라운드는 단순 4뷰를 넘어 **8방향 회전**(정면 → 3/4 → 측면 → 3/4 백 → 후면 …)을 표준으로 다루는 교육·실무 자료가 많다.  
AI 1차에서는:

- **MVP**: front / three-quarter / side / back (4뷰)
- **프로 확장**: 8-point + head-only turnaround

를 권장한다.

### 2.5 Character Bible (비주얼 시트의 텍스트 쌍)

시나리오·TV 제작에서 character bible은 외형뿐 아니라:

- 동기, 성격, 말투, 관계, 배경
- 외형 디테일 (흉터, 헤어 습관, 옷 취향)
- 시리즈 일관성용 고정 사실

을 담는 **서술 레퍼런스**다.  
AI 영상 에이전트에게는 이를 **`bible.json` + 자연어 프롬프트 블록**으로 기계화해야 한다.

---

## 3. 리서치: AI/ComfyUI 쪽 캐릭터 일관성 실무

### 3.1 업계/커뮤니티에서 검증된 계층

| 계층 | 기술 | 일관성 | 적합한 상황 |
|------|------|--------|-------------|
| Soft | 동일 프롬프트 + 시드 관리 | 낮음 | 컨셉 탐색 |
| Soft+ | I2I denoise (현재 Moody) | 중하~중 | 로컬 편집, 짧은 파생 |
| Mid | IP-Adapter / FaceID 등 레퍼런스 주입 | 중 | 단역, 빠른 변형, 1~10장 레퍼 |
| **High** | **캐릭터 LoRA 학습** | **상** | 주연, 멀티샷, 에피소드 |
| Control | ControlNet (OpenPose/Depth 등) | 구조 고정 | 턴어라운드·동일 포즈 시트 |
| Hybrid | LoRA + ref + ControlNet | 최상 | 프로덕션 권장 |

커뮤니티 합의에 가까운 결론:
- **배치·변형·장기 프로젝트**에서는 학습된 **캐릭터 LoRA가 IP-Adapter를 크게 상회**한다.
- IP-Adapter는 **빠른 프로토 / 단역 / LoRA 데이터셋 시드**에 유용하나, “완벽한 멀티뷰 데이터셋 자동 생성”에는 한계가 보고된다.
- Z-Image Turbo 생태계에서는 **AI-Toolkit 등 LoRA 학습 + ControlNet 일관성 워크플로**가 이미 튜토리얼·실무 사례로 존재한다.

### 3.2 우리 환경(Z-Image + Moody)에 대한 함의

| 항목 | 함의 |
|------|------|
| 기존 T2I/I2I | 마스터 생성·샷 연출·데이터셋 시드로 유지 |
| 아이덴티티 본체 | **캐릭터 LoRA**를 L3 목표의 기본 경로로 설정 |
| 시트 기하 구조 | ControlNet 포즈 템플릿으로 turnaround 규격화 |
| 빠른 경로 | LoRA 없이 I2I+approved ref (L1~L2 일부) |
| 영상 연계 | 시트/LoRA로 **키프레임 일관성**을 먼저 확보 → I2V는 그 키프레임을 애니메이트 |

---

## 4. 제품 정의: 에이전트용 “캐릭터 패키지”

프로 시트를 AI용으로 재정의한다.

```text
Character Package = Visual Model Sheets + Machine Bible + Identity Anchor + Agent API
```

### 4.1 권장 디렉터리 구조

```text
characters/
  <character_id>/                 # 예: mina_park_v1
    bible.json                    # 기계 판독 캐릭터 바이블
    bible.md                      # 사람 읽기용 요약 (선택)
    prompts/
      positive_core.txt           # 고정 외형 블록
      negative_core.txt           # 금지/붕괴 방지
      shot_templates.json         # 샷 타입별 프롬프트 템플릿
    identity/
      lora/                       # *.safetensors + meta.json (L3)
      trigger_words.txt
    refs/
      master/                     # 히어로 원본 (neutral light)
      turnaround/                 # front, qf, side, back, ...
      head/                       # head turnaround
      expression/                 # joy, sad, angry, ...
      pose/                       # idle, walk, sit, ...
      costume/                    # default, winter, formal, ...
      color/                      # palette card, lighting variants
      props/                      # (선택)
      scale/                      # (선택, 멀티캐릭터)
    sheets/                       # 사람 검수용 그리드 합성본
      turnaround_grid.png
      expression_grid.png
      full_model_sheet.png
    approved/                     # 검수 통과 심볼릭/복사본만
      *.png
    dataset/                      # LoRA 학습용 (raw/cleaned/captions)
      raw/
      cleaned/
      captions/
    versions/
      CHANGELOG.md
    manifest.json                 # 패키지 인덱스, 해시, 상태
```

### 4.2 `bible.json` 스키마 (초안)

```json
{
  "id": "mina_park_v1",
  "display_name": "Mina Park",
  "version": "1.0.0",
  "status": "approved",
  "created_at": "2026-07-11",
  "style": {
    "medium": "cinematic_photoreal",
    "base_model": "moody_pro",
    "look": "Korean woman, mid-20s, natural skin texture, film still"
  },
  "appearance": {
    "age_range": "mid-20s",
    "gender_presentation": "female",
    "ethnicity_notes": "East Asian / Korean",
    "face": "oval face, soft jaw, warm brown eyes, straight brows",
    "hair": "shoulder-length dark brown hair, soft natural waves",
    "body": "average height, slim-athletic build",
    "distinctive": ["small mole under left eye"],
    "wardrobe_default": "black crew-neck tee, light wash jeans, minimal jewelry"
  },
  "prompts": {
    "positive_core": "Mina Park, [LOCKED APPEARANCE BLOCK]...",
    "negative_core": "identity shift, different person, extra fingers, warped face...",
    "trigger": "mina_park_v1"
  },
  "identity": {
    "mode": "lora_plus_refs",
    "lora_path": "identity/lora/mina_park_v1.safetensors",
    "lora_strength_default": 0.85,
    "primary_ref": "approved/master_front.png",
    "fallback_refs": ["approved/head_front.png", "approved/turn_front.png"]
  },
  "consistency_rules": {
    "must_keep": ["face identity", "hair length/color", "mole under left eye"],
    "may_change": ["outfit", "lighting", "background", "pose"],
    "forbidden": ["glasses", "tattoos", " drastical age-up"]
  },
  "performance": {
    "personality": ["reserved", "observant", "warm when comfortable"],
    "default_expression": "soft neutral smile",
    "mannerisms": ["tucks hair behind ear when thinking"]
  },
  "sheet_index": {
    "turnaround": ["refs/turnaround/front.png", "refs/turnaround/side.png"],
    "expression": ["refs/expression/joy.png", "refs/expression/sad.png"]
  },
  "video_defaults": {
    "preferred_keyframe_ref": "approved/master_front.png",
    "i2v_motion_style": "subtle natural motion, cinematic camera",
    "max_identity_risk_denoise": 0.78
  }
}
```

### 4.3 생성해야 할 시트 산출물 (에이전트 체크리스트)

#### MVP (L2)
- [ ] Master hero (neutral light, simple BG, front upper-body + full-body)
- [ ] Turnaround 4뷰 (front / 3-4 / side / back)
- [ ] Expression 6종 (neutral, joy, sad, angry, surprise, think)
- [ ] Costume 1~2 변형
- [ ] Color notes (텍스트 또는 palette card)
- [ ] `bible.json` + `manifest.json`
- [ ] 사람/에이전트 검수 후 `approved/` 복사
- [ ] (선택) turnaround_grid / expression_grid 합성

#### Pro 확장 (L3+)
- [ ] Head turnaround
- [ ] 8-point body turnaround
- [ ] Pose/action sheet 4+
- [ ] Lighting variants (day/night/neon)
- [ ] Prop scale
- [ ] Multi-character scale chart
- [ ] Character LoRA + trigger
- [ ] Dataset captions + training meta

---

## 5. 시스템 설계

### 5.1 아키텍처 개요

```text
┌─────────────────────────────────────────────────────────────┐
│                     Agent Orchestrator                       │
│  create_character / expand_sheets / approve / use_in_shot   │
└───────────────┬─────────────────────┬───────────────────────┘
                │                     │
                ▼                     ▼
     ┌──────────────────┐   ┌────────────────────┐
     │ Character Factory│   │ Shot Factory       │
     │ (시트 생성)       │   │ (키프레임·I2V)     │
     └────────┬─────────┘   └─────────┬──────────┘
              │                       │
     ┌────────▼────────┐     ┌────────▼──────────┐
     │ Moody T2I/I2I   │     │ Character Package │
     │ + ControlNet*   │◄────│ bible/refs/lora   │
     │ + LoRA load*    │     └───────────────────┘
     └────────┬────────┘
              │
     ┌────────▼────────┐
     │ I2V / Upscale / │
     │ FFmpeg Assemble │  ← video_pipeline_roadmap
     └─────────────────┘
```

\* ControlNet / LoRA 로드는 구현 단계에서 워크플로 확장.

### 5.2 파이프라인 단계 (Character Factory)

```text
Phase CF0  Concept lock
  - 사용자/에이전트 입력: 한 줄 로그라인 + 외형 키워드 + 스타일
  - 출력: bible draft (status=draft)

Phase CF1  Master generation
  - T2I (Moody)로 후보 N장 (시드 기록)
  - 사람 또는 비전 루프 선별 → master

Phase CF2  Soft sheet expansion (LoRA 전)
  - I2I 체인: turnaround/expression/costume 후보
  - denoise 레시피 적용 (기존 스위트 스팟)
  - 실패 컷 재시도

Phase CF3  Structure lock (권장)
  - ControlNet pose templates로 턴어라운드 정렬
  - 동일 포즈 스탠딩 템플릿에 캐릭터 투영

Phase CF4  Identity bake (L3)
  - approved refs → dataset 정제
  - Z-Image 캐릭터 LoRA 학습
  - LoRA 장착 재생성으로 시트 재베이크 (품질 점프)

Phase CF5  Package & approve
  - sheets 그리드 합성
  - approved/ 확정, version bump
  - manifest 해시/경로 기록
```

### 5.3 기존 Moody 도구 매핑

| 기존 도구 | 캐릭터 시스템에서의 역할 |
|----------|-------------------------|
| `generate_moody.py` (T2I) | 마스터·신규 각도 후보 생성 |
| `generate_moody_i2i.py` (I2I) | 마스터 기반 파생, 의상/표정/조명 |
| I2I denoise 0.70~0.73 | 소품·미세 디테일 |
| I2I denoise 0.75~0.78 | 조명/분위기 (얼굴 유지 우선) |
| I2I denoise 0.82~0.86 | 포즈/의상 큰 변화 (검수 필수) |
| CFG ≥ 3.5 | I2I 프롬프트 반영력 확보 |

### 5.4 신규 컴포넌트 (구현 대상)

| ID | 컴포넌트 | 형태 | 설명 |
|----|----------|------|------|
| C1 | `characters/` 규약 + 템플릿 | 폴더/스키마 | bible/manifest 템플릿 |
| C2 | `character_create.py` | CLI | 바이블 초안 + 마스터 T2I |
| C3 | `character_expand_sheets.py` | CLI | I2I/배치로 시트 확장 |
| C4 | `character_approve.py` | CLI | approved 승격, 버전 |
| C5 | Pose template pack | 이미지/JSON | OpenPose 등 턴어라운드 템플릿 |
| C6 | ControlNet sheet WF | Comfy JSON | 구조 고정 시트 생성 |
| C7 | LoRA train recipe | 문서+스크립트 | 데이터셋→학습→검증 |
| C8 | LoRA-aware T2I/I2I WF | Comfy JSON+py | 기존 생성기에 LoRA 주입 |
| C9 | Grid composer | 스크립트 | turnaround/expression 그리드 |
| C10 | `shot_with_character.py` | CLI | bible+refs(+LoRA)로 샷 키프레임 |
| C11 | Vision QA (선택) | 스크립트 | 얼굴 유사도/붕괴 휴리스틱 |

### 5.5 에이전트 CLI 인터페이스 (초안)

```bash
# 1) 캐릭터 생성 (바이블 + 마스터 후보)
python scripts/character_create.py \
  --id mina_park_v1 \
  --name "Mina Park" \
  --prompt "..." \
  --model pro \
  --candidates 4

# 2) 시트 확장
python scripts/character_expand_sheets.py \
  --id mina_park_v1 \
  --sheets turnaround,expression,costume \
  --model pro

# 3) 검수 승격
python scripts/character_approve.py \
  --id mina_park_v1 \
  --from refs/turnaround/front_03.png \
  --as approved/turn_front.png

# 4) 샷 키프레임 (스토리 연출)
python scripts/shot_with_character.py \
  --id mina_park_v1 \
  --shot "medium shot, rainy night street, holding umbrella" \
  --ref approved/master_front.png \
  --denoise 0.78 \
  --out shots/ep01_s03.png

# 5) (이후) I2V
python scripts/generate_i2v.py -i shots/ep01_s03.png -p "slow push-in, wind on hair" -o clips/ep01_s03.mp4
```

### 5.6 필수 CLI 개선 (기존 스크립트)

캐릭터 재현을 위해 기존 생성기에 다음이 필요하다.

| 개선 | 이유 |
|------|------|
| `--seed` 고정/재현 | 동일 후보 재생성 |
| `--negative` / 코어 프롬프트 파일 로드 | bible 블록 주입 |
| LoRA path + strength | L3 identity |
| 출력 메타 JSON (seed, model, prompt hash) | 추적성 |
| 해상도/배치 옵션 | 시트 일괄 생성 |

---

## 6. 비디오 생성 도구와의 연계 (일관성 E2E)

### 6.1 원칙

```text
캐릭터 일관성은 "영상 모델"이 아니라
"키프레임 단계에서 이미 고정"되어야 한다.
```

I2V/T2V는 얼굴을 다시 해석하는 경향이 있다.  
따라서 프로덕션 순서는 항상:

```text
Character Package
  → Shot Keyframes (T2I/I2I + LoRA/refs)
  → Optional keyframe refine (face detail)
  → I2V per shot (짧은 클립)
  → Continuity (last-frame handoff)
  → Upscale / Interpolate
  → FFmpeg assemble + audio
```

### 6.2 샷 타입별 레퍼런스 선택 규칙

| 샷 타입 | 우선 ref | identity 전략 | denoise 가이드 |
|---------|----------|---------------|----------------|
| Extreme close-up | `head/front` or expression | LoRA 강 + ref | I2I 낮게~중 |
| Close-up / Medium | `master` or `turn_front` | LoRA + ref | 0.70~0.78 |
| Full body action | turnaround + pose ref | LoRA + ControlNet pose | 0.82~0.86 (검수) |
| Costume change | costume ref | LoRA + 의상 프롬프트 | 0.78~0.85 |
| Night/mood | master + lighting prompt | LoRA 유지, 조명만 | 0.75~0.78 |
| B-roll (얼굴 미미) | 약 ref 또는 없음 | 낮은 우선순위 | 자유 |

### 6.3 I2V 연계 시 일관성 체크리스트

1. **키프레임 승인 전에는 I2V 금지** (`approved` 또는 샷 검수 플래그)
2. 모션 프롬프트에 **정체성 붕괴 유발어 최소화**  
   (“transform into”, “morph”, “different person” 금지)
3. 카메라 움직임은 **약한 모션 우선** (slow pan / push-in / hair wind)
4. 클립 길이 **3~6초**부터 (길수록 identity drift)
5. 연속 샷은 **직전 클립 last frame** 또는 **같은 approved ref 계열** 사용
6. 얼굴 클로즈업 클립은 생성 후 **프레임 샘플 검수** (자동/수동)
7. 동일 캐릭터 에피소드 단위로 **LoRA strength / CFG 프로필 고정**

### 6.4 데이터 흐름 (E2E 예시: 15~30초 쇼츠)

```text
1. character_create → mina_park_v1 (L2 package)
2. (옵션) train LoRA → L3
3. 샷리스트:
   S1 wide establishing (로케 중심, 캐릭터 작음)
   S2 medium 주인공 (master ref)
   S3 close-up 감정 (expression/sad)
   S4 action insert (pose + higher denoise, 검수)
4. 각 샷 키프레임 생성 → shots/ep01_sXX.png
5. I2V → clips/ep01_sXX.mp4
6. 업스케일/보간
7. FFmpeg concat + BGM/VO
8. final/ep01.mp4
```

### 6.5 영상 단계에서 캐릭터 패키지가 제공하는 것

| 제공물 | 영상 단계 사용처 |
|--------|------------------|
| `positive_core` / `negative_core` | 모든 키프레임 프롬프트 접두/접미 |
| `approved/*` | I2I 입력, IP-Adapter ref, 검수 기준 |
| LoRA | T2I/I2I(및 가능 시 I2V) identity |
| `video_defaults` | 모션 스타일, 위험 denoise 상한 |
| expression refs | 감정 비트 키프레임 |
| costume refs | 장면별 의상 연속성 |
| manifest version | 재현·롤백 (“v1 얼굴로 재렌더”) |

### 6.6 실패 모드와 대응

| 증상 | 원인 | 대응 |
|------|------|------|
| 컷마다 다른 사람 | LoRA 없음/약함, ref 미사용 | L3 LoRA, approved ref 강제 |
| 측면만 붕괴 | 측면 데이터 부족 | turnaround side 추가 학습/생성 |
| I2V 후 얼굴 붕괴 | 과도한 모션/긴 클립 | 짧은 클립, 약한 모션, 키프레임 재생성 |
| 의상은 맞는데 연령 변동 | 프롬프트 drift | bible must_keep + negative 강화 |
| 시트는 좋은데 샷이 다름 | 샷 프롬프트가 core를 덮음 | 프롬프트 템플릿 강제 조립 |
| LoRA 과적합 (모든 컷 동일 포즈) | 데이터셋 편중 | 포즈/표정 다양 데이터, strength 하향 |

---

## 7. 품질 기준 (프로급 판정)

### 7.1 시트 품질 게이트

| 게이트 | 기준 |
|--------|------|
| G1 Identity | 동일 인물로 인지 (주관 + 가능 시 임베딩 유사도) |
| G2 Proportion | 전신 비율이 뷰 간 크게 안 흔들림 |
| G3 Features | 지정 특징(점, 헤어 등) 유지 |
| G4 Readability | 실루엣·의상 디테일 판독 가능 |
| G5 Neutrality (master) | 과장 포즈/극단 조명 없는 마스터 |
| G6 Coverage | MVP 시트 목록 충족 |
| G7 Traceability | seed/model/prompt/version 기록 |

### 7.2 영상 품질 게이트

| 게이트 | 기준 |
|--------|------|
| V1 | 연속 3샷 이상에서 주인공 동일 인물 |
| V2 | 감정 샷에서 표정 의도가 전달 |
| V3 | I2V 후 얼굴 붕괴 프레임 < 허용 임계 |
| V4 | 의상 연속성 (의도적 변경 제외) |
| V5 | 최종 15~30초 조립본에서 “다른 배우 캐스팅” 느낌 없음 |

---

## 8. 작업 계획 (로드맵)

### 8.1 전체 일정 감 (로컬 1인/에이전트 협업 기준)

| Phase | 이름 | 산출물 | 의존 |
|-------|------|--------|------|
| **P0** | 규약·스키마 확정 | 폴더 템플릿, bible/manifest 스키마 | 없음 |
| **P1** | 기존 CLI 재현성 강화 | seed/meta/prompt file 지원 | P0 |
| **P2** | Soft Character Factory | create/expand/approve CLI (I2I 기반 L2) | P1 |
| **P2.5** | 용도 프로필 | `video_ref` / `artbook` size·MVP·export | P2 |
| **P3** | 시트 템플릿·그리드 | pose templates, grid composer (artbook 연계) | P2.5 |
| **P4** | ControlNet 시트 WF | 구조 고정 turnaround | P2/P3, 모델 확보 |
| **P5** | LoRA 학습 파이프 | dataset recipe + train + validate (L3) | P2 |
| **P6** | LoRA 연동 생성 WF | T2I/I2I LoRA 주입 | P5 |
| **P7** | Shot-with-character | 스토리 키프레임 CLI (`video_ref` 기본) | P2/P6 |
| **P8** | I2V 연계 규약 구현 | roadmap의 I2V와 연결 | P7 + I2V 도구 |
| **P9** | QA·문서·에이전트 핸드북 | 검수 체크리스트, agent_rules 갱신 | P7~P8 |

### 8.2 상세 작업 패키지

#### P0 — 규약 (문서/템플릿) — ✅ 완료 (2026-07-11)
- [x] 본 설계 문서 작성
- [x] [character_impl_spec.md](character_impl_spec.md) 구현 착수 스펙
- [x] `characters/_template/` 생성
- [x] `characters/schemas/bible.schema.json` / `manifest.schema.json`
- [x] `characters/sheet_presets.json` (시트 프리셋 SSOT)
- [x] 명명 규칙·에러 코드·CLI 계약 문서화
- [x] 파일럿 브리프 `mina_park_v1`

#### P1 — 기존 스크립트 재현성 — ✅ 코드 완료
- [x] `generate_moody.py`: `--seed`, `--meta-out`, `--prompt-file` 등
- [x] `generate_moody_i2i.py`: 동일 + `--core-prefix-file`
- [x] `lib/comfy_client.py` 추출
- [x] process.md / README 사용 예 업데이트
- [ ] 실 Comfy 스모크 테스트

#### P2 — Soft Character Factory (LoRA 없이 L2) — ✅ 코드 + 파일럿 E2E 완료
- [x] `character_create.py`
- [x] `character_expand_sheets.py` + `sheet_presets.json` 로드
- [x] `character_approve.py`
- [x] 파일럿 `mina_park_v1` E2E (표현 OK / turnaround 약함 — PILOT_NOTES)

#### P2.5 — 용도 프로필 (`video_ref` | `artbook`) — 스펙 ✅ / 코드 대부분 ✅
- [x] 설계: 동일 패키지 + 프로필별 해상도·MVP·export ([impl §1.5](character_impl_spec.md))
- [x] SSOT: [characters/profiles.json](../characters/profiles.json)
- [x] CLI `--profile` (create/expand/approve), 기본 `video_ref`
- [x] create: 프로필 size → T2I width/height; artbook full-body 기본
- [x] 프로필별 `mvp_aliases` / `missing_mvp` / `all_mvp`
- [x] `exports/` 디렉터리 + bible.exports status
- [ ] I2I 출력 강제 리사이즈 (현재 size_hint만; ControlNet/후속)
- [ ] artbook upscale + grid (P3 연계, 후순위)

#### P3 — 그리드·템플릿
- [ ] expression/turnaround grid 합성 (`artbook.grid_export`)
- [ ] 포즈 템플릿 이미지 팩 (스탠딩 front/side/back)
- [ ] 사람 검수용 `sheets/full_model_sheet.png` 생성

#### P4 — ControlNet (품질 점프)
- [x] Z-Image ControlNet 러너 연동 (`generate_moody_controlnet.py` + expand)
- [x] 포즈 템플릿 생성기 (`lib/pose_templates.py`) + edge preprocess
- [x] turnaround preset → `engine: controlnet` 기본
- [x] **full-body master 경로** (`lib/fullbody_source.py`) + expand 자동 ensure
- [x] empty-latent CN 옵션 (`--engine controlnet_empty` / `--empty-latent`)
- [x] 실측: full-body 소스로 전신 구도 유지 성공 (side/back 각도·아티팩트는 잔여)
- [ ] OpenPose/실사 포즈 맵으로 side/back 각도 정밀화

#### P5~P6 — LoRA (L3)
- [ ] 데이터셋 최소 기준 문서 (15~40장, 각도/표정 다양, 클린 BG 권장)
- [ ] 학습 설정 프리셋 (AI-Toolkit 등, 환경 확정 후)
- [ ] 학습 후 검증 프롬프트 세트 (같은 인물 / 다른 장면 10종)
- [ ] LoRA 로드가 포함된 T2I/I2I JSON + CLI

#### P7~P8 — 영상 연결
- [ ] `shot_with_character.py`
- [ ] 샷리스트 YAML 스키마 (`episode.yaml`)
- [ ] I2V 입력 규약 (키프레임 경로, motion prompt, duration)
- [ ] `video_pipeline_roadmap.md`와 API 명칭 정렬

#### P9 — 운영
- [ ] 에이전트 규칙: “스토리 샷은 approved 캐릭터만”
- [ ] 실패 시 롤백/재학습 가이드
- [ ] 샘플 쇼츠 1편으로 게이트 V1~V5 통과 시도

### 8.3 우선순위 권장 (지금 당장)

```text
1순위  P0 + P1 + P2     → ✅ 완료 (L2 도구 + 파일럿)
2순위  P2.5 용도 프로필 → video_ref 기본 / artbook 옵션 코드화
3순위  P4 ControlNet    → turnaround 품질 (video_ref 옵션 + artbook 필수에 가깝)
4순위  P7 shot_with_character → 영상 레퍼 팩 실사용
5순위  P5 + P6 LoRA / P8 I2V
```

> 기본 프로필은 항상 **`video_ref`**. artbook은 필요할 때만 `--profile artbook`.  
> 스토리 주연 영상은 L2 ref 팩 이후 L3 LoRA·I2V로 확장.

---

## 9. 리스크와 결정 필요 사항

### 9.1 기술 리스크
| 리스크 | 영향 | 완화 |
|--------|------|------|
| Z-Image용 ControlNet/IP-Adapter 호환 불완전 | 시트 구조 고정 약화 | LoRA+I2I 우선, ControlNet은 검증 후 |
| LoRA 학습 VRAM/시간 | L3 지연 | 소수 장 고품질 데이터, micro-LoRA 옵션 |
| I2V identity drift | 최종 영상 붕괴 | 짧은 클립, 키프레임 재생성, 모션 약화 |
| Moody 커스텀 노드 의존 | API 매핑 깨짐 | agent_rules Rule 2 준수, 표준 노드 우선 |

### 9.2 제품 결정 (파일럿 기본값 — 구현 스펙에 반영됨)
1. **타깃 매체**: `cinematic_photoreal` (실사) — 확정(파일럿)
2. **주연 일관성 수준**: **L2** 먼저, L3 LoRA는 후속 — 확정(트랙)
3. **검수 주체**: **사람 approve 필수** — 확정(파일럿)
4. **첫 파일럿**: `mina_park_v1` 캐릭터 팩 → 이후 9:16 쇼츠 키프레임(P7)

---

## 10. 기존 로드맵과의 관계

| video_pipeline_roadmap 항목 | 본 문서 대응 |
|----------------------------|--------------|
| Character ref pack | **본 시스템의 본체** |
| T2I / I2I | Character Factory + Shot Factory 엔진 |
| I2V | 키프레임 이후 단계, 패키지의 `video_defaults` 사용 |
| Upscale / Assemble | 캐릭터 이후 공통 마감 층 |

권장 병행 순서:

```text
Character L2 (본 문서 P0~P2)
    +
I2V MVP (video roadmap P0)
    →
shot_with_character + I2V (스토리 1편 파일럿)
    →
Character L3 LoRA
```

---

## 11. 참고 자료 (리서치)

### 프로 시트 / 제작 관행
- Clip Studio Art Rocket — Model Sheets for Character Designers (construction, head/body turnaround, color, expression, pose)
- CGWire — Character Sheets as blueprint for consistent animation (turnaround, expression, pose, props, color palette, annotations)
- 업계 교육/실무: 4~8 view turnaround, expression/pose sheets, style guide 묶음 (Do/Don't 포함 사례)
- Character bible (시나리오/TV): 외형+성격+관계의 서술 레퍼런스

### AI 일관성 / Z-Image
- ComfyUI 캐릭터 일관성: IP-Adapter(빠른 ref) vs **Character LoRA(장기·배치 우위)** 커뮤니티 합의
- Z-Image Turbo LoRA 학습 가이드·AI-Toolkit / ControlNet 연계 튜토리얼 (2025~2026)
- I2V 파이프라인 권장: 키프레임 단계에서 identity 고정 후 모션

> 웹 자료는 도구 버전이 빠르게 바뀌므로, **구현 착수 시 Z-Image 호환 ControlNet/LoRA 학습 설정을 로컬에서 재검증**할 것.

---

## 12. 다음 즉시 액션

1. ~~P0~P2 / P2.5 / 파일럿 / full-body CN / P7 shot / I2V MVP~~ ✅
2. **FFmpeg 조립** (클립 concat + 오디오 슬롯)
3. **포즈맵 개선** (turn 선 아티팩트·side/back 각도)
4. P2.5e artbook upscale/grid (여유 시)
5. L3 캐릭터 LoRA

---

## 13. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 초안 작성 — 프로 시트 리서치, 패키지 설계, 영상 연계, 작업 계획 |
| 2026-07-11 | 구현 착수 가능 수준으로 보강 — impl spec, presets, schemas, template, pilot, P0 완료 처리 |
| 2026-07-11 | **용도 프로필** (`video_ref` / `artbook`) 스펙·작업 계획 P2.5 추가, `profiles.json` |
