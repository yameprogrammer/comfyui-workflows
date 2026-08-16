# Clip review (one-off)

Live IDs: `python scripts/review_media.py show clip`

Open first / mid / last. If last ≈ mid and nothing moved, that is freeze.

| ID | Pass | Fail 예 |
|----|------|---------|
| **C1_no_freeze** | 끝까지 모션 | 후반 정지, tpad로 길이 채움 |
| **C2_motion_matches** | 시킨 카메라/몸 동작 | push-in 인데 정지, 고개 돌림이 없음 |
| **C3_identity_hold** | 시작 스틸과 같은 사람 | 얼굴이 다른 사람으로 변함 |
| **C4_no_warp** | 형태 유지 | 손 녹음, 배경 모핑 |
| **C5_duration** | 요청 길이에 가깝고 패드 없음 | 2초 생성 후 침묵 패드로 5초 |

I2V 프롬프트가 얼굴·의상을 다시 쓰면 생성 전에 이미 실패다 (`generation-prompt`).

에피소드 클립은 C* 게이트 (`shot_qa_record --stage clip`).
