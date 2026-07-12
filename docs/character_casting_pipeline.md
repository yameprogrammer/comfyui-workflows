# 캐릭터 창조 공정 — 탐색 풀 → 승격 → 일관 시트

- **작성일**: 2026-07-12  
- **상태**: 설계 + CLI MVP  
- **관련**: [character_impl_spec.md](character_impl_spec.md), [character_sheet_system_design.md](character_sheet_system_design.md)

---

## 0. 한 줄

**캐스팅(오디션)** 과 **전속 시트 공장** 을 분리한다.  
탐색 단계에서는 모델을 섞어 후보를 뽑고, 확정 후에만 identity ref로 시트를 굳힌다.

```text
A cast_pool   →  다엔진 T2I 후보 (Moody real/pro/wild, Krea, …)
B promote     →  고른 1장 + 프롬프트로 character package 생성 + master_front 승인
C expand      →  기존 L2: I2I + approved ref (일관성)
D video       →  shot_compose / I2V / SI2V
```

---

## 1. 커뮤니티·업계에서 통하는 패턴 (리서치 요약)

| 출처 패턴 | 요지 | 우리 반영 |
|-----------|------|-----------|
| **Character sheet first** (Mickmumpitz, Reddit, Civitai) | 1 이미지 확정 → 표정/턴/의상 시트를 만들고, 그 ref로 씬 생성 | C 단계 = 기존 expand + approved |
| **IP-Adapter / InstantID / FaceID** | 확정 얼굴 ref 로 일관성 (탐색 단계에는 과함) | 후속 L2.5; 지금은 I2I ref 유지 |
| **ControlNet OpenPose turnaround** | multi-view 시트는 포즈 템플릿 필수 | 이미 expand CN 경로 있음 |
| **Multi-model casting** | 초안은 Flux/SDXL/전용 모델 여러 개로 “오디션” | **A: multi-engine cast pool** |
| **Human gate** | 자동 QA보다 사람 선택·approve | promote / character_approve |
| **Lock bible after cast** | 확정 후 positive_core·룩 고정 | promote 시 core 기록 |
| **video_ref vs artbook** | 용도별 해상도·MVP | profiles.json (기존) |
| **Contact sheet review** | 후보 그리드로 한눈에 비교 | cast pool → contact sheet |

**의도적으로 후순위:** 탐색 단계 LoRA 학습 (느림), 확정 전 InstantID (오버킬).

---

## 2. 단계 정의

### A — Cast pool (탐색)

| 항목 | 내용 |
|------|------|
| 단위 | `cast_id` (예: `heroine_ep01_cast`) |
| 경로 | `characters/casts/<cast_id>/` |
| 생성 | 엔진 목록 × 후보 수 T2I |
| 엔진 | `moody_real` / `moody_pro` / `moody_wild` / `krea` |
| 산출 | `candidates/*.png`, `manifest.json`, `contact_sheet.png` |
| 상태 | `open` → `shortlisted` → `promoted` / `archived` |

### B — Promote (승격)

| 항목 | 내용 |
|------|------|
| 입력 | cast 후보 경로 또는 임의 이미지 + appearance 프롬프트 |
| 출력 | `characters/<character_id>/` 패키지 |
| 동작 | template 복사 → cores 기록 → 이미지를 `refs/master` + **`approved/master_front`** + primary_ref |
| 다음 | `character_expand_sheets` (C) |

### C — Sheet factory (일관)

기존: `character_expand_sheets` + `character_approve`  
엔진 기본 **Moody I2I** (ref 고정). 탐색 엔진과 달라도 됨.

### D — Video

`shot_compose` → I2V/SI2V (별 문서).

---

## 3. CLI

```bash
# A) 다엔진 후보 풀
python scripts/character_cast_pool.py \
  --cast heroine_v1_cast \
  --prompt "mid-20s Korean woman, oval face, soft jaw, warm brown eyes, ..." \
  --engines moody_pro,krea,moody_wild \
  --per-engine 3 \
  --contact-sheet

# B) 고른 후보 → 패키지 + master 승인
python scripts/character_promote.py \
  --from characters/casts/heroine_v1_cast/candidates/xxx.png \
  --id mina_park_v2 \
  --name "Mina Park" \
  --appearance-prompt "..." \
  --cast heroine_v1_cast

# C) 일관 시트
python scripts/character_expand_sheets.py --id mina_park_v2 --sheets all_mvp
python scripts/character_approve.py --id mina_park_v2 --from refs/... --as expr_neutral
```

---

## 4. 디렉터리

```text
characters/
  casts/
    <cast_id>/
      brief.md              # optional notes
      manifest.json         # prompts, engines, candidate index, status
      candidates/
        <cast_id>__e{engine}__s{seed}__c{nn}.png
      contact_sheet.png
      shortlist.json        # optional human picks
  <character_id>/           # promote 후 정식 패키지
```

---

## 5. 구현 상태

| ID | 작업 | 상태 |
|----|------|------|
| CAST-0 | 본 설계 + 리서치 반영 | ✅ |
| CAST-1 | `lib/cast_pool.py` + cast 디렉터리 규약 | ✅ |
| CAST-2 | `character_cast_pool.py` multi-engine T2I | ✅ |
| CAST-3 | `character_promote.py` | ✅ |
| CAST-4 | contact sheet | ✅ |
| CAST-5 | InstantID / IPAdapter 시트 엔진 | ⬜ 후속 |
| CAST-6 | shot_compose multi-engine | ⬜ 후속 |

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초안: A/B/C 분리, 커뮤니티 패턴 반영, CLI MVP |
