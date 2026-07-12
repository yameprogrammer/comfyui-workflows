# OpenMontage 제작 레시피(파이프라인) 목록

- **작성일**: 2026-07-12  
- **대상**: `OpenMontage_full/pipeline_defs/*.yaml`  
- **상태**: **목록·설명 READY** · agent_custom **공식 연동 아님** (참고용)  
- **관련**: [openmontage_capability_catalog.md](openmontage_capability_catalog.md) · [openmontage_eval_notes.md](openmontage_eval_notes.md)

---

## 0. 레시피가 뭔가요?

OpenMontage에서 **파이프라인 YAML** = 한 종류의 영상을 끝내는 **제작 레시피**입니다.

| 포함되는 것 | 설명 |
|-------------|------|
| **stages** | idea / script / scene_plan / assets / edit / compose / publish … 순서 |
| **director skills** | 스테이지마다 에이전트가 읽을 지시 MD |
| **tools** | 그 단계에서 쓸 도구 목록 |
| **artifacts** | brief, script, scene_plan 등 남길 산출물 |
| **checkpoint** | 사람 승인·검수 게이트 |
| **playbook** | 추천 비주얼 스타일 (clean-professional 등) |

에이전트는 “그냥 영상 만들어”가 아니라 **이 레시피 중 하나를 고른 뒤** 스테이지를 따라갑니다.  
우리 `agent_custom`의 `episode_pipeline` / 캐릭·로케·샷 공정과는 **별 시스템**이고, 지금은 **참고 메뉴판**입니다.

경로:

```text
F:\ComfyUI_workflows\agent_custom\OpenMontage_full\pipeline_defs\
```

스테이지 스킬:

```text
OpenMontage_full\skills\pipelines\<recipe-name>\*-director.md
```

---

## 1. 한눈에 보는 목록

