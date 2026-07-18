# 댄스 챌린지 쇼츠 공정 설계 (초안 · 미착수)

- **작성**: 2026-07-14  
- **상태**: 📋 풀 에피 공정은 백로그 · ✅ **v1 원샷 도구** `generate_dance_ref` (2026-07-18)  
- **원샷 CLI:** [workflows/human/dance_ref/AGENT_GUIDE.md](../workflows/human/dance_ref/AGENT_GUIDE.md) · `python scripts/generate_dance_ref.py`  

- **목적**: 특정 댄스 챌린지를 **레퍼런스**로 두고, 채널 캐릭터로 정교한 9:16 쇼츠를 **반복 가능한 공장 파이프**로 만들기  
- **관련**: [agent_video_tooling_todo.md](agent_video_tooling_todo.md) P3-1 · [audio_motion_production_modes.md](audio_motion_production_modes.md) · [production_asset_pipeline.md](production_asset_pipeline.md)

---

## 0. 합의된 이해

| 말 | 의미 |
|----|------|
| 공정 파이프라인을 설계·구현한다 | 레퍼 댄스 → 포즈/구간 → 캐릭 입히기 → 모션 → 음악 락 → 조립을 **레시피화** |
| 정교한 댄스 챌린지 쇼츠 | 토킹 에피처럼 **체계적으로** 뽑고, 레퍼 추종·박자·캐릭 일관성을 목표로 함 |
| 상한 | 모델·손발·비트 동기 한계는 남음. 파이프 = “정교하게 갈 **길**” |

**하지 않음 (이 모드)**

- 기존 story/토킹 공정을 댄스 모드로 덮어쓰기  
- 유명 챌린지 **저작권 무시** 복제 (레퍼 사용 시 정책 확인)  
- 클라우드 댄스 생성기로 본선 전면 대체 (선택 실험은 별도)

---

## 1. production_mode 제안

```text
production_mode = dance_challenge   # story / music_video 와 병행
```

| story (지금 카페) | dance_challenge |
|-------------------|-----------------|
| TTS + SI2V 립 중심 | **음악 + 몸 모션** 중심 |
| 시놉 대사 샷 | 레퍼 안무 구간 샷 |
| InfiniteTalk hero | I2V / 포즈 가이드 모션 (립 거의 없음) |
| BGM under dialogue | **음악 락** (볼륨·루프·길이 = 챌린지 훅) |

---

## 2. 목표 파이프 (스테이지)

```text
0  brief: 챌린지 이름, 레퍼 URL/파일, 훅 길이(초), 캐릭/룩/로케
1  ingest: 레퍼 영상 정규화 (9:16 또는 중앙 크롭 가이드)
2  analyze: 비트/구간 분해, 키 포즈 프레임 추출 (OpenPose 등)
3  cast: 기존 character pack 재사용 또는 댄스 의상 lock
4  keyframes: 포즈별 스틸 — shot_compose / ControlNet 포즈 락
5  motion: 구간별 I2V (또는 포즈 시퀀스 제어 WF) · 필요 시 last-frame 체인
6  audio: 챌린지 BGM / 루프 · (선택) 비트 마커 메타
7  assemble: hardcut 또는 비트 정렬 컷 · 자막 훅 옵션
8  deliver: 1080 upscale · export_to_workspace
9  gate: clip_status 컷 검수 (몸 붕괴·비트 어긋남 육안)
```

---

## 3. 입력 계약 (초안)

| 필드 | 설명 |
|------|------|
| `reference_dance` | 로컬 경로 또는 유저 제공 파일 |
| `hook_sec` | 목표 길이 (예 8 / 12 / 15) |
| `character_id` / `look_id` / `location_id` | 자산 삼각형 |
| `choreography_notes` | 필수 동작 키워드 |
| `music_path` 또는 `generate_bgm` | 음악 소스 |
| `pose_backend` | none / openpose / … (구현 시) |

`shots.json` 확장 예:

```json
{
  "production_mode": "dance_challenge",
  "mix_policy": "music_locked",
  "dance": {
    "reference": "refs/dance_challenge_01.mp4",
    "hook_sec": 12
  }
}
```

---

## 4. 구현 백로그 (착수 시)

| ID | 작업 | 우선 |
|----|------|------|
| D0 | 본 문서 확정 + `production_mode` enum 문서화 | P3 |
| D1 | 레퍼 → 키 포즈 프레임 추출 CLI (ffmpeg + 선택 pose) | P3 |
| D2 | 포즈 락 키프레임 레시피 (ControlNet / I2I) | P3 |
| D3 | 댄스 구간 I2V 프리셋 (fps/steps/motion 템플릿) | P3 |
| D4 | 음악 락 assemble (`music_locked` + 훅 길이) | P3 |
| D5 | (고급) 비트 마커·구간 자동 샷 분할 | P4 |
| D6 | (고급) 포즈 시퀀스 제어 I2V/V2V WF | P4 |

토킹 파이프 **P0–P1 안정화 이후** 착수 권장 (`agent_video_tooling_todo` 스프린트 A–C 다음).

---

## 5. 성공 기준 (나중에 검수)

- [ ] 같은 캐릭으로 8–15초 댄스 훅 1편이 **문서 순서만 따라** 재현 가능  
- [ ] 레퍼 대비 “같은 챌린지로 읽히는” 포즈 키 3개 이상 일치 (육안)  
- [ ] 음악과 대략 동기 (완벽 프레임 단위 불필요, 훅 루프 가능)  
- [ ] 토킹 에피 공정·기본값과 **충돌 없음**

---

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-14 | 초안. 유저 합의: 별 장르 파이프 설계로 정교한 댄스 챌린지 쇼츠 목표. 구현 전 기록. |
