# 캐릭터 창조 공정 — Production v1 (실무용)

- **작성일**: 2026-07-12  
- **상태**: **Production v1 READY** (A→B→C 한 줄로 실무 사용 가능)  
- **관련**: [character_impl_spec.md](character_impl_spec.md), Rule 6.2

---

## 0. 이게 “완성”인 범위

| 포함 (v1+ 공정) | 코드만 유지 / 미포함 |
|----------------|----------------------|
| 다엔진 후보 풀 (Moody + Krea) | InstantID (별도 모델·노드) |
| 컨택시트 · shortlist · status | 자동 얼굴 QA 점수 |
| 1장 promote → master_front 잠금 | 탐색 단계 LoRA 학습 |
| expand 공정: **full_sheet** (head/turn/expr/costume/pose/props) | **ipadapter** — CLI 유지, **공정 SOP 미사용** |
| head/body turn: **Qwen multi-angles** (기본) | OpenPose CN turn — 레거시 폴백만 |
| `character_full_sheet.py` 원샷 + review grids | `video_ref` thin pack만으로 “시트 완성” 보고 금지 |

**사람 게이트는 의도적으로 남김:** 후보 고르기, expression approve.

---

## 1. 공정 (고정)

```text
A cast     multi-engine T2I → characters/casts/<cast_id>/
B promote  pick → characters/<id>/ + approved/master_front.png
B2 lock    wardrobe_default + wardrobe_alt1 + props_default  (bible, human gate)
C expand   **full_sheet** ordered industry pack
           master_full → design flats/props (off-body) → on-model costume
           → Qwen turns → expr/pose/props.hand
           CLI: character_full_sheet.py --run
D video    shot_compose → I2V/SI2V  (video_ref thin pack may be enough for shots)
```

커뮤니티 정합: **오디션 → 얼굴 → 의상/소품 잠금 → 디자인 플레이트(옷/소품 단독) → 착용 모델시트 → 영상 레퍼**.

### B2 의상·소품 잠금 (face 직후 필수)

```bash
python scripts/character_set_wardrobe.py --id X \
  --default "cream knit cardigan over white blouse, light wash jeans, white sneakers, small silver earrings" \
  --alt1 "beige trench coat over white blouse, dark trousers, sneakers" \
  --props "closed black compact umbrella held in right hand at realistic scale" \
  --lock
python scripts/character_set_wardrobe.py --id X --show
```

bible SSOT: `appearance.wardrobe_*`, `props_default`, `wardrobe_locked`.  
`character_full_sheet.py --run` 은 미잠금 시 중단 (비상: `--allow-unlocked-wardrobe`).

### C 캐릭터 시트 (공정 SOP — full_sheet)

```bash
# 원샷 (B2 이후) — 단계 순서 고정
python scripts/character_full_sheet.py --id X --run
# Phase0 master_full → B2.5 design (flat/callout/prop) → on-model costume
# → Qwen turns → expr/pose/props.hand

# 페이즈만
python scripts/character_full_sheet.py --id X --run --phases design
python scripts/character_full_sheet.py --id X --run --phases costume
python scripts/character_full_sheet.py --id X --run --phases turns
python scripts/character_full_sheet.py --id X --run --phases rest

# design_pack만 expand
python scripts/character_expand_sheets.py --id X --sheets design_pack --require-wardrobe

# 턴만 (body 소스 = costume_default 우선)
python scripts/character_qwen_turns.py --id X --mode both --approve
python scripts/character_full_sheet.py --id X --approve-only
# 리뷰: characters/<id>/exports/full_sheet/review_*.png
```

### C 실험 전용 (공정 밖 · 코드 유지)

```bash
# IP-Adapter face — 공정 치트시트에 넣지 않음
python scripts/character_expand_sheets.py --id X --sheets expression \
  --engine ipadapter --ipa-weight 0.72
# OpenPose 턴 폴백 (공정 기본 아님)
python scripts/character_expand_sheets.py --id X --sheets head,turnaround \
  --engine controlnet --ensure-fullbody
# video_ref thin only (NOT full sheet complete)
python scripts/character_expand_sheets.py --id X --profile video_ref --sheets all_mvp
```

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

# --- B2. 의상·소품 잠금 (풀시트 전 필수) ---
python scripts/character_set_wardrobe.py --id mina_cast_v1 \
  --default "..." --alt1 "..." --props "..." --lock

# --- C. 풀 캐릭터 시트 (full_sheet 공정) ---
python scripts/character_full_sheet.py --id mina_cast_v1 --run
# 검수: characters/mina_cast_v1/exports/full_sheet/review_FULL_PACKAGE.png
# missing_mvp=[] (profile=full_sheet) 이면 시트 공정 완료
# 영상만 급하면 이후 video_ref aliases로도 shot_compose 가능
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
| i2i_lock | C 공정 권장 identity (가중치 없이 항상 동작) |
| IPAdapter face | **코드·CLI 유지**, 공정 SOP **제외** (SD1.5 경로; ZIT 페어 아님) |

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-12 | 초안 A/B/C + CLI |
| 2026-07-12 | **Production v1**: status/shortlist/pipeline + 실무 SOP DoD |
| 2026-07-12 | C 공정 엔진 = i2i / i2i_lock only. ipadapter 기능 유지·SOP 제외 |
