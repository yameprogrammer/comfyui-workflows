# 수정 요청 — character_full_sheet / InfiniteTalk (2026-07-30)

| 항목 | 내용 |
|------|------|
| **상태** | 🟢 **MOSTLY DONE** — 기능 핫픽스 반영 · 문서/패키지 정리 2026-07-30 |
| **우선순위** | 원 P0 블로커 해소 · 잔여 품질 항목 후순위 |
| **구현 계획** | [docs/superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md](superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md) |
| **보고 세션** | GREEN LIGHTER 쇼츠 MV (`D:\뮤직비디오 작업\GREEN LIGHTER`) |
| **캐릭터** | `green_lighter_idol_v1` |
| **에피소드** | `stories/green_lighter_ep01` |
| **관련 failure notes** | `FN-20260729-001` (mitigated) · `FN-20260729-002` (fixed) |
| **작성** | Grok agent session 2026-07-29~30 |

---

## 0. 현재 한 줄 (2026-07-30 말 기준)

1. **InfiniteTalk** — `WanVideoWrapper` 재활성 + `VHS_LoadAudio` + `tool_health` / queue preflight. 스모크 OK. status=`ready`.  
2. **full_sheet** — auto-approve 기본 OFF · framing QA · sheet-role core · costume 본선 **`krea2_identity`** (master_front → 전신).  
3. **키프레임** — 계속 `krea2_identity_edit` + master_front (9:16). 립싱크 기본 `ltx23_ia2v`.

---

## 1. InfiniteTalk — 조치 완료

| 항목 | 결과 |
|------|------|
| 원인 | `ComfyUI-WanVideoWrapper.disabled` + 오디오 노드 `JWLoadAudio` numba 크래시 |
| 수정 | Wrapper 재활성 · `VHS_LoadAudio` · `lib/s2v_backend_health.py` · `scripts/tool_health.py` |
| 스모크 | `stories/_tool_smoke/infinitetalk_smoke.mp4` · `video_backends.infinitetalk=ready` |
| FN | `FN-20260729-002` **fixed** |

```bash
python scripts/tool_health.py --backend infinitetalk
python scripts/generate_s2v.py --backend infinitetalk -i face.png -a drive.wav -o out.mp4
```

---

## 2. character_full_sheet / expand — 조치 완료

| 항목 | 결과 |
|------|------|
| core 정책 | `lib/sheet_prompt_policy.py` — head-and-shoulders 전신 주입 제거 |
| size | plain i2i에 width/height 전달 · CN `largest_size=max(w,h)` |
| auto L2 | `character_full_sheet` 기본 bulk auto-approve **OFF** (`--auto-approve` 옵트인) |
| costume 본선 | `engine=krea2_identity` · source=`master_front` · 2:3 · ref_boost 5.5 |
| fullbody master | `lib/fullbody_source.py` — krea2 from face 우선 · feet QA · T2I 폴백 |
| mid-lock | costume.default **feet_score 최고 candidate** 만 approve (마지막 덮어쓰기 금지) |
| OpenPose | 몸/포즈 폴백 (`--engine controlnet`) — 얼굴 SSOT 아님 |
| FN | `FN-20260729-001` **mitigated** |

```bash
python scripts/character_expand_sheets.py --id X --only costume.default --require-wardrobe
python scripts/character_full_sheet.py --id X --run   # bulk approve 없음
python scripts/character_full_sheet.py --id X --run --auto-approve  # 옵트인
```

---

## 3. green_lighter_idol_v1 패키지

| 항목 | 내용 |
|------|------|
| status | **`pending_review`** (조용히 `approved` 되던 것 정정) |
| 신뢰 | `approved/master_front.png` · `approved/costume_default.png` (krea2_identity 계열) |
| 비신뢰 | 구 OpenPose 전용 얼굴 드리프트 컷 · 구 1024×576 i2i costume · footwear face-CU |

---

## 4. 수락 기준

- [x] InfiniteTalk: 스모크 + preflight  
- [x] full_sheet: gates + krea2_identity costume  
- [x] 카탈로그/backends 정합 (지속 갱신)  
- [x] FN-001 / 002 처리  
- [x] process.md 이력  
- [x] mid-lock best-candidate  
- [x] fullbody master krea2 경로  
- [ ] (선택) full_pack 전 페이즈 e2e · footwear 순수 크롭 · dual-ref 얼굴 스왑  

---

## 5. 비범위

- GREEN LIGHTER 가창 타이밍 · 자막 · 1080  
- 캐릭터 LoRA 학습  
- dual-ref 완전 face-swap (본선 아님)  
