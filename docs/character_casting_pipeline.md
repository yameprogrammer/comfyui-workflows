# 캐릭터 창조 공정 — Production v1 (실무용)

- **작성일**: 2026-07-12  
- **상태**: **Production v1 READY** (A→B→C 한 줄로 실무 사용 가능)  
- **관련**: [character_impl_spec.md](character_impl_spec.md), Rule 6.2

---

## 0. 이게 “완성”인 범위

| 포함 (v1) | 미포함 (나중에) |
|-----------|-----------------|
| 다엔진 후보 풀 (Moody + Krea) | InstantID / IPAdapter |
| 컨택시트 · shortlist · status | 자동 얼굴 QA 점수 |
| 1장 promote → master_front 잠금 | 탐색 단계 LoRA 학습 |
| expand I2I 로 expression MVP | artbook 전용 고해상 파이프 고도화 |
| 오케스트레이터 `character_pipeline` | shot_compose 다엔진 |

**사람 게이트는 의도적으로 남김:** 후보 고르기, expression approve.

---

## 1. 공정 (고정)

```text
A cast     multi-engine T2I → characters/casts/<cast_id>/
B promote  pick → characters/<id>/ + approved/master_front.png
C expand   I2I sheets from master → refs/ + approve aliases
D video    shot_compose → I2V/SI2V  (기존, 본 문서 범위 밖)
```

커뮤니티 정합: **오디션(다모델) → 인간 선택 → 시트 공장(ref 고정)**.

---

## 2. 실무 치트시트 (복사해서 쓰기)

### 2.1 새 캐릭터 처음부터

```bash
# --- A. 탐색 풀 (Comfy 켜둘 것) ---
python scripts/character_cast_pool.py \
  --cast heroine_ep01_cast \
  --prompt "mid-20s Korean woman, oval face, soft jawline, warm brown eyes, shoulder-length dark brown wavy hair, natural skin, cinematic photoreal head-and-shoulders" \
  --engines moody_pro,krea \
  --per-engine 3

# 리뷰: characters/casts/heroine_ep01_cast/contact_sheet.png
# 또는
python scripts/character_status.py --cast heroine_ep01_cast

# 후보 찜 (선택)
python scripts/character_shortlist.py --cast heroine_ep01_cast \
  -f candidates/heroine_ep01_cast__emoody_pro__s....png

# --- B. 승격 (고른 파일 경로로) ---
python scripts/character_promote.py \
  --from characters/casts/heroine_ep01_cast/candidates/<PICK>.png \
  --id mina_cast_v1 \
  --name "Mina" \
  --cast heroine_ep01_cast \
  --profile video_ref

python scripts/character_status.py --id mina_cast_v1

# --- C. 일관 시트 (video_ref MVP = master 이미 있음 + expressions) ---
python scripts/character_expand_sheets.py \
  --id mina_cast_v1 \
  --sheets all_mvp \
  --engine i2i \
  --profile video_ref

# 생성 refs 중 고른 것을 approve (표정 등)
python scripts/character_approve.py --id mina_cast_v1 \
  --from refs/expression/<file>.png --as expr_neutral
# … expr_joy, expr_sad, expr_angry, expr_surprise, expr_think

python scripts/character_status.py --id mina_cast_v1
# missing_mvp=[] 이면 L2 MVP 완료 → shot_compose 가능
```

### 2.2 오케스트레이터 (계획 / 실행)

```bash
# 계획만
python scripts/character_pipeline.py --cast heroine_ep01_cast --id mina_cast_v1

# A만 실행
python scripts/character_pipeline.py --run --from cast --to cast \
  --cast heroine_ep01_cast -p "..." --engines moody_pro,krea --per-engine 2

# B 실행 (사람 픽 필수)
python scripts/character_pipeline.py --run --from promote --to promote \
  --from-image path/to/pick.png --id mina_cast_v1 --name "Mina" --cast heroine_ep01_cast

# C 실행
python scripts/character_pipeline.py --run --from expand --to expand \
  --id mina_cast_v1 --sheets all_mvp
```

### 2.3 이미 얼굴 하나만 있을 때 (풀 스킵)

```bash
python scripts/character_promote.py --from ./face.png --id hero_v1 --name "Hero"
python scripts/character_expand_sheets.py --id hero_v1 --sheets all_mvp --engine i2i
# approve expressions…
```

---

## 3. CLI 목록 (v1)

| 스크립트 | 단계 |
|----------|------|
| `character_cast_pool.py` | A |
| `character_shortlist.py` | A 보조 |
| `character_status.py` | A/B/C 상태 |
| `character_promote.py` | B |
| `character_expand_sheets.py` | C |
| `character_approve.py` | C 게이트 |
| `character_pipeline.py` | A–C 오케스트레이션 |
| `character_create.py` | (대안) 단일 엔진 패키지+후보 — 레거시/빠른 경로 |

엔진: `moody_real` `moody_pro` `moody_wild` `krea`

---

## 4. 완료 정의 (v1 Definition of Done)

- [x] cast → candidates + contact_sheet  
- [x] promote → package + `approved/master_front` + cores  
- [x] expand → expression 등 refs 생성  
- [x] approve → missing_mvp 소거 가능  
- [x] status 로 다음 액션 확인  
- [x] dry-run / pipeline plan  
- [ ] (선택) Comfy 실생성 풀 E2E 파일럿 캐릭터 — 운영 시 1회 돌리면 됨  

---

## 5. 리서치 반영 (요약)

| 패턴 | v1 적용 |
|------|---------|
| Multi-model casting | cast_pool engines |
| Human gate | shortlist + promote + approve |
| Sheet-first before video | expand before shot_compose |
| Ref lock after pick | master_front primary_ref |
| Contact sheet review | cast contact_sheet.png |
| IPAdapter/InstantID | 후속 C 엔진 |

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초안 A/B/C + CLI |
| 2026-07-12 | **Production v1**: status/shortlist/pipeline + 실무 SOP DoD |