| 레시피 ID | 한글 한 줄 | 카테고리 | 안정성 | 우리 쇼츠와 |
|-----------|------------|----------|--------|-------------|
| [talking-head](#21-talking-head) | 말하는 사람 원본 → 편집·자막·믹스 | talking_head | beta | 구조 참고 (원본 실사 있을 때) |
| [cinematic](#22-cinematic) | 무드 중심 트레일러·브랜드·몽타주 | cinematic | production | 톤/페이싱 참고 |
| [clip-factory](#23-clip-factory) | 롱폼 1개 → 숏폼 N개 | custom | beta | **숏폼 리퍼포즈 참고 강** |
| [podcast-repurpose](#24-podcast-repurpose) | 팟캐스트 → 비주얼 클립 | custom | beta | 오디오 중심 재가공 |
| [localization-dub](#25-localization-dub) | 번역·자막·더빙·(선택) 립 | custom | beta | 다국어 확장 시 |
| [hybrid](#26-hybrid) | 실사 푸티지 + 그래픽/생성 보조 | hybrid | production | 화면+오버레이 혼합 |
| [screen-demo](#27-screen-demo) | 앱/터미널 데모 영상 | screen_recording | production | 제품 데모용 |
| [documentary-montage](#28-documentary-montage) | 실사 아카이브 검색→테마 몽타주 | documentary | beta | B-roll 몽타주 참고 |
| [animated-explainer](#29-animated-explainer) | 주제만 있으면 AI 설명 영상 | generated | production | 설명형 콘텐츠 |
| [animation](#210-animation) | 모션그래픽·도식·키네틱 타이포 | animation | production | 타이포/도식 위주 |
| [character-animation](#211-character-animation) | 로컬 카툰 캐릭 리그·포즈 애니 | animation | beta | 2D 캐릭 애니 (시트와 다른 축) |
| [avatar-spokesperson](#212-avatar-spokesperson) | 디지털 아바타 대변인 | custom | production | **립 스택 중복 → 비본선** |
| [framework-smoke](#213-framework-smoke) | 프레임워크 계약 스모크 | custom | beta | 개발 테스트 전용 |

---

## 2. 레시피별 설명

### 2.1 talking-head

- **파일**: `talking-head.yaml`  
- **한 줄**: 이미 찍힌 **말하는 사람 영상**을 받아, 전사 → 편집 판단 → 자막 → 오디오 믹스 → 최종 합성.  
- **스테이지 예**: idea → script → scene_plan → assets → edit → compose → publish  
- **언제 쓰나**: 인터뷰, 토크, 웨비나 얼굴 클립을 **숏폼/본편으로 다듬을 때**.  
- **입력 감각**: 원본 푸티지 중심 (생성 캐릭터 아님).  
- **우리와의 관계**: 시놉 기반 **AI 히어로인 생성**과는 다름. 다만 “전사·자막·믹스·게이트” 운영은 참고 가능.

### 2.2 cinematic

- **파일**: `cinematic.yaml`  
- **한 줄**: **분위기·감정 페이싱**이 중심인 트레일러, 브랜드 필름, 몽타주, 숏폼 드라마틱 편집.  
- **스테이지 예**: research → proposal → sample → script → scene_plan → assets → edit → compose → publish  
- **특징**: 사전 **리서치·컨셉 제안·샘플·승인** 후 본 제작. 공급 푸티지/스틸 위주, 빈 구간만 생성 보조.  
- **검수 포인트 (레시피 취지)**: 감정 페이싱, 컬러 일관, 오디오 다이내믹.  
- **우리와의 관계**: Quiet Luxury 쇼츠의 **톤·페이싱 게이트** 문구를 빌리기 좋음. 생성 엔진은 우리 Comfy.

### 2.3 clip-factory

- **파일**: `clip-factory.yaml`  
- **한 줄**: 웨비나·스트림·발표·인터뷰 **롱폼 1개 → 소셜용 숏클립 N개**.  
- **스테이지 예**: idea → script → scene_plan → assets → edit → compose → publish  
- **검수 포인트**: 클립 선정, 배치 일관성, **훅 배치**.  
- **우리와의 관계**: 유튜브 롱·릴스 **대량 컷** 공정 참고 1순위. agent_custom은 클립 단위 생성 강함, OM은 “원본에서 뽑기” 강함.

### 2.4 podcast-repurpose

- **파일**: `podcast-repurpose.yaml`  
- **한 줄**: 팟캐스트 오디오(또는 영상 팟캐스트) → 오디오그램/캡션 클립/인용 카드/(선택) 풀 에피 컴패니언 영상.  
- **검수 포인트**: 오디오 보존, 클립 선정, 다중 산출물 일관성.  
- **우리와의 관계**: 음성 에셋이 있을 때 시각화 레시피. 우리는 TTS·BGM 쪽과 역할이 다름.

### 2.5 localization-dub

- **파일**: `localization-dub.yaml`  
- **한 줄**: 기존 영상 → **번역 자막, 더빙, (선택) 립싱크 다국어 버전**.  
- **특징**: transcript-first.  
- **검수 포인트**: 번역 정확도, 타이밍, 로케일별 일관성.  
- **우리와의 관계**: 완성 쇼츠의 다국어 확장 시 참고. 본선 생성 경로 아님.

### 2.6 hybrid

- **파일**: `hybrid.yaml`  
- **한 줄**: **실사 + 설계/생성 보조 에셋** 혼합 (인터뷰+도식, 제품샷+오버레이, 스크린캡+그래픽 등).  
- **검수 포인트**: 소스/서포트 균형, 오버레이 밀도, 매체 간 통일감.  
- **우리와의 관계**: 키프레임 실사 톤 + 자막/그래픽을 얹을 때 개념적으로 가깝다. 생성은 Comfy, 오버레이는 후반.

### 2.7 screen-demo

- **파일**: `screen-demo.yaml`  
- **한 줄**: **앱/브라우저/코딩 데모** 영상.  
  1) REAL CAPTURE — 실제 화면 녹화 후 콜아웃·줌·자막·오디오 정리  
  2) SYNTHETIC — CLI/터미널 플로우는 Remotion TerminalScene 등으로 합성 녹화  
- **우리와의 관계**: SaaS 데모·튜토리얼용. 인플루언서 카페 쇼츠 본선과는 장르가 다름.

### 2.8 documentary-montage

- **파일**: `documentary-montage.yaml`  
- **한 줄**: 테마 브리프 → **실사 아카이브/스톡 코퍼스** 구축 → CLIP 검색으로 슬롯 채움 → 비트·음악 싱크·통일 그레이드 몽타주.  
- **소스 예**: Pexels, Archive.org, NASA, Wikimedia, Unsplash 등.  
- **스테이지**: idea → scene_plan → assets → edit → compose (publish 단계가 짧은 편).  
- **톤**: Adam Curtis / Chris Marker 류 테마 몽타주 영감.  
- **우리와의 관계**: B-roll·아카이브 중심. 캐릭터 시트 본선과 축이 다름.

### 2.9 animated-explainer

- **파일**: `animated-explainer.yaml`  
- **한 줄**: **주제/아이디어만**으로 AI 설명 영상 (나레이션·비주얼·음악).  
- **사전 제작**: research → proposal(비용 견적) → **유저 승인 후** sample → 본제작.  
- **스테이지**: research, proposal, sample, script, scene_plan, assets, edit, compose, publish  
- **우리와의 관계**: “팩트 설명 숏” 운영 참고. 이미지/영상 생성기는 OM 클라우드 쪽이 많을 수 있어 **엔진만 Comfy로 갈아 끼우는** 식으로 참고.

### 2.10 animation

- **파일**: `animation.yaml`  
- **한 줄**: 모션 그래픽, 도식 설명, 키네틱 타이포, 수학 비주얼, 일러스트 시퀀스 등 **애니 우선**.  
- **사전 제작**: research → proposal(애니 모드·비용) → 승인 → sample → …  
- **우리와의 관계**: Manim/HyperFrames/Remotion 쪽. agent_custom 포토리얼 캐릭 파이프와는 별 트랙.

### 2.11 character-animation

- **파일**: `character-animation.yaml`  
- **한 줄**: **로컬 재사용 카툰 캐릭** — 스크립트·씬플랜 → 캐릭 스펙, 리그, 포즈 라이브러리, 액션 타임라인 → SVG/Canvas/Remotion/HyperFrames 브라우저 렌더.  
- **명시**: 원격 비디오젠 대체가 아니라 **결정적 로컬 모션**.  
- **추가 스테이지**: character_design, rig_plan  
- **우리와의 관계**: 우리 `character_full_sheet` 는 **포토리얼 영상 레퍼**. OM 쪽은 **2D 리그 애니**. 개념(시트→포즈→타임라인)만 빌려볼 수 있음.

### 2.12 avatar-spokesperson

- **파일**: `avatar-spokesperson.yaml`  
- **한 줄**: **디지털 발표자**가 앵커인 대변인·온보딩·세일즈 인트로·짧은 스크립트 설명.  
- **검수 포인트**: 립싱크, 프레이밍, CTA.  
- **우리와의 관계**: agent_custom 정책상 **아바타 립 스택 중복 → 본선 비권장**. 게이트 레시피 구조만 참고.

### 2.13 framework-smoke

- **파일**: `framework-smoke.yaml`  
- **한 줄**: Phase 0 프레임워크 계약 검증용 **미니 파이프** (research, script 정도).  
- **용도**: OM 내부 개발/테스트. 콘텐츠 제작용 아님.

---

## 3. 스테이지 이름 빠른 사전

레시피마다 일부 생략/추가 있음. 자주 나오는 것:

| 스테이지 | 하는 일 (감각) |
|----------|----------------|
| **research** | 주제·레퍼런스·기법 조사 |
| **proposal** | 컨셉 2~3안 + 비용·리스크, 사람 승인 |
| **sample** | 값싼 샘플로 톤 확인 |
| **idea** | 브리프·목표 플랫폼·길이 |
| **script** | 대본·전사·타임스탬프 |
| **scene_plan** | 장면/비트 분해 |
| **character_design** / **rig_plan** | (캐릭 애니 전용) 디자인·리그 |
| **assets** | 이미지·클립·보이스 등 에셋 확보 |
| **edit** | 컷 판정·EDL 감각 |
| **compose** | 최종 영상 조립·렌더 |
| **publish** | 납품·플랫폼 패키지 |

---

## 4. agent_custom 쇼츠에 “빌려오기 좋은” 것

우선순위 감각 (공식 연동 전):

| 우선 | 빌릴 것 | 출처 레시피 감각 |
|------|---------|------------------|
| 1 | **체크포인트·사람 승인 위치** (에셋 후, 보드 후, 립 후) | talking-head / cinematic |
| 2 | **proposal + sample 후 본제작** | cinematic / explainer / animation |
| 3 | **훅·숏폼 선정 기준** | clip-factory |
| 4 | **하이브리드 오버레이 밀도 게이트** | hybrid |
| 5 | **생성 엔진 슬롯만 Comfy로** | 전 레시피의 assets/compose 자리 |

생성·일관성 본선은 계속:

```text
cast → character_full_sheet → location → look
→ story / shots → keyframes → tts → s2v/i2v → assemble → export workspace
```

레시피 결합 설계 초안이 필요하면 별도 문서 (`shorts_comfy_pipeline_recipe` 등)로 확장.

---

## 5. 관련 파일 맵

| 종류 | 경로 |
|------|------|
| 레시피 YAML | `OpenMontage_full/pipeline_defs/*.yaml` |
| 스테이지 스킬 | `OpenMontage_full/skills/pipelines/<id>/` |
| 스타일 playbook | `OpenMontage_full/styles/*.yaml` |
| 아티팩트 스키마 | `OpenMontage_full/schemas/artifacts/` |
| 기능 전체 카탈로그 | [openmontage_capability_catalog.md](openmontage_capability_catalog.md) |

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 레시피 13종 목록·설명 문서 초안 (YAML description 기반). |
