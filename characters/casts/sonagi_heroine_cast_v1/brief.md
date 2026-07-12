# Cast brief — sonagi_heroine_cast_v1

- **cast_id**: `sonagi_heroine_cast_v1`
- **purpose**: Style Core + A→B→C 공정 테스트 (소나기 뮤비 주인공)
- **look_id (Style Core)**: `cinematic_moody_v1` (approved)
- **engines**: moody_pro, krea
- **identity**: 미고정 — 사람 픽 후 promote

## Character intent (소나기 주인공)

| Field | Value |
|------|--------|
| Role | 노래「소나기」뮤비 주인공 / 1인 시네 초상 |
| Age | mid-20s |
| Presentation | female |
| Ethnicity | East Asian / Korean |
| Face | oval face, soft jawline, warm brown eyes, straight natural brows |
| Hair | shoulder-length dark brown soft waves |
| Skin | natural realistic texture |
| Distinctive | small mole under left eye (optional, candidate-dependent) |
| Mood | reserved, rainy-day melancholy warmth (cast 단계는 표정 soft neutral) |
| Wardrobe (cast) | simple black crew-neck — 얼굴 오디션 우선 |
| Forbidden | glasses, heavy tattoos, blonde, heavy makeup, busy BG |

## Process order (이 테스트)

1. **Look 지정** — `cinematic_moody_v1` ✅
2. **A cast** — 본 풀 후보 + contact_sheet
3. **사람 선택** — shortlist / promote 대상 파일 지정
4. **B promote** — `characters/<id>/` + master_front
5. **C expand** — `--engine i2i_lock` (공정 SOP; ipadapter 미사용)
6. **approve** expressions → missing_mvp=[]

## Notes

- 기존 `mina_park_v1` / `mina_cafe_ep01` 과 분리된 **새 캐스트**.
- 룩은 샷 조립(`shot_compose`) 시 주입; 캐스트 프롬프트에는 톤 접두만 약하게 포함.
