# Audio review (one-off)

Live IDs: `python scripts/review_media.py show audio`

Do not pass by imagining the sound. Open `probe.json` + spectrogram.

| ID | Pass | Fail 예 |
|----|------|---------|
| **A1_duration** | 요청 길이 ±10% | 45초 요청인데 12초, 또는 침묵 패딩 |
| **A2_not_dead** | 실효 레벨 있음, 풀스케일 상수 PCM 아님 | 무음, ACE 쓰레기 PCM |
| **A3_bpm** | 추정 BPM이 brief와 맞음 (지정 시) | 90 요청인데 뚜렷이 다른 템포 |
| **A4_role_pure** | drums/bass/piano only 면 그 역할만 | “드럼만”인데 화성·보컬이 섞임 |
| **A5_key** | 지정 키/코드와 충돌 없음 | Am 침대 위에 C# 메이저 리드 |
| **A6_not_fullmix** | 솔로/스템 요청이면 믹스가 아님 | 피아노 솔로 요청인데 밴드 완곡 |

독립 T2A 스템을 겹치기 전에 A3·A4·A5가 깨지면 **그 레이어를 버린다.** 시계가 안 잠긴 레이어는 노래가 아니다.

완곡(MiniMax/ACE 믹스)은 A4/A6을 skip 하고 침대/완곡으로 판정한다.
