# Still review (one-off)

Live IDs: `python scripts/review_media.py show still`

Open the image. Compare to the brief, not to “it looks like AI art.”

| ID | Pass | Fail 예 |
|----|------|---------|
| **S1_intent** | 요청한 동작·주체·장소가 보임 | medium 골목인데 얼굴 CU / 우산이 없음 |
| **S2_shot_size** | 샷 사이즈가 brief와 같음 | insert인데 전신, ECU인데 와이드 |
| **S3_identity** | 지정 인물이면 그 사람 | 다른 얼굴, 연령 붕괴 (캐릭 없을 땐 skip) |
| **S4_anatomy** | 손·발·사지 정상 | 여분 손가락, 접힌 발, 녹은 관절 |
| **S5_anti** | brief 금지항 없음 | 금지한 얼굴 CU / 발 클로즈업이 주인공 |
| **S6_junk_text** | 의도한 글자만 | 난잡한 워터마크, 깨진 간판 |
| S7_light | 빛·재질이 구체적 | 납작한 태그수프 룩 (막힘은 아님, 재작성 힌트) |

에피소드 키프레임은 이 표 대신 K1–K15 (`docs/image_cut_verification_gate.md`).
